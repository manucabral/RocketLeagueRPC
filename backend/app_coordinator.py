"""
Coordinator for managing the application's state and interactions.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import threading
from typing import Any, Callable

from .config import config
from .discord_service import DiscordRPCService
from .logger import get_log_level, logger, set_log_level
from .presence_service import PresenceService
from .presence_settings_service import PresenceSettingsService
from .stats_api_config import get_stats_api_status, set_stats_api_enabled
from .tracker import RLStatsTracker


class _CoordinatorLogBuffer:
    """Thread-safe ring buffer of timestamped coordinator debug lines."""

    def __init__(self, maxlen: int = 250) -> None:
        self._lock = threading.Lock()
        self._lines: deque[str] = deque(maxlen=maxlen)

    def append(self, line: str) -> None:
        """
        Prepend a UTC ISO timestamp and append the line to the buffer.

        Args:
            line: The log message to store.
        """
        stamped = f"[{datetime.now(timezone.utc).isoformat()}] {line}"
        with self._lock:
            self._lines.append(stamped)

    def snapshot(self) -> list[str]:
        """Return a point-in-time copy of all buffered log lines."""
        with self._lock:
            return list(self._lines)


class _CoordinatorState:
    """Thread-safe container for tracker and Discord state snapshots."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tracker_state: dict[str, Any] = {}
        self._discord_state: dict[str, Any] = {
            "connected": False,
            "client_id": None,
            "last_error": None,
            "reconnecting": False,
        }

    def update_tracker(self, state: dict[str, Any]) -> None:
        """
        Replace the stored tracker state with a shallow copy of *state*.

        Args:
            state: Latest tracker state dict from ``RLStatsTracker``.
        """
        with self._lock:
            self._tracker_state = dict(state)

    def update_discord(self, state: dict[str, Any]) -> None:
        """
        Replace the stored Discord state with a shallow copy of *state*.

        Args:
            state: Latest Discord state dict from ``DiscordRPCService``.
        """
        with self._lock:
            self._discord_state = dict(state)

    def tracker_snapshot(self) -> dict[str, Any]:
        """Return a point-in-time shallow copy of the tracker state."""
        with self._lock:
            return dict(self._tracker_state)

    def discord_connected(self) -> bool:
        """Return whether the Discord RPC client is currently connected."""
        with self._lock:
            return bool(self._discord_state.get("connected"))

    def build_live_state(
        self,
        *,
        presence_config: dict[str, Any],
        extra_logs: list[str],
    ) -> dict[str, Any]:
        """
        Assemble the unified live-state dict sent to the frontend.

        Args:
            presence_config: Current presence feature-toggle mapping.
            extra_logs: Additional log lines from the coordinator log buffer.

        Returns:
            The merged live-state dict.
        """
        with self._lock:
            tracker_state = dict(self._tracker_state)
            discord_state = dict(self._discord_state)
        tracker_logs = list(tracker_state.get("debug_logs", []))
        tracker_state["discord"] = discord_state
        tracker_state["presence_config"] = dict(presence_config)
        tracker_state["debug_logs"] = (tracker_logs + extra_logs)[-250:]
        tracker_state["log_level"] = get_log_level()
        return tracker_state


