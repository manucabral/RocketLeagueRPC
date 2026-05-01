"""
Presence settings service for managing presence config persistence and presets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .presence_config import (
    load_presence_config,
    sanitize_presence_config,
    save_presence_config,
)
from .presence_presets import PresencePresetStore


class PresenceSettingsService:
    """Presence config persistence and presets."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._config = load_presence_config(data_dir)
        self._preset_store = PresencePresetStore(data_dir)

    def get_config(self) -> dict[str, bool]:
        """Return a copy of the currently active presence configuration."""
        return dict(self._config)

    def set_config(self, new_config: dict[str, Any]) -> dict[str, bool]:
        """Validate, persist, and activate a new presence configuration.

        Args:
            new_config: Untrusted mapping of presence feature keys to values.

        Returns:
            The sanitised config dict that is now active.
        """
        merged = sanitize_presence_config(new_config)
        self._config = merged
        save_presence_config(self._data_dir, merged)
        return dict(merged)

    def list_presets(self) -> list[str]:
        """Return a sorted list of all saved presence preset names."""
        return self._preset_store.list_names()

    def save_preset(
        self, name: str, cfg: dict[str, Any], overwrite: bool = False
    ) -> dict[str, bool]:
        """Save a presence configuration preset.

        Args:
            name: Human-readable preset name.
            cfg: Presence feature-toggle mapping to persist.
            overwrite: When ``True``, replace an existing preset with the same name.

        Returns:
            The sanitised config dict that was stored.
        """
        return self._preset_store.save(name=name, cfg=cfg, overwrite=overwrite)

    def load_preset(self, name: str) -> dict[str, bool]:
        """Load and return the config dict for the named preset.

        Args:
            name: Name of the preset to load.

        Returns:
            A copy of the stored preset config.
        """
        return self._preset_store.load(name)

    def delete_preset(self, name: str) -> None:
        """Delete the named preset from the store.

        Args:
            name: Name of the preset to delete.
        """
        self._preset_store.delete(name)
