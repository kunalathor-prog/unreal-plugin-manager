"""Generate Windows metadata and collect dependency license files from the build environment."""
from __future__ import annotations
from importlib import metadata
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.version import APP_NAME, VERSION, FILE_VERSION


def main():
    config = json.loads((ROOT / 'packaging/release.json').read_text(encoding='utf-8'))
    publisher = config['publisher'] or 'Publisher not configured'
    output = ROOT / 'build/metadata'
    output.mkdir(parents=True, exist_ok=True)
    strings = {'CompanyName': publisher, 'FileDescription': APP_NAME,
               'FileVersion': '.'.join(map(str, FILE_VERSION)), 'InternalName': 'UnrealPipelineManager',
               'OriginalFilename': 'UnrealPipelineManager.exe', 'ProductName': APP_NAME, 'ProductVersion': VERSION}
    entries = ',\n'.join(f'StringStruct({key!r}, {value!r})' for key, value in strings.items())
    resource = f'''VSVersionInfo(ffi=FixedFileInfo(filevers={FILE_VERSION!r}, prodvers={FILE_VERSION!r},
mask=0x3f, flags=0x2, OS=0x40004, fileType=0x1, subtype=0, date=(0, 0)),
kids=[StringFileInfo([StringTable('040904B0', [{entries}])]),
VarFileInfo([VarStruct('Translation', [1033, 1200])])])'''
    (output / 'version.txt').write_text(resource, encoding='utf-8')
    licenses = output / 'licenses'
    licenses.mkdir(exist_ok=True)
    inventory = []
    for package in ('PySide6-Essentials', 'shiboken6', 'PyInstaller'):
        dist = metadata.distribution(package)
        count = 0
        for relative in dist.files or []:
            if any('license' in part.lower() or 'copying' in part.lower() for part in relative.parts):
                source = Path(dist.locate_file(relative))
                if source.is_file() and '..' not in relative.parts:
                    dest = licenses / package / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                    count += 1
        if not count:
            raise RuntimeError(f'No license files found for {package}; inspect the installed distribution.')
        inventory.append({'package': package, 'version': dist.version, 'license_files': count})
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError(f'Python license missing: {python_license}')
    shutil.copy2(python_license, licenses / 'Python-LICENSE.txt')
    (output / 'components.json').write_text(json.dumps({'python': sys.version, 'packages': inventory}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
