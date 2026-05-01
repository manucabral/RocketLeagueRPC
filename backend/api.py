"""
Main API class.
"""

from typing import Any

from .app_coordinator import AppCoordinator
from .config import config
from .logger import logger


class Api:
    """API exposed to JavaScript via pywebview."""

    def __init__(self, coordinator: AppCoordinator) -> None:
        self._coordinator = coordinator
        logger.debug("API initialized")

    def get_app_info(self) -> dict[str, Any]:
        """Return application name, version, and development mode flag."""
        return {
            "name": config.app_name,
            "version": config.app_version,
            "dev_mode": config.development_mode,
        }

    def log_message(self, message: str) -> dict[str, str]:
        """Log a message originating from the frontend at INFO level.

        Args:
            message: The message string sent by the JavaScript frontend.

        Returns:
            A status dict with key ``"status"`` set to ``"ok"``.
        """
        logger.info("Frontend: %s", message)
        return {"status": "ok"}

    def connect_tracker(self) -> dict[str, Any]:
        """Connect the Rocket League stats tracker and return live state."""
        return self._coordinator.connect_tracker()

    def disconnect_tracker(self) -> dict[str, Any]:
        """Disconnect the Rocket League stats tracker and return live state."""
        return self._coordinator.disconnect_tracker()

    def connect_discord_rpc(self) -> dict[str, Any]:
        """Connect to Discord RPC and return live state."""
        return self._coordinator.connect_discord_rpc()

    def disconnect_discord_rpc(self) -> dict[str, Any]:
        """Disconnect from Discord RPC and return live state."""
        return self._coordinator.disconnect_discord_rpc()

    def debug_discord_ipc(self) -> dict[str, Any]:
        """Run the Discord IPC debug probe and return live state."""
        return self._coordinator.debug_discord_ipc()

    def get_presence_config(self) -> dict[str, bool]:
        """Return the current presence feature-toggle configuration."""
        return self._coordinator.get_presence_config()

    def set_presence_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Persist an updated presence configuration and return live state.

        Args:
            cfg: Mapping of presence feature keys to boolean toggle values.

        Returns:
            The full live state dict after applying the new configuration.
        """
        return self._coordinator.set_presence_config(cfg)

    def list_presence_presets(self) -> list[str]:
        """Return a sorted list of saved presence preset names."""
        return self._coordinator.list_presence_presets()

    def save_presence_preset(
        self, name: str, cfg: dict[str, Any], overwrite: bool = False
    ) -> dict[str, Any]:
        """Save a presence configuration under the given preset name.

        Args:
            name: Human-readable preset name (max 64 characters).
            cfg: Presence feature-toggle mapping to persist.
            overwrite: When ``True``, replace an existing preset with the same
                name instead of raising an error.

        Returns:
            A dict with ``"name"`` and ``"config"`` keys for the saved preset.
        """
        return self._coordinator.save_presence_preset(name=name, cfg=cfg, overwrite=overwrite)

    def load_presence_preset(self, name: str) -> dict[str, Any]:
        """Load a saved preset, apply it as the active config, and return live state.

        Args:
            name: Name of the preset to load.

        Returns:
            The full live state dict after applying the preset.
        """
        return self._coordinator.load_presence_preset(name)

    def delete_presence_preset(self, name: str) -> dict[str, Any]:
        """Delete a saved presence preset by name.

        Args:
            name: Name of the preset to delete.

        Returns:
            A dict with a ``"deleted"`` key containing the stripped preset name.
        """
        return self._coordinator.delete_presence_preset(name)

    def get_live_state(self) -> dict[str, Any]:
        """Return the current aggregated live state from all backend services."""
        return self._coordinator.get_live_state()
