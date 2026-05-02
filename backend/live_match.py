"""
Live match view construction and related utilities.
"""

from __future__ import annotations

from typing import Any

"""
Credits to https://github.com/segalll/DiscordRPCPlugin
"""
MAP_NAMES = {
    "arc_darc_p": "Starbase ARC (Aftermath)",
    "arc_standard_p": "Starbase ARC",
    "arc_p": "ARCtagon (Night)",
    "bb_p": "Champions Field (NFL)",
    "beach_p": "Salty Shores",
    "beach_night_grs_p": "Salty Shores (Salty Fest)",
    "beach_night_p": "Salty Shores (Night)",
    "cs_hw_p": "Rivals Arena",
    "cs_day_p": "Champions Field (Day)",
    "cs_p": "Champions Field (Night)",
    "chn_stadium_day_p": "Forbidden Temple (Day)",
    "chn_stadium_p": "Forbidden Temple (Dawn)",
    "eurostadium_p": "Mannfield (Day)",
    "eurostadium_night_p": "Mannfield (Night)",
    "eurostadium_rainy_p": "Mannfield (Stormy)",
    "eurostadium_snownight_p": "Mannfield (Snowy)",
    "eurostadium_dusk_p": "Mannfield (Dusk)",
    "fni_stadiun_p": "Forbidden Temple (Fire & Ice)",
    "ff_dusk_p": "Stadium Vida (Dusk)",
    "farm_p": "Farmstead (Dusk)",
    "farm_night_p": "Farmstead (Night)",
    "farm_grs_p": "Farmstead (Pitched)",
    "farm_hw_p": "Farmstead (Spooky)",
    "haunted_trainstation_p": "Urban Central (Haunted)",
    "hoopsstadium_p": "Dunk House (Night)",
    "hoopsstreet_p": "The Block (Dusk)",
    "ko_calavera_p": "Calavera",
    "ko_carbon_p": "Carbon",
    "ko_quadron_p": "Quadron",
    "labs_basin_p": "Basin",
    "labs_circlepillars_p": "Pillars",
    "labs_corridor_p": "Corridor",
    "labs_cosmic_p": "Cosmic (Old)",
    "labs_cosmic_v4_p": "Cosmic (New)",
    "labs_doublegoal_p": "Double Goal (Old)",
    "labs_doublegoal_v2_p": "Double Goal (New)",
    "labs_galleon_mast_p": "Galleon Retro",
    "labs_galleon_p": "Galleon",
    "labs_holyfield_p": "Loophole",
    "labs_holyfield_space_p": "Force Field",
    "labs_octagon_02_p": "Octagon (New)",
    "labs_octagon_p": "Octagon (Old)",
    "labs_pillarglass_p": "Hourglass",
    "labs_pillarheat_p": "Barricade",
    "labs_pillarwings_p": "Colossus",
    "labs_underpass_p": "Underpass",
    "labs_utopia_p": "Utopia Retro",
    "music_p": "Neon Fields",
    "neotokyo_arcade_p": "Neo Tokyo (Arcade)",
    "neotokyo_p": "Tokyo Underpass",
    "neotokyo_standard_p": "Neo Tokyo",
    "neotokyo_toon_p": "Neo Tokyo (Comic)",
    "neotokyo_hax_p": "Neo Tokyo (Hacked)",
    "outlaw_p": "Deadeye Canyon",
    "outlaw_oasis_p": "Deadeye Canyon (Oasis)",
    "park_night_p": "Beckwith Park (Midnight)",
    "park_p": "Beckwith Park",
    "park_rainy_p": "Beckwith Park (Stormy)",
    "park_snowy_p": "Beckwith Park (Snowy)",
    "park_bman_p": "Beckwith Park (Night)",
    "shattershot_p": "Core 707",
    "stadium_p": "DFH Stadium",
    "stadium_foggy_p": "DFH Stadium (Stormy)",
    "stadium_race_day_p": "DFH Stadium (Circuit)",
    "stadium_winter_p": "DFH Stadium (Snowy)",
    "stadium_day_p": "DFH Stadium (Day)",
    "stadium_10a_p": "DFH Stadium (10th Anniversary)",
    "street_p": "Sovereign Heights (Dusk)",
    "swoosh_p": "Champions Field (Nike FC)",
    "trainstation_dawn_p": "Urban Central (Dawn)",
    "trainstation_night_p": "Urban Central (Night)",
    "trainstation_p": "Urban Central (Rainy)",
    "throwbackhockey_p": "Throwback Stadium (Snowy)",
    "throwbackstadium_p": "Throwback Stadium",
    "underwater_p": "AquaDome",
    "underwater_grs_p": "AquaDome (Salty Shallows)",
    "uf_day_p": "Futura Garden (Day)",
    "utopiastadium_p": "Utopia Coliseum (Day)",
    "utopiastadium_dusk_p": "Utopia Coliseum (Dusk)",
    "utopiastadium_lux_p": "Utopia Coliseum (Gilded)",
    "utopiastadium_snow_p": "Utopia Coliseum (Snowy)",
    "wasteland_p": "Badlands (Day)",
    "wasteland_night_p": "Badlands (Night)",
    "wasteland_s_p": "Wasteland (Day)",
    "wasteland_night_s_p": "Wasteland (Night)",
    "wasteland_grs_p": "Wasteland (Pitched)",
    "woods_p": "Drift Woods (Dawn)",
    "woods_night_p": "Drift Woods (Night)",
}


