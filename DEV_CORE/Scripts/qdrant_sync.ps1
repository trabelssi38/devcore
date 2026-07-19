# qdrant_sync.ps1 -- DEV_CORE
# Sync des 4 collections Qdrant : decisions, lessons, patterns, codebase
# Sources : DECISIONS.md, LESSONS.md, PATTERNS.md, codebase scan

# Use invariant culture for JSON numbers
[System.Globalization.CultureInfo]::CurrentCulture = [System.Globalization.CultureInfo]::InvariantCulture

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$QDRANT_URL = if ($env:QDRANT_URL) { $env:QDRANT_URL } else { "http://localhost:6333" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$LOG = "$DEV_CORE_DATA\Logs\scripts\qdrant_sync_$TODAY.log"
. "$DEV_CORE\Scripts\platform_version.ps1"
. "$DEV_CORE\Scripts\embedding_contract.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$EMBEDDING_CONTRACT = Get-DevCoreEmbeddingContract

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Qdrant Sync (4 collections)" -ForegroundColor Cyan

# Check Qdrant
try {
    $q = Invoke-RestMethod "$QDRANT_URL/collections" -TimeoutSec 3
    Write-Log "Qdrant connected - $($q.result.collections.Count) collections" "Green"
} catch {
    Write-Log "Qdrant unavailable - sync cancelled" "Yellow"
    exit 0
}

# Get embedding from Gemini Router (OpenAI-compatible endpoint)
function Get-GeminiEmbedding {
    param([string]$text)
    
    $maxAttempts = 3
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            Write-Log "Retrieving embedding from Gemini Router (attempt $attempt/$maxAttempts)..." "Gray"
            # Clean text
            $cleanText = $text -replace "`r", "" -replace "`n", " "
            if ($cleanText.Length -gt 8000) { $cleanText = $cleanText.Substring(0, 8000) }

            $bodyObj = New-DevCoreEmbeddingRequestBody -Text $cleanText
            $jsonStr = $bodyObj | ConvertTo-Json
            $bodyJson = [System.Text.Encoding]::UTF8.GetBytes($jsonStr)

            $apiKey = if ($env:NINEROUTER_API_KEY) { $env:NINEROUTER_API_KEY } elseif ($env:DEVCORE_ROUTER_TOKEN) { $env:DEVCORE_ROUTER_TOKEN } else { "" }
            $headers = @{}
            if ($apiKey) {
                $headers["Authorization"] = "Bearer $apiKey"
            }

            $response = Invoke-RestMethod -Uri $EMBEDDING_CONTRACT.endpoint -Method Post -Body $bodyJson -ContentType "application/json; charset=utf-8" -Headers $headers -TimeoutSec 15
            if ($response -and $response.data -and $response.data.Count -gt 0 -and $response.data[0].embedding) {
                $embedding = $response.data[0].embedding
                Assert-DevCoreEmbeddingVector -Vector $embedding -Context "qdrant_sync"
                Write-Log "Embedding retrieved successfully (vector size: $($embedding.Count))" "Green"
                return $embedding
            }
            throw "No embedding found in response"
        } catch {
            Write-Log "Gemini embedding attempt $attempt/$maxAttempts failed: $_" "Yellow"
            if ($attempt -lt $maxAttempts) {
                Start-Sleep -Seconds 2
            }
        }
    }
    Write-Log "All $maxAttempts attempts for Gemini embedding failed." "Red"
    return $null
}

