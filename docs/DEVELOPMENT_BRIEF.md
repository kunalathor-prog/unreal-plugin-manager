# Unreal Pipeline Manager — Reusable Development Brief

Use this document to resume development in a new session or hand the project to another developer. It describes the Unreal Pipeline Manager discussed in this conversation. It does not describe the separate “Unreal Project Launcher + Perforce Manager” file shown in the IDE; that file was not available in this workspace.

## Product objective

Build a reliable Windows desktop utility for managing Unreal Engine installations, project plugin settings, external plugin imports, and reusable plugin presets. Prepare it for commercial distribution outside Fab.

The customer should install or extract the application and run an EXE without installing Python or Python modules. Preserve project data and make every destructive replacement reviewable and recoverable when an operation fails.

## Product decisions

- Desktop framework: Python and PySide6 / Qt Widgets.
- Distribution target: Windows 11 x64. macOS is currently a development/test host, not the release target.
- Windows builder: Python 3.12 x64, PyInstaller, and Inno Setup 6.
- Customer distribution: per-user Setup EXE and portable ZIP containing the EXE plus its runtime folder.
- Dependencies are installed during development/build and bundled for customers.
- Repair means rerunning Setup to restore application files offline, or extracting a fresh portable package. Do not silently download or install arbitrary modules at runtime.
- Distribution is outside Fab. The owner selected this after reviewing Epic’s published restriction on executable/installer uploads. A future Fab product would be a separate Unreal Editor plugin, not a renamed or disguised desktop executable.
- Keep project profiles as a proposed future feature, not an implemented feature.

## Existing functionality

### Engine and project selection

- Discover installed engines from standard paths and a user-selected directory.
- Accept an engine source-build root with an arbitrary folder name.
- Select the engine version and an existing `.uproject` file.
- Launch the editor with the selected project using an argument list.
- Remember the engine path, external plugin path, theme, window geometry, last project, and up to ten recent projects.
- Rescan plugins when the selected engine changes.

### Plugin discovery and state

- Scan engine, project, and external directories for `.uplugin` descriptors in a background thread.
- Identify a plugin by its descriptor filename; display its friendly name.
- Show origin, checkbox state, search/filter controls, and details in tooltips.
- Explicit `.uproject` `Enabled` values override defaults.
- Otherwise respect `.uplugin` `EnabledByDefault`; absent values default on for project plugins and off for engine plugins.
- Respect the project’s `DisableEnginePluginsByDefault` setting.
- External plugins start unchecked unless the project explicitly enables them.
- Duplicate-name precedence is Project > Custom > Engine.
- Skip malformed plugin descriptors with diagnostics.
- Serialize scans, reject stale results after a context change, and stop scans cooperatively when closing.

Checkboxes describe descriptor configuration, not actual runtime loading. Dependencies, target rules, platform restrictions, compilation, and binary compatibility are not resolved by this utility.

### Applying settings and importing files

- Preview setting changes and plugin copies/replacements before applying.
- Write explicit overrides only for changed checkbox settings.
- Preserve unrelated project fields, plugin-reference metadata, and unavailable plugin references.
- Refuse to apply if the project descriptor changed externally since scanning.
- Validate imports: exactly one JSON-object `.uplugin` descriptor at the plugin folder root.
- Reject overlapping source/destination paths and symbolic-link destinations.
- Stage all copies before replacing destinations.
- Roll back replacements after handled copy/save failures; preserve recoverable originals if rollback fails.
- Run import/apply/restore operations in a background worker, disable conflicting controls, and wait for active file operations before closing.

### Backups

- Save the preceding descriptor as `.uproject.bak` on apply.
- Restore that backup on explicit user action.
- Preserve the current descriptor as `.uproject.before-restore` before restoration.
- Descriptor restoration does not undo plugin folder imports.

### Presets

- Save/load named JSON presets in `~/UnrealPluginPresets`.
- Support an empty selection.
- Validate preset names and payloads.
- Require confirmation before overwriting an existing preset.
- Import/export presets; report missing plugin names before applying the available portion.
- Loading a preset changes the selection; writing to the project remains a separate action.

