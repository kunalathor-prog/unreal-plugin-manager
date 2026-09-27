from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

class EngineManager:
    @staticmethod
    def get_default_install_dir() -> str:
        if os.name == "nt":
            return r"C:\Program Files\Epic Games"
        elif sys.platform == "darwin":
            return "/Users/Shared/Epic Games"
        return str(Path.home() / "Epic Games")

    @staticmethod
    def editor_for_root(root: Path) -> Optional[Path]:
        if root.suffix == ".app" and root.exists():
            return root
        if sys.platform == "darwin":
            candidates = [
                root / "Engine/Binaries/Mac/UnrealEditor.app",
                root / "Engine/Binaries/Mac/UnrealEditor"
            ]
        elif os.name == "nt":
            candidates = [
                root / "Engine/Binaries/Win64/UnrealEditor.exe"
            ]
        else:
            candidates = [
                root / "Engine/Binaries/Linux/UnrealEditor"
            ]
        return next((p for p in candidates if p.exists()), None)

    @classmethod
    def scan_versions(cls, custom_root: str = "") -> list[tuple[str, Path]]:
        roots: list[Path] = []
        if custom_root.strip():
            roots.append(Path(custom_root.strip()).expanduser())

        if sys.platform == "darwin":
            roots.extend([Path("/Users/Shared/Epic Games"), Path("/Users/Shared/UnrealEngine")])
        elif os.name == "nt":
            roots.extend([Path("C:/Program Files/Epic Games"), Path("D:/Epic Games")])
        else:
            roots.extend([Path.home() / "Epic Games", Path("/opt/UnrealEngine")])

        found: list[Path] = []
        for base in roots:
            if not base.exists() or not base.is_dir():
                continue
            if cls.editor_for_root(base):
                found.append(base)
            else:
                for folder in base.iterdir():
                    if folder.is_dir() and cls.editor_for_root(folder):
                        found.append(folder)

        unique = sorted({str(p): p for p in found}.values(), key=lambda p: p.name)
        return [(folder.name, folder) for folder in unique]

    @classmethod
    def launch(cls, engine_path: Path, project_file: Optional[Path] = None) -> None:
        editor = cls.editor_for_root(engine_path)
        if not editor:
            raise FileNotFoundError(f"UnrealEditor binary not found in: {engine_path}")

        if sys.platform == "darwin" and editor.suffix == ".app":
            args = ["open", "-a", str(editor)]
            if project_file and project_file.is_file():
                args.extend(["--args", str(project_file)])
            subprocess.Popen(args)
        else:
            args = [str(editor)]
            if project_file and project_file.is_file():
                args.append(str(project_file))
            subprocess.Popen(args)