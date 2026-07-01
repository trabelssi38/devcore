# endday_check.ps1 -- DEV_CORE v9.0
# Verifie si endday.ps1 a ete execute aujourd'hui
# Si non -> lance endday.ps1

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$FLAG = "$DEV_CORE_DATA\Logs\endday_flag_$TODAY.txt"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v9.0 -- Endday Check" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray

if (Test-Path $FLAG) {
    $lastEndday = Get-Content $FLAG
    Write-Log "endday deja execute aujourd'hui ($lastEndday)" "Green"
    exit 0
}

Write-Log "endday NON execute aujourd'hui - lancement..." "Yellow"
Write-Log "Verification Qdrant disponible..." "Gray"

try {
    $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3
    Write-Log "Qdrant OK - lancement endday.ps1" "Green"
    & "$DEV_CORE\Scripts\endday.ps1"

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $timestamp | Set-Content $FLAG -Encoding UTF8
    Write-Log "Flag endday cree: $timestamp" "Green"
} catch {
    Write-Log "Qdrant non disponible - endday reporte" "Yellow"
    # DO NOT create flag - allows retry on next run
}
Write-Host ""