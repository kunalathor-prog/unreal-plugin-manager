# Windows build and release

## Status

The repository contains a Windows release-candidate build pipeline. A successful macOS source test is not a Windows executable or a Windows validation result. Do not distribute as a final commercial release until Windows build/install/repair tests and real-editor acceptance checks pass.

## Build using GitHub Actions

Place this application's contents at the repository root, so `.github/workflows/windows-release.yml` is at the GitHub repository root. Enable Actions, then run **Windows release candidate**. The workflow uses Windows Server 2025 x64 and Python 3.12; desktop acceptance remains on Windows 11.

The workflow installs build dependencies, runs unit/Qt tests, builds with PyInstaller, launches the actual executable using `--self-test`, builds the Inno Setup installer, tests installation and file repair, and uploads artifacts. It does not publish a release or upload to a storefront. Pull-request runs also build candidates.

Download the artifact from the completed workflow run. Expected files:

- `UnrealPipelineManager-1.0.0-rc.1-Windows-x64-Setup.exe`
- `UnrealPipelineManager-1.0.0-rc.1-Windows-x64-Portable.zip`
- `SHA256SUMS-1.0.0-rc.1.txt`
- Build environment inventory and installer-test log.

## Local Windows build

Install Python 3.12 x64 with the Python Launcher and Inno Setup 6 from their official sources. In PowerShell, from the project root:

```powershell
.\scripts\Build-Windows.ps1
.\scripts\Test-Installer.ps1
```

Use `-SkipInstaller` to build only the portable ZIP. The script creates an isolated `.venv-build`, installs `requirements-build.txt` (which includes runtime requirements), and checks dependencies. Network access is needed to build, not to run the result.

If PowerShell blocks local scripts, review them and use an execution policy appropriate to your environment. The scripts do not change machine execution policy.

## Before sale

- Fill `packaging/release.json` with the publisher and support URL. Finalize customer license terms and the Qt distribution route; verify notices, exact corresponding sources, and third-party licenses for the delivered build.
- Run the workflow and inspect artifacts. Test on a clean Windows 11 x64 system with no Python installed and no Internet connection.
- Test real supported Unreal versions: select and launch a project; enable/disable plugins; import/overwrite; load presets with missing plugins; restore a backup. Record the specific engine versions tested instead of claiming blanket compatibility.
- Test a standard non-admin account, non-ASCII/spaced paths, read-only projects, a full disk, and a large plugin copy. Confirm install, repair, upgrade, and uninstall behavior.
- Sign the application executable before generating the installer, then sign the installer with the publisher's code-signing certificate and timestamp service. Signing credentials must stay outside the repository. The current pipeline produces **unsigned candidates**. Recalculate final checksums after signing.
- Change `app/version.py` to the final version only after validation; update the file version tuple too. Prepare product screenshots, demonstration video, support policy, and supported-engine matrix.

## Fab decision

This desktop edition is intended for distribution outside Fab. Epic's posted policy disallows executables and installers, including additional files in archives:
https://forums.unrealengine.com/t/unsupported-file-types-on-fab/2094150

A future Fab edition would require a separate engine-native plugin product and its own packaging/testing process. Do not upload the desktop executable disguised in another format.