def format_clock(seconds: int) -> str:
    """Format a non-negative integer number of seconds as ``M:SS``.

    Args:
        seconds: Number of seconds to format. Negative values are clamped to 0.

    Returns:
        A string in ``M:SS`` format, e.g. ``"4:37"``.
    """
    safe = max(seconds, 0)
    return f"{safe // 60}:{safe % 60:02d}"


def resolve_arena_name(arena_id: Any) -> Any:
    """Resolve a Rocket League arena ID to a human-readable arena name.

    Args:
        arena_id: Raw arena identifier from the game payload. Non-string values
            are returned unchanged.

    Returns:
        The display name from ``MAP_NAMES`` if found, otherwise the original
        ``arena_id`` value.
    """
    if not isinstance(arena_id, str):
        return arena_id
    return MAP_NAMES.get(arena_id.strip().lower(), arena_id)


def infer_mode(players: list[Any]) -> str | None:
    """Infer the match mode (e.g. Duel, Doubles, Standard) from the player list.

    Args:
        players: List of player dicts from the game payload, each expected to
            contain a ``"TeamNum"`` key (0 for Blue, 1 for Orange).

    Returns:
        A string such as ``"Duel"``, ``"Doubles"``, ``"Standard"``,
        ``"Training"``, ``"Training Online"``, or an auto-generated ``"NvM"``
        label. Returns ``None`` when the mode cannot be determined.
    """
    if not players:
        return None
    if len(players) == 1:
        return "Training"

    blue = 0
    orange = 0
    for player in players:
        if not isinstance(player, dict):
            continue
        team_num = player.get("TeamNum")
        if team_num == 0:
            blue += 1
        elif team_num == 1:
            orange += 1

    if blue == 0 and orange == 0:
        return None
    if (blue > 0 and orange == 0) or (orange > 0 and blue == 0):
        return "Training Online"
    if blue == orange:
        if blue == 1:
            return "Duel"
        if blue == 2:
            return "Doubles"
        if blue == 3:
            return "Standard"
        if blue == 4:
            return "Quad"
        return f"{blue}v{blue}"
    return f"{blue}v{orange}"


def game_get_list(payload: dict[str, Any], key: str) -> list[Any]:
    """Safely extract a list value from a game payload dict.

    Args:
        payload: The source dict to read from.
        key: The key whose value should be a list.

    Returns:
        The list stored at *key*, or an empty list if the value is missing or
        not a ``list`` instance.
    """
    value = payload.get(key)
    return value if isinstance(value, list) else []


def is_mvp(players: list[Any], chosen: dict[str, Any] | None, mode: Any) -> bool | None:
    """Determine whether the chosen player has the highest score on their team.

    Args:
        players: Full list of player dicts from the game payload.
        chosen: The player dict to evaluate, or ``None``.
        mode: The inferred or raw game mode string.

    Returns:
        ``True`` if *chosen* is MVP, ``False`` in Training mode, or ``None``
        when the result cannot be determined (e.g. missing score data).
    """
    if str(mode or "") == "Training":
        return False
    if not isinstance(chosen, dict):
        return None
    team = chosen.get("TeamNum")
    player_score = chosen.get("Score")
    if not isinstance(team, int) or not isinstance(player_score, int):
        return None

    best = None
    for player in players:
        if not isinstance(player, dict):
            continue
        if player.get("TeamNum") != team:
            continue
        score = player.get("Score")
        if isinstance(score, int):
            best = score if best is None else max(best, score)

    if best is None:
        return None
    return player_score >= best


