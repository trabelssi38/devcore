# qdrant_sync.ps1 -- DEV_CORE v7.3
# Sync des 4 collections Qdrant : decisions, lessons, patterns, codebase
# Sources : DECISIONS.md, LESSONS.md, PATTERNS.md, codebase scan

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
Write-Host "  DEV_CORE v7.3 -- Qdrant Sync (4 collections)" -ForegroundColor Cyan

# Check Qdrant
try {
    $q = Invoke-RestMethod "$QDRANT_URL/collections" -TimeoutSec 3
    Write-Log "Qdrant connected - $($q.result.collections.Count) collections" "Green"
} catch {
    Write-Log "Qdrant unavailable - sync cancelled" "Yellow"
    exit 0
}

# Check Ollama (DISABLED FOR NOW)
$ollamaOk = $false
Write-Log "Ollama desactive pour le moment" "Yellow"

# Get embedding from Ollama
function Get-OllamaEmbedding {
    param([string]$text)
    if (-not $ollamaOk) { return $null }
    try {
        $escapedText = $text -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '' -replace "`n", '\n'
        # Tronquer a 4000 chars pour eviter les timeouts
        if ($escapedText.Length -gt 4000) { $escapedText = $escapedText.Substring(0, 4000) }
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

# Get embedding from 9Router (Fallback)
function Get-9RouterEmbedding {
    param([string]$text)
    try {
        # Clean text
        $cleanText = $text -replace "`r", "" -replace "`n", " "
        if ($cleanText.Length -gt 8000) { $cleanText = $cleanText.Substring(0, 8000) }

        # Get API key from env or fallback
        $apiKey = if ($env:NINEROUTER_API_KEY) { $env:NINEROUTER_API_KEY } else { "sk-60c873dfaa73a810-kfwd8f-6f9cfc28" }
        $bodyObj = @{
            model = "text-embedding-3-small"
            input = $cleanText
        }
        $bodyJson = $bodyObj | ConvertTo-Json

        $headers = @{
            "Authorization" = "Bearer $apiKey"
            "Content-Type" = "application/json"
        }

        # Query Gemini Router (Port 20129)
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:20129/v1/embeddings" -Method Post -Body $bodyJson -ContentType "application/json" -Headers $headers -TimeoutSec 15
        if ($response -and $response.data -and $response.data.Count -gt 0 -and $response.data[0].embedding) {
            return $response.data[0].embedding
        }
        throw "No embedding found in 9Router response"
    } catch {
        Write-Log "9Router embedding fallback failed: $_" "Red"
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

    $jsonFile = "$env:TEMP\qdrant_$(Get-Date -Format 'yyyyMMddHHmmss').json"
    $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
    [System.IO.File]::WriteAllText($jsonFile, $json, $Utf8NoBomEncoding)

    $pyFile = "$env:TEMP\qdrant_call_$(Get-Date -Format 'yyyyMMddHHmmss').py"
    $pyContent = @"
import subprocess, json, sys
json_file = r'$jsonFile'
url = '$QDRANT_URL/collections/$collection/points'
with open(json_file, 'r') as f:
    data = f.read()
result = subprocess.run(
    ['curl', '-s', '-X', 'PUT', url, '-H', 'Content-Type: application/json', '-d', data],
    capture_output=True, text=True
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
    $result = & python.exe $pyFile 2>&1
    Remove-Item $jsonFile, $pyFile -Force -ErrorAction SilentlyContinue

    if ($result -match 'OK') { return $true }
    Write-Log "Qdrant upsert failed: $result" "Red"
    return $false
}

# Helper : sync un fichier markdown vers une collection
function Sync-MarkdownToCollection {
    param(
        [string]$filePath,
        [string]$collection,
        [string]$type
    )
    if (-not (Test-Path $filePath)) {
        Write-Log "$type : fichier absent ($filePath)" "Yellow"
        return
    }
    $content = Get-Content $filePath -Raw
    if (-not $content -or $content.Length -lt 10) {
        Write-Log "$type : fichier vide" "Yellow"
        return
    }
    
    Write-Log "Syncing $type..." "Cyan"
    $embedding = Get-OllamaEmbedding $content
    if (-not $embedding) {
        Write-Log "Ollama embedding failed for $type, trying 9Router fallback..." "Yellow"
        $embedding = Get-9RouterEmbedding $content
    }

    if (-not $embedding) {
        Write-Log "CRITICAL ERROR: Failed to get embedding for $type from both Ollama and 9Router. Terminating script." "Red"
        exit 1
    }

    $preview = ($content -replace "`n", " " -replace "\s+", " ").Substring(0, [Math]::Min(200, $content.Length))
    $payload = @{
        source = (Split-Path $filePath -Leaf)
        date = $TODAY
        type = $type
        preview = $preview
        title = (Split-Path $filePath -Leaf)
    }
    if (Add-ToQdrant $collection "${type}_$TODAY" $embedding $payload) {
        Write-Log "$type upserted to Qdrant" "Green"
    }
}

# ===========================
# 1. DECISIONS
# ===========================
Sync-MarkdownToCollection `
    -filePath "$DEV_CORE_DATA\Memory\DECISIONS.md" `
    -collection "decisions" `
    -type "decisions"

# ===========================
# 2. LESSONS
# ===========================
Sync-MarkdownToCollection `
    -filePath "$DEV_CORE_DATA\Memory\LESSONS.md" `
    -collection "lessons" `
    -type "lessons"

# ===========================
# 3. PATTERNS
# ===========================
Sync-MarkdownToCollection `
    -filePath "$DEV_CORE_DATA\Memory\PATTERNS.md" `
    -collection "patterns" `
    -type "patterns"

# ===========================
# 4. CODEBASE
# ===========================
# Generer un index codebase a partir des scripts et modules Python
Write-Log "Syncing codebase..." "Cyan"

$codebaseIndex = "# DEV_CORE Codebase Index`n`n"

# Scripts principaux
$codebaseIndex += "## Scripts`n"
$scripts = Get-ChildItem "$DEV_CORE\Scripts\*.ps1" -File
foreach ($s in $scripts) {
    $firstLine = (Get-Content $s.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($s.Name) : $firstLine`n"
}

# Auto layer
$codebaseIndex += "`n## Auto Layer`n"
$autoScripts = Get-ChildItem "$DEV_CORE\Scripts\Auto\*.ps1" -File
foreach ($s in $autoScripts) {
    $firstLine = (Get-Content $s.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($s.Name) : $firstLine`n"
}

# Python modules
$codebaseIndex += "`n## Python Tools`n"
$pyModules = Get-ChildItem "$DEV_CORE\Tools\devcore\*.py" -File | Where-Object { $_.Name -ne "__init__.py" }
foreach ($m in $pyModules) {
    $firstLine = (Get-Content $m.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($m.Name) : $firstLine`n"
}

# Skills
$codebaseIndex += "`n## Skills`n"
$skillDirs = Get-ChildItem "$DEV_CORE\Skills" -Directory
foreach ($d in $skillDirs) {
    $skillMd = "$($d.FullName)\SKILL.md"
    if (Test-Path $skillMd) {
        $desc = (Get-Content $skillMd | Select-Object -Skip 2 -First 1) -replace "^description:\s*>?-?\s*", ""
        $codebaseIndex += "- $($d.Name) : $desc`n"
    }
}

# Sauvegarder l'index
$indexPath = "$DEV_CORE_DATA\Memory\CODEBASE_INDEX.md"
$codebaseIndex | Set-Content $indexPath -Encoding UTF8

$embedding = Get-OllamaEmbedding $codebaseIndex
if (-not $embedding) {
    Write-Log "Ollama embedding failed for codebase index, trying 9Router fallback..." "Yellow"
    $embedding = Get-9RouterEmbedding $codebaseIndex
}

if (-not $embedding) {
    Write-Log "CRITICAL ERROR: Failed to get embedding for codebase index from both Ollama and 9Router. Terminating script." "Red"
    exit 1
}

$preview = ($codebaseIndex -replace "`n", " " -replace "\s+", " ").Substring(0, [Math]::Min(200, $codebaseIndex.Length))
$payload = @{
    source = "CODEBASE_INDEX.md"
    date = $TODAY
    type = "codebase"
    preview = $preview
    title = "CODEBASE_INDEX.md"
    scripts_count = $scripts.Count.ToString()
    modules_count = $pyModules.Count.ToString()
    skills_count = $skillDirs.Count.ToString()
}
if (Add-ToQdrant "codebase" "codebase_$TODAY" $embedding $payload) {
    Write-Log "Codebase index upserted to Qdrant" "Green"
}

# ===========================
# RAPPORT FINAL
# ===========================
Write-Host ""
$collections = @("decisions","lessons","patterns","codebase")
foreach ($c in $collections) {
    try {
        $info = Invoke-RestMethod "$QDRANT_URL/collections/$c" -TimeoutSec 3
        $count = $info.result.points_count
        Write-Host "    $($c.PadRight(12)) : $count points" -ForegroundColor $(if($count -gt 0){"Green"}else{"Yellow"})
    } catch {
        Write-Host "    $($c.PadRight(12)) : erreur" -ForegroundColor Red
    }
}

# Agréger les atomes L1 en scénarios L2 et mettre à jour le persona L3
try {
    Write-Log "Agrégation de la mémoire hiérarchique L1 -> L2/L3..." "Cyan"
    & "$DEV_CORE\Scripts\memory_hierarchy.ps1" -Action Aggregate
} catch {
    Write-Log "Erreur d'agrégation de la mémoire : $_" "Yellow"
}

Write-Log "Qdrant sync complete (4 collections)" "Green"
Write-Host ""
