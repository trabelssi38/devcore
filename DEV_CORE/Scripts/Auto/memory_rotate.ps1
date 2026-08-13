# memory_rotate.ps1 -- DEV_CORE v9.0 Auto layer
param(
    [int]$MaxLines = 300,
    [int]$KeepLines = 200
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
. "$DEV_CORE\Scripts\platform_version.ps1"
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path $DEV_CORE "DEV_CORE_DATA") }
$DEV_CORE_LOCAL = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\DEV_CORE_LOCAL" } else { $DEV_CORE_DATA }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\memory_rotate_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "memory_rotate -- rotation MEMORY.md" "Cyan"

$service = Join-Path (Split-Path -Parent $PSScriptRoot) "memory_service.ps1"
$resultJson = & $service -Action RotateMemory -MaxLines $MaxLines -KeepLines $KeepLines -Json | Out-String
$result = $resultJson | ConvertFrom-Json

if ($result.rotated) {
    Log "Archive : $($result.archive_path)" "Green"
    Log "MEMORY.md tronque a $($result.lines) lignes" "Cyan"
} else {
    Log "MEMORY.md -- $($result.lines) lignes" "Green"
}
