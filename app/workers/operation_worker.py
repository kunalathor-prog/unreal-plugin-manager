"""Run file transactions without blocking Qt's event loop."""
import logging
from PySide6.QtCore import QThread


class OperationWorker(QThread):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.error = ""

    def run(self):
        try:
            self.operation()
        except Exception as exc:
            self.error = str(exc)
            logging.exception("File operation failed")
