"""Packaged smoke test: exercises actual bundled Qt without using customer projects."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import time
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPixmap
from app.core.plugin_service import PluginService
from app.core.project_manager import ProjectManager
from app.ui.main_window import MainWindow


def run_self_test(app) -> int:
    with tempfile.TemporaryDirectory(prefix="pipeline-smoke-") as folder:
        root = Path(folder)
        project = root / "Smoke.uproject"
        project.write_text('{"FileVersion": 3}', encoding="utf-8")
        plugin = root / "Plugins" / "SmokePlugin"
        plugin.mkdir(parents=True)
        (plugin / "SmokePlugin.uplugin").write_text('{"EnabledByDefault": true}', encoding="utf-8")
        settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
        window = MainWindow(settings=settings, preset_dir=root / "presets", discover_engines=False)
        try:
            resource = Path(__file__).parent / "resources" / "pipeline.ico"
            if QPixmap(str(resource)).isNull():
                raise RuntimeError("Bundled application icon is missing or unreadable.")
            window.show()
            window.register_project(project)
            deadline = time.monotonic() + 15
            while window.active_scan_worker is not None and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.005)
            if window.active_scan_worker is not None:
                raise RuntimeError("Plugin scan timed out.")
            if not window.plugin_checks["SmokePlugin"].isChecked():
                raise RuntimeError("Incorrect default plugin state.")
            PluginService.apply(project, {"SmokePlugin": False}, window.plugins, window.scan_snapshot)
            if ProjectManager.load_descriptor(project)["Plugins"][0]["Enabled"] is not False:
                raise RuntimeError("Descriptor update failed.")
            ProjectManager.restore_backup(project)
            if json.loads(project.read_text(encoding="utf-8")) != {"FileVersion": 3}:
                raise RuntimeError("Descriptor backup restore failed.")
            return 0
        finally:
            window.close()
            if window.active_scan_worker is not None:
                window.active_scan_worker.requestInterruption()
                window.active_scan_worker.wait()
            app.processEvents()
