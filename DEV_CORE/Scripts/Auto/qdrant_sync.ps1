# qdrant_sync.ps1 -- DEV_CORE v6 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\qdrant_sync_$TODAY.log"
function Log { param($msg,$color="Gray"); $l="[$(Get-Date -f HH:mm:ss)] $msg"; Add-Content $LOG $l -ErrorAction SilentlyContinue; Write-Host "    $l" -ForegroundColor $color }
Log "qdrant_sync -- verification Qdrant" "Cyan"
$env:PYTHONPATH = "$DEV_CORE\Tools"
try {
    $status = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 5
    Log "Qdrant OK -- $($status.result.collections.Count) collections" "Green"
    # Traiter la queue de refresh si elle existe
    $queue = "$DEV_CORE_DATA\Memory\qdrant-refresh.jsonl"
    if (Test-Path $queue) {
        $lines = Get-Content $queue
        Log "$($lines.Count) entrees en attente dans la queue" "Cyan"
        # La queue sera traitee par le worker Python dedie
        # python -m devcore.qdrant_worker (a implementer selon ton setup Ollama)
        Log "Queue disponible pour traitement : $queue" "Gray"
    }
} catch { Log "Qdrant non disponible -- upsert differe" "Yellow" }
