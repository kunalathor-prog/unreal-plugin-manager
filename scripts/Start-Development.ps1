# Source-checkout helper only. Customer executables bundle their dependencies.
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (!(Test-Path '.venv\Scripts\python.exe')) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 with the Python Launcher first.' }
    }
    $Python = '.venv\Scripts\python.exe'
    & $Python -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the network and rerun.' }
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'The Python environment needs repair.' }
    & $Python run.py
    if ($LASTEXITCODE -ne 0) { throw 'Application failed. Check its startup message and diagnostic log.' }
} finally { Pop-Location }
