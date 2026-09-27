import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.plugin_service import PluginService, enabled_state
from app.core.project_manager import ProjectManager
from app.workers.scan_worker import PluginScanWorker

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def plugin(self, folder, **meta):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'Example.uplugin').write_text(json.dumps(meta))
        return folder

    def test_defaults_and_overrides(self):
        self.assertTrue(enabled_state({'EnabledByDefault': True}, 'Engine', None))
        self.assertFalse(enabled_state({'EnabledByDefault': True}, 'Engine', False))
        self.assertFalse(enabled_state({'EnabledByDefault': False}, 'Project', None))
        self.assertTrue(enabled_state({}, 'Project', None))
        self.assertFalse(enabled_state({}, 'Engine', None))
        self.assertFalse(enabled_state({'EnabledByDefault': True}, 'Custom', None))
        self.assertFalse(enabled_state({'EnabledByDefault': True}, 'Engine', None, True))
        self.assertTrue(enabled_state({}, 'Engine', True, True))

    def test_scanner_project_wins_and_filename_is_identity(self):
        roots = [(self.plugin(self.root / origin, Name='Wrong'), origin) for origin in ('Project', 'Engine', 'Custom')]
        worker = PluginScanWorker(roots, {})
        result = []
        worker.scan_completed.connect(result.append)
        worker.run()
        self.assertEqual(result[0]['Example']['origin'], 'Project')
        self.assertNotIn('Wrong', result[0])

    def test_changes_preserve_metadata_and_unavailable_references(self):
        original = {'Plugins': [{'Name': 'Missing', 'Enabled': True}, {'Name': 'Example', 'Enabled': True, 'PlatformAllowList': ['Win64']}]}
        updated = PluginService.updated_descriptor(original, {'Example': False, 'Default': False}, {'Example': {'enabled': True}, 'Default': {'enabled': True}})
        entries = {p['Name']: p for p in updated['Plugins']}
        self.assertFalse(entries['Default']['Enabled'])
        self.assertEqual(entries['Example']['PlatformAllowList'], ['Win64'])
        self.assertTrue(entries['Missing']['Enabled'])
        self.assertTrue(original['Plugins'][1]['Enabled'])

    def test_copy_failure_keeps_original(self):
        src = self.plugin(self.root / 'source')
        dst = self.plugin(self.root / 'dest', Description='original')
        before = (dst / 'Example.uplugin').read_bytes()
        with patch('app.core.plugin_service.shutil.copytree', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                PluginService.transact([(src, dst)])
        self.assertEqual((dst / 'Example.uplugin').read_bytes(), before)

    def test_commit_failure_rolls_back_all_copies(self):
        src = self.plugin(self.root / 'source')
        dst = self.plugin(self.root / 'dest', Description='original')
        new = self.root / 'new'
        before = (dst / 'Example.uplugin').read_bytes()
        def fail():
            raise OSError('save failed')
        with self.assertRaises(OSError):
            PluginService.transact([(src, dst), (src, new)], fail)
        self.assertEqual((dst / 'Example.uplugin').read_bytes(), before)
        self.assertFalse(new.exists())
        self.assertFalse(list(self.root.glob('.plugin-import-*')))

    def test_overlap_rejected(self):
        src = self.plugin(self.root / 'source')
        for dest in (src, src / 'child', self.root):
            with self.assertRaises(ValueError):
                PluginService.transact([(src, dest)])
        self.assertTrue((src / 'Example.uplugin').exists())

    def test_latest_backup_and_restore(self):
        project = self.root / 'Game.uproject'
        project.write_text('{"Description": "original"}')
        ProjectManager.save_descriptor(project, {'Description': 'first'})
        ProjectManager.save_descriptor(project, {'Description': 'second'})
        ProjectManager.restore_backup(project)
        self.assertEqual(ProjectManager.load_descriptor(project)['Description'], 'first')
        self.assertEqual(json.loads(project.with_suffix('.uproject.before-restore').read_text())['Description'], 'second')

    def test_changed_project_is_not_overwritten(self):
        project = self.root / 'Game.uproject'
        project.write_text('{}')
        expected = project.read_bytes()
        project.write_text('{"Description": "external edit"}')
        with self.assertRaises(ValueError):
            PluginService.apply(project, {}, {}, expected)
        self.assertEqual(ProjectManager.load_descriptor(project)['Description'], 'external edit')

    def test_apply_copies_plugin_and_keeps_original_descriptor_backup(self):
        project = self.root / 'Game.uproject'
        original = '{"Description": "Keep me", "Plugins": [{"Name": "Unavailable", "Enabled": true}]}'
        project.write_text(original)
        src = self.plugin(self.root / 'external' / 'Example')
        plugins = {'Example': {'enabled': False, 'origin': 'Custom', 'plugin_dir': src}}
        PluginService.apply(project, {'Example': True}, plugins, project.read_bytes())
        self.assertTrue((self.root / 'Plugins' / 'Example' / 'Example.uplugin').is_file())
        result = ProjectManager.load_descriptor(project)
        self.assertEqual(result['Description'], 'Keep me')
        self.assertEqual({p['Name'] for p in result['Plugins']}, {'Example', 'Unavailable'})
        self.assertEqual(project.with_suffix('.uproject.bak').read_text(), original)

    def test_atomic_write_failure_keeps_project_and_removes_temp(self):
        project = self.root / 'Game.uproject'
        project.write_text('{}')
        with patch.object(Path, 'replace', side_effect=OSError('write denied')):
            with self.assertRaises(OSError):
                ProjectManager.atomic_write(project, b'{"changed": true}')
        self.assertEqual(project.read_text(), '{}')
        self.assertEqual(list(self.root.iterdir()), [project])

    def test_invalid_backup_cannot_replace_project(self):
        project = self.root / 'Game.uproject'
        project.write_text('{}')
        project.with_suffix('.uproject.bak').write_text('not json')
        with self.assertRaises(ValueError):
            ProjectManager.restore_backup(project)
        self.assertEqual(project.read_text(), '{}')

    def test_duplicate_copy_destinations_rejected_before_replacement(self):
        src = self.plugin(self.root / 'source')
        dst = self.plugin(self.root / 'dest', Description='original')
        with self.assertRaises(ValueError):
            PluginService.transact([(src, dst), (src, dst)])
        self.assertEqual(json.loads((dst / 'Example.uplugin').read_text())['Description'], 'original')

    def test_corrupt_plugin_skipped_with_diagnostic(self):
        folder = self.plugin(self.root / 'plugins')
        (folder / 'Broken.uplugin').write_text('[]')
        worker = PluginScanWorker([(folder, 'Project')], {})
        results, messages = [], []
        worker.scan_completed.connect(results.append)
        worker.progress.connect(messages.append)
        worker.run()
        self.assertEqual(set(results[0]), {'Example'})
        self.assertIn('Broken.uplugin', messages[0])
