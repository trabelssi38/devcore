# endday_check.ps1 -- DEV_CORE
# Verifie si endday.ps1 a ete execute aujourd'hui
# Si non -> lance endday.ps1

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
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$FLAG = "$DEV_CORE_DATA\Logs\endday_flag_$TODAY.txt"
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Endday Check" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray

if (Test-Path $FLAG) {
    $lastEndday = Get-Content $FLAG
    Write-Log "endday deja execute aujourd'hui ($lastEndday)" "Green"
    exit 0
}

Write-Log "endday NON execute aujourd'hui - lancement de la maintenance..." "Yellow"

try {
    & "$DEV_CORE\Scripts\endday.ps1"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $timestamp | Set-Content $FLAG -Encoding UTF8
    Write-Log "Maintenance endday terminee avec succes ($timestamp)" "Green"
} catch {
    Write-Log "Erreur lors de l'execution de endday : $_" "Red"
}
Write-Host ""
