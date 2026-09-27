import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.engine_manager import EngineManager

class EngineTests(unittest.TestCase):
    def test_source_build_with_arbitrary_folder_name_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'MySourceBuild'
            root.mkdir()
            with patch.object(EngineManager, 'editor_for_root', side_effect=lambda p: p if p == root else None):
                found = EngineManager.scan_versions(str(root))
            self.assertIn(('MySourceBuild', root), found)

    def test_mac_launch_passes_project_as_argument(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'Project with spaces.uproject'
            project.write_text('{}')
            editor = Path(temp) / 'UnrealEditor.app'
            with patch('app.core.engine_manager.sys.platform', 'darwin'), patch.object(EngineManager, 'editor_for_root', return_value=editor), patch('app.core.engine_manager.subprocess.Popen') as launch:
                EngineManager.launch(Path(temp), project)
            launch.assert_called_once_with(['open', '-a', str(editor), '--args', str(project)])

    def test_windows_launch_uses_argument_list_for_spaced_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'Project with spaces.uproject'
            project.write_text('{}')
            editor = Path(temp) / 'UnrealEditor.exe'
            with patch('app.core.engine_manager.sys.platform', 'win32'), patch.object(EngineManager, 'editor_for_root', return_value=editor), patch('app.core.engine_manager.subprocess.Popen') as launch:
                EngineManager.launch(Path(temp), project)
            launch.assert_called_once_with([str(editor), str(project)])
