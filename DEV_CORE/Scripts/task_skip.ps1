# task_skip.ps1 -- DEV_CORE v9.0 single client
param([string]$Reason="")

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}

if (-not $Reason) {
    $Reason = Read-Host "  Raison du skip (optionnel)"
}

& "$PSScriptRoot\task_service.ps1" -Action Skip -Reason $Reason
& "$DEV_CORE\Scripts\task_next.ps1"

