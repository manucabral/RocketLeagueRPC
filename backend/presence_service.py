"""
Presence service for composing and dispatching updates based on live match state.
"""

from __future__ import annotations

from typing import Any

from .presence_payload import compose_presence_args


class PresenceService:
    """Compose and dispatch Discord presence from tracker match state."""

    def __init__(
        self,
        *,
        rpc_service: Any,
        overtime_details_text: str = "Overtime",
        overtime_state_prefix: str = "+",
    ) -> None:
        self._rpc_service = rpc_service
        self._overtime_details_text = str(overtime_details_text or "Overtime")
        self._overtime_state_prefix = str(overtime_state_prefix or "+")
        self._match_start_epoch_sec: int | None = None
        self._match_start_guid: str | None = None
        self._overtime_started_epoch_sec: int | None = None
        self._last_target_name: str | None = None
        self._last_target_platform: str | None = None

    def set_last_target(self, name: str | None, platform: str | None) -> None:
        """Update the cached last-seen player name and platform.

        Only non-empty values replace the stored ones; ``None`` or empty strings
        are ignored so the last valid values are preserved.

        Args:
            name: Player display name, or ``None`` to leave unchanged.
            platform: Platform identifier (e.g. ``"epic"``), or ``None``.
        """
        if name:
            self._last_target_name = str(name)
        if platform:
            self._last_target_platform = str(platform)

    def reset_match_memory(self) -> None:
        """Clear stored match start time and GUID used for timer presence."""
        self._match_start_epoch_sec = None
        self._match_start_guid = None
        self._overtime_started_epoch_sec = None

    def apply_now(
        self,
        *,
        discord_connected: bool,
        view: dict[str, Any] | None,
        in_match: bool,
        cfg: dict[str, Any],
        match_guid: str | None,
    ) -> None:
        """Compose a presence payload and send it to Discord if connected.

        Does nothing when *discord_connected* is ``False``.

        Args:
            discord_connected: Whether the Discord RPC client is currently open.
            view: Live match view dict, or ``None`` when not in a match.
            in_match: Whether the player is currently in a match.
            cfg: Presence feature-toggle mapping.
            match_guid: Unique identifier for the current match, used to track
                the match start time for the elapsed timer.
        """
        if not discord_connected:
            return
        args = self.compose_args(
            view=view if in_match else None,
            in_match=in_match,
            cfg=cfg,
            match_guid=match_guid,
        )
        self._rpc_service.send_presence(args)

    def compose_args(
        self,
        view: dict[str, Any] | None,
        *,
        in_match: bool,
        cfg: dict[str, Any],
        match_guid: str | None,
    ) -> dict[str, Any]:
        """Build the presence payload dict from current match state.

        Also updates the internal match-start epoch and GUID used for the
        elapsed-time timer.

        Args:
            view: Live match view dict, or ``None`` when not in a match.
            in_match: Whether the player is currently in a match.
            cfg: Presence feature-toggle mapping.
            match_guid: Unique identifier for the current match.

        Returns:
            A dict suitable for passing to ``DiscordRPCService.send_presence``.
        """
        (
            args,
            self._match_start_epoch_sec,
            self._match_start_guid,
            self._overtime_started_epoch_sec,
        ) = compose_presence_args(
            view=view,
            in_match=in_match,
            cfg=cfg,
            current_guid=match_guid,
            match_start_epoch_sec=self._match_start_epoch_sec,
            match_start_guid=self._match_start_guid,
            overtime_started_epoch_sec=self._overtime_started_epoch_sec,
            overtime_details_text=self._overtime_details_text,
            overtime_state_prefix=self._overtime_state_prefix,
            last_target_platform=self._last_target_platform,
            last_target_name=self._last_target_name,
        )
        return args
