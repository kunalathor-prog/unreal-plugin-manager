from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from app.core.plugin_service import enabled_state


class PluginScanWorker(QThread):
    scan_completed = Signal(dict)
    scan_failed = Signal(str)
    progress = Signal(str)

    def __init__(self, roots: list[tuple[Path, str]], enabled_in_project: dict[str, bool], disable_engine_defaults: bool = False) -> None:
        super().__init__()
        self.roots = roots
        self.enabled_in_project = enabled_in_project
        self.disable_engine_defaults = disable_engine_defaults

    def run(self) -> None:
        plugins: dict[str, dict] = {}
        priority = {"Engine": 0, "Custom": 1, "Project": 2}
        try:
            for root, origin in self.roots:
                if not root.is_dir():
                    continue
                for file in root.rglob("*.uplugin"):
                    if self.isInterruptionRequested():
                        return
                    if any(part.startswith(".plugin-import-") for part in file.parts):
                        continue
                    try:
                        meta = json.loads(file.read_text(encoding="utf-8-sig"))
                        if not isinstance(meta, dict):
                            raise ValueError("Descriptor must be an object")
                        internal = file.stem
                        if internal in plugins and priority[plugins[internal]["origin"]] >= priority[origin]:
                            continue
                        plugins[internal] = {
                            "internal": internal,
                            "friendly": str(meta.get("FriendlyName") or internal),
                            "descriptor": file, "plugin_dir": file.parent, "origin": origin,
                            "enabled": enabled_state(meta, origin, self.enabled_in_project.get(internal), self.disable_engine_defaults),
                            "description": str(meta.get("Description", "")),
                            "version": str(meta.get("VersionName", meta.get("Version", "Unknown"))),
                        }
                        if len(plugins) % 50 == 0:
                            self.progress.emit(f"Scanning… {len(plugins)} plugins found")
                    except (OSError, UnicodeError, ValueError) as exc:
                        self.progress.emit(f"Skipped {file.name}: {exc}")
            if not self.isInterruptionRequested():
                self.scan_completed.emit(plugins)
        except Exception as exc:
            self.scan_failed.emit(str(exc))
