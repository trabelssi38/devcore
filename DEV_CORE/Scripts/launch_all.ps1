# launch_all.ps1 -- DEV_CORE
# Lance l'ensemble des services DEV_CORE et le daemon HERMES

[CmdletBinding()]
param(
    [switch]$QuickStart,
    [string]$Project,
    [string]$Client
)

$ErrorActionPreference = "Stop"
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

Write-Host ""
Write-Host "  $($PLATFORM.title) -- LAUNCH ALL SYSTEMS" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

# 1. Boot standard platform services
Write-Host "[1/2] Lancement des services DEV_CORE (launch.ps1)..." -ForegroundColor White
$launchParams = @{}
if ($PSBoundParameters.ContainsKey('QuickStart')) { $launchParams['QuickStart'] = $true }
if ($PSBoundParameters.ContainsKey('Project')) { $launchParams['Project'] = $Project }
if ($PSBoundParameters.ContainsKey('Client')) { $launchParams['Client'] = $Client }
& "$DEV_CORE\Scripts\launch.ps1" @launchParams

# 2. Boot Hermes standalone tick daemon
Write-Host "[2/2] Lancement du daemon HERMES..." -ForegroundColor White
& "$DEV_CORE\Scripts\hermes-daemon.ps1" -Start

Write-Host ""
Write-Host "  Systemes DEV_CORE et HERMES initialises avec succes !" -ForegroundColor Green
Write-Host "  Consultez le Cockpit a : http://127.0.0.1:20129/" -ForegroundColor Green
Write-Host ""
