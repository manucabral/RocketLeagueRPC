"""
RLStatsTracker for reading Rocket League events and exposing tracker-only state.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from .constants import MAX_CONNECT_TRIES, TRACKED_EVENTS
from .live_match import build_live_match_view
from .logger import logger


class RLStatsTracker:
    """Read Rocket League events and expose tracker-only state."""

    def __init__(
        self,
        *,
        on_state_change: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._on_state_change = on_state_change
        self._lock = threading.Lock()
        self._running = False
        self._should_connect = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._debug_logs: deque[str] = deque(maxlen=250)
        self._connect_attempts = 0
        self._state: dict[str, Any] = {
            "connected": False,
            "listening": False,
            "requested": False,
            "connect_attempts": 0,
            "max_connect_tries": MAX_CONNECT_TRIES,
            "in_match": False,
            "match_guid": None,
            "winner_team_num": None,
            "last_event": None,
            "last_update": None,
            "last_error": None,
            "last_update_state": None,
            "live_match_view": None,
            "last_target": {"name": None, "platform": None},
            "errors": [],
        }

    def connect(self) -> dict[str, Any]:
        """Request a tracker connection and start the background loop if needed.

        Returns:
            The current tracker state dict.
        """
        with self._lock:
            self._should_connect = True
            self._state["requested"] = True
            self._state["last_error"] = None
            self._connect_attempts = 0
            self._state["connect_attempts"] = 0
        self._ensure_thread()
        self._log("connect requested")
        self._notify_state_change()
        return self.get_state()

    def disconnect(self) -> dict[str, Any]:
        with self._lock:
            self._should_connect = False
            self._state["requested"] = False
            self._state["connected"] = False
            self._state["listening"] = False
        self._log("disconnect requested")
        self._notify_state_change()
        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "connected": self._state["connected"],
                "listening": self._state["listening"],
                "requested": self._state["requested"],
                "connect_attempts": self._state["connect_attempts"],
                "max_connect_tries": self._state["max_connect_tries"],
                "in_match": self._state["in_match"],
                "match_guid": self._state["match_guid"],
                "winner_team_num": self._state["winner_team_num"],
                "last_event": self._state["last_event"],
                "last_update": self._state["last_update"],
                "last_error": self._state["last_error"],
                "last_update_state": self._state["last_update_state"],
                "live_match_view": self._state["live_match_view"],
                "last_target": dict(self._state["last_target"]),
                "errors": list(self._state["errors"]),
                "debug_logs": list(self._debug_logs),
            }

    def shutdown(self) -> None:
        self._running = False
        self._stop_event.set()

    def _ensure_thread(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="rlstats-tracker")
        self._thread.start()

    def _run_loop(self) -> None:
        try:
            asyncio.run(self._supervise())
        except Exception:
            logger.exception("RLStatsTracker crashed")
            self._push_error("tracker_crashed")

    async def _supervise(self) -> None:
        while self._running and not self._stop_event.is_set():
            if not self._should_connect:
                await asyncio.sleep(0.2)
                continue
            try:
                await self._listen_session()
                self._set_connect_attempts(0)
            except Exception as exc:
                attempt = self._increment_connect_attempts()
                self._set_flags(connected=False, listening=False)
                self._set_last_error(str(exc))
                self._log(f"connection attempt {attempt}/{MAX_CONNECT_TRIES} failed: {exc}")
                logger.warning(
                    "connnection attempt %s/%s failed: %s",
                    attempt,
                    MAX_CONNECT_TRIES,
                    exc,
                )
                self._push_error("connection_lost")
                if attempt >= MAX_CONNECT_TRIES:
                    self._stop_requested_connect()
                    self._set_last_error(
                        f"Could not connect to StatsClient after {MAX_CONNECT_TRIES} "
                        "attempts; manual reconnect required"
                    )
                    self._log(
                        "max connect tries reached, stopping auto-connect "
                        "and waiting manual reconnect"
                    )
                    logger.error(
                        "Reached max connect tries (%s), "
                        "auto-connect stopped until manual reconnect",
                        MAX_CONNECT_TRIES,
                    )
                    self._notify_state_change()
                    continue
                self._notify_state_change()
                await asyncio.sleep(2)

    async def _listen_session(self) -> None:
        from rlstatsapi import StatsClient

        client = StatsClient(reconnect=False, connect_timeout=3.0)
        client.on_any(self._on_event)
        await client.connect()

        deadline = asyncio.get_running_loop().time() + 4.0
        while not client.is_connected:
            if asyncio.get_running_loop().time() >= deadline:
                await client.disconnect()
                raise TimeoutError("StatsClient did not establish TCP connection in time")
            await asyncio.sleep(0.05)

        self._set_flags(connected=True, listening=True)
        self._set_last_error(None)
        self._set_connect_attempts(0)
        self._log("connected and listening")
        self._notify_state_change()

        try:
            while self._running and self._should_connect and not self._stop_event.is_set():
                if not client.is_connected:
                    raise ConnectionError("StatsClient TCP connection lost")
                await asyncio.sleep(0.25)
        finally:
            await client.disconnect()
            self._set_flags(connected=False, listening=False)
            self._log("session ended")
            self._notify_state_change()

    def _on_event(self, msg: Any) -> None:
        event = getattr(msg, "event", "Unknown")
        raw_data = getattr(msg, "data", {})
        data = self._normalize_data(raw_data)
        should_dispatch = False

        with self._lock:
            self._state["last_event"] = event
            self._state["last_update"] = datetime.now(timezone.utc).isoformat()

            if event not in TRACKED_EVENTS:
                should_dispatch = False
            elif event == "MatchCreated":
                self._state["in_match"] = True
                self._state["winner_team_num"] = None
                self._state["match_guid"] = data.get("MatchGuid") or self._state["match_guid"]
                self._log("event=MatchCreated")
                should_dispatch = True
            elif event == "MatchInitialized":
                self._state["in_match"] = True
                self._state["winner_team_num"] = None
                self._state["match_guid"] = data.get("MatchGuid") or self._state["match_guid"]
                self._log("event=MatchInitialized")
                should_dispatch = True
            elif event == "MatchDestroyed":
                self._state["in_match"] = False
                self._state["match_guid"] = None
                self._state["winner_team_num"] = None
                self._state["last_update_state"] = None
                self._state["live_match_view"] = None
                self._log("event=MatchDestroyed")
                should_dispatch = True
            elif event == "MatchEnded":
                self._state["in_match"] = False
                self._state["winner_team_num"] = data.get("WinnerTeamNum")
                self._state["match_guid"] = data.get("MatchGuid") or self._state["match_guid"]
                self._log("event=MatchEnded")
                should_dispatch = True
            elif event == "UpdateState":
                self._state["in_match"] = True
                self._state["match_guid"] = data.get("MatchGuid") or self._state["match_guid"]
                self._state["last_update_state"] = data
                self._state["live_match_view"] = build_live_match_view(data)
                live = self._state["live_match_view"] or {}
                self._state["last_target"] = {
                    "name": live.get("player_name") or self._state["last_target"]["name"],
                    "platform": live.get("player_platform")
                    or self._state["last_target"]["platform"],
                }
                self._log("event=UpdateState")
                should_dispatch = True

        if should_dispatch:
            self._notify_state_change()

    def _normalize_data(self, raw_data: Any) -> dict[str, Any]:
        if raw_data is None:
            return {}
        if isinstance(raw_data, dict):
            return raw_data
        if isinstance(raw_data, str):
            try:
                parsed = json.loads(raw_data)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {}

    def _set_flags(self, *, connected: bool, listening: bool) -> None:
        with self._lock:
            self._state["connected"] = connected
            self._state["listening"] = listening

    def _set_last_error(self, message: str | None) -> None:
        with self._lock:
            self._state["last_error"] = message

    def _set_connect_attempts(self, attempts: int) -> None:
        with self._lock:
            self._connect_attempts = attempts
            self._state["connect_attempts"] = attempts

    def _increment_connect_attempts(self) -> int:
        with self._lock:
            self._connect_attempts += 1
            self._state["connect_attempts"] = self._connect_attempts
            return self._connect_attempts

    def _stop_requested_connect(self) -> None:
        with self._lock:
            self._should_connect = False
            self._state["requested"] = False

    def _push_error(self, code: str) -> None:
        with self._lock:
            self._state["errors"].append(
                {"code": code, "at": datetime.now(timezone.utc).isoformat()}
            )
            self._state["errors"] = self._state["errors"][-20:]
        self._notify_state_change()

    def _log(self, line: str) -> None:
        stamped = f"[{datetime.now(timezone.utc).isoformat()}] {line}"
        self._debug_logs.append(stamped)
        logger.debug("tracker: %s", line)

    def _notify_state_change(self) -> None:
        self._dispatch_snapshot(self.get_state())

    def _dispatch_snapshot(self, snapshot: dict[str, Any]) -> None:
        if self._on_state_change is not None:
            self._on_state_change(snapshot)
