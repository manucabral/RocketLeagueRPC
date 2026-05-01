"""
Presence configuration utilities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import PRESENCE_CONFIG_FILE
from .logger import logger

DEFAULT_PRESENCE_CONFIG: dict[str, bool] = {
    "arena_name": True,
    "current_score": True,
    "timer": True,
    "game_mode": True,
    "match_status": True,
    "player_name": True,
    "player_score": True,
    "goals": True,
    "assists": True,
    "shots": True,
}


def sanitize_presence_config(raw: dict[str, Any]) -> dict[str, bool]:
    """Merge *raw* into the default config, coercing known keys to ``bool``.

    Unknown keys in *raw* are silently ignored. Missing keys fall back to the
    default value from ``DEFAULT_PRESENCE_CONFIG``.

    Args:
        raw: Untrusted config mapping supplied by the caller.

    Returns:
        A sanitised ``dict[str, bool]`` with exactly the keys from
        ``DEFAULT_PRESENCE_CONFIG``.
    """
    merged = dict(DEFAULT_PRESENCE_CONFIG)
    for key in DEFAULT_PRESENCE_CONFIG:
        if key in raw:
            merged[key] = bool(raw[key])
    return merged


def load_presence_config(data_dir: Path) -> dict[str, bool]:
    """
    Load presence configuration from the data directory.

    Args:
        data_dir: The data directory containing the presence configuration file.

    Returns:
        The presence configuration as a dictionary.
    """
    try:
        path = data_dir / PRESENCE_CONFIG_FILE
        logger.debug("Loading presence config from %s", path)
        if not path.exists():
            return dict(DEFAULT_PRESENCE_CONFIG)
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            return dict(DEFAULT_PRESENCE_CONFIG)
        return sanitize_presence_config(parsed)
    except Exception:
        logger.exception("Failed to load presence config")
        return dict(DEFAULT_PRESENCE_CONFIG)


def save_presence_config(data_dir: Path, cfg: dict[str, bool]) -> None:
    """
    Save presence configuration to the data directory.

    Args:
        data_dir: The data directory containing the presence configuration file.
        cfg: The presence configuration to save.
    """
    try:
        path = data_dir / PRESENCE_CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        logger.debug("Saved presence config to %s", path)
    except Exception:
        logger.exception("Failed to save presence config")
