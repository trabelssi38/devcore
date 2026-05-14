# qdrant_sync.ps1 -- DEV_CORE v6.1
# Sync les decisions et lessons vers Qdrant via Ollama embeddings

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$QDRANT_URL = if ($env:QDRANT_URL) { $env:QDRANT_URL } else { "http://localhost:6333" }
$OLLAMA_URL = if ($env:OLLAMA_URL) { $env:OLLAMA_URL } else { "http://localhost:11434" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$LOG = "$DEV_CORE_DATA\Logs\scripts\qdrant_sync_$TODAY.log"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Qdrant Sync" -ForegroundColor Cyan

# Verifier Qdrant
try {
    $q = Invoke-RestMethod "$QDRANT_URL/collections" -TimeoutSec 3
    Write-Log "Qdrant connecte - $($q.result.collections.Count) collections" "Green"
} catch {
    Write-Log "Qdrant non disponible - sync annule" "Yellow"
    exit 0
}

# Get embedding from Ollama
function Get-OllamaEmbedding {
    param([string]$text)
    try {
        $body = @{ model = "nomic-embed-text"; prompt = $text } | ConvertTo-Json
        $resp = Invoke-RestMethod "$OLLAMA_URL/api/embeddings" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
        return $resp.embedding
    } catch {
        Write-Log "Ollama embedding failed: $_" "Red"
        return $null
    }
}

# Upsert to Qdrant
function Add-ToQdrant {
    param(
        [string]$collection,
        [string]$id,
        [object]$vector,
        [hashtable]$payload
    )
    $point = @{
        id = $id -replace "[^a-zA-Z0-9_-]", "_"
        vector = $vector
        payload = $payload
    } | ConvertTo-Json -Compress

    try {
        Invoke-RestMethod "$QDRANT_URL/collections/$collection/points" `
            -Method Put -Body $point -ContentType "application/json" -TimeoutSec 10 | Out-Null
        return $true
    } catch {
        Write-Log "Qdrant upsert failed: $_" "Red"
        return $false
    }
}

# Sync decisions
$decisionsFile = "$DEV_CORE_DATA\Memory\DECISIONS.md"
if (Test-Path $decisionsFile) {
    $decisions = Get-Content $decisionsFile -Raw
    Write-Log "Syncing decisions..." "Cyan"

    $embedding = Get-OllamaEmbedding $decisions
    if ($embedding) {
        $payload = @{
            source = "DECISIONS.md"
            date = $TODAY
            type = "decisions"
            preview = ($decisions -replace "`n", " " -replace "\s+", " ").Substring(0, [Math]::Min(200, $decisions.Length))
        }
        if (Add-ToQdrant "decisions" "decisions_$TODAY" $embedding $payload) {
            Write-Log "Decisions upserted to Qdrant" "Green"
        }
    }
}

# Sync lessons
$lessonsFile = "$DEV_CORE_DATA\Memory\LESSONS.md"
if (Test-Path $lessonsFile) {
    $lessons = Get-Content $lessonsFile -Raw
    Write-Log "Syncing lessons..." "Cyan"

    $embedding = Get-OllamaEmbedding $lessons
    if ($embedding) {
        $payload = @{
            source = "LESSONS.md"
            date = $TODAY
            type = "lessons"
            preview = ($lessons -replace "`n", " " -replace "\s+", " ").Substring(0, [Math]::Min(200, $lessons.Length))
        }
        if (Add-ToQdrant "lessons" "lessons_$TODAY" $embedding $payload) {
            Write-Log "Lessons upserted to Qdrant" "Green"
        }
    }
}

Write-Log "Qdrant sync termine" "Green"
Write-Host ""