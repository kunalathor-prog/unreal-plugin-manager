from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QTabWidget, QGridLayout, QGroupBox,
    QCheckBox, QComboBox, QPlainTextEdit, QMessageBox, QFileDialog,
    QSizePolicy, QFrame
)

from app.version import APP_NAME, VERSION
from app.core.config_service import ConfigService
from app.core.plugin_service import PluginService
from app.core.engine_manager import EngineManager
from app.core.project_manager import ProjectManager
from app.core.preset_service import PresetService
from app.workers.scan_worker import PluginScanWorker
from app.workers.operation_worker import OperationWorker
from app.ui.accordion import AccordionSection
from app.ui.styles import THEME_DARK, THEME_LIGHT

class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None, preset_dir: Path | None = None, discover_engines: bool = True) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setMinimumSize(980, 720)
        self.resize(1180, 950)
        self.settings = settings if settings is not None else QSettings("UnrealPipelineManager", "Desktop")
        self.is_dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.recent_projects = self.settings.value("recent_projects", [], type=list)

        self.preset_service = PresetService(preset_dir)
        self.plugin_checks: dict[str, QCheckBox] = {}
        self.active_scan_worker: Optional[PluginScanWorker] = None

        self.operation_worker = None
        self._operation_message = ""
        self._operation_rescan = True
        self.plugins = {}
        self.scan_snapshot = b""
        self._scan_generation = 0
        self._scan_pending = False
        self._closing = False
        self._build_ui()
        self.engine_root_path.setText(self.settings.value("engine_root", EngineManager.get_default_install_dir(), type=str))
        self.custom_plugin_path.setText(self.settings.value("custom_plugins", "", type=str))
        self.apply_theme()
        if discover_engines:
            self.populate_versions()
        else:
            self.version_combo.addItem("No engine selected", "")
        self.refresh_presets()
        self.version_combo.currentIndexChanged.connect(self.scan_all_plugins)
        self.engine_root_path.editingFinished.connect(self.populate_versions)
        self.custom_plugin_path.editingFinished.connect(self.scan_all_plugins)
        self.refresh_recent_projects()
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        last_project = self.settings.value("last_project", "", type=str)
        if last_project and Path(last_project).is_file():
            self.register_project(Path(last_project))

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 14, 20, 16)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        # Top Bar: Theme Toggle right above the banner
        top_bar_layout = QHBoxLayout()
        about_btn = QPushButton("About")
        about_btn.clicked.connect(self.show_about)
        top_bar_layout.addWidget(about_btn)
        top_bar_layout.addStretch(1)
        self.theme_btn = QPushButton("☀️ Light Mode")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setFixedSize(130, 38)
        top_bar_layout.addWidget(self.theme_btn)
        root_layout.addLayout(top_bar_layout)

        # Hero Banner
        self.hero_banner = QLabel()
        self.hero_banner.setObjectName("HeroBanner")
        self.hero_banner.setMinimumHeight(130)
        self.hero_banner.setMaximumHeight(160)
        self.hero_banner.setScaledContents(True)
        self.hero_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        banner_path = Path(__file__).resolve().parent.parent / "resources" / "unreal_pipeline_header.png"
        if banner_path.exists():
            self.hero_banner.setPixmap(QPixmap(str(banner_path)))
        else:
            self.hero_banner.setText("  UNREAL ENGINE  /  PIPELINE MANAGER\n  Configure environments, manage plugins and launch your projects.")
            self.hero_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(self.hero_banner)

        # Main Scroll Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 8, 4)
        layout.setSpacing(12)

        # ---------------- Section 1: Engine ----------------
        self.engine_section = AccordionSection("01  ·  Engine Configuration", "Select Unreal Engine installation and version.", True)
        e_layout = QVBoxLayout()
        e_row1 = QHBoxLayout()
        e_row1.addWidget(QLabel("Installation Directory:"))
        self.engine_root_path = QLineEdit(EngineManager.get_default_install_dir())
        e_row1.addWidget(self.engine_root_path, 1)
        browse_eng = QPushButton("📁 Browse")
        browse_eng.clicked.connect(self.browse_engine_root)
        e_row1.addWidget(browse_eng)
        scan_vers_btn = QPushButton("↻ Scan Versions")
        scan_vers_btn.clicked.connect(self.populate_versions)
        e_row1.addWidget(scan_vers_btn)
        e_layout.addLayout(e_row1)

        e_row2 = QHBoxLayout()
        e_row2.addWidget(QLabel("Active UE Version:"))
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(250)
        e_row2.addWidget(self.version_combo, 1)
        e_layout.addLayout(e_row2)
        self.engine_section.body_layout.addLayout(e_layout)
        layout.addWidget(self.engine_section)

        # ---------------- Section 2: Project ----------------
        self.project_section = AccordionSection("02  ·  Target Project", "Select an existing .uproject file to enable the Plugin Manager.", True)
        p_layout = QVBoxLayout()
        p_row1 = QHBoxLayout()
        p_row1.addWidget(QLabel("Project File:"))
        self.uproject_path_edit = QLineEdit()
        self.uproject_path_edit.setPlaceholderText("Select your .uproject file...")
        self.uproject_path_edit.setReadOnly(True)
        p_row1.addWidget(self.uproject_path_edit, 1)
        browse_proj = QPushButton("📁 Select Project")
        browse_proj.clicked.connect(self.browse_project_folder)
        p_row1.addWidget(browse_proj)
        p_layout.addLayout(p_row1)
        self.recent_combo = QComboBox()
        self.recent_combo.activated.connect(self.open_recent_project)
        p_layout.addWidget(self.recent_combo)

        p_row2 = QHBoxLayout()
        p_row2.addWidget(QLabel("Detected Name:"))
        self.detected_project_name = QLineEdit()
        self.detected_project_name.setReadOnly(True)
        self.detected_project_name.setPlaceholderText("Awaiting project selection...")
        p_row2.addWidget(self.detected_project_name, 1)
        p_layout.addLayout(p_row2)

        self.detected_project_location = QLineEdit()
        self.detected_project_location.setVisible(False)
        self.project_section.body_layout.addLayout(p_layout)
        layout.addWidget(self.project_section)

        # ---------------- Section 3: Plugins ----------------
        self.plugin_section = AccordionSection("03  ·  Plugin Environment", "Manage and configure plugins for the registered project.", True)
        self.plugin_section.setEnabled(False)

        self.plugin_status = QLabel("Register a project above to unlock plugin management.")
        self.plugin_status.setObjectName("StatusLabel")
        self.plugin_section.body_layout.addWidget(self.plugin_status)

        pl_row1 = QHBoxLayout()
        pl_row1.addWidget(QLabel("External Plugins (Optional):"))
        self.custom_plugin_path = QLineEdit()
        self.custom_plugin_path.setPlaceholderText("Path to centralized custom plugins...")
        pl_row1.addWidget(self.custom_plugin_path, 1)
        browse_cust = QPushButton("📁 Browse")
        browse_cust.clicked.connect(self.browse_custom_plugin_path)
        pl_row1.addWidget(browse_cust)
        rescan_all = QPushButton("↻ Rescan All")
        rescan_all.clicked.connect(self.scan_all_plugins)
        pl_row1.addWidget(rescan_all)
        self.plugin_section.body_layout.addLayout(pl_row1)

        pl_row2 = QHBoxLayout()
        self.plugin_count_label = QLabel("🔌 Plugins: 0 enabled / 0 total")
        self.plugin_count_label.setObjectName("pluginCount")
        pl_row2.addWidget(self.plugin_count_label)
        pl_row2.addStretch(1)
        self.plugin_search = QLineEdit()
        self.plugin_search.setPlaceholderText("⌕ Filter by name...")
        self.plugin_search.setMaximumWidth(250)
        self.plugin_search.textChanged.connect(self.filter_plugins)
        pl_row2.addWidget(self.plugin_search)
        self.show_enabled_only_cb = QCheckBox("Show Enabled Only")
        self.show_enabled_only_cb.stateChanged.connect(self.filter_plugins)
        pl_row2.addWidget(self.show_enabled_only_cb)
        self.plugin_section.body_layout.addLayout(pl_row2)

        self.plugin_type_tabs = QTabWidget()
        self.engine_plugin_scroll = QScrollArea()
        self.engine_plugin_scroll.setWidgetResizable(True)
        self.engine_plugin_container = QWidget()
        self.engine_plugin_layout = QVBoxLayout(self.engine_plugin_container)
        self.engine_plugin_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.engine_plugin_scroll.setWidget(self.engine_plugin_container)
        self.plugin_type_tabs.addTab(self.engine_plugin_scroll, "⚙️ Default Engine Plugins")

        custom_tab_widget = QWidget()
        custom_tab_layout = QVBoxLayout(custom_tab_widget)
        self.import_custom_btn = QPushButton("📥 Import New Plugin from Folder to Project...")
        self.import_custom_btn.clicked.connect(self.import_single_custom_plugin)
        custom_tab_layout.addWidget(self.import_custom_btn)

        self.custom_plugin_scroll = QScrollArea()
        self.custom_plugin_scroll.setWidgetResizable(True)
        self.custom_plugin_container = QWidget()
        self.custom_plugin_layout = QVBoxLayout(self.custom_plugin_container)
        self.custom_plugin_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.custom_plugin_scroll.setWidget(self.custom_plugin_container)
        custom_tab_layout.addWidget(self.custom_plugin_scroll)
        self.plugin_type_tabs.addTab(custom_tab_widget, "📦 Project & Custom Plugins")
        self.plugin_section.body_layout.addWidget(self.plugin_type_tabs, 1)

        # Presets GroupBox
        preset_box = QGroupBox("Plugin Presets")
        preset_layout = QGridLayout(preset_box)
        preset_layout.setSpacing(10)
        self.preset_name_edit = QLineEdit()
        self.preset_name_edit.setPlaceholderText("Name for new preset...")
        self.save_preset_btn = QPushButton("💾 Save Preset")
        self.save_preset_btn.clicked.connect(self.save_plugin_preset)

        self.preset_combo = QComboBox()
        self.load_preset_btn = QPushButton("📂 Load Preset")
        self.load_preset_btn.clicked.connect(self.load_plugin_preset)

        preset_layout.addWidget(QLabel("Save Current Layout:"), 0, 0)
        preset_layout.addWidget(self.preset_name_edit, 0, 1)
        preset_layout.addWidget(self.save_preset_btn, 0, 2)
        preset_layout.addWidget(QLabel("Load Saved Layout:"), 1, 0)
        preset_layout.addWidget(self.preset_combo, 1, 1)
        preset_layout.addWidget(self.load_preset_btn, 1, 2)
        self.import_preset_btn = QPushButton("Import Preset…")
        self.export_preset_btn = QPushButton("Export Checked Plugins…")
        self.import_preset_btn.clicked.connect(self.import_plugin_preset)
        self.export_preset_btn.clicked.connect(self.export_plugin_preset)
        preset_layout.addWidget(self.import_preset_btn, 2, 1)
        preset_layout.addWidget(self.export_preset_btn, 2, 2)
        self.plugin_section.body_layout.addWidget(preset_box)

        # Execution buttons
        bottom_actions = QHBoxLayout()
        bottom_actions.setSpacing(16)
        self.apply_plugins_btn = QPushButton("✅ Apply & Save Checked Plugins to Project")
        self.apply_plugins_btn.setObjectName("PrimaryButton")
        self.apply_plugins_btn.setMinimumHeight(48)
        self.apply_plugins_btn.clicked.connect(self.apply_plugins)

        self.launch_engine_button = QPushButton("▶ Launch Unreal Engine")
        self.launch_engine_button.setMinimumHeight(48)
        self.launch_engine_button.setObjectName("PrimaryButton")
        self.launch_engine_button.clicked.connect(self.launch_selected_engine)

        self.restore_btn = QPushButton("Restore Project Backup")
        self.restore_btn.clicked.connect(self.restore_project_backup)
        self.plugin_section.body_layout.addWidget(self.restore_btn)
        bottom_actions.addWidget(self.apply_plugins_btn, 2)
        bottom_actions.addWidget(self.launch_engine_button, 1)
        self.plugin_section.body_layout.addLayout(bottom_actions)
        layout.addWidget(self.plugin_section)

        # ---------------- Section 4: Project Config ----------------
        self.config_section = AccordionSection("04  ·  Project Config Settings", "Copy and merge Config settings from another project.", True)
        config_layout = self.config_section.body_layout
        source_row = QHBoxLayout()
        self.config_source_edit = QLineEdit()
        self.config_source_edit.setReadOnly(True)
        self.config_source_edit.setPlaceholderText("Choose the project to copy settings from…")
        source_row.addWidget(self.config_source_edit, 1)
        source_button = QPushButton("Select Source Project…")
        source_button.clicked.connect(self.select_config_source)
        source_row.addWidget(source_button)
        config_layout.addLayout(source_row)
        config_note = QLabel("Merge all Config .ini settings, including platform folders. Source values win; unrelated target settings remain.")
        config_note.setWordWrap(True)
        config_layout.addWidget(config_note)
        actions = QHBoxLayout()
        self.merge_config_btn = QPushButton("Preview Config Merge…")
        self.merge_config_btn.clicked.connect(self.preview_config_merge)
        self.restore_config_btn = QPushButton("Restore Config Backup…")
        self.restore_config_btn.clicked.connect(self.restore_config_backup)
        for button in (self.merge_config_btn, self.restore_config_btn):
            button.setEnabled(False)
            actions.addWidget(button)
        config_layout.addLayout(actions)
        layout.addWidget(self.config_section)

        # ---------------- Section 5: Log ----------------
        self.log_section = AccordionSection("05  ·  Output Log", "Application status and system logs.", True)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("logView")
        self.log_view.setMinimumHeight(160)
        self.log_view.setPlaceholderText("System logs and operations will appear here...")
        self.log_section.body_layout.addWidget(self.log_view)
        layout.addWidget(self.log_section)

        scroll.setWidget(page)
        root_layout.addWidget(scroll, 1)

    def show_about(self) -> None:
        QMessageBox.about(self, "About", f"{APP_NAME} {VERSION}\n\n"
            "Independent project and plugin management utility.\n"
            "Not affiliated with or endorsed by Epic Games.\n\n"
            "Uses Python and PySide6 / Qt. Third-party notices and the user guide "
            "are included with the Windows distribution.")

    def apply_theme(self) -> None:
        if self.is_dark_mode:
            self.setStyleSheet(THEME_DARK)
            self.theme_btn.setText("☀️ Light Mode")
        else:
            self.setStyleSheet(THEME_LIGHT)
            self.theme_btn.setText("🌙 Dark Mode")

    def toggle_theme(self) -> None:
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def append_log(self, text: str) -> None:
        logging.info(text)
        self.log_view.appendPlainText(text)

    # ---------------- Engine Operations ----------------
    def browse_engine_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Epic Games installation folder", self.engine_root_path.text())
        if folder:
            self.engine_root_path.setText(folder)
            self.populate_versions()

    def populate_versions(self) -> None:
        previous = self.version_combo.currentData() or self.settings.value("engine_path", "", type=str)
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        try:
            found = EngineManager.scan_versions(self.engine_root_path.text())
        except OSError as exc:
            found = []
            self.append_log(f"[ERROR] Engine scan failed: {exc}")
        for name, folder in found:
            self.version_combo.addItem(name, str(folder))

        if not found:
            self.version_combo.addItem("No installed engine detected", "")
            self.append_log("[SYSTEM] No Unreal Engine installations located.")
        else:
            self.append_log(f"[SYSTEM] Detected {len(found)} Unreal Engine installation(s).")

        index = self.version_combo.findData(previous)
        if index >= 0:
            self.version_combo.setCurrentIndex(index)
        self.version_combo.blockSignals(False)
        if self.get_registered_uproject_file():
            self.scan_all_plugins()

    def launch_selected_engine(self) -> None:
        engine_str = self.version_combo.currentData()
        if not engine_str:
            QMessageBox.warning(self, "No Engine", "Please select an Unreal Engine installation to launch.")
            return

        proj_file = self.get_registered_uproject_file()
        try:
            self.append_log(f"[LAUNCH] Executing Unreal Engine from: {engine_str}")
            EngineManager.launch(Path(engine_str), proj_file)
        except Exception as exc:
            self.append_log(f"[ERROR] Engine launch failed: {exc}")
            QMessageBox.critical(self, "Launch Failed", str(exc))

    # ---------------- Project Operations ----------------
    def browse_project_folder(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Select Unreal Project", str(Path.home()), "Unreal Projects (*.uproject)")
        if file:
            self.register_project(Path(file))

    def register_project(self, uproject: Path) -> None:
        try:
            ProjectManager.load_descriptor(uproject)
        except Exception as exc:
            QMessageBox.warning(self, "Project Selection", str(exc))
            return
        uproject = uproject.resolve()
        self.recent_projects = [str(uproject)] + [p for p in self.recent_projects if p != str(uproject)]
        self.recent_projects = self.recent_projects[:10]
        self.refresh_recent_projects()
        self.uproject_path_edit.setText(str(uproject))
        self.detected_project_name.setText(uproject.stem)
        self.detected_project_location.setText(str(uproject.parent))
        self.append_log(f"[PROJECT] Bound to project '{uproject.stem}'.")

        self.plugin_section.setEnabled(True)
        self.plugin_status.setObjectName("pluginStatusActive")
        self.plugin_status.setText(f"🟢 Project '{uproject.stem}' active. Plugin management unlocked.")
        self.plugin_status.style().unpolish(self.plugin_status)
        self.plugin_status.style().polish(self.plugin_status)
        self.scan_all_plugins()

    def refresh_recent_projects(self) -> None:
        self.recent_combo.clear()
        self.recent_combo.addItem("Open a recent project…", "")
        for path in self.recent_projects:
            self.recent_combo.addItem(path, path)

    def open_recent_project(self, index: int) -> None:
        path = self.recent_combo.itemData(index)
        if path:
            self.register_project(Path(path))

    def save_workspace(self) -> None:
        self.settings.setValue("dark_mode", self.is_dark_mode)
        self.settings.setValue("engine_root", self.engine_root_path.text())
        self.settings.setValue("engine_path", self.version_combo.currentData() or "")
        self.settings.setValue("custom_plugins", self.custom_plugin_path.text())
        self.settings.setValue("recent_projects", self.recent_projects)
        project = self.get_registered_uproject_file()
        self.settings.setValue("last_project", str(project) if project else "")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.sync()

    def get_registered_uproject_file(self) -> Optional[Path]:
        loc = self.detected_project_location.text().strip()
        name = self.detected_project_name.text().strip()
        if not loc or not name:
            return None
        return Path(loc) / f"{name}.uproject"

    # ---------------- Plugin Operations ----------------
    def browse_custom_plugin_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select custom plugin folder", str(Path.home()))
        if path:
            self.custom_plugin_path.setText(path)
            self.scan_all_plugins()

    def clear_plugin_rows(self) -> None:
        for layout in [self.engine_plugin_layout, self.custom_plugin_layout]:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self.plugin_checks.clear()

    def update_plugin_count_label(self, *_) -> None:
        total = len(self.plugin_checks)
        enabled = sum(1 for check in self.plugin_checks.values() if check.isChecked())
        self.plugin_count_label.setText(f"🔌 Plugins: {enabled} enabled / {total} total")

    def cancel_scan(self) -> None:
        self._scan_generation += 1
        if self.active_scan_worker:
            self.active_scan_worker.requestInterruption()

    def set_scan_busy(self, busy: bool) -> None:
        for widget in (self.apply_plugins_btn, self.import_custom_btn, self.load_preset_btn,
                       self.save_preset_btn, self.restore_btn, self.plugin_type_tabs,
                       self.launch_engine_button, self.import_preset_btn, self.export_preset_btn):
            widget.setEnabled(not busy)
        for button in (self.merge_config_btn, self.restore_config_btn):
            button.setEnabled(not busy and self.get_registered_uproject_file() is not None)

    def scan_all_plugins(self, *_) -> None:
        if self._closing or self.operation_worker:
            return
        self.cancel_scan()
        if self.active_scan_worker is not None:
            self._scan_pending = True
            return
        self._scan_pending = False
        self.clear_plugin_rows()
        self.plugins = {}
        self.update_plugin_count_label()
        proj_file = self.get_registered_uproject_file()
        if not proj_file or not proj_file.is_file():
            self.plugin_status.setText("Please register an existing project above first.")
            return

        try:
            self.scan_snapshot = proj_file.read_bytes()
            descriptor = ProjectManager.load_descriptor(proj_file)
        except Exception as exc:
            QMessageBox.critical(self, "Read Error", f"Failed reading .uproject file:\n{exc}")
            return

        enabled_in_project = {
            entry.get("Name"): entry["Enabled"]
            for entry in descriptor.get("Plugins", [])
            if isinstance(entry, dict) and entry.get("Name") and "Enabled" in entry
        }

        roots: list[tuple[Path, str]] = []
        proj_plugins = proj_file.parent / "Plugins"
        if proj_plugins.is_dir():
            roots.append((proj_plugins, "Project"))

        eng_str = self.version_combo.currentData()
        if eng_str:
            eng_plugins = Path(eng_str) / "Engine" / "Plugins"
            if eng_plugins.is_dir():
                roots.append((eng_plugins, "Engine"))

        custom_text = self.custom_plugin_path.text().strip()
        if custom_text:
            custom_path = Path(custom_text).expanduser()
            if custom_path.is_dir():
                roots.append((custom_path, "Custom"))

        self.append_log("[SCAN] Scanning plugin repositories in background...")
        generation = self._scan_generation
        worker = PluginScanWorker(roots, enabled_in_project, descriptor.get("DisableEnginePluginsByDefault", False))
        self.active_scan_worker = worker
        worker.scan_completed.connect(self.accept_scan_result)
        worker.scan_failed.connect(self.scan_error)
        worker.progress.connect(self.scan_progress)
        worker.finished.connect(self.scan_finished)
        worker.generation = generation
        self.set_scan_busy(True)
        self.plugin_status.setText("Scanning plugin folders…")
        worker.start()

    def accept_scan_result(self, plugins: dict) -> None:
        if not self._closing and self.sender().generation == self._scan_generation:
            self._on_scan_completed(plugins)

    def scan_error(self, error: str) -> None:
        if not self._closing and self.sender().generation == self._scan_generation:
            self.plugin_status.setText("Scan failed. Rescan to try again.")
            self.append_log(f"[ERROR] {error}")

    def scan_progress(self, message: str) -> None:
        if not self._closing and self.sender().generation == self._scan_generation:
            self.plugin_status.setText(message)
            if message.startswith("Skipped"):
                self.append_log(f"[SCAN] {message}")

    def scan_finished(self) -> None:
        worker = self.active_scan_worker
        self.active_scan_worker = None
        worker.deleteLater()
        self.set_scan_busy(False)
        if self._closing:
            QTimer.singleShot(0, self.close)
        elif self._scan_pending:
            self.scan_all_plugins()

    def start_operation(self, operation, message: str, rescan: bool = True) -> None:
        if self.active_scan_worker or self.operation_worker:
            return
        self._operation_message = message
        self._operation_rescan = rescan
        self.operation_worker = OperationWorker(operation)
        self.operation_worker.finished.connect(self.operation_finished)
        for section in (self.engine_section, self.project_section, self.plugin_section, self.config_section):
            section.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)
        self.append_log("[WORKING] Updating files. Please wait for the operation to finish.")
        self.operation_worker.start()

    def operation_finished(self) -> None:
        worker = self.operation_worker
        self.operation_worker = None
        error = worker.error
        worker.deleteLater()
        self.unsetCursor()
        for section in (self.engine_section, self.project_section, self.plugin_section, self.config_section):
            section.setEnabled(True)
        if error:
            self.append_log(f"[ERROR] {error}")
            if not self._closing:
                QMessageBox.critical(self, "Operation Failed", error)
        else:
            self.append_log(self._operation_message)
            if not self._closing and self._operation_rescan:
                self.scan_all_plugins()
        if self._closing:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event) -> None:
        self._closing = True
        if self.operation_worker is not None:
            self.append_log("[SYSTEM] Finishing the file operation before closing…")
            event.ignore()
            return
        if self.active_scan_worker is not None:
            self.cancel_scan()
            self.plugin_status.setText("Stopping scan before closing…")
            event.ignore()
            return
        self.save_workspace()
        event.accept()

    def _on_scan_completed(self, plugins: dict) -> None:
        self.clear_plugin_rows()
        self.plugins = plugins
        self.plugin_status.setText("Scan complete. Review plugin settings below.")
        if not plugins:
            QMessageBox.information(self, "No Plugins", "No .uplugin files detected in the scanned locations.")
            self.update_plugin_count_label()
            return

        for internal, info in sorted(plugins.items(), key=lambda i: i[1]["friendly"].lower()):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 2, 4, 2)

            # Updated: Only show the friendly name
            check = QCheckBox(info["friendly"])
            check.setChecked(info["enabled"])
            check.setToolTip(f"{internal} — Version {info['version']}\n{info['description']}\n{info['descriptor']}")
            check.stateChanged.connect(self.update_plugin_count_label)
            check.stateChanged.connect(self.filter_plugins)
            row_layout.addWidget(check, 1)

            origin_lbl = QLabel(f"[{info['origin']}]")
            origin_lbl.setProperty("originType", info["origin"])
            origin_lbl.setMinimumWidth(80)
            row_layout.addWidget(origin_lbl)

            if info["origin"] == "Engine":
                self.engine_plugin_layout.addWidget(row)
            else:
                self.custom_plugin_layout.addWidget(row)

            self.plugin_checks[internal] = check

        self.append_log(f"[SCAN] Successfully indexed {len(plugins)} plugins.")
        self.update_plugin_count_label()
        self.filter_plugins()

    def filter_plugins(self, *_) -> None:
        query = self.plugin_search.text().strip().lower()
        show_enabled = self.show_enabled_only_cb.isChecked()
        for name, checkbox in self.plugin_checks.items():
            row = checkbox.parentWidget()
            matches_text = query in name.lower() or query in checkbox.text().lower()
            matches_state = not show_enabled or checkbox.isChecked()
            if row:
                row.setVisible(matches_text and matches_state)

    def import_single_custom_plugin(self) -> None:
        proj_file = self.get_registered_uproject_file()
        if not proj_file or not proj_file.is_file():
            QMessageBox.warning(self, "No Project", "Please register a target project first.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Plugin Folder (Must contain a .uplugin file)", str(Path.home()))
        if not folder:
            return

        src_path = Path(folder)
        uplugins = list(src_path.glob("*.uplugin"))
        if not uplugins:
            QMessageBox.warning(self, "Invalid Plugin", "No .uplugin file detected inside the selected directory.")
            return

        dest_dir = proj_file.parent / "Plugins" / src_path.name
        try:
            PluginService.validate_copy(src_path, dest_dir)
            if dest_dir.exists():
                reply = QMessageBox.question(
                    self, "Overwrite?", f"Plugin '{src_path.name}' already exists in project. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.start_operation(lambda: PluginService.transact([(src_path, dest_dir)]),
                                 f"[PLUGIN] Imported '{src_path.name}' into the project.")
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))

    def refresh_presets(self) -> None:
        self.preset_combo.clear()
        presets = self.preset_service.list_presets()
        for name, path in presets:
            self.preset_combo.addItem(name, str(path))
        if not presets:
            self.preset_combo.addItem("No saved presets found", "")

    def save_plugin_preset(self) -> None:
        if not self.plugin_checks:
            QMessageBox.warning(self, "No Plugins", "Please scan plugins first.")
            return
        name = self.preset_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid preset name.")
            return

        enabled = [k for k, v in self.plugin_checks.items() if v.isChecked()]

        try:
            name = self.preset_service.validate_name(name)
            exists = (self.preset_service.preset_dir / f"{name}.json").exists()
            if exists and not self.confirm_preset_overwrite(name):
                return
            self.preset_service.save_preset(name, enabled, overwrite=exists)
            self.append_log(f"[PRESET] Saved preset '{name}' ({len(enabled)} plugins).")
            self.preset_name_edit.clear()
            self.refresh_presets()
            idx = self.preset_combo.findText(name)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
            QMessageBox.information(self, "Saved", f"Preset '{name}' successfully saved.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def load_plugin_preset(self) -> None:
        preset_path_str = self.preset_combo.currentData()
        if not preset_path_str:
            QMessageBox.warning(self, "Invalid Selection", "Please select a preset from the dropdown.")
            return

        try:
            preset_plugins = set(self.preset_service.load_preset(Path(preset_path_str)))
            missing = sorted(preset_plugins - self.plugin_checks.keys())
            if missing:
                report = QMessageBox(self)
                report.setWindowTitle("Missing Preset Plugins")
                report.setText(f"{len(missing)} preset plugin(s) were not found. Apply available plugins?")
                report.setDetailedText("\n".join(missing))
                report.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                report.setDefaultButton(QMessageBox.StandardButton.No)
                if report.exec() != QMessageBox.StandardButton.Yes:
                    return
                self.append_log("[PRESET] Missing: " + ", ".join(missing))
            applied = 0
            for name, check in self.plugin_checks.items():
                if name in preset_plugins:
                    check.setChecked(True)
                    applied += 1
                else:
                    check.setChecked(False)

            self.filter_plugins()
            self.update_plugin_count_label()
            self.append_log(f"[PRESET] Applied preset from '{preset_path_str}' ({applied} plugins checked).")
            QMessageBox.information(self, "Loaded", f"Loaded preset with {applied} enabled plugins.")
        except Exception as exc:
            QMessageBox.critical(self, "Load Failed", str(exc))

    def confirm_preset_overwrite(self, name: str) -> bool:
        return QMessageBox.question(self, "Replace Preset", f"Replace saved preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def import_plugin_preset(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Import Plugin Preset", "", "JSON presets (*.json)")
        if not file:
            return
        try:
            source = Path(file)
            name = self.preset_service.validate_name(source.stem)
            exists = (self.preset_service.preset_dir / f"{name}.json").exists()
            if exists and not self.confirm_preset_overwrite(name):
                return
            self.preset_service.import_preset(source, overwrite=exists)
            self.refresh_presets()
            self.preset_combo.setCurrentIndex(self.preset_combo.findText(name))
            self.append_log(f"[PRESET] Imported {name}. Select Load Preset to use it.")
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))

    def export_plugin_preset(self) -> None:
        file, _ = QFileDialog.getSaveFileName(self, "Export Checked Plugins", "plugins.json", "JSON presets (*.json)")
        if not file:
            return
        try:
            path = Path(file)
            enabled = [name for name, check in self.plugin_checks.items() if check.isChecked()]
            self.preset_service.export_preset(path, path.stem, enabled)
            self.append_log(f"[PRESET] Exported {len(enabled)} enabled plugins to {path}.")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def apply_plugins(self) -> None:
        proj_file = self.get_registered_uproject_file()
        if not proj_file or not proj_file.is_file():
            QMessageBox.warning(self, "No Project", "Please register a project first.")
            return

        if not self.plugin_checks:
            QMessageBox.warning(self, "No Plugins", "No plugins available to apply.")
            return

        if self.active_scan_worker:
            return
        selected = {name: check.isChecked() for name, check in self.plugin_checks.items()}
        changes = [f"{'Enable' if selected[name] else 'Disable'}: {name}"
                   for name, info in self.plugins.items() if selected[name] != info["enabled"]]
        copies = []
        for name, info in self.plugins.items():
            if selected[name] and info["origin"] == "Custom":
                dest = proj_file.parent / "Plugins" / info["plugin_dir"].name
                copies.append(f"{'Overwrite' if dest.exists() else 'Copy'}: {name} → {dest}")
        if not changes and not copies:
            QMessageBox.information(self, "No Changes", "Plugin settings are unchanged.")
            return
        preview = QMessageBox(self)
        preview.setWindowTitle("Review Plugin Changes")
        preview.setText(f"Apply {len(changes)} setting change(s) and {len(copies)} folder import(s)?")
        preview.setInformativeText("Review details below. Existing destination folders listed as Overwrite will be replaced. A project descriptor backup will be saved.")
        preview.setDetailedText("\n".join(changes + copies))
        preview.setStandardButtons(QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel)
        preview.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if preview.exec() != QMessageBox.StandardButton.Apply:
            return
        plugins, snapshot = self.plugins.copy(), self.scan_snapshot
        self.start_operation(lambda: PluginService.apply(proj_file, selected, plugins, snapshot),
                             "[SUCCESS] Plugin changes applied. Restart Unreal Editor to load the new settings.")

    def restore_project_backup(self) -> None:
        project = self.get_registered_uproject_file()
        if not project or self.active_scan_worker:
            return
        answer = QMessageBox.question(self, "Restore Project Backup",
            "Restore the descriptor from before the last apply? Copied plugin folders will remain. "
            "The current descriptor will be saved as .uproject.before-restore.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.start_operation(lambda: ProjectManager.restore_backup(project),
                             "[PROJECT] Restored project descriptor backup.")

    def select_config_source(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, "Source Project for Config Settings", str(Path.home()), "Unreal Projects (*.uproject)")
        if file:
            self.config_source_edit.setText(file)

    def preview_config_merge(self) -> None:
        target = self.get_registered_uproject_file()
        if not target or self.active_scan_worker or self.operation_worker:
            return
        source = self.config_source_edit.text().strip()
        if not source:
            QMessageBox.warning(self, "Select Source", "Choose the source .uproject file first.")
            return
        try:
            plan = ConfigService.plan(Path(source), target)
            self.confirm_config_plan(plan, "Merge Project Config Settings")
        except Exception as exc:
            QMessageBox.critical(self, "Config Preview Failed", str(exc))

    def confirm_config_plan(self, plan, title: str) -> None:
        if not plan.changes:
            message = "No Config settings need changing."
            if plan.skipped:
                message += "\nNon-INI files were not copied: " + ", ".join(plan.skipped)
            QMessageBox.information(self, title, message)
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(f"Update {len(plan.changes)} Config file(s) in {plan.target.parent.name}?")
        dialog.setInformativeText("Review Show Details before applying. Close Unreal Editor first. "
            "All source settings are included, including project IDs and asset paths. "
            "Referenced assets are not copied. A restorable backup is saved in .pipeline-config-backups.")
        dialog.setDetailedText(plan.preview())
        dialog.setStandardButtons(QMessageBox.StandardButton.Apply | QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if dialog.exec() == QMessageBox.StandardButton.Apply:
            self.start_operation(lambda: ConfigService.apply(plan),
                f"[CONFIG] Updated {len(plan.changes)} file(s). Backup: {plan.target.parent / '.pipeline-config-backups'}. Restart Unreal Editor.",
                rescan=False)

    def restore_config_backup(self) -> None:
        target = self.get_registered_uproject_file()
        if not target or self.active_scan_worker or self.operation_worker:
            return
        file, _ = QFileDialog.getOpenFileName(self, "Select Config Backup",
            str(target.parent / ".pipeline-config-backups"), "Config backups (*.json)")
        if not file:
            return
        try:
            plan = ConfigService.restore_plan(target, Path(file))
            self.confirm_config_plan(plan, "Restore Project Config Settings")
        except Exception as exc:
            QMessageBox.critical(self, "Config Restore Failed", str(exc))