# Upsert to Qdrant
function Add-ToQdrant {
    param(
        [string]$collection,
        [string]$id,
        [object]$vector,
        [hashtable]$payload
    )
    Assert-DevCoreEmbeddingVector -Vector $vector -Context "Qdrant upsert $collection"
    # Déduplication déterministe via hash SHA-256
    $contentForHash = if ($payload.preview) { $payload.preview } else { $id }
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($contentForHash)
    $hashBytes = $sha256.ComputeHash($bytes)
    $hashHex = ($hashBytes | ForEach-Object { "{0:x2}" -f $_ }) -join ""
    # Formater les 32 caractères hexadécimaux en format GUID standard
    $uuid = "$($hashHex.Substring(0,8))-$($hashHex.Substring(8,4))-$($hashHex.Substring(12,4))-$($hashHex.Substring(16,4))-$($hashHex.Substring(20,12))"
    $payload["sha256"] = $hashHex

    # Round to 6 decimal places
    $roundedVector = $vector | ForEach-Object { "{0:F6}" -f [double]$_ }
    $vectorStr = $roundedVector -join ','

    # Escape payload values
    $payloadParts = @()
    foreach ($key in $payload.Keys) {
        $val = $payload[$key].ToString() -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '\r' -replace "`n", '\n' -replace "`t", '\t'
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

    $maxAttempts = 3
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            Write-Log "Upserting to Qdrant collection '$collection' (attempt $attempt/$maxAttempts)..." "Gray"
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
    ['curl', '--max-time', '15', '-s', '-X', 'PUT', url, '-H', 'Content-Type: application/json', '-d', data],
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
except Exception as ex:
    print('ERROR: Failed to parse response -', str(ex))
    sys.exit(1)
"@
            Set-Content -Path $pyFile -Value $pyContent -Encoding UTF8
            $result = & python.exe $pyFile 2>&1
            Remove-Item $jsonFile, $pyFile -Force -ErrorAction SilentlyContinue

            if ($result -match 'OK') {
                Write-Log "Qdrant upsert success on attempt $attempt" "Green"
                return $true
            }
            throw "Qdrant upsert failed with result: $result"
        } catch {
            Write-Log "Qdrant upsert attempt $attempt/$maxAttempts failed: $_" "Yellow"
            if ($attempt -lt $maxAttempts) {
                Start-Sleep -Seconds 2
            }
        }
    }
    Write-Log "All $maxAttempts attempts for Qdrant upsert failed." "Red"
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
    $embedding = Get-GeminiEmbedding $content
    if (-not $embedding) {
        Write-Log "CRITICAL ERROR: Failed to get embedding for $type from Gemini Router. Terminating script." "Red"
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
Write-Log "Syncing codebase (fragmented)..." "Cyan"

# 1. Collect files
$scripts = @(Get-ChildItem "$DEV_CORE\Scripts\*.ps1" -File -ErrorAction SilentlyContinue)
$autoScripts = @(Get-ChildItem "$DEV_CORE\Scripts\Auto\*.ps1" -File -ErrorAction SilentlyContinue)
$autoPy = @(Get-ChildItem "$DEV_CORE\Scripts\Auto\*.py" -File -ErrorAction SilentlyContinue)
$toolsPy = @(Get-ChildItem "$DEV_CORE\Tools\devcore\*.py" -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "__init__.py" -and $_.Name -notmatch "^test_" })
$mcpPy = @(Get-ChildItem "$DEV_CORE\MCP\devcore-scripts\*.py" -File -ErrorAction SilentlyContinue)