class AppCoordinator:
    """Coordinate Rocket League tracker, Discord RPC, and frontend-facing state."""

    def __init__(
        self,
        *,
        tracker_factory: Callable[..., RLStatsTracker] = RLStatsTracker,
        discord_service_factory: Callable[..., DiscordRPCService] = DiscordRPCService,
        presence_service_factory: Callable[..., PresenceService] = PresenceService,
        settings_service_factory: Callable[..., PresenceSettingsService] = PresenceSettingsService,
    ) -> None:
        self._logs = _CoordinatorLogBuffer()
        self._state = _CoordinatorState()
        self._settings_service = settings_service_factory(config.data_dir)
        self._tracker = tracker_factory(on_state_change=self._on_tracker_state_change)
        self._state.update_tracker(self._tracker.get_state())
        self._discord_service = discord_service_factory(
            on_state_change=self._on_discord_state_change,
            on_log=self._log,
            on_connected=self._on_discord_connected,
        )
        self._presence_service = presence_service_factory(
            rpc_service=self._discord_service,
            overtime_details_text=config.overtime_details_text,
            overtime_state_prefix=config.overtime_state_prefix,
        )

    def connect_tracker(self) -> dict[str, Any]:
        """Connect the stats tracker and return the updated live state."""
        self._state.update_tracker(self._tracker.connect())
        return self.get_live_state()

    def disconnect_tracker(self) -> dict[str, Any]:
        """Disconnect the stats tracker and return the updated live state."""
        self._state.update_tracker(self._tracker.disconnect())
        return self.get_live_state()

    def connect_discord_rpc(
        self,
        max_tries: int = 1,
        retry_delay_seconds: float = 1.0,
    ) -> dict[str, Any]:
        """
        Attempt to connect to Discord RPC and return the updated live state.

        Args:
            max_tries: Maximum number of connection attempts.
            retry_delay_seconds: Seconds to wait between attempts.

        Returns:
            The full live state dict after the connection attempt.
        """
        self._discord_service.connect(max_tries, retry_delay_seconds)
        return self.get_live_state()

    def disconnect_discord_rpc(self) -> dict[str, Any]:
        """Disconnect from Discord RPC and return the updated live state."""
        self._discord_service.disconnect()
        return self.get_live_state()

    def debug_discord_ipc(self) -> dict[str, Any]:
        """Run the Discord IPC debug probe and return the updated live state."""
        self._discord_service.debug_ipc()
        return self.get_live_state()

    def get_presence_config(self) -> dict[str, Any]:
        """Return the active presence feature-toggle configuration."""
        return self._settings_service.get_config()

    def set_presence_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """
        Persist a new presence configuration and push it to Discord.

        Args:
            cfg: Mapping of presence feature keys to boolean toggle values.

        Returns:
            The full live state dict after applying the new configuration.
        """
        self._settings_service.set_config(cfg)
        self._log("presence config updated")
        self._apply_presence_from_tracker_state()
        return self.get_live_state()

    def list_presence_presets(self) -> list[str]:
        """Return a sorted list of saved presence preset names."""
        return self._settings_service.list_presets()

    def save_presence_preset(
        self, name: str, cfg: dict[str, Any] | None = None, overwrite: bool = False
    ) -> dict[str, Any]:
        """
        Save a presence configuration preset.

        Args:
            name: Human-readable preset name.
            cfg: Configuration to save; defaults to the currently active config.
            overwrite: When ``True``, replace an existing preset with the same name.

        Returns:
            A dict with ``"name"`` and ``"config"`` keys for the saved preset.
        """
        payload = cfg if cfg is not None else self._settings_service.get_config()
        saved = self._settings_service.save_preset(
            name=name,
            cfg=payload,
            overwrite=overwrite,
        )
        self._log(f"preset saved: {name}")
        return {"name": name.strip(), "config": saved}

    def load_presence_preset(self, name: str) -> dict[str, Any]:
        """
        Load a saved preset, make it active, and return the updated live state.

        Args:
            name: Name of the preset to load.

        Returns:
            The full live state dict after applying the preset.
        """
        cfg = self._settings_service.load_preset(name)
        return self.set_presence_config(cfg)

    def delete_presence_preset(self, name: str) -> dict[str, Any]:
        """
        Delete a saved presence preset by name.

        Args:
            name: Name of the preset to delete.

        Returns:
            A dict with a ``"deleted"`` key containing the stripped preset name.
        """
        self._settings_service.delete_preset(name)
        self._log(f"preset deleted: {name}")
        return {"deleted": name.strip()}

    def get_live_state(self) -> dict[str, Any]:
        """Return the current aggregated live state for the frontend."""
        return self._state.build_live_state(
            presence_config=self._settings_service.get_config(),
            extra_logs=self._logs.snapshot(),
        )

    def get_stats_api_status(self) -> dict[str, Any]:
        """Return Rocket League StatsAPI config status."""
        return get_stats_api_status()

    def set_stats_api_enabled(self, enabled: bool) -> dict[str, Any]:
        """Enable or disable Rocket League StatsAPI config when available."""
        status = set_stats_api_enabled(bool(enabled))
        self._log(
            "stats api enabled"
            if status.get("found") and status.get("enabled")
            else "stats api disabled" if status.get("found") else "stats api config not found"
        )
        return status

    def get_log_level(self) -> str:
        """Return the current logger level name."""
        return get_log_level()

    def set_log_level(self, level_name: str) -> dict[str, Any]:
        """Update application log verbosity and return live state."""
        previous = get_log_level()
        set_log_level(level_name)
        current = get_log_level()
        self._log(f"log level changed: {previous} -> {current}")
        return self.get_live_state()

    def shutdown(self) -> None:
        """Shut down the tracker and disconnect from Discord RPC."""
        self._tracker.shutdown()
        self._discord_service.disconnect()

    def _on_tracker_state_change(self, state: dict[str, Any]) -> None:
        """
        Handle a tracker state-change notification.

        Updates the stored tracker state, propagates the last-seen target to the
        presence service, and triggers a presence refresh for relevant events.

        Args:
            state: Latest state dict emitted by ``RLStatsTracker``.
        """
        self._state.update_tracker(state)
        last_target = state.get("last_target") or {}
        self._presence_service.set_last_target(
            last_target.get("name"),
            last_target.get("platform"),
        )
        last_event = state.get("last_event")
        if last_event == "MatchDestroyed":
            self._presence_service.reset_match_memory()
        if last_event in {"UpdateState", "MatchEnded", "MatchDestroyed"}:
            self._apply_presence_from_snapshot(state)

    def _on_discord_state_change(self, state: dict[str, Any]) -> None:
        """
        Handle a Discord state-change notification.

        Args:
            state: Latest state dict emitted by ``DiscordRPCService``.
        """
        self._state.update_discord(state)

    def _on_discord_connected(self) -> None:
        """Push the current presence immediately after Discord reconnects."""
        self._apply_presence_from_tracker_state(force_discord_connected=True)

    def _apply_presence_from_tracker_state(self, *, force_discord_connected: bool = False) -> None:
        """
        Read the latest tracker snapshot and push presence to Discord.

        Args:
            force_discord_connected: When ``True``, skip the connected-state
                check and always attempt to send presence.
        """
        self._apply_presence_from_snapshot(
            self._state.tracker_snapshot(),
            force_discord_connected=force_discord_connected,
        )

    def _apply_presence_from_snapshot(
        self,
        state: dict[str, Any],
        *,
        force_discord_connected: bool = False,
    ) -> None:
        """
        Compute and dispatch a Discord presence update from a state snapshot.

        Args:
            state: Tracker state dict to derive the presence payload from.
            force_discord_connected: When ``True``, treat Discord as connected
                regardless of the cached connection flag.
        """
        self._presence_service.apply_now(
            discord_connected=force_discord_connected or self._state.discord_connected(),
            view=state.get("live_match_view"),
            in_match=bool(state.get("in_match")),
            cfg=self._settings_service.get_config(),
            match_guid=state.get("match_guid"),
        )

    def _log(self, line: str) -> None:
        """
        Append a line to the coordinator log buffer and emit a debug log.

        Args:
            line: The message to record.
        """
        self._logs.append(line)
        logger.debug("coordinator: %s", line)
