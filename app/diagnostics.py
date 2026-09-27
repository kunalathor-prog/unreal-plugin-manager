"""Startup diagnostics use only the standard library, even if Qt cannot import."""
from __future__ import annotations
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile


def configure_logging() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    folder = base / "UnrealPipelineManager" / "logs"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        folder = Path(tempfile.gettempdir()) / "UnrealPipelineManager-logs"
        folder.mkdir(parents=True, exist_ok=True)
    path = folder / "application.log"
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
    return path


def startup_error(error: BaseException, log_path: Path | None) -> None:
    logging.exception("Application startup failed")
    if getattr(sys, "frozen", False):
        recovery = ("Run the original Setup executable again to repair the installation, "
                    "or extract a fresh copy of the entire portable ZIP. Python and modules are bundled; "
                    "installing pip packages will not repair this application.")
    else:
        recovery = "Run scripts/Start-Development.ps1 on Windows to create or repair the local Python environment."
    message = f"The application could not start.\n\n{error}\n\n{recovery}\n\nLog: {log_path or 'unavailable'}"
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, message, "Unreal Pipeline Manager — Startup Error", 0x10)
    elif sys.stderr:
        print(message, file=sys.stderr)
