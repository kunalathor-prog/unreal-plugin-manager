# Unreal Pipeline Manager

A PySide6 desktop application (Windows release candidate) for selecting an Unreal Engine installation, managing a project's plugin settings, importing plugin folders, and sharing plugin presets.

## Run

Use Python 3.12 for release builds (Python 3.10 or newer for source development) and an installed Unreal Engine editor. From this directory:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

On Windows, activate with `.venv\Scripts\activate` instead. When using the existing virtual environment in the parent workspace, run `../.venv/bin/python run.py`.

## Workflow

1. Select the engine installation directory or a source-build root, then select the engine version.
2. Select a `.uproject` file, or open a recent project.
3. Wait for the plugin scan. Engine, project, and optional external plugin directories are indexed in a background thread. Changing engines rescans the project.
4. Search/filter plugins and change the checkboxes. Hover over a plugin for its internal name, version, description, and descriptor path.
5. Select **Apply & Save Checked Plugins to Project**, review the detailed setting and folder changes, then select **Apply**. Restart Unreal Editor to load the changed settings.

Selecting a project or loading a preset does not write plugin changes to the project. Unapplied selections are discarded on rescan, project switch, or exit.

## Plugin settings

Checkboxes show descriptor-level configuration, not live editor runtime state:

- Explicit `.uproject` `Enabled` values take precedence.
- Otherwise, installed plugins use `.uplugin` `EnabledByDefault`; without that field, project plugins default on and engine plugins default off.
- `DisableEnginePluginsByDefault` suppresses inherited engine defaults.
- External plugins start unchecked unless referenced as enabled by the project. Checking one schedules an import on Apply.
- A project copy takes precedence over external and engine copies with the same descriptor filename. External copies take precedence over engine copies.
- Only changed checkbox settings become explicit project overrides. Existing reference metadata, unavailable plugin references, and other project fields are preserved.

The tool does not resolve plugin dependencies, platform/target restrictions, build compatibility, or settings in target files. Unreal remains responsible for loading and compiling plugins. See Epic's [plugin documentation](https://dev.epicgames.com/documentation/unreal-engine/plugins-in-unreal-engine) and [project descriptor reference](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Projects/FProjectDescriptor).

## Imports and recovery

A plugin import requires a folder containing exactly one valid `.uplugin` JSON object. Overlapping source/destination paths and symbolic-link destinations are rejected. Importing a single folder asks before replacement; bulk Apply lists every replacement in the preview.

Copies are staged beside the destination before replacements begin. If copying or saving fails, replaced folders are rolled back. If rollback itself fails, original folders remain in `.plugin-import-*/old` for manual recovery. This protects against handled operation failures; it is not a crash-safe filesystem transaction. File transactions run in a background worker; conflicting controls are disabled and closing waits for the transaction to finish.

Every successful descriptor save keeps the preceding descriptor in `Project.uproject.bak`. **Restore Project Backup** restores it and saves the current descriptor as `Project.uproject.before-restore`. Restoring the descriptor does not remove or restore imported plugin folders. A project modified externally since its scan must be rescanned before applying.

## Copy project Config settings

Select a target project, then choose **Select Source Project… → Preview Config Merge…** in step 04, Project Config Settings. Review the detailed diff and apply. All Config `.ini` files, including platform subfolders, are merged with source values taking precedence; unrelated target settings remain. **Restore Config Backup…** restores a selected timestamped backup. See the [user guide](docs/USER_GUIDE.md#copy-all-project-config-settings) for array behavior, supported formats, and recovery limits.

## Presets and workspace

Presets are JSON files in `~/UnrealPluginPresets`. Save named selections, including an empty selection, or import/export them. Loading a preset replaces the current checkbox selection. Missing plugins are reported before applying the available portion. Presets contain plugin names, not binaries or source files. Existing preset names require confirmation before replacement.

The engine path, external plugin path, theme, window geometry, last project, and ten recent projects are stored on clean exit using native `QSettings` under organization `UnrealPipelineManager`, application `Desktop`.

## Tests

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

Tests also set the offscreen Qt platform internally, so on Windows use `python -m unittest discover -s tests -v`. They use temporary project/plugin folders and isolated settings; no installed engine is launched and no real projects are edited.

The suite covers descriptor defaults and overrides, source precedence, copy and save failures, rollback, backup restoration, preset validation, preview cancellation/application, scan lifecycle, engine changes, and workspace restoration.

## Windows release candidate

The distribution target is **Windows 11 x64**. Version `1.0.0-rc.1` adds bundled-runtime packaging, startup diagnostics, single-instance protection, and background file operations. The Windows build is not yet verified; it must run on a Windows machine or GitHub Actions.

See [Windows release instructions](docs/WINDOWS_RELEASE.md) for the build workflow and release checks, [customer guide](docs/USER_GUIDE.md) for installation/repair, and [third-party notices](docs/THIRD_PARTY_NOTICES.md) for dependency distribution details.

On Windows, install Python 3.12 x64 and Inno Setup 6, then run:

```powershell
.\scripts\Build-Windows.ps1
.\scripts\Test-Installer.ps1
```

The builder installs the pinned requirements automatically into an isolated environment. Customers receive Python and Qt inside the package and do not run pip. Rerunning Setup repairs installed application files; no runtime package downloads occur.

The GitHub workflow creates a Setup EXE, portable ZIP, checksums, and build inventory. It uploads candidate artifacts without publishing a release. This desktop edition is intended for distribution **outside Fab**, whose published policy disallows executable uploads.

## Structure

- `app/main.py`: QApplication startup.
- `app/ui/main_window.py`: interface and user workflows.
- `app/ui/accordion.py`, `styles.py`: reusable sections and themes.
- `app/core/engine_manager.py`: engine discovery and launching.
- `app/core/plugin_service.py`: state interpretation, descriptor updates, staged imports, rollback.
- `app/core/config_service.py`: Config INI merge, diff previews, multi-file writes, and restoration.
- `app/core/project_manager.py`: validated descriptors, atomic writes, backups and restore.
- `app/core/preset_service.py`: preset validation and interchange.
- `app/workers/scan_worker.py`: cancellable background discovery.
- `tests/`: standard-library unittest suite with offscreen Qt integration tests.
