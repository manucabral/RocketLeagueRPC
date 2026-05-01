"""
Presence payload composition logic for Discord Rich Presence updates.
"""

from __future__ import annotations

import time
from typing import Any

from .rpc import ActivityType


def compose_presence_args(
    *,
    view: dict[str, Any] | None,
    in_match: bool,
    cfg: dict[str, bool],
    current_guid: str | None,
    match_start_epoch_sec: int | None,
    match_start_guid: str | None,
    overtime_started_epoch_sec: int | None,
    overtime_details_text: str,
    overtime_state_prefix: str,
    last_target_platform: str | None,
    last_target_name: str | None,
) -> tuple[dict[str, Any], int | None, str | None, int | None]:
    """Compose presence arguments from view and config."""

    all_disabled = not any(cfg.values())
    args: dict[str, Any] = {
        "activity_type": ActivityType.PLAYING,
        "details": None,
        "state": None,
        "start_time": None,
        "end_time": None,
        "large_image": None,
        "large_text": None,
        "small_image": None,
        "small_text": None,
    }

    if all_disabled:
        args["details"] = "Rocket League"
        args["state"] = "Waiting"
        args["large_image"] = "rocket"
        return args, match_start_epoch_sec, match_start_guid, overtime_started_epoch_sec

    if not in_match or not view:
        args["details"] = "Rocket League"
        args["state"] = "Waiting"
        args["large_image"] = "rocket"
        if cfg["player_name"]:
            args["small_image"] = last_target_platform
            args["small_text"] = last_target_name
        return args, match_start_epoch_sec, match_start_guid, overtime_started_epoch_sec

    mode = view.get("mode")
    arena = view.get("arena")
    status = view.get("status")
    has_target = bool(view.get("has_target"))
    mode_lc = str(mode or "").strip().lower()
    is_xv0_mode = mode_lc.endswith("v0") and "v" in mode_lc
    is_training = mode_lc in {"training", "training online"} or is_xv0_mode
    training_label = (
        "Training Online" if mode_lc in {"training online"} or is_xv0_mode else "Training"
    )

    remaining_seconds_txt = None
    if isinstance(view.get("remaining_seconds"), int):
        remaining_seconds_txt = max(0, int(view["remaining_seconds"]))

    if is_training:
        if cfg["game_mode"]:
            if training_label == "Training Online" and remaining_seconds_txt is not None:
                args["details"] = f"{training_label} {remaining_seconds_txt}s"
            else:
                args["details"] = training_label
        else:
            args["details"] = "Rocket League"
    elif not has_target:
        if cfg["game_mode"]:
            args["details"] = f"{mode} | Goal Replay" if mode else "Goal Replay"
            args["large_image"] = "rocket"
        else:
            args["details"] = "Rocket League"
    elif (
        mode and arena and status and cfg["game_mode"] and cfg["arena_name"] and cfg["match_status"]
    ):
        args["details"] = f"{mode} in {arena} | {status}"
    elif mode and arena and cfg["game_mode"] and cfg["arena_name"]:
        args["details"] = f"{mode} in {arena}"
    elif mode and status and cfg["game_mode"] and cfg["match_status"]:
        args["details"] = f"{mode} | {status}"
    elif mode and cfg["game_mode"]:
        args["details"] = str(mode)
    elif arena and status and cfg["arena_name"] and cfg["match_status"]:
        args["details"] = f"{arena} | {status}"
    elif arena and cfg["arena_name"]:
        args["details"] = str(arena)
    elif status and cfg["match_status"]:
        args["details"] = str(status)
    else:
        args["details"] = "Rocket League"

    if is_training:
        if cfg["arena_name"] and arena:
            args["state"] = f"Estadio {arena}"
        elif cfg["game_mode"]:
            args["state"] = training_label
    elif not has_target:
        if cfg["game_mode"]:
            args["state"] = "Replay"
    else:
        state_bits: list[str] = []
        if (
            cfg["current_score"]
            and isinstance(view.get("team_score"), int)
            and isinstance(view.get("opponent_score"), int)
        ):
            score_txt = f"{view['team_score']}-{view['opponent_score']}"
            if cfg["match_status"] and status:
                score_txt += f" ({status})"
            state_bits.append(score_txt)
        if cfg["match_status"] and view.get("is_mvp") is True:
            state_bits.append("MVP")
        if state_bits:
            args["state"] = " • ".join(state_bits)

    goals = view.get("player_goals")
    assists = view.get("player_assists")
    if (cfg["goals"] and isinstance(goals, int)) or (cfg["assists"] and isinstance(assists, int)):
        left = f"{goals or 0} Goals" if cfg["goals"] and isinstance(goals, int) else ""
        right = f"{assists or 0} Assists" if cfg["assists"] and isinstance(assists, int) else ""
        if left and right:
            args["large_text"] = f"{left} & {right}"
        elif left:
            args["large_text"] = left
        elif right:
            args["large_text"] = right
        args["large_image"] = "rocket"

    small_bits: list[str] = []
    if cfg["player_name"] and view.get("player_name"):
        small_bits.append(str(view["player_name"]))
    if cfg["player_score"] and isinstance(view.get("player_score"), int):
        small_bits.append(f"Score: {view['player_score']}")
    if cfg["shots"] and isinstance(view.get("player_shots"), int):
        small_bits.append(f"Shots: {view['player_shots']}")
    if small_bits:
        args["small_text"] = " | ".join(small_bits)

    if cfg["player_name"]:
        args["small_image"] = view.get("player_platform") or last_target_platform

    now_sec = int(time.time())
    remaining = view.get("remaining_seconds")
    is_overtime = bool(view.get("is_overtime"))
    if cfg["timer"] and has_target:
        # Start of a new match: prefer GUID changes, then countdown heuristic.
        is_new_match = (
            match_start_epoch_sec is None
            or (current_guid is not None and match_start_guid != current_guid)
            or (
                current_guid is None
                and not is_overtime
                and isinstance(remaining, int)
                and remaining >= 299
            )
        )
        if is_new_match and isinstance(remaining, int):
            elapsed = max(0, 300 - max(0, remaining))
            match_start_epoch_sec = max(0, now_sec - elapsed)
            match_start_guid = current_guid
            overtime_started_epoch_sec = None

        if is_overtime:
            if overtime_started_epoch_sec is None:
                overtime_started_epoch_sec = now_sec
            overtime_elapsed = max(0, now_sec - overtime_started_epoch_sec)
            args["details"] = overtime_details_text
            args["state"] = (
                f"{overtime_state_prefix}" f"{overtime_elapsed // 60}:{overtime_elapsed % 60:02d}"
            )
        else:
            overtime_started_epoch_sec = None

        if match_start_epoch_sec is not None:
            args["start_time"] = match_start_epoch_sec
            if not is_overtime and isinstance(remaining, int):
                args["end_time"] = now_sec + max(0, remaining)
            else:
                args["end_time"] = None

    return args, match_start_epoch_sec, match_start_guid, overtime_started_epoch_sec
