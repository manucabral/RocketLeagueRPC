"""Build script for Rocket League RPC final app."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from backend.config import config

COMPANY_NAME = os.getenv("COMPANY_NAME", "Rocket League RPC")
OUTPUT_DIR = "dist_build"
OUTPUT_FILENAME = "RocketLeagueRPC"
TARGET_FILE = "main.py"


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _frontend_dist_dir(project_root: Path) -> Path:
    return project_root / "frontend"


def _icon_path(project_root: Path) -> Path:
    return project_root / "frontend" / "assets" / "logo.ico"


def build() -> None:
    """Build the application with Nuitka."""
    project_root = _project_root()
    frontend_dist_dir = _frontend_dist_dir(project_root)
    icon_path = _icon_path(project_root)

    if not frontend_dist_dir.exists():
        raise FileNotFoundError(f"Frontend directory not found: {frontend_dist_dir}")

    if not icon_path.exists():
        raise FileNotFoundError(f"Icon file not found: {icon_path}")

    nuitka_args = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--windows-console-mode=disable",
        f"--output-dir={OUTPUT_DIR}",
        f"--output-filename={OUTPUT_FILENAME}",
        f"--windows-icon-from-ico={icon_path}",
        f"--windows-product-name={config.app_name}",
        "--windows-file-description=Rocket League Discord Rich Presence",
        f"--windows-company-name={COMPANY_NAME}",
        f"--windows-file-version={config.app_version}.0",
        f"--windows-product-version={config.app_version}.0",
        f"--include-data-dir={frontend_dist_dir}=frontend",
        "--disable-plugin=pywebview",
        "--include-module=clr",
        "--include-module=pythonnet",
        "--include-module=webview.platforms.winforms",
        "--include-module=webview.platforms.win32",
        "--include-module=webview.platforms.edgechromium",
        "--include-module=webview.platforms.mshtml",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=unittest.mock",
        "--nofollow-import-to=doctest",
        "--nofollow-import-to=pytest",
        "--nofollow-import-to=test",
        "--nofollow-import-to=webview.platforms.cocoa",
        "--nofollow-import-to=webview.platforms.gtk",
        "--nofollow-import-to=webview.platforms.qt",
        "--nofollow-import-to=webview.platforms.android",
        "--nofollow-import-to=webview.platforms.linux",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=_tkinter",
        "--nofollow-import-to=PyQt5",
        "--nofollow-import-to=PyQt6",
        "--nofollow-import-to=PySide2",
        "--nofollow-import-to=PySide6",
        "--nofollow-import-to=gi",
        "--nofollow-import-to=pydoc",
        "--nofollow-import-to=distutils",
        "--nofollow-import-to=setuptools",
        "--remove-output",
        "--python-flag=no_docstrings",
        "--python-flag=no_asserts",
        "--msvc=latest",
        TARGET_FILE,
    ]

    print("Building Rocket League RPC with Nuitka...")
    print(" ".join(map(str, nuitka_args)))

    try:
        subprocess.run(nuitka_args, check=True, cwd=project_root)
    except subprocess.CalledProcessError as exc:
        print(f"Build failed with exit code {exc.returncode}")
        sys.exit(exc.returncode)

    print("Build completed successfully.")
    print(f"Output directory: {project_root / OUTPUT_DIR}")


if __name__ == "__main__":
    build()
