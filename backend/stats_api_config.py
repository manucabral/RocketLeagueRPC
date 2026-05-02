from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from .constants import STATS_API_WARNING, TARGET_PORT


STATS_API_RELATIVE_PATH = (
    Path("My Games") / "Rocket League" / "TAGame" / "Config" / "TAStatsAPI.ini"
)

def candidate_stats_api_paths(home: Path | None = None) -> list[Path]:
    """Return likely user-specific locations for Rocket League StatsAPI config."""
    base = (home or Path.home()).resolve()
    candidates = [
        base / "Documents" / STATS_API_RELATIVE_PATH,
        base / "OneDrive" / "Documents" / STATS_API_RELATIVE_PATH,
        base / "OneDrive" / "Documentos" / STATS_API_RELATIVE_PATH,
        base / "Documentos" / STATS_API_RELATIVE_PATH,
    ]
    userprofile = os.getenv("USERPROFILE")
    if userprofile:
        profile = Path(userprofile).resolve()
        candidates.extend(
            [
                profile / "Documents" / STATS_API_RELATIVE_PATH,
                profile / "OneDrive" / "Documents" / STATS_API_RELATIVE_PATH,
                profile / "OneDrive" / "Documentos" / STATS_API_RELATIVE_PATH,
                profile / "Documentos" / STATS_API_RELATIVE_PATH,
            ]
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).casefold()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def _read_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip().casefold()] = value.strip()
    return values


def _status_for_missing() -> dict[str, Any]:
    return {
        "found": False,
        "enabled": False,
        "path": None,
        "packet_send_rate": None,
        "port": None,
        "warning": STATS_API_WARNING,
    }


def _status_for_path(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    values = _read_key_values(text)
    packet_send_rate = _parse_int(values.get("packetsendrate"))
    port = _parse_int(values.get("port"))
    return {
        "found": True,
        "enabled": bool(packet_send_rate and packet_send_rate > 0),
        "path": str(path),
        "packet_send_rate": packet_send_rate,
        "port": port,
        "warning": None,
    }


def find_stats_api_config(home: Path | None = None) -> Path | None:
    """Return the first existing TAStatsAPI.ini path from known user locations."""
    for path in candidate_stats_api_paths(home):
        if path.exists():
            return path
    return None


def get_stats_api_status(home: Path | None = None) -> dict[str, Any]:
    """Return current StatsAPI config status, or a manual setup warning."""
    path = find_stats_api_config(home)
    if path is None:
        return _status_for_missing()
    return _status_for_path(path)


def _set_or_append_key(lines: list[str], key: str, value: str) -> list[str]:
    output: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            output.append(line)
            continue
        current_key, _current_value = stripped.split("=", 1)
        if current_key.strip().casefold() == key.casefold():
            leading = line[: len(line) - len(line.lstrip())]
            output.append(f"{leading}{key}={value}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{key}={value}")
    return output


def set_stats_api_enabled(enabled: bool, home: Path | None = None) -> dict[str, Any]:
    """Enable or disable StatsAPI in TAStatsAPI.ini when the config exists."""
    path = find_stats_api_config(home)
    if path is None:
        return _status_for_missing()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines = _set_or_append_key(lines, "PacketSendRate", "1" if enabled else "0")
    lines = _set_or_append_key(lines, "Port", str(TARGET_PORT))
    newline = "\n" if text.endswith(("\n", "\r\n")) else ""
    path.write_text("\n".join(lines) + newline, encoding="utf-8")
    return _status_for_path(path)
