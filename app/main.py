from __future__ import annotations
import logging
from pathlib import Path
import sys

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from app.version import APP_NAME, VERSION


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("UnrealPipelineManager")
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "resources" / "pipeline.ico")))
    if "--self-test" in sys.argv:
        from app.self_test import run_self_test
        return run_self_test(app)

    data = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    data.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data / "application.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, APP_NAME, "The application is already running, or its application-data folder is not writable.")
        return 1

    def exception_hook(kind, error, traceback):
        logging.error("Unhandled application error", exc_info=(kind, error, traceback))
        QMessageBox.critical(None, "Application Error", f"{error}\n\nRestart the app before making further changes. Details are in the diagnostic log.")

    sys.excepthook = exception_hook
    from app.ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    logging.info("Started %s %s", APP_NAME, VERSION)
    try:
        return app.exec()
    finally:
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