### Application support

- Light/dark themes and accordion sections.
- Versioned application identity and original geometric Windows icon.
- Single-instance protection during normal application startup.
- Rotating diagnostic logs and startup errors with repair instructions.
- No automatic telemetry uploads.
- Packaged `--self-test` mode using temporary fixtures and isolated settings.

## Architecture

| Path | Responsibility |
| --- | --- |
| `run.py` | Startup wrapper and error reporting |
| `app/main.py` | QApplication, instance lock, exception handling, self-test routing |
| `app/version.py` | Application and Windows file versions |
| `app/diagnostics.py` | Standard-library logging and native startup error reporting |
| `app/self_test.py` | Bundled Qt/plugin/backup smoke test |
| `app/ui/main_window.py` | UI and workflow coordination |
| `app/ui/accordion.py` | Reusable collapsible sections |
| `app/ui/styles.py` | Qt stylesheets |
| `app/core/engine_manager.py` | Engine discovery and process launch |
| `app/core/project_manager.py` | Descriptor validation, atomic writes, backup/restore |
| `app/core/plugin_service.py` | Plugin state, descriptor updates, staged copies and rollback |
| `app/core/preset_service.py` | Preset validation and persistence |
| `app/workers/scan_worker.py` | Cancellable plugin discovery |
| `app/workers/operation_worker.py` | Background file transactions |
| `tests/` | Service and offscreen Qt integration tests |
| `scripts/Build-Windows.ps1` | Dependencies, tests, build, smoke test, ZIP/installer/checksums |
| `scripts/Test-Installer.ps1` | Isolated install, missing-runtime repair, uninstall checks |
| `scripts/Start-Development.ps1` | Windows source-environment setup and launch |
| `scripts/prepare_build.py` | Version resources and dependency license collection |
| `scripts/make_icon.py` | Reproducible original icon generation |
| `scripts/create_source_archive.py` | Clean source handoff archive |
| `packaging/windows.iss` | Per-user Inno Setup configuration |
| `packaging/release.json` | Publisher/support metadata |
| `.github/workflows/windows-release.yml` | Windows CI and candidate artifact upload |

## Development workflow

1. Read the current repository instructions and inspect the actual code. This brief is a baseline, not proof that every described behavior is still present.
2. Define a bounded stage with observable acceptance criteria.
3. Implement the stage, keeping filesystem and descriptor logic in services rather than widgets.
4. Add meaningful regression coverage for risky behavior or newly fixed bugs.
5. Run relevant tests, then the complete suite before a release candidate.
6. Report changes, test results, known limitations, and outstanding work.
7. Update documentation when behavior or packaging changes.

Never use real customer projects for automated destructive tests. Use temporary directories and isolated QSettings. Never expose credentials in logs, chat, commits, or archives. Do not force-push or overwrite unrelated repository changes.

## Commands

Run from the application repository root.

### Source tests

```sh
python -m unittest discover -s tests -v
```

