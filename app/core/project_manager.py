from __future__ import annotations
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional


class ProjectManager:
    @staticmethod
    def find_uproject(folder_path: Path) -> Optional[Path]:
        matches = sorted(folder_path.glob("*.uproject")) if folder_path.is_dir() else []
        if len(matches) > 1:
            raise ValueError("Multiple .uproject files found. Select a project file instead.")
        return matches[0] if matches else None

    @staticmethod
    def load_descriptor(project_file: Path) -> dict:
        data = json.loads(project_file.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("Plugins", []), list):
            raise ValueError("Invalid project descriptor.")
        for entry in data.get("Plugins", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("Name"), str):
                raise ValueError("Each plugin reference must have a name.")
            if "Enabled" in entry and not isinstance(entry["Enabled"], bool):
                raise ValueError("Plugin Enabled values must be booleans.")
        return data

    @staticmethod
    def atomic_write(path: Path, data: bytes) -> None:
        fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            if path.exists():
                shutil.copymode(path, temporary)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def save_descriptor(cls, project_file: Path, descriptor: dict) -> None:
        # Keep the immediately preceding version for undo, rather than the first-ever save.
        cls.atomic_write(project_file.with_suffix(".uproject.bak"), project_file.read_bytes())
        cls.atomic_write(project_file, (json.dumps(descriptor, indent=4) + "\n").encode())

    @classmethod
    def restore_backup(cls, project_file: Path) -> None:
        backup = project_file.with_suffix(".uproject.bak")
        cls.load_descriptor(backup)
        data = backup.read_bytes()
        cls.atomic_write(project_file.with_suffix(".uproject.before-restore"), project_file.read_bytes())
        cls.atomic_write(project_file, data)
