# qdrant_sync.ps1 -- DEV_CORE v6.1
# Sync decisions and lessons to Qdrant via Ollama embeddings

# Use invariant culture for JSON numbers
[System.Globalization.CultureInfo]::CurrentCulture = [System.Globalization.CultureInfo]::InvariantCulture

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

# Check Qdrant
try {
    $q = Invoke-RestMethod "$QDRANT_URL/collections" -TimeoutSec 3
    Write-Log "Qdrant connected - $($q.result.collections.Count) collections" "Green"
} catch {
    Write-Log "Qdrant unavailable - sync cancelled" "Yellow"
    exit 0
}

# Get embedding from Ollama
function Get-OllamaEmbedding {
    param([string]$text)
    try {
        $escapedText = $text -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '' -replace "`n", '\n'
        $body = '{"model":"nomic-embed-text","prompt":"' + $escapedText + '"}'

        $tempFile = "$env:TEMP\ollama_embed_$(Get-Date -Format 'yyyyMMddHHmmss').json"
        Set-Content -Path $tempFile -Value $body -Encoding ASCII -NoNewline

        $result = & curl.exe -s -X POST "$OLLAMA_URL/api/embeddings" -H 'Content-Type: application/json' --data-binary "@$tempFile"
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue

        $jsonResult = $result | ConvertFrom-Json
        if ($jsonResult.embedding) {
            return $jsonResult.embedding
        }
        throw "No embedding in response"
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
    $uuid = [guid]::NewGuid().ToString()
    # Round to 6 decimal places
    $roundedVector = $vector | ForEach-Object { "{0:F6}" -f [double]$_ }
    $vectorStr = $roundedVector -join ','

    # Escape payload values
    $payloadParts = @()
    foreach ($key in $payload.Keys) {
        $val = $payload[$key].ToString() -replace '\\', '\\\\' -replace '"', '\"'
        $payloadParts += "        `"$key`": `"$val`""
    }
    $payloadJson = $payloadParts -join ",`n"

    $json = "{" +
        "`n  `"points`": [{" +
        "`n    `"id`": `"$uuid`"," +
        "`n    `"vector`": [$vectorStr]," +
        "`n    `"payload`": {" +
        "`n$payloadJson" +
        "`n    }" +
        "`n  }]" +
        "`n}"

    # Write JSON to temp file (no BOM)
    $jsonFile = "$env:TEMP\qdrant_$(Get-Date -Format 'yyyyMMddHHmmss').json"
    $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
    [System.IO.File]::WriteAllText($jsonFile, $json, $Utf8NoBomEncoding)

    # Write Python script to file
    $pyFile = "$env:TEMP\qdrant_call_$(Get-Date -Format 'yyyyMMddHHmmss').py"
    $pyContent = @"
import subprocess
import json
import sys

json_file = r'$jsonFile'
url = '$QDRANT_URL/collections/$collection/points'

with open(json_file, 'r') as f:
    data = f.read()

result = subprocess.run(
    ['curl', '-s', '-X', 'PUT', url, '-H', 'Content-Type: application/json', '-d', data],
    capture_output=True,
    text=True
)

try:
    resp = json.loads(result.stdout)
    if resp.get('status') == 'ok':
        print('OK')
        sys.exit(0)
    else:
        print('ERROR:', resp.get('status'))
        sys.exit(1)
except:
    print('ERROR: Failed to parse response')
    sys.exit(1)
"@
    Set-Content -Path $pyFile -Value $pyContent -Encoding UTF8

    # Run Python script
    $result = & python.exe $pyFile 2>&1

    Remove-Item $jsonFile, $pyFile -Force -ErrorAction SilentlyContinue

    if ($result -match 'OK') {
        return $true
    }
    Write-Log "Qdrant upsert failed: $result" "Red"
    return $false
}

# Sync decisions
$decisionsFile = "$DEV_CORE_DATA\Memory\DECISIONS.md"
if (Test-Path $decisionsFile) {
    $decisions = Get-Content $decisionsFile -Raw
    Write-Log "Syncing decisions..." "Cyan"

    $embedding = Get-OllamaEmbedding $decisions
    if ($embedding) {
        $preview = ($decisions -replace "`n", " " -replace "\s+", " ").Substring(0, [Math]::Min(200, $decisions.Length))
        $payload = @{
            source = "DECISIONS.md"
            date = $TODAY
            type = "decisions"
            preview = $preview
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
        $preview = ($lessons -replace "`n", " " -replace "\s+", " ").Substring(0, [Math]::Min(200, $lessons.Length))
        $payload = @{
            source = "LESSONS.md"
            date = $TODAY
            type = "lessons"
            preview = $preview
        }
        if (Add-ToQdrant "lessons" "lessons_$TODAY" $embedding $payload) {
            Write-Log "Lessons upserted to Qdrant" "Green"
        }
    }
}

Write-Log "Qdrant sync complete" "Green"
Write-Host ""