def build_live_match_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a normalised live-match view dict from a raw ``UpdateState`` payload.

    Extracts and derives arena, game mode, score, timer, player stats, and MVP
    status from the raw payload emitted by the Rocket League stats client.

    Args:
        payload: Raw ``UpdateState`` event payload dict.

    Returns:
        A dict containing the following keys: ``arena``, ``mode``, ``time``,
        ``status``, ``team_score``, ``opponent_score``, ``player_name``,
        ``player_score``, ``player_goals``, ``player_assists``, ``player_shots``,
        ``has_target``, ``remaining_seconds``, ``elapsed_seconds``,
        ``player_platform``, ``is_mvp``.
    """
    game = payload.get("Game") or {}
    players = game_get_list(payload, "Players")
    teams = game_get_list(game, "Teams")
    target = game.get("Target") if isinstance(game.get("Target"), dict) else None

    has_target = bool(game.get("bHasTarget")) or isinstance(target, dict)
    target_shortcut = target.get("Shortcut") if isinstance(target, dict) else None
    target_name = target.get("Name") if isinstance(target, dict) else None
    target_team = target.get("TeamNum") if isinstance(target, dict) else None

    chosen = None
    for player in players:
        if not isinstance(player, dict):
            continue
        if target_shortcut is not None and player.get("Shortcut") == target_shortcut:
            chosen = player
            break
        if target_name is not None and target_team is not None:
            if player.get("Name") == target_name and player.get("TeamNum") == target_team:
                chosen = player
                break
    if chosen is None and has_target and players:
        first = players[0]
        chosen = first if isinstance(first, dict) else None

    player_team = chosen.get("TeamNum") if isinstance(chosen, dict) else target_team

    team_score = None
    opponent_score = None
    for team in teams:
        if not isinstance(team, dict):
            continue
        if player_team is not None and team.get("TeamNum") == player_team:
            team_score = team.get("Score")
        elif (
            player_team is not None
            and team.get("TeamNum") != player_team
            and opponent_score is None
        ):
            opponent_score = team.get("Score")

    if team_score is None and teams and isinstance(teams[0], dict):
        team_score = teams[0].get("Score")
    if opponent_score is None and len(teams) > 1 and isinstance(teams[1], dict):
        opponent_score = teams[1].get("Score")

    status = None
    if has_target and isinstance(team_score, int) and isinstance(opponent_score, int):
        if team_score > opponent_score:
            status = "Winning"
        elif team_score < opponent_score:
            status = "Losing"
        else:
            status = "Tied"

    inferred_mode = infer_mode(players)
    raw_mode = game.get("Mode") or game.get("GameMode") or game.get("Playlist")
    mode = inferred_mode or raw_mode
    # TimeSeconds is the RL countdown clock (seconds remaining), not elapsed.
    time_seconds_raw = game.get("TimeSeconds")
    time_seconds = max(0, int(time_seconds_raw)) if isinstance(time_seconds_raw, int) else None
    time_text = format_clock(time_seconds) if isinstance(time_seconds, int) else None
    is_overtime = bool(game.get("bOvertime"))

    player_platform = None
    if isinstance(chosen, dict):
        pid = chosen.get("PrimaryId")
        if isinstance(pid, str):
            if pid.startswith("Epic|"):
                player_platform = "epic"
            elif pid.startswith("Steam|"):
                player_platform = "steam"

    return {
        "arena": resolve_arena_name(game.get("Arena")),
        "mode": mode,
        "time": time_text,
        "status": status,
        "team_score": team_score if has_target else None,
        "opponent_score": opponent_score if has_target else None,
        "player_name": chosen.get("Name") if isinstance(chosen, dict) else target_name,
        "player_score": chosen.get("Score") if isinstance(chosen, dict) else None,
        "player_goals": chosen.get("Goals") if isinstance(chosen, dict) else None,
        "player_assists": chosen.get("Assists") if isinstance(chosen, dict) else None,
        "player_shots": chosen.get("Shots") if isinstance(chosen, dict) else None,
        "has_target": has_target,
        "remaining_seconds": time_seconds if isinstance(time_seconds, int) else None,
        "is_overtime": is_overtime,
        "elapsed_seconds": (
            int(game.get("Elapsed")) if isinstance(game.get("Elapsed"), (int, float)) else None
        ),
        "player_platform": player_platform,
        "is_mvp": is_mvp(players, chosen, mode),
    }
