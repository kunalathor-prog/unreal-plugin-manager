from __future__ import annotations
import json
import re
from pathlib import Path
from app.core.project_manager import ProjectManager


class PresetService:
    def __init__(self, preset_dir: Path | None = None) -> None:
        self.preset_dir = preset_dir or (Path.home() / "UnrealPluginPresets")
        self.preset_dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> list[tuple[str, Path]]:
        return [(file.stem, file) for file in sorted(self.preset_dir.glob("*.json"))]

    @staticmethod
    def validate_name(name: str) -> str:
        name = name.strip()
        if (not name or len(name) > 100 or name in (".", "..") or name.endswith(".")
                or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
                or re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', name)):
            raise ValueError("Use a preset name of 1–100 characters without path separators or reserved filename characters.")
        return name

    @staticmethod
    def validate_plugins(plugins) -> list[str]:
        if not isinstance(plugins, list) or any(not isinstance(p, str) or not p.strip() for p in plugins):
            raise ValueError("preset_plugins must be a list of non-empty plugin names.")
        return sorted(set(plugins))

    def save_preset(self, name: str, enabled_plugins: list[str], overwrite: bool = False) -> Path:
        name = self.validate_name(name)
        path = self.preset_dir / f"{name}.json"
        if path.exists() and not overwrite:
            raise FileExistsError(f"Preset '{name}' already exists.")
        self.export_preset(path, name, enabled_plugins)
        return path

    def load_preset(self, preset_path: Path) -> list[str]:
        data = json.loads(preset_path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or "preset_plugins" not in data:
            raise ValueError("Not a plugin preset: missing preset_plugins list.")
        return self.validate_plugins(data["preset_plugins"])

    def import_preset(self, source: Path, overwrite: bool = False) -> Path:
        return self.save_preset(source.stem, self.load_preset(source), overwrite)

    @classmethod
    def export_preset(cls, path: Path, name: str, plugins: list[str]) -> None:
        plugins = cls.validate_plugins(plugins)
        data = {"name": name, "plugin_count": len(plugins), "preset_plugins": plugins}
        ProjectManager.atomic_write(path, (json.dumps(data, indent=4) + "\n").encode())
