# qdrant_sync.ps1 -- DEV_CORE v6.1
# Sync les decisions et lessons vers Qdrant

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$QDRANT_URL = if ($env:QDRANT_URL) { $env:QDRANT_URL } else { "http://localhost:6333" }
$TODAY = Get-Date -Format "yyyy-MM-dd"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Qdrant Sync" -ForegroundColor Cyan

# Verifier Qdrant
try {
    $q = Invoke-RestMethod "$QDRANT_URL/collections" -TimeoutSec 3
    Write-Log "Qdrant connecte" "Green"
} catch {
    Write-Log "Qdrant non disponible - sync annule" "Yellow"
    exit 0
}

# Sync decisions -> Qdrant collection decisions
$decisionsFile = "$DEV_CORE_DATA\Memory\DECISIONS.md"
if (Test-Path $decisionsFile) {
    $decisions = Get-Content $decisionsFile -Raw
    Write-Log "Syncing decisions..." "Cyan"
    # Note: embeddings via Ollama in production
    Write-Log "Decisions sync (placeholder - full impl needs embeddings)" "Yellow"
}

# Sync lessons -> Qdrant collection lessons
$lessonsFile = "$DEV_CORE_DATA\Memory\LESSONS.md"
if (Test-Path $lessonsFile) {
    $lessons = Get-Content $lessonsFile -Raw
    Write-Log "Syncing lessons..." "Cyan"
    Write-Log "Lessons sync (placeholder - full impl needs embeddings)" "Yellow"
}

Write-Log "Qdrant sync termine" "Green"
Write-Host ""