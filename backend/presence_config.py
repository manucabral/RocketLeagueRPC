"""
Presence configuration utilities.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .constants import PRESENCE_CONFIG_FILE
from .logger import logger

PresenceConfig = dict[str, bool | str]

DEFAULT_LARGE_IMAGE = "rocket"
ALLOWED_LARGE_IMAGES = {"rocket", "rocket2"}

DEFAULT_PRESENCE_CONFIG: PresenceConfig = {
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
    "large_image": DEFAULT_LARGE_IMAGE,
}


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, bool]:
    """Load a JSON object, recovering the first object when trailing data exists."""
    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
        return (parsed, False) if isinstance(parsed, dict) else (None, False)
    except JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        try:
            parsed, end = decoder.raw_decode(text)
        except JSONDecodeError:
            raise exc
        if isinstance(parsed, dict) and text[end:].strip():
            return parsed, True
        raise exc


def sanitize_presence_config(raw: dict[str, Any]) -> PresenceConfig:
    """Merge *raw* into the default config, coercing known values.

    Unknown keys in *raw* are silently ignored. Missing keys fall back to the
    default value from ``DEFAULT_PRESENCE_CONFIG``.

    Args:
        raw: Untrusted config mapping supplied by the caller.

    Returns:
        A sanitised config dict with exactly the keys from
        ``DEFAULT_PRESENCE_CONFIG``.
    """
    merged = dict(DEFAULT_PRESENCE_CONFIG)
    for key in DEFAULT_PRESENCE_CONFIG:
        if key == "large_image":
            continue
        if key in raw:
            merged[key] = bool(raw[key])
    large_image = raw.get("large_image", DEFAULT_LARGE_IMAGE)
    merged["large_image"] = (
        large_image if large_image in ALLOWED_LARGE_IMAGES else DEFAULT_LARGE_IMAGE
    )
    return merged


def load_presence_config(data_dir: Path) -> PresenceConfig:
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
        parsed, recovered = load_json_object(path)
        if not isinstance(parsed, dict):
            return dict(DEFAULT_PRESENCE_CONFIG)
        sanitized = sanitize_presence_config(parsed)
        if recovered:
            logger.warning("Recovered presence config from trailing JSON data: %s", path)
            save_presence_config(data_dir, sanitized)
        return sanitized
    except Exception:
        logger.exception("Failed to load presence config")
        return dict(DEFAULT_PRESENCE_CONFIG)


def save_presence_config(data_dir: Path, cfg: PresenceConfig) -> None:
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
