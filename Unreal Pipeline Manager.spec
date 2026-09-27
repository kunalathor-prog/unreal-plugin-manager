# Build on Windows with scripts/Build-Windows.ps1. No macOS bundle is produced.
import sys
from pathlib import Path
if sys.platform != 'win32':
    raise SystemExit('Windows executables must be built on Windows. Use the Windows Actions workflow.')
root = Path(SPECPATH)
a = Analysis(
    [str(root / 'run.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root / 'app/resources/pipeline.ico'), 'app/resources'),
           (str(root / 'docs/USER_GUIDE.md'), 'docs'),
           (str(root / 'docs/THIRD_PARTY_NOTICES.md'), 'docs'),
           (str(root / 'build/metadata/licenses'), 'licenses'),
           (str(root / 'build/metadata/components.json'), '.')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml',
              'PySide6.QtQuick', 'tkinter', 'unittest'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='UnrealPipelineManager', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False,
          icon=str(root / 'app/resources/pipeline.ico'),
          version=str(root / 'build/metadata/version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='UnrealPipelineManager')
