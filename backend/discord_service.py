"""
Service for managing Discord Rich Presence IPC connection, state, and presence updates.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

from .constants import DEFAULT_DISCORD_CLIENT_ID, MAX_CONNECT_TRIES
from .logger import logger
from .rpc import ClientRPC

_UNSET = object()


class DiscordRPCService:
    """Manage Discord RPC lifecycle, state snapshot, and reconnect behavior."""

    def __init__(
        self,
        *,
        on_state_change: Callable[[dict[str, Any]], None],
        on_log: Callable[[str], None],
        on_connected: Callable[[], None] | None = None,
        rpc_factory: Callable[..., ClientRPC] = ClientRPC,
    ) -> None:
        self._on_state_change = on_state_change
        self._on_log = on_log
        self._on_connected = on_connected
        self._rpc_factory = rpc_factory
        self._lock = threading.Lock()
        self._should_connect = False
        self._reconnect_inflight = False
        self._debug_inflight = False
        self._rpc: ClientRPC | None = None
        self._client_id: str | None = None
        self._last_error: str | None = None

    def connect(
        self,
        max_tries: int = 1,
        retry_delay_seconds: float = 1.0,
    ) -> dict[str, Any]:
        """Attempt to open and handshake a Discord IPC connection.

        Args:
            max_tries: Maximum number of connection attempts.
            retry_delay_seconds: Seconds to wait between failed attempts.

        Returns:
            The current connection state snapshot dict.
        """
        selected_id = DEFAULT_DISCORD_CLIENT_ID
        tries = max(1, int(max_tries))
        last_error: str | None = None
        with self._lock:
            self._should_connect = True

        for attempt in range(1, tries + 1):
            try:
                rpc = self._rpc_factory(client_id=selected_id, debug=True)
                if not rpc.connect():
                    raise RuntimeError("Discord IPC handshake failed")

                previous_rpc: ClientRPC | None = None
                with self._lock:
                    previous_rpc = self._rpc
                    self._rpc = rpc
                    self._client_id = selected_id
                    self._last_error = None
                if previous_rpc is not None and previous_rpc is not rpc:
                    try:
                        previous_rpc.close()
                    except Exception:
                        logger.exception("Failed to close replaced Discord RPC client")
                self._publish_state(connected=True, reconnecting=False, last_error=None)
                self._on_log(f"discord connected (attempt {attempt}/{tries})")
                if self._on_connected is not None:
                    self._on_connected()
                return self.snapshot()
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Discord RPC connect attempt %s/%s failed: %s", attempt, tries, exc)
                self._on_log(f"discord connect attempt {attempt}/{tries} failed: {exc}")
                if attempt < tries:
                    time.sleep(retry_delay_seconds)

        with self._lock:
            self._last_error = last_error
            self._client_id = selected_id
            self._rpc = None
        self._publish_state(
            connected=False,
            reconnecting=False,
            last_error=last_error,
            client_id=selected_id,
        )
        logger.error("Discord RPC connect failed after %s attempts", tries)
        return self.snapshot()

    def disconnect(self) -> dict[str, Any]:
        """Close the Discord IPC connection and publish a disconnected state.

        Returns:
            The current connection state snapshot dict.
        """
        with self._lock:
            self._should_connect = False
            self._reconnect_inflight = False
            rpc = self._rpc
            self._rpc = None
        try:
            if rpc is not None:
                rpc.close()
        except Exception as exc:
            logger.exception("Discord RPC close failed")
            with self._lock:
                self._last_error = str(exc)

        self._publish_state(connected=False, reconnecting=False)
        self._on_log("discord disconnected")
        return self.snapshot()

    def debug_ipc(self) -> dict[str, Any]:
        """Reconnect to Discord IPC and send a probe activity for diagnostics.

        Skips the probe if a debug run is already in progress.

        Returns:
            The current connection state snapshot dict.
        """
        with self._lock:
            if self._debug_inflight:
                self._on_log("discord ipc debug: skipped (already running)")
                return self.snapshot()
            self._debug_inflight = True
        try:
            self._on_log("discord ipc debug: restarting rpc client")
            self.disconnect()
            state = self.connect(
                max_tries=MAX_CONNECT_TRIES,
                retry_delay_seconds=1.0,
            )
            if not state.get("connected"):
                return state
            self.send_presence({"details": "Rocket League", "activity_type": None})
            self._on_log("discord ipc debug: probe activity sent")
            return self.snapshot()
        finally:
            with self._lock:
                self._debug_inflight = False

    def send_presence(self, args: dict[str, Any]) -> None:
        """Send a Rich Presence update to Discord via the open IPC connection.

        Silently does nothing when no RPC client is connected. On failure the
        client is marked disconnected and a background reconnect is scheduled.

        Args:
            args: Presence payload dict with optional keys: ``state``,
                ``details``, ``activity_type``, ``start_time``, ``end_time``,
                ``large_image``, ``large_text``, ``small_image``, ``small_text``.
        """
        with self._lock:
            rpc = self._rpc
        if rpc is None:
            return
        try:
            rpc.update(
                state=args.get("state"),
                details=args.get("details"),
                activity_type=args.get("activity_type"),
                start_time=args.get("start_time"),
                end_time=args.get("end_time"),
                large_image=args.get("large_image"),
                large_text=args.get("large_text"),
                small_image=args.get("small_image"),
                small_text=args.get("small_text"),
                buttons=None,
            )
            with self._lock:
                self._last_error = None
            self._publish_state(
                connected=True, reconnecting=self._reconnect_inflight, last_error=None
            )
        except Exception as exc:
            self._mark_disconnected(str(exc))
            self._schedule_reconnect()

    def _mark_disconnected(self, message: str | None) -> None:
        """Close the stale RPC client and publish a disconnected state snapshot.

        Args:
            message: Error message describing the disconnect reason, or ``None``.
        """
        with self._lock:
            rpc = self._rpc
            self._rpc = None
            self._last_error = message
        if rpc is not None:
            try:
                rpc.close()
            except Exception:
                logger.exception("Failed to close stale Discord RPC client")
        self._publish_state(
            connected=False,
            reconnecting=self._reconnect_inflight,
            last_error=message,
        )

    def _schedule_reconnect(self) -> None:
        """Spawn a background thread to reconnect Discord RPC if appropriate.

        Does nothing if a reconnect is already in-flight or if the service was
        deliberately disconnected.
        """
        with self._lock:
            if not self._should_connect or self._reconnect_inflight:
                return
            self._reconnect_inflight = True
        self._publish_state(connected=False, reconnecting=True)
        self._on_log("discord reconnect scheduled")

        def _worker() -> None:
            try:
                self.connect(
                    max_tries=MAX_CONNECT_TRIES,
                    retry_delay_seconds=1.0,
                )
            finally:
                with self._lock:
                    self._reconnect_inflight = False
                self._publish_state(reconnecting=False)

        threading.Thread(target=_worker, daemon=True, name="discord-rpc-reconnect").start()

    def snapshot(self) -> dict[str, Any]:
        """Return a thread-safe point-in-time snapshot of the connection state."""
        with self._lock:
            return {
                "connected": self._rpc is not None,
                "client_id": self._client_id,
                "last_error": self._last_error,
                "reconnecting": self._reconnect_inflight,
            }

    def _publish_state(
        self,
        *,
        connected: bool | None = None,
        client_id: str | None = None,
        last_error: str | None | object = _UNSET,
        reconnecting: bool | None = None,
    ) -> None:
        """Build a state snapshot, apply overrides, and call the state-change callback.

        Only the keyword arguments that are explicitly provided override the
        corresponding fields in the current snapshot; omitted arguments are left
        unchanged.

        Args:
            connected: Override for the ``connected`` field, if provided.
            client_id: Override for the ``client_id`` field, if provided.
            last_error: Override for the ``last_error`` field, if provided.
                Pass ``None`` to explicitly clear the error.
            reconnecting: Override for the ``reconnecting`` field, if provided.
        """
        snap = self.snapshot()
        if connected is not None:
            snap["connected"] = connected
        if client_id is not None:
            snap["client_id"] = client_id
        if last_error is not _UNSET:
            snap["last_error"] = last_error
        if reconnecting is not None:
            snap["reconnecting"] = reconnecting
        self._on_state_change(snap)
