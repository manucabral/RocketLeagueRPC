"""
Utility functions for the backend.
"""

from __future__ import annotations

import os
import socket
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .logger import logger


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def remove_none(d: dict[str, Any]) -> dict[str, Any]:
    def clean_dict(value: dict[str, Any]) -> dict[str, Any]:
        return {
            key: clean_dict(item) if isinstance(item, dict) else item
            for key, item in value.items()
            if item is not None and (not isinstance(item, dict) or len(item) > 0)
        }

    return clean_dict(d)

def json_safe_presence(args: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in args.items():
        if hasattr(value, "value"):
            safe[key] = value.value
        else:
            safe[key] = value
    return safe

def normalize_preset_name(name: str | None, max_len: int) -> str | None:
    if name is None:
        return None
    cleaned = str(name).strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for_http_server(host: str, port: int, timeout_seconds: float = 5.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def serve_dist(directory: Path, port: int) -> None:
    try:
        handler_class = partial(SimpleHTTPRequestHandler, directory=str(directory))
        httpd = ThreadingHTTPServer(("127.0.0.1", port), handler_class)
        logger.info("Serving frontend dist at http://127.0.0.1:%s", port)
        httpd.serve_forever()
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Failed to serve frontend dist")