# Also build CODEBASE_INDEX.md for backward compat
$codebaseIndex = "# DEV_CORE Codebase Index`n`n"
$codebaseIndex += "## Scripts`n"
foreach ($s in $scripts) {
    $firstLine = (Get-Content $s.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($s.Name) : $firstLine`n"
}
$codebaseIndex += "`n## Auto Layer`n"
foreach ($s in $autoScripts) {
    $firstLine = (Get-Content $s.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($s.Name) : $firstLine`n"
}
foreach ($s in $autoPy) {
    $firstLine = (Get-Content $s.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($s.Name) : $firstLine`n"
}
$codebaseIndex += "`n## Python Tools`n"
foreach ($m in $toolsPy) {
    $firstLine = (Get-Content $m.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($m.Name) : $firstLine`n"
}
$codebaseIndex += "`n## MCP Scripts`n"
foreach ($m in $mcpPy) {
    $firstLine = (Get-Content $m.FullName -TotalCount 1) -replace "^#\s*", ""
    $codebaseIndex += "- $($m.Name) : $firstLine`n"
}
$codebaseIndex += "`n## Skills`n"
$skillDirs = Get-ChildItem "$DEV_CORE\Skills" -Directory -ErrorAction SilentlyContinue
foreach ($d in $skillDirs) {
    $skillMd = "$($d.FullName)\SKILL.md"
    if (Test-Path $skillMd) {
        $desc = (Get-Content $skillMd | Select-Object -Skip 2 -First 1) -replace "^description:\s*>?-?\s*", ""
        $codebaseIndex += "- $($d.Name) : $desc`n"
    }
}
$indexPath = "$DEV_CORE_DATA\Memory\CODEBASE_INDEX.md"
$codebaseIndex | Set-Content $indexPath -Encoding UTF8

$allFiles = @()
$allFiles += $scripts
$allFiles += $autoScripts
$allFiles += $autoPy
$allFiles += $toolsPy
$allFiles += $mcpPy

# Limit to max 50 files
$allFiles = $allFiles | Select-Object -First 50

# 2. Process summaries
$processedFiles = @()
foreach ($file in $allFiles) {
    $lines = Get-Content $file.FullName
    if (-not $lines) { continue }
    # Ensure $lines is an array even for 1-line files
    if ($lines -is [string]) { $lines = @($lines) }
    if ($lines.Count -eq 0) { continue }
    
    $firstLine = $lines[0] -replace "^#\s*", "" -replace '"', "'"
    $size = $file.Length
    $ext = $file.Extension
    
    $funcCount = 0
    $classCount = 0
    if ($ext -eq ".py") {
        $funcCount = @($lines -match "^def ").Count
        $classCount = @($lines -match "^class ").Count
    } elseif ($ext -eq ".ps1") {
        $funcCount = @($lines -match "^function ").Count
    }
    
    $type = "script"
    if ($file.FullName -match "\\MCP\\devcore-scripts\\") { $type = "mcp" }
    elseif ($file.FullName -match "\\Tools\\devcore\\") { $type = "module" }
    
    $relPath = $file.FullName.Substring($DEV_CORE.Length + 1)
    $summary = "File: $relPath`nType: $type`nDescription: $firstLine`nSize: $size bytes`nFunctions: $funcCount"
    if ($ext -eq ".py") {
        $summary += "`nClasses: $classCount"
    }
    
    $processedFiles += @{
        File = $file
        Summary = $summary
        FirstLine = $firstLine
        FuncCount = $funcCount
        Type = $type
        RelPath = $relPath
    }
}

# 3. Batch and upsert
$batchSize = 10
for ($i = 0; $i -lt $processedFiles.Count; $i += $batchSize) {
    $batch = $processedFiles | Select-Object -Skip $i -First $batchSize
    $batchText = ($batch.Summary -join "`n`n")
    Write-Log "Processing codebase batch $([math]::Floor($i/$batchSize) + 1) ($($batch.Count) files)..." "Cyan"
    
    $embedding = Get-GeminiEmbedding $batchText
    if (-not $embedding) {
        Write-Log "Failed to get embedding for batch, skipping." "Yellow"
        continue
    }
    
    foreach ($item in $batch) {
        $payload = @{
            path = $item.RelPath
            type = $item.Type
            description = $item.FirstLine
            functions_count = $item.FuncCount.ToString()
            size = $item.File.Length.ToString()
            last_modified = $item.File.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            source = $item.File.Name
            preview = $item.Summary
        }
        $id = "codebase_$($item.RelPath -replace '[^a-zA-Z0-9]','_')"
        if (Add-ToQdrant "codebase" $id $embedding $payload) {
            Write-Log "Upserted $($item.File.Name) to Qdrant" "Green"
        }
    }
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
