import json
import tempfile
import unittest
from pathlib import Path
from app.core.preset_service import PresetService

class PresetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = PresetService(self.root / 'presets')

    def test_empty_preset_round_trip(self):
        path = self.service.save_preset('Empty', [])
        self.assertEqual(self.service.load_preset(path), [])

    def test_unsafe_names_rejected(self):
        for name in ('../escape', '/absolute', 'a/b', 'a\\b', '..', 'NUL', 'CON.txt', 'bad?', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.service.save_preset(name, [])
        self.assertEqual(list(self.service.preset_dir.iterdir()), [])

    def test_import_export_and_explicit_overwrite(self):
        source = self.root / 'Shared.json'
        self.service.export_preset(source, 'Shared', ['B', 'A', 'B'])
        imported = self.service.import_preset(source)
        self.assertEqual(self.service.load_preset(imported), ['A', 'B'])
        with self.assertRaises(FileExistsError):
            self.service.save_preset('Shared', [])
        self.service.save_preset('Shared', [], overwrite=True)
        self.assertEqual(self.service.load_preset(imported), [])

    def test_invalid_payloads_rejected(self):
        source = self.root / 'Bad.json'
        for value in ([], {}, {'preset_plugins': 'Example'}, {'preset_plugins': [3]}):
            source.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                self.service.import_preset(source)
        self.assertFalse((self.service.preset_dir / 'Bad.json').exists())
