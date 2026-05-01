"""
Application configuration management.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from .utils import env_bool


@dataclass
class Config:
    """Application configuration."""

    app_name: str = os.getenv("APP_NAME", "Rocket League RPC")
    app_version: str = os.getenv("APP_VERSION", "0.0.1")
    overtime_details_text: str = os.getenv("OVERTIME_DETAILS_TEXT", "Overtime")
    overtime_state_prefix: str = os.getenv("OVERTIME_STATE_PREFIX", "+")
    window_width: int = int(os.getenv("WINDOW_WIDTH", "1000"))
    window_height: int = int(os.getenv("WINDOW_HEIGHT", "700"))
    development_mode: bool = env_bool("DEVELOPMENT_MODE", False)

    project_root: Path = Path(__file__).resolve().parent.parent
    frontend_dist_dir: Path = project_root / "frontend" / "dist"

    @property
    def data_dir(self) -> Path:
        """Return the resolved user data directory, creating it if necessary."""
        data_dir = Path.home() / ".rocketleaguerpc"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir.resolve()

    @property
    def log_path(self) -> Path:
        """Return the path to the application log file, creating the directory if needed."""
        if self.development_mode:
            log_dir = self.project_root / "logs"
        else:
            log_dir = self.data_dir / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "app.log"


config = Config()
