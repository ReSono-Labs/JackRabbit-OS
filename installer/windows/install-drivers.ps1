$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$MediaTek = Join-Path $PackageRoot "drivers\mediatek\MediaTek_Preloader_USB_VCOM_drivers.exe"
$GoogleInf = Join-Path $PackageRoot "drivers\google-usb-driver\usb_driver\android_winusb.inf"

if (-not (Test-Path -PathType Leaf $MediaTek)) {
    throw "Missing Rabbit MediaTek driver installer: $MediaTek"
}
if (-not (Test-Path -PathType Leaf $GoogleInf)) {
    throw "Missing Google fastboot USB driver: $GoogleInf"
}

Write-Host "Windows will request administrator approval for Rabbit's signed MediaTek driver."
$MediaTekProcess = Start-Process -FilePath $MediaTek -Verb RunAs -Wait -PassThru
if ($MediaTekProcess.ExitCode -ne 0) {
    throw "Rabbit MediaTek driver installer exited with code $($MediaTekProcess.ExitCode)"
}

Write-Host "Windows will request administrator approval for Google's signed fastboot driver."
$Arguments = "/add-driver `"$GoogleInf`" /install"
$GoogleProcess = Start-Process -FilePath "$env:SystemRoot\System32\pnputil.exe" -ArgumentList $Arguments -Verb RunAs -Wait -PassThru
if ($GoogleProcess.ExitCode -ne 0) {
    throw "Google USB driver installation exited with code $($GoogleProcess.ExitCode)"
}

Write-Host "R1 Windows USB drivers are installed."
