[CmdletBinding()]
param([switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Build on Windows x64, or run the GitHub Actions Windows workflow.' }
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    if (!(Test-Path '.venv-build\Scripts\python.exe')) {
        & py -3.12 -m venv .venv-build
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 with the Python Launcher, then rerun.' }
    }
    $Python = Join-Path $ProjectRoot '.venv-build\Scripts\python.exe'
    & $Python -c "import struct; assert struct.calcsize('P') == 8, 'Python x64 required'"
    if ($LASTEXITCODE -ne 0) { throw 'A 64-bit Python installation is required.' }
    & $Python -m pip install --disable-pip-version-check -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the network and rerun this script.' }
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency check failed.' }
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; packaging stopped.' }
    & $Python scripts/make_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
    & $Python scripts/prepare_build.py
    if ($LASTEXITCODE -ne 0) { throw 'Build metadata/license collection failed.' }
    & $Python -m PyInstaller --clean --noconfirm 'Unreal Pipeline Manager.spec'
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    $AppFolder = Join-Path $ProjectRoot 'dist\UnrealPipelineManager'
    Copy-Item docs/USER_GUIDE.md, docs/THIRD_PARTY_NOTICES.md -Destination $AppFolder
    $Smoke = Start-Process -FilePath "$AppFolder\UnrealPipelineManager.exe" -ArgumentList '--self-test' -PassThru
    if (!$Smoke.WaitForExit(60000)) { $Smoke.Kill(); throw 'Packaged smoke test timed out.' }
    if ($Smoke.ExitCode -ne 0) { throw "Packaged smoke test failed: $($Smoke.ExitCode)" }
    $Version = & $Python -c 'from app.version import VERSION; print(VERSION)'
    New-Item -ItemType Directory -Force release | Out-Null
    $Archive = "release\UnrealPipelineManager-$Version-Windows-x64-Portable.zip"
    Compress-Archive -Path $AppFolder -DestinationPath $Archive -Force
    if (!$SkipInstaller) {
        $Compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        $Iscc = if ($Compiler) { $Compiler.Source } else { "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
        if (!(Test-Path $Iscc)) { throw 'Install Inno Setup 6, or use -SkipInstaller for the portable package only.' }
        $Metadata = Get-Content packaging/release.json -Raw | ConvertFrom-Json
        $Publisher = if ($Metadata.publisher) { $Metadata.publisher } else { 'Publisher not configured' }
        & $Iscc "/DAppVersion=$Version" "/DPublisher=$Publisher" "/DSupportURL=$($Metadata.support_url)" packaging/windows.iss
        if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
    }
    & $Python -m pip freeze | Set-Content -Encoding UTF8 "release\build-environment-$Version.txt"
    Get-ChildItem release -File | Where-Object { $_.Name -like "*$Version*" -and $_.Extension -in '.zip', '.exe' } |
        ForEach-Object { $Hash = Get-FileHash $_.FullName -Algorithm SHA256; "$($Hash.Hash.ToLower())  $($_.Name)" } |
        Set-Content -Encoding ASCII "release\SHA256SUMS-$Version.txt"
    Write-Host 'Build and packaged smoke test completed. Artifacts are in release/.'
} finally { Pop-Location }
