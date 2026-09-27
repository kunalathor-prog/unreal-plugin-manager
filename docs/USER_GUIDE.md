# Unreal Pipeline Manager — Windows user guide

## Install and start

Target platform: Windows 11 x64. This release candidate must pass Windows testing before it is advertised as supported. Unreal Engine itself must already be installed.

Run the supplied `UnrealPipelineManager-...-Setup.exe`, then launch **Unreal Pipeline Manager** from Start. The installation is per user and normally does not require administrator access.

For the portable edition, extract the **entire** ZIP and launch `UnrealPipelineManager.exe`. Keep the `_internal` folder beside it. Copying only the executable will not work.

Python, Qt, and required modules are included. Customers do not need Python, pip, `requirements.txt`, or an Internet connection to run the installed application. Source-code development instructions are separate.

## Configure your project

1. Choose your Epic Games installation folder or Unreal source-build root. Select the engine version.
2. Choose an existing `.uproject` file. The application scans installed plugins.
3. Optionally choose an external plugin folder. Project copies take precedence over external and engine copies with the same name.
4. Search plugins, inspect their details by hovering, and change the checkboxes.
5. Select **Apply & Save Checked Plugins to Project**. Expand **Show Details** to review every setting change, copy, and overwrite. Apply the changes and restart Unreal Editor.

Unchanged defaults remain inherited. The checkboxes represent descriptor settings, not Unreal's runtime dependency or platform resolution. They do not guarantee plugin compatibility with the selected engine. Missing project references are preserved.

A rescan, engine change, project switch, or exit discards unchecked/unapplied UI edits. Use Apply before changing contexts if you want those edits saved. Do not edit the same project in another program while applying changes.

## Presets

Save selections under a name, including an empty selection. Import/export JSON presets to share them. Loading a preset changes checkboxes; it does not immediately write to the project. Missing plugin names are reported before loading the available portion. A preset does not contain plugin binaries.

Presets are stored in `%USERPROFILE%\UnrealPluginPresets`. The theme, recent projects, paths, and window geometry are stored per user using Qt settings.

## Backups and repair

Each apply saves the preceding descriptor as `.uproject.bak`. **Restore Project Backup** restores that descriptor and saves the current version as `.uproject.before-restore`. This restores settings only; it does not undo copied plugin folders.

Plugin files are staged before replacement. Handled copy/save failures trigger rollback. Power loss and termination during replacement are not crash-safe; inspect any `.plugin-import-*\old` folders if recovery is needed. Copies run in the background. Conflicting controls are disabled until completion; closing waits for the operation to finish.

If an application file or Python module is missing, close the application and rerun the original Setup executable. It replaces installed program files offline without modifying projects or presets. For a portable installation, extract a fresh ZIP into a new folder. Repair is initiated by you; the app does not download or execute arbitrary packages in the background.

If the Python runtime itself is missing, Windows or the executable's loader may report the error before the app can display its own message. Rerunning Setup is still the repair path.

Diagnostic logs are in `%LOCALAPPDATA%\UnrealPipelineManager\logs\application.log`. Review logs before sharing them: project and plugin paths may appear. Nothing is uploaded automatically.

## Uninstall

Use Windows Settings → Apps → Unreal Pipeline Manager → Uninstall. User projects, presets, logs, and workspace preferences are retained.

This is an independent utility, not an Epic Games product. See the included third-party notices.
