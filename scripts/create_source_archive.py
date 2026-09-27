"""Create a clean source handoff; this is NOT a Windows executable package."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'release'
SKIP = {'.git', '.venv', '.venv-build', '__pycache__', 'build', 'dist', 'release'}


def main():
    OUTPUT.mkdir(exist_ok=True)
    archive = OUTPUT / 'UnrealPipelineManager-Windows-build-source.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(ROOT.rglob('*')):
            relative = path.relative_to(ROOT)
            if any(part in SKIP for part in relative.parts):
                continue
            if path.is_file() and path.name != '.DS_Store' and path.suffix not in ('.pyc', '.pfx', '.p12'):
                bundle.write(path, relative.as_posix())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    print(archive)


if __name__ == '__main__':
    main()
