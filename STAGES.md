# Enhancement stages

## Stage 1 — Reliable plugin management

Implemented descriptor defaults and explicit overrides, serialized cancellable scans with stale-result rejection, safe staged imports, change previews, external-edit detection, and descriptor backup restoration.

Checkpoint: **10 tests passed**, including failure rollback and Qt scan lifecycle tests.

## Stage 2 — Daily workflow

Implemented remembered workspace settings, recent projects, rescanning after engine selection, scan status and disabled conflicting actions, plugin detail tooltips, empty presets, validated names, import/export, and missing-plugin reports.

Checkpoint: **16 tests passed**. A macOS path-alias assertion in the test was corrected to compare resolved paths.

## Stage 3 — Maintainability and validation

Plugin mutation and copying now live in `PluginService`; validation and atomic persistence live in the core services. Added setup, workflow, recovery, architecture, testing, and packaging documentation. Expanded coverage to preview cancellation/application, malformed input, import collisions, successful imports, atomic-write failures, and engine launch argument construction.

Checkpoint: **26 tests passed** using Python 3.14 / PySide6 6.11.2 with Qt's offscreen platform on macOS. Real editor launch, packaged builds, and interactive testing on Windows/Linux remain unverified.

## Suggested future upgrade

Project profiles could group an engine, external plugin directory, and preferred preset. Loading a profile should select its configuration; applying project changes should remain explicit. Profiles are not part of this implementation.

## Windows commercial release preparation — in progress

- Windows-only PyInstaller spec and per-user Inno Setup installer definitions.
- GitHub Actions Windows build, packaged smoke test, install/repair/uninstall test, candidate artifact upload.
- Pinned runtime/build dependencies; dependency installation during development/build only.
- Startup error reporting and rotating logs; single-instance protection.
- Background import/apply/restore operations with safe close handling.
- Original application icon; existing banner excluded from executable distribution.
- User guide, repair instructions, build instructions, third-party notices and release metadata template.

Local checkpoint: **31 tests passed**, plus the source `--self-test` passed on macOS. No Windows EXE has been built or verified here yet. Repository authentication, publisher/support metadata, Windows acceptance and final license/signing decisions remain outstanding. Distribution is outside Fab, as selected by the owner.

## Project Config transfer — October 4, 2026

Implemented source-project selection, recursive Config INI merge with source precedence, file-difference preview, timestamped backups, and previewed restoration. Unrelated target settings and files remain; matching array operator groups are replaced in source order. Includes platform subfolders and reports non-INI files that are not copied. Config operations run in the background and preserve unsaved plugin selections.

Validation: **46 tests passed** on the local macOS development host, including merge/restore UI integration, Unicode, repeated sections, array operators, rollback, stale-file checks, and path validation. Windows packaging has not been rerun for this change.
