# Destructive checks are confined to a fresh temporary test installation.
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ExistingInstall = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{A661FC26-CBB2-421D-94DC-7E5E4A4C9A75}_is1'
if (Test-Path $ExistingInstall) { throw 'Run installer tests in a clean Windows account/VM without an existing Unreal Pipeline Manager installation.' }
$Installer = Get-ChildItem "$ProjectRoot\release\*-Setup.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (!$Installer) { throw 'No Setup executable was built.' }
$TestRoot = Join-Path ([IO.Path]::GetTempPath()) ('pipeline-install-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $TestRoot | Out-Null
function Run-Checked([string]$File, [string[]]$Arguments) {
    $Process = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru
    if (!$Process.WaitForExit(120000)) { $Process.Kill(); throw "Timed out: $File" }
    if ($Process.ExitCode -ne 0) { throw "Failed ($($Process.ExitCode)): $File" }
}
$InstallArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS', "/DIR=`"$TestRoot\app`"", "/LOG=`"$ProjectRoot\release\installer-test.log`"")
Run-Checked $Installer.FullName $InstallArgs
$Executable = "$TestRoot\app\UnrealPipelineManager.exe"
Run-Checked $Executable @('--self-test')
$Library = "$TestRoot\app\_internal\python312.dll"
if (!(Test-Path $Library)) { throw 'Expected bundled Python runtime is missing.' }
$OriginalHash = (Get-FileHash $Library -Algorithm SHA256).Hash
Move-Item $Library "$TestRoot\python312.dll.original"
Run-Checked $Installer.FullName $InstallArgs
if ((Get-FileHash $Library -Algorithm SHA256).Hash -ne $OriginalHash) { throw 'Installer did not restore the original Python runtime.' }
Run-Checked $Executable @('--self-test')
Run-Checked "$TestRoot\app\unins000.exe" @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
if (Test-Path $Executable) { throw 'Uninstall left the executable behind.' }
Write-Host "Install, file repair and uninstall tests passed. Test directory: $TestRoot"
