# memory_hierarchy.ps1 -- DEV_CORE v9.0
# Gère la hiérarchie de mémoire L0-L3 (Persona, Scenarios, Qdrant, SQLite)
# Usage : & "memory_hierarchy.ps1" -Action Query -Query "JWT auth" -TaskType "auth"
#         & "memory_hierarchy.ps1" -Action Aggregate
#         & "memory_hierarchy.ps1" -Action LogConversation -Role "user" -Content "..."

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Query", "Aggregate", "LogConversation", "Test")]
    [string]$Action,
    
    [string]$Query,
    [string]$TaskType = "devcore", # "auth", "api", "ui", "deploy", "debug", "devcore"
    [string]$Role,
    [string]$Content,
    [string]$TaskId
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$DB_PATH       = "$DEV_CORE_DATA\Memory\conversations.db"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\memory_hierarchy_$TODAY.log"
$MEMORY_SERVICE = "$DEV_CORE\Scripts\memory_service.ps1"
$CONTEXT_SERVICE = "$DEV_CORE\Scripts\context_service.ps1"
. "$DEV_CORE\Scripts\embedding_contract.ps1"
$EMBEDDING_CONTRACT = Get-DevCoreEmbeddingContract

function Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] [$Action] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    if ($Action -ne "Query") {
        Write-Host "  $l" -ForegroundColor $color
    }
}

$projName = & "$DEV_CORE\Scripts\Get-ActiveProject.ps1"

