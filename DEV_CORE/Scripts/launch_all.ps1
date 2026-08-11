# launch_all.ps1 -- DEV_CORE
# Lance l'ensemble des services DEV_CORE et le daemon HERMES

[CmdletBinding()]
param(
    [switch]$QuickStart,
    [string]$Project,
    [string]$Client
)

$ErrorActionPreference = "Stop"
$defaultDevCore = Split-Path -Parent $PSScriptRoot
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Config\platform.json"))) {
    $env:DEVCORE_PLATFORM_ROOT
} else {
    $defaultDevCore
}
if ($DEV_CORE -match '\\Scripts\\?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

Write-Host ""
Write-Host "  $($PLATFORM.title) -- LAUNCH ALL SYSTEMS" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

# 1. Boot standard platform services in background (WMI)
Write-Host "[1/1] Lancement des services DEV_CORE (launch.ps1) en arriere-plan..." -ForegroundColor White
$launchScript = Join-Path $DEV_CORE "Scripts\launch.ps1"
$launchArgs = ""
if ($QuickStart) { $launchArgs += " -QuickStart" }
if ($Project) { $launchArgs += " -Project `"$Project`"" }
if ($Client) { $launchArgs += " -Client `"$Client`"" }

$commandLine = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launchScript`"$launchArgs"
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $commandLine } | Out-Null

# Wait up to 30s for the API and Router to come online
Write-Host "Attente du demarrage des services..." -NoNewline
$success = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    Write-Host "." -NoNewline
    $conn1 = Get-NetTCPConnection -LocalPort 20129 -ErrorAction SilentlyContinue
    $conn2 = Get-NetTCPConnection -LocalPort 20130 -ErrorAction SilentlyContinue
    if ($conn1 -and $conn2) {
        $success = $true
        break
    }
}
Write-Host ""

if ($success) {
    Write-Host ""
    Write-Host "  Systemes DEV_CORE initialises avec succes !" -ForegroundColor Green
    Write-Host "  Consultez le Cockpit a : http://127.0.0.1:20129/" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "  Avertissement: Les services ont mis trop de temps a demarrer." -ForegroundColor Yellow
}
