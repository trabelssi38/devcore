# session_end.ps1 -- DEV_CORE
# Execute a la fin de session Claude Code
# 1. Sync Qdrant
# 2. Sync Obsidian
# 3. Genere metrics

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
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG_DIR       = "$DEV_CORE_DATA\Logs\scripts"
$LOG           = "$LOG_DIR\session_end_$TODAY.log"
$PLATFORM = Get-DevCorePlatformInfo

New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

function Log {
    param($msg, $color="Cyan")
    Write-Host "  $msg" -ForegroundColor $color
    Add-Content $LOG "[$(Get-Date -f HH:mm:ss)] $msg" -ErrorAction SilentlyContinue
}

Write-Host ""
Log "$($PLATFORM.title) -- Session End" "Cyan"
Log "========================================" "DarkGray"
Log "Date: $TODAY" "White"
Write-Host ""

Log "[1/6] Sync Qdrant..." "Cyan"
& "$DEV_CORE\Scripts\qdrant_sync.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append

Log "[2/6] Sync Obsidian..." "Cyan"
& "$DEV_CORE\Scripts\obsidian_sync.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append

Log "[3/6] Generation metrics..." "Cyan"
& "$DEV_CORE\Scripts\gen_metrics.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append

Log "[4/6] Task scan..." "Cyan"
& "$DEV_CORE\Scripts\task_scan.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append

Log "[5/6] Task sync + Dashboard..." "Cyan"
& "$DEV_CORE\Scripts\task_sync.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append

Log "[6/6] Endday check..." "Cyan"
& "$DEV_CORE\Scripts\endday_check.ps1" 2>&1 | Tee-Object -FilePath $LOG -Append

Write-Host ""
Log "========================================" "Green"
Log "||  Session end complete               ||" "Green"
Log "========================================" "Green"
Write-Host ""
