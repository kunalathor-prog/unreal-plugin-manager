import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from app.core.preset_service import PresetService
from app.ui.main_window import MainWindow

APP = QApplication.instance() or QApplication([])

class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patches = [patch('app.ui.main_window.PresetService', return_value=PresetService(self.root / 'presets')),
                        patch('app.ui.main_window.EngineManager.scan_versions', return_value=[]),
                        patch('app.ui.main_window.QMessageBox.information')]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.settings = QSettings(str(self.root / "settings.ini"), QSettings.Format.IniFormat)
        self.window = MainWindow(settings=self.settings)
        self.addCleanup(self.close_window)

    def pump(self, condition):
        deadline = time.monotonic() + 10
        while not condition() and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(.002)
        self.assertTrue(condition())

    def close_window(self):
        self.window.close()
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        APP.processEvents()

    def select(self, name):
        folder = self.root / name
        folder.mkdir()
        (folder / f'{name}.uproject').write_text('{}')
        plugins = folder / 'Plugins' / name
        plugins.mkdir(parents=True)
        (plugins / f'{name}.uplugin').write_text(json.dumps({'EnabledByDefault': True}))
        self.window.detected_project_name.setText(name)
        self.window.detected_project_location.setText(str(folder))
        self.window.plugin_section.setEnabled(True)
        self.window.scan_all_plugins()

    def test_switch_during_scan_only_shows_current_project(self):
        self.select('First')
        first = self.window.active_scan_worker
        self.select('Second')
        self.assertIs(self.window.active_scan_worker, first)
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.assertEqual(set(self.window.plugin_checks), {'Second'})
        self.assertTrue(self.window.apply_plugins_btn.isEnabled())

    def test_close_during_scan_stops_worker(self):
        self.select('Closing')
        self.window.close()
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.assertTrue(self.window._closing)

    def test_workspace_restores_theme_paths_and_recent_project(self):
        self.select('Remember')
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        project = (self.root / 'Remember' / 'Remember.uproject').resolve()
        self.window.register_project(project)
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.window.toggle_theme()
        self.window.custom_plugin_path.setText(str(self.root / 'external'))
        self.close_window()
        self.window = MainWindow(settings=self.settings)
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.assertFalse(self.window.is_dark_mode)
        self.assertEqual(self.window.custom_plugin_path.text(), str(self.root / 'external'))
        self.assertEqual(self.window.get_registered_uproject_file(), project)
        self.assertEqual(self.window.recent_projects, [str(project)])

    def test_engine_selection_rescans(self):
        self.select('EngineChange')
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        engine = self.root / 'UE'
        plugins = engine / 'Engine' / 'Plugins' / 'EngineOnly'
        plugins.mkdir(parents=True)
        (plugins / 'EngineOnly.uplugin').write_text('{"EnabledByDefault": true}')
        self.window.version_combo.addItem('Test engine', str(engine))
        self.window.version_combo.setCurrentIndex(1)
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.assertIn('EngineOnly', self.window.plugin_checks)
        self.assertTrue(self.window.plugin_checks['EngineOnly'].isChecked())

    def test_cancelled_preview_leaves_project_untouched(self):
        from PySide6.QtWidgets import QMessageBox
        self.select('Cancel')
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        project = self.window.get_registered_uproject_file()
        original = project.read_bytes()
        self.window.plugin_checks['Cancel'].setChecked(False)
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Cancel):
            self.window.apply_plugins()
        self.assertEqual(project.read_bytes(), original)
        self.assertFalse(project.with_suffix('.uproject.bak').exists())

    def test_confirmed_preview_applies_and_rescans(self):
        from PySide6.QtWidgets import QMessageBox
        self.select('Apply')
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.window.plugin_checks['Apply'].setChecked(False)
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Apply):
            self.window.apply_plugins()
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        project = self.window.get_registered_uproject_file()
        self.assertEqual(json.loads(project.read_text())['Plugins'], [{'Name': 'Apply', 'Enabled': False}])
        self.assertFalse(self.window.plugin_checks['Apply'].isChecked())

    def test_missing_preset_cancel_preserves_selection(self):
        from PySide6.QtWidgets import QMessageBox
        self.select('Available')
        self.pump(lambda: self.window.active_scan_worker is None and self.window.operation_worker is None)
        self.window.preset_service.save_preset('Missing', ['Unavailable'])
        self.window.refresh_presets()
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.No):
            self.window.load_plugin_preset()
        self.assertTrue(self.window.plugin_checks['Available'].isChecked())

    def test_close_waits_for_file_operation(self):
        import threading
        gate = threading.Event()
        self.addCleanup(gate.set)
        self.window.start_operation(lambda: gate.wait(2), 'Finished')
        self.assertFalse(self.window.project_section.isEnabled())
        self.window.close()
        self.assertIsNotNone(self.window.operation_worker)
        gate.set()
        self.pump(lambda: self.window.operation_worker is None)
        APP.processEvents()
        self.assertTrue(self.window._closing)

    def prepare_config_source(self):
        source = self.root / 'Source' / 'Source.uproject'
        source.parent.mkdir()
        source.write_text('{}')
        config = source.parent / 'Config'
        config.mkdir()
        (config / 'DefaultEngine.ini').write_text('[Render]\nQuality=3\n')
        self.window.config_source_edit.setText(str(source))
        target = self.window.get_registered_uproject_file().parent / 'Config'
        target.mkdir()
        file = target / 'DefaultEngine.ini'
        file.write_text('[Render]\nQuality=1\nKeep=2\n')
        return file

    def test_config_preview_cancel_writes_nothing(self):
        from PySide6.QtWidgets import QMessageBox
        self.select('ConfigCancel')
        self.pump(lambda: self.window.active_scan_worker is None)
        target = self.prepare_config_source()
        original = target.read_bytes()
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Cancel):
            self.window.preview_config_merge()
        self.assertEqual(target.read_bytes(), original)
        self.assertFalse((target.parent.parent / '.pipeline-config-backups').exists())

    def test_config_merge_preserves_unsaved_plugin_selection(self):
        from PySide6.QtWidgets import QMessageBox
        self.select('ConfigApply')
        self.pump(lambda: self.window.active_scan_worker is None)
        target = self.prepare_config_source()
        self.window.plugin_checks['ConfigApply'].setChecked(False)
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Apply):
            self.window.preview_config_merge()
        self.pump(lambda: self.window.operation_worker is None)
        self.assertIn('Quality=3', target.read_text())
        self.assertIn('Keep=2', target.read_text())
        self.assertFalse(self.window.plugin_checks['ConfigApply'].isChecked())
        self.assertEqual(len(list((target.parent.parent / '.pipeline-config-backups').glob('*.json'))), 1)

    def test_config_restore_through_ui(self):
        from PySide6.QtWidgets import QMessageBox
        self.select('ConfigRestore')
        self.pump(lambda: self.window.active_scan_worker is None)
        target = self.prepare_config_source()
        original = target.read_bytes()
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Apply):
            self.window.preview_config_merge()
        self.pump(lambda: self.window.operation_worker is None)
        backup = next((target.parent.parent / '.pipeline-config-backups').glob('*.json'))
        with patch('app.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(backup), '')), patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Apply):
            self.window.restore_config_backup()
        self.pump(lambda: self.window.operation_worker is None)
        self.assertEqual(target.read_bytes(), original)
