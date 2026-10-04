import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.core.config_service import ConfigService, merge_ini
from app.core.project_manager import ProjectManager


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Source' / 'Source.uproject'
        self.target = self.root / 'Target' / 'Target.uproject'
        for project in (self.source, self.target):
            project.parent.mkdir()
            project.write_text('{}')

    def config(self, project, relative, data):
        path = project.parent / 'Config' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_scalar_override_preserves_unrelated_settings_and_comments(self):
        result = merge_ini(b'; keep\r\n[Render]\r\nQuality=1\r\nOther=2\r\n', b'[render]\nquality=3\nNew=4\n')
        self.assertEqual(result, b'; keep\r\n[Render]\r\nquality=3\r\nOther=2\r\nNew=4\r\n')

    def test_array_group_replaced_in_source_order_with_repeated_sections(self):
        source = b'[Input]\n!Actions=ClearArray\n+Actions=A\n.Actions=A\n[Input]\n-Actions=B\n'
        target = b'[Input]\n+Actions=Old\nOther=1\n[Input]\n.Actions=Old\n'
        result = merge_ini(target, source)
        self.assertNotIn(b'Old', result)
        self.assertIn(b'!Actions=ClearArray\n+Actions=A\n.Actions=A\n-Actions=B\n', result)
        self.assertIn(b'Other=1', result)
        self.assertEqual(merge_ini(result, source), result)

    def test_new_sections_and_no_final_newline(self):
        result = merge_ini(b'[Existing]\nKeep=1', b'[Existing]\nNew=2\n[Added]\nValue=3\n')
        self.assertIn(b'Keep=1\nNew=2\n[Added]\nValue=3\n', result)

    def test_unicode_and_bom(self):
        target = '[Section]\r\nName=old\r\n'.encode('utf-16')
        result = merge_ini(target, '[Section]\nName=हेलो\n'.encode('utf-8-sig'))
        self.assertIn('Name=हेलो', result.decode('utf-16'))

    def test_recursive_merge_backup_restore_and_preserved_target_only_file(self):
        self.config(self.source, 'DefaultEngine.ini', b'[A]\nx=2\n')
        self.config(self.source, 'Windows/WindowsEngine.ini', b'[B]\ny=3\n')
        self.config(self.source, 'Readme.txt', b'not a setting')
        dest = self.config(self.target, 'DefaultEngine.ini', b'[A]\nx=1\nkeep=4\n')
        extra = self.config(self.target, 'DefaultInput.ini', b'[C]\nz=5\n')
        before = dest.read_bytes()
        plan = ConfigService.plan(self.source, self.target)
        self.assertEqual(plan.skipped, ('Readme.txt',))
        self.assertEqual(len(plan.changes), 2)
        backup = ConfigService.apply(plan)
        self.assertIn(b'x=2', dest.read_bytes())
        self.assertIn(b'keep=4', dest.read_bytes())
        self.assertEqual(extra.read_bytes(), b'[C]\nz=5\n')
        self.assertFalse(ConfigService.plan(self.source, self.target).changes)
        ConfigService.apply(ConfigService.restore_plan(self.target, backup))
        self.assertEqual(dest.read_bytes(), before)
        self.assertFalse((self.target.parent / 'Config/Windows/WindowsEngine.ini').exists())

    def test_external_edit_aborts_before_any_write(self):
        self.config(self.source, 'DefaultEngine.ini', b'[A]\nx=2\n')
        dest = self.config(self.target, 'DefaultEngine.ini', b'[A]\nx=1\n')
        plan = ConfigService.plan(self.source, self.target)
        dest.write_bytes(b'[A]\nx=9\n')
        with self.assertRaises(ValueError):
            ConfigService.apply(plan)
        self.assertEqual(dest.read_bytes(), b'[A]\nx=9\n')

    def test_multi_file_failure_rolls_back_previous_write(self):
        for name in ('A.ini', 'B.ini'):
            self.config(self.source, name, b'[A]\nx=2\n')
            self.config(self.target, name, b'[A]\nx=1\n')
        plan = ConfigService.plan(self.source, self.target)
        original_write = ProjectManager.atomic_write
        def write(path, data):
            if path.name == 'B.ini' and b'x=2' in data:
                raise OSError('disk full')
            original_write(path, data)
        with patch.object(ProjectManager, 'atomic_write', side_effect=write), self.assertRaises(RuntimeError):
            ConfigService.apply(plan)
        for name in ('A.ini', 'B.ini'):
            self.assertEqual((self.target.parent / 'Config' / name).read_bytes(), b'[A]\nx=1\n')

    def test_restore_refuses_later_edits_and_wrong_project(self):
        self.config(self.source, 'A.ini', b'[A]\nx=2\n')
        dest = self.config(self.target, 'A.ini', b'[A]\nx=1\n')
        backup = ConfigService.apply(ConfigService.plan(self.source, self.target))
        with self.assertRaises(ValueError):
            ConfigService.restore_plan(self.source, backup)
        dest.write_bytes(b'[A]\nx=9\n')
        with self.assertRaises(ValueError):
            ConfigService.restore_plan(self.target, backup)

    def test_same_project_and_unsupported_syntax_rejected(self):
        self.config(self.source, 'A.ini', b'[A]\nx=1\n')
        with self.assertRaises(ValueError):
            ConfigService.plan(self.source, self.source)
        self.config(self.source, 'A.ini', b'[A]\nunsupported\n')
        with self.assertRaises(ValueError):
            ConfigService.plan(self.source, self.target)

    def test_backup_path_traversal_rejected(self):
        backup = self.root / 'bad.json'
        backup.write_text(json.dumps({'version': 1, 'target': str((self.target.parent / 'Config').resolve()),
            'files': [{'path': '../outside.ini', 'before': None, 'after_sha256': None}]}))
        with self.assertRaises(ValueError):
            ConfigService.restore_plan(self.target, backup)

    def test_target_symlink_cannot_escape_config(self):
        self.config(self.source, 'A.ini', b'[A]\nx=2\n')
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.target.parent / 'Config').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        with self.assertRaises(ValueError):
            ConfigService.plan(self.source, self.target)
        self.assertEqual(list(outside.iterdir()), [])

    def test_apply_to_project_without_config_and_restore(self):
        self.config(self.source, 'DefaultGame.ini', b'[Game]\nProjectID=source-id\n')
        backup = ConfigService.apply(ConfigService.plan(self.source, self.target))
        dest = self.target.parent / 'Config/DefaultGame.ini'
        self.assertIn(b'ProjectID=source-id', dest.read_bytes())
        ConfigService.apply(ConfigService.restore_plan(self.target, backup))
        self.assertFalse(dest.exists())
