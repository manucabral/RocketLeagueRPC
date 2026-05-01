"""
Logging setup and utilities.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rocketleaguerpc")


def setup_logger(log_file: Optional[Path] = None, level: int = logging.INFO) -> None:
    """Set up logging to console and optionally to a file."""
    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Make setup idempotent across repeated calls/imports.
    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def set_log_level(level_name: str) -> None:
    """Set the log level by name (e.g., 'DEBUG', 'INFO')."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)
