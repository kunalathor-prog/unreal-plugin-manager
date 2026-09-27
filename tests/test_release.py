import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from app import diagnostics
from app.workers.operation_worker import OperationWorker


class ReleaseTests(unittest.TestCase):
    def test_windows_startup_failure_reports_repair_without_pip(self):
        native = Mock()
        with patch.object(diagnostics.sys, 'platform', 'win32'), \
             patch.object(diagnostics.sys, 'frozen', True, create=True), \
             patch.object(diagnostics.ctypes, 'windll', native, create=True), \
             patch.object(diagnostics.logging, 'exception'):
            diagnostics.startup_error(ModuleNotFoundError('PySide6'), Path('test.log'))
        message = native.user32.MessageBoxW.call_args.args[1]
        self.assertIn('Setup executable', message)
        self.assertIn('Python and modules are bundled', message)

    def test_rotating_log_writes_to_configured_local_data(self):
        with tempfile.TemporaryDirectory() as temp:
            before = list(logging.getLogger().handlers)
            old_level = logging.getLogger().level
            with patch.dict(diagnostics.os.environ, {'LOCALAPPDATA': temp}):
                try:
                    path = diagnostics.configure_logging()
                    logging.info('release test')
                    self.assertTrue(path.is_relative_to(Path(temp)))
                    self.assertIn('release test', path.read_text(encoding='utf-8'))
                finally:
                    logging.getLogger().setLevel(old_level)
                    for handler in list(logging.getLogger().handlers):
                        if handler not in before:
                            logging.getLogger().removeHandler(handler)
                            handler.close()

    def test_operation_worker_reports_exception(self):
        def fail():
            raise OSError('disk full')
        worker = OperationWorker(fail)
        with patch('app.workers.operation_worker.logging.exception'):
            worker.run()
        self.assertEqual(worker.error, 'disk full')