For headless development on macOS/Linux:

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen python -m app.main --self-test
```

### Windows source development

With Python 3.12 x64 and its launcher installed:

```powershell
.\scripts\Start-Development.ps1
```

### Windows packaging

With Python 3.12 x64 and Inno Setup 6 installed:

```powershell
.\scripts\Build-Windows.ps1
.\scripts\Test-Installer.ps1
```

Installer tests require a clean account/VM without an existing installation of the product. `-SkipInstaller` builds only the portable package.

### GitHub build

Repository: https://github.com/kunalathor-prog/unreal-plugin-manager

The application contents must be at the repository root, including `.github/workflows`. Run **Windows release candidate** from Actions, or use its configured push/PR triggers. A successful run uploads candidate artifacts; it does not publish a commercial release.

## Required regression coverage

- Defaults, explicit overrides, and duplicate-plugin precedence.
- Preservation of unrelated metadata and unavailable plugin references.
- Malformed descriptors/presets and unsafe preset names.
- Failed copies, failed writes, rollback, and import destination collisions.
- Backup restoration and rejection of invalid backups.
- External project edits between scanning and applying.
- Preview cancellation causing no project writes.
- Confirmed apply followed by a refreshed scan.
- Project/engine switching during scans and safe shutdown.
- Background file operation failure and close-wait behavior.
- Preset import/export, empty presets, and missing-plugin cancellation.
- Workspace restoration using isolated settings.
- Windows launch arguments with paths containing spaces.
- Actual frozen EXE startup, installation, runtime-file repair, and uninstall on Windows.

## Known limits and release gates

- Current recorded version: `1.0.0-rc.1`; do not label it final without validation.
- Latest recorded local result: 31 tests passed, plus the source smoke test, on macOS. These do not establish Windows runtime compatibility.
- GitHub `main` was verified at `8c8c4f0` with the initial release-candidate implementation. Inspect current remote history before resuming work.
- The conversation did not verify a successful Windows build or produce a verified Windows EXE.
- Publisher name and support URL were still unconfigured at handoff.
- Candidate binaries are unsigned. Final signing requires the publisher’s certificate and a secure signing process.
- Verify the chosen Qt licensing route, redistributed notices, and any required source/relinking materials before sale. Collected license files alone do not establish compliance.
- The existing banner is excluded from Windows binaries because redistribution rights were not established.
- Test real supported Unreal versions and publish only the compatibility claims backed by those tests.
- Transactions recover from handled failures but are not power-loss/crash-safe.
- Unapplied checkbox edits are discarded on rescan, context switch, or exit. A future improvement is explicit dirty-state confirmation.
- No dependency resolution, plugin recompilation, runtime auto-update service, or project profiles are implemented.

## Suggested next stages

1. **Validate Windows delivery:** inspect Actions logs, fix build failures, download artifacts, and test on a clean Windows 11 machine with no Python installed.
2. **Complete commercial metadata:** publisher, support details, customer terms, dependency licensing, signing, and supported-engine matrix.
3. **Improve project switching:** dirty-state confirmation and optional project profiles that group engine path, external plugin path, and preferred preset.
4. **Improve plugin diagnostics:** missing references, compatibility hints, and dependency information without claiming authoritative runtime resolution.
5. **Strengthen recovery:** investigate crash-recovery journals and transactional folder restoration before promising recovery from interrupted installations.

## Reusable AI/developer prompt

> Continue developing Unreal Pipeline Manager using this brief and the current repository as context. First inspect repository instructions, current files, Git status, and existing tests. Explain any differences between this brief and the code. Work in bounded stages and test after each stage. Preserve project metadata and user files, keep file operations recoverable, and keep the Qt UI responsive. Target Windows 11 x64 with bundled Python/Qt dependencies, a portable ZIP, and a repairable Setup EXE. Do not install arbitrary Python packages at customer runtime. Verify actual Windows build and installer results before calling the release complete. Keep secrets out of source and logs, retain explicit previews for destructive changes, and clearly distinguish completed work from remaining release gates. Do not add Perforce features or convert to an Unreal Editor plugin unless explicitly requested.

## Supporting documents

- [README](../README.md)
- [Stage history](../STAGES.md)
- [Windows release instructions](WINDOWS_RELEASE.md)
- [Customer user guide](USER_GUIDE.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Update — October 4, 2026: Project Config transfer

The owner requested copying all project Config settings with merging. This is now implemented in `app/core/config_service.py` and the separate Project Config Settings step. Recursive `.ini` settings use source precedence, preserve unrelated target values, and replace matching array keys as complete ordered operator groups. Non-INI files are reported and skipped. Includes diff preview, timestamped JSON backups, background writes, rollback, and guarded restoration. No plugin rescan occurs after a Config operation, preserving unsaved plugin selections. Local validation now totals 46 passing tests; earlier 31-test counts above are historical. Windows build validation for this addition remains pending. See the user guide for exact semantics and limitations.