switch ($Action) {
    "Query" {
        if (-not $Query) {
            Write-Error "Argument Query manquant pour Query."
            exit 1
        }
        
        $results = @()
        $results += "=== MEMORY HIERARCHY SEARCH RESULTS ==="

        if (Test-Path $CONTEXT_SERVICE) {
            try {
                $scorePayload = & $CONTEXT_SERVICE -Action ScoreSources -Query $Query -TaskType $TaskType -Json | Out-String | ConvertFrom-Json
                $results += "`n=== CONTEXT SOURCE SCORES ==="
                foreach ($source in @($scorePayload.sources | Where-Object { $_.included })) {
                    $results += ("- {0} score={1} relevance={2} freshness={3} authority={4} reason={5}" -f $source.id, $source.score, $source.relevance, $source.freshness, $source.authority, $source.justification)
                }
            } catch {
                Log "Context source scoring failed: $_" "Yellow"
            }
        }
        
        # 1. L3 Persona & L2 Scenario (chargement immédiat)
        $personaPath = & $MEMORY_SERVICE -Action Path -Name PERSONA
        if (Test-Path $personaPath) {
            $results += "`n[L3 Persona]"
            $results += (& $MEMORY_SERVICE -Action ReadText -Name PERSONA | Out-String).TrimEnd()
        }
        
        $scenarioFile = & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType $TaskType
        if (Test-Path $scenarioFile) {
            $results += "`n[L2 Scenario: $TaskType]"
            $results += (& $MEMORY_SERVICE -Action ReadText -Name SCENARIO -TaskType $TaskType | Out-String).TrimEnd()
        } else {
            $generalScenario = & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType "devcore"
            if (Test-Path $generalScenario) {
                $results += "`n[L2 Scenario: devcore]"
                $results += (& $MEMORY_SERVICE -Action ReadText -Name SCENARIO -TaskType "devcore" | Out-String).TrimEnd()
            }
        }

        # 2. Récupération des multiplicateurs de score Context Service
        $contextMultipliers = @{}
        if (Test-Path $CONTEXT_SERVICE) {
            try {
                $scorePayload = & $CONTEXT_SERVICE -Action ScoreSources -Query $Query -TaskType $TaskType -Json | Out-String | ConvertFrom-Json
                foreach ($source in @($scorePayload.sources)) {
                    $contextMultipliers[$source.id] = [double]$source.score
                }
            } catch {
                Log "Context source scoring failed: $_" "Yellow"
            }
        }

        # 3. Lancement parallèle : Qdrant Vector Search (4 collections) + SQLite FTS5 Search
        $qdrantUrl = "http://localhost:6333"
        $collections = @("decisions", "lessons", "patterns", "codebase")
        
        # Récupération de l'embedding via Gemini Router (20130)
        $vector = $null
        try {
            $bodyObj = New-DevCoreEmbeddingRequestBody -Text $Query -Query
            $jsonStr = $bodyObj | ConvertTo-Json
            $bodyJson = [System.Text.Encoding]::UTF8.GetBytes($jsonStr)
            $headers = @{ "Authorization" = "Bearer dummy_key" }
            $embedRes = Invoke-RestMethod -Uri $EMBEDDING_CONTRACT.endpoint -Method Post -Body $bodyJson -ContentType "application/json; charset=utf-8" -Headers $headers -TimeoutSec 10
            if ($embedRes -and $embedRes.data -and $embedRes.data.Count -gt 0 -and $embedRes.data[0].embedding) {
                $vector = $embedRes.data[0].embedding
            }
        } catch {
            Log "Embedding query failed: $_" "Yellow"
        }

        # Structure pour accumuler les listes de résultats (pour RRF)
        $rankedLists = @()

        # Job 1: SQLite FTS5 Search
        $ftsScript = @"
import sqlite3, json
conn = sqlite3.connect(r'$DB_PATH')
c = conn.cursor()
query = "$Query"
res = []
try:
    c.execute("SELECT project, task_id, content FROM conversations_fts WHERE content MATCH ? LIMIT 10", (query,))
    rows = c.fetchall()
    for r in rows:
        res.append({"id": f"fts_{r[0]}_{r[1]}", "type": "fts", "preview": f"[{r[0]}/{r[1]}] {r[2][:300]}..."})
except Exception:
    c.execute("SELECT project, task_id, content FROM conversations WHERE content LIKE ? LIMIT 10", (f"%{query}%",))
    rows = c.fetchall()
    for r in rows:
        res.append({"id": f"fts_{r[0]}_{r[1]}", "type": "fts", "preview": f"[{r[0]}/{r[1]}] {r[2][:300]}..."})
conn.close()
print(json.dumps(res))
"@
        $ftsResult = @()
        try {
            $tempPy = "$env:TEMP\sqlite_fts_$(Get-Date -Format 'yyyyMMddHHmmss').py"
            $ftsScript | Set-Content $tempPy -Encoding UTF8
            $rawJson = & python.exe $tempPy 2>$null
            Remove-Item $tempPy -Force -ErrorAction SilentlyContinue
            if ($rawJson) {
                $ftsResult = $rawJson | ConvertFrom-Json
                if ($ftsResult.Count -gt 0) {
                    $rankedLists += ,$ftsResult
                }
            }
        } catch {}

        # Job 2: Qdrant Vector Search sur les 4 collections
        if ($vector) {
            $roundedVector = $vector | ForEach-Object { "{0:F6}" -f [double]$_ }
            $vectorStr = $roundedVector -join ','
            foreach ($col in $collections) {
                try {
                    $searchJson = '{"vector":[' + $vectorStr + '],"limit":5,"with_payload":true}'
                    $tempSearchFile = "$env:TEMP\qdrant_search_$col`_$(Get-Date -Format 'yyyyMMddHHmmss').json"
                    $Utf8NoBom = New-Object System.Text.UTF8Encoding $False
                    [System.IO.File]::WriteAllText($tempSearchFile, $searchJson, $Utf8NoBom)
                    
                    $searchRes = & curl.exe --max-time 5 -s -X POST "$qdrantUrl/collections/$col/points/search" -H 'Content-Type: application/json' --data-binary "@$tempSearchFile"
                    Remove-Item $tempSearchFile -Force -ErrorAction SilentlyContinue
                    
                    $searchObj = $searchRes | ConvertFrom-Json
                    if ($searchObj.result -and $searchObj.result.Count -gt 0) {
                        $colList = @()
                        foreach ($pt in $searchObj.result) {
                            $colList += [pscustomobject]@{
                                id = "$col`_" + $pt.id
                                type = "qdrant_$col"
                                preview = "[L1 Atom: $col (Score: $($pt.score))] " + $pt.payload.preview
                            }
                        }
                        $rankedLists += ,$colList
                    }
                } catch {}
            }
        }

        # 4. Fusion RRF (Reciprocal Rank Fusion) avec k=60 & Application des Multiplicateurs Context Service
        $k = 60
        $rrfScores = @{}
        $previews = @{}

        foreach ($list in $rankedLists) {
            $rank = 1
            foreach ($item in $list) {
                $itemId = $item.id
                $previews[$itemId] = $item.preview
                $rrfContribution = 1.0 / ($k + $rank)
                
                if (-not $rrfScores.ContainsKey($itemId)) {
                    $rrfScores[$itemId] = 0.0
                }
                $rrfScores[$itemId] += $rrfContribution
                $rank++
            }
        }

        # Application des multiplicateurs Context Service si présents
        $finalScores = @{}
        foreach ($itemId in $rrfScores.Keys) {
            $mult = 1.0
            if ($contextMultipliers.ContainsKey($itemId)) {
                $mult = [double]$contextMultipliers[$itemId]
            }
            $finalScores[$itemId] = $rrfScores[$itemId] * $mult
        }

        # Tri et extraction des Top 5 résultats
        $topResults = $finalScores.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5

        if ($topResults) {
            $results += "`n=== HYBRID RRF SEARCH RESULTS (Top 5) ==="
            foreach ($entry in $topResults) {
                $itemId = $entry.Key
                $score = [math]::Round($entry.Value, 5)
                $preview = $previews[$itemId]
                $results += "- [RRF Score: $score] $preview"
            }
        }

        # Output tout
        $results -join "`n"
    }
    
    "Aggregate" {
        Log "Agrégation de la mémoire hiérarchique L1 -> L2..." "Cyan"
        # Ce script agrège les décisions, leçons et patterns récents
        # dans les fichiers de Scenarios correspondants.
        
        # Créer scenarios si absents
        & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType "devcore" | Out-Null
        
        # Lister les fichiers sources
        $decisionsFile = & $MEMORY_SERVICE -Action Path -Name DECISIONS
        $lessonsFile = & $MEMORY_SERVICE -Action Path -Name LESSONS
        $patternsFile = & $MEMORY_SERVICE -Action Path -Name PATTERNS
        
        # Types de tâches cibles
        $types = @("auth", "api", "ui", "deploy", "debug", "devcore")
        
        foreach ($t in $types) {
            $content = "# Scenario: " + $t.ToUpper() + "`n`n"
            
            # 1. Decisions
            if (Test-Path $decisionsFile) {
                $decisions = ((& $MEMORY_SERVICE -Action ReadText -Name DECISIONS | Out-String) -split "\r?\n") | Where-Object { $_ -match $t }
                if ($decisions) {
                    $content += "## Decisions`n"
                    $content += ($decisions -join "`n") + "`n`n"
                }
            }
            
            # 2. Lessons
            if (Test-Path $lessonsFile) {
                $lessons = ((& $MEMORY_SERVICE -Action ReadText -Name LESSONS | Out-String) -split "\r?\n") | Where-Object { $_ -match $t }
                if ($lessons) {
                    $content += "## Lessons`n"
                    $content += ($lessons -join "`n") + "`n`n"
                }
            }
            
            # Enregistrer le scénario s'il contient des infos, sinon écrire un squelette
            if ($content.Length -gt 50) {
                & $MEMORY_SERVICE -Action WriteText -Name SCENARIO -TaskType $t -Content $content | Out-Null
                Write-Host "  Scénario mis à jour : $t" -ForegroundColor Green
            }
        }
        
        # Mettre à jour le persona.md en y injectant les 5 derniers patterns
        $personaPath = & $MEMORY_SERVICE -Action Path -Name PERSONA
        if ((Test-Path $personaPath) -and (Test-Path $patternsFile)) {
            $patterns = ((& $MEMORY_SERVICE -Action ReadText -Name PATTERNS | Out-String) -split "\r?\n") | Select-Object -Last 5
            if ($patterns) {
                $persona = (& $MEMORY_SERVICE -Action ReadText -Name PERSONA | Out-String).TrimEnd()
                # Remplacer la section Patterns récurrents
                $newPatterns = "## Patterns récurrents`n" + ($patterns -join "`n")
                if ($persona -match "## Patterns récurrents[\s\S]*") {
                    $persona = $persona -replace "## Patterns récurrents[\s\S]*", $newPatterns
                } else {
                    $persona += "`n`n" + $newPatterns
                }
                & $MEMORY_SERVICE -Action WriteText -Name PERSONA -Content $persona | Out-Null
                Write-Host "  Persona.md mis à jour avec les derniers patterns." -ForegroundColor Green
            }
        }
    }
    
    "LogConversation" {
        if (-not $Role -or -not $Content) {
            Write-Error "Arguments manquants pour LogConversation: Role et Content requis."
            exit 1
        }
        
        $maxAttempts = 3
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            try {
                Log "Logging conversation to SQLite (attempt $attempt/$maxAttempts)..." "Gray"
                $escContent = $Content -replace '"', '\"' -replace "`n", '\n' -replace "`r", ""
                $escRole = $Role -replace '"', '\"'
                $escProj = $projName -replace '"', '\"'
                $escTaskId = if ($TaskId) { $TaskId } else { "None" }
                
                # Insérer dans SQLite
                $pyInsert = @"
import sqlite3, sys
try:
    conn = sqlite3.connect(r'$DB_PATH', timeout=10.0)
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (session_date, project, task_id, role, content, tokens_estimate) VALUES (?, ?, ?, ?, ?, ?)",
        ('$TODAY', '$escProj', '$escTaskId', '$escRole', """$escContent""", len('$escContent')//4)
    )
    conn.commit()
    conn.close()
    print("OK")
    sys.exit(0)
except Exception as e:
    print("ERROR:", str(e))
    sys.exit(1)
"@
                $tempPy = "$env:TEMP\sqlite_insert_$(Get-Date -Format 'yyyyMMddHHmmss').py"
                $pyInsert | Set-Content $tempPy -Encoding UTF8
                $result = & python.exe $tempPy 2>&1
                Remove-Item $tempPy -Force -ErrorAction SilentlyContinue
                
                if ($result -match "OK") {
                    Log "Log conversation enregistré dans SQLite avec succès." "Green"
                    break
                }
                throw "SQLite insert failed: $result"
            } catch {
                Log "SQLite insert attempt $attempt/$maxAttempts failed: $_" "Yellow"
                if ($attempt -lt $maxAttempts) {
                    Start-Sleep -Seconds 1
                } else {
                    Write-Warning "Impossible d'enregistrer la conversation dans SQLite."
                }
            }
        }
    }
    
    "Test" {
        Write-Host "Test de memory_hierarchy.ps1..."
        # 1. Log conversation
        & $MyInvocation.MyCommand.Path -Action LogConversation -Role "user" -Content "Verification de la memoire hierarchique." -TaskId "T-99"
        
        # 2. Query
        $res = & $MyInvocation.MyCommand.Path -Action Query -Query "Verification" -TaskType "devcore"
        Write-Host "Query Result: $res"
        
        if ($res -match "Verification") {
            Write-Host "Verification MATCH SQLite : OK !" -ForegroundColor Green
        } else {
            Write-Error "Verification MISMATCH SQLite !"
        }
    }
}
