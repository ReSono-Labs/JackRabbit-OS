$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $PackageRoot "bin\jackrabbit-installer.exe"
$Release = [System.IO.Path]::GetFullPath((Join-Path $PackageRoot "..\..\release"))
$env:JACKRABBIT_FASTBOOT = Join-Path $PackageRoot "tools\fastboot.exe"
$DriverSetup = Join-Path $PackageRoot "install-drivers.ps1"

Write-Host "JackRabbit guided Windows installer" -ForegroundColor Cyan
Write-Host ""
Write-Host "Windows may need one-time R1 USB driver setup before flashing."
$SkipDrivers = $false
while ($true) {
    $Answer = Read-Host "Press Enter to install or repair the included R1 drivers, or type S to skip"
    if ([string]::IsNullOrEmpty($Answer)) { break }
    if ($Answer -match "^[sS]$") {
        $SkipDrivers = $true
        break
    }
    Write-Host ""
    Write-Host "ENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?"
    while ($true) {
        $CancelAnswer = Read-Host "Type Y to cancel, or press Enter to return to the same prompt"
        if ($CancelAnswer -match "^(y|yes)$") { exit 2 }
        if ([string]::IsNullOrEmpty($CancelAnswer) -or $CancelAnswer -match "^(n|no)$") { break }
        Write-Host "Please type Y to cancel, or press Enter to retry."
    }
}
if (-not $SkipDrivers) {
    & $DriverSetup
}

if (-not (Test-Path -PathType Leaf $Installer)) {
    throw "Missing installer binary: $Installer"
}
if (-not (Test-Path -PathType Leaf $env:JACKRABBIT_FASTBOOT)) {
    throw "Missing packaged fastboot: $env:JACKRABBIT_FASTBOOT"
}
if (-not (Test-Path -PathType Container (Join-Path $Release "images"))) {
    throw "Missing packaged release: $Release"
}

& $Installer install $Release
exit $LASTEXITCODE
