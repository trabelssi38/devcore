# qdrant_sync.ps1 -- DEV_CORE v9.0 Auto layer
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
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "DEV_CORE_DATA") }
$DEV_CORE_LOCAL = if ($env:DEVCORE_LOCAL_ROOT) { $env:DEVCORE_LOCAL_ROOT } elseif ($env:LOCALAPPDATA) { "$env:LOCALAPPDATA\DEV_CORE_LOCAL" } else { $DEV_CORE_DATA }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\qdrant_sync_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "qdrant_sync -- verification memoire vectorielle unifiee" "Cyan"
$dbFile = Join-Path $DEV_CORE_LOCAL "devcore.db"
if (Test-Path $dbFile) {
    Log "Base vectorielle sqlite-vec active ($dbFile)" "Green"
} else {
    Log "Base devcore.db locale absente -- initialisation requise" "Yellow"
}

# Verification optionnelle Qdrant distant / conteneur
try {
    $status = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 1
    Log "Qdrant HTTP externe detecte -- $($status.result.collections.Count) collections" "Green"
} catch {
    # Normal in native sqlite-vec mode
}

# Traiter la queue de refresh si elle existe
$queue = "$DEV_CORE_DATA\Memory\qdrant-refresh.jsonl"
if (Test-Path $queue) {
    $lines = Get-Content $queue
    Log "$($lines.Count) entrees en attente dans la queue" "Cyan"
    Log "Queue disponible pour traitement : $queue" "Gray"
}
