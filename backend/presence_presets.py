"""
Presence configuration preset management, including persistence to disk and sanitisation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import MAX_PRESET_NAME_LEN, PRESETS_FILE, PRESETS_VERSION
from .logger import logger
from .presence_config import sanitize_presence_config
from .utils import normalize_preset_name


def _normalize(name: str | None) -> str | None:
    return normalize_preset_name(name, MAX_PRESET_NAME_LEN)


class PresencePresetStore:
    """Manage presence configuration presets."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir.resolve()
        logger.debug("Presence presets data dir: %s", self._data_dir)
        self._presets = self._load()

    def list_names(self) -> list[str]:
        """Return a sorted list of all stored preset names."""
        return sorted(self._presets.keys())

    def save(self, name: str, cfg: dict[str, Any], overwrite: bool = False) -> dict[str, bool]:
        """Persist a new preset, optionally overwriting an existing one.

        Args:
            name: Human-readable preset name (will be normalised and truncated).
            cfg: Presence feature-toggle mapping to store.
            overwrite: When ``True``, replace an existing preset with the same
                normalised name.

        Returns:
            The sanitised config dict that was stored.

        Raises:
            ValueError: If *name* normalises to empty, or if the preset already
                exists and *overwrite* is ``False``.
        """
        preset_name = _normalize(name)
        if preset_name is None:
            raise ValueError("Preset name is required")
        if preset_name in self._presets and not overwrite:
            raise ValueError("Preset already exists")
        payload = sanitize_presence_config(cfg)
        self._presets[preset_name] = payload
        self._persist()
        return payload

    def load(self, name: str) -> dict[str, bool]:
        """Return a copy of the stored preset config for *name*.

        Args:
            name: Name of the preset to load.

        Returns:
            A shallow copy of the preset's config dict.

        Raises:
            ValueError: If *name* normalises to empty or the preset does not exist.
        """
        preset_name = _normalize(name)
        if preset_name is None or preset_name not in self._presets:
            raise ValueError("Preset not found")
        return dict(self._presets[preset_name])

    def delete(self, name: str) -> None:
        """Remove the named preset from the store and persist the change.

        Args:
            name: Name of the preset to delete.

        Raises:
            ValueError: If *name* normalises to empty or the preset does not exist.
        """
        preset_name = _normalize(name)
        if preset_name is None or preset_name not in self._presets:
            raise ValueError("Preset not found")
        del self._presets[preset_name]
        self._persist()

    def _path(self) -> Path:
        return self._data_dir / PRESETS_FILE

    def _load(self) -> dict[str, dict[str, bool]]:
        """Load and return all presets from disk, returning ``{}`` on any error."""
        try:
            path = self._path()
            logger.debug("Loading presets from %s", path)
            if not path.exists():
                return {}
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict):
                return {}
            presets_obj = parsed.get("presets")
            if not isinstance(presets_obj, dict):
                return {}
            output: dict[str, dict[str, bool]] = {}
            for key, value in presets_obj.items():
                name = _normalize(key)
                if name is None or not isinstance(value, dict):
                    continue
                output[name] = sanitize_presence_config(value)
            return output
        except Exception:
            logger.exception("Failed to load presets")
            return {}

    def _persist(self) -> None:
        """Write the current in-memory presets to disk as JSON."""
        try:
            path = self._path()
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": PRESETS_VERSION, "presets": self._presets}
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.debug("Saved presets to %s", path)
        except Exception:
            logger.exception("Failed to save presets")
