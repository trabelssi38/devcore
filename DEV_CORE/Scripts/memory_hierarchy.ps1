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

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$DB_PATH       = "$DEV_CORE_DATA\Memory\conversations.db"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\memory_hierarchy_$TODAY.log"
$MEMORY_SERVICE = "$DEV_CORE\Scripts\memory_service.ps1"
$CONTEXT_SERVICE = "$DEV_CORE\Scripts\context_service.ps1"

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
                    $results += ("- {0} score={1} relevance={2} freshness={3} authority={4}" -f $source.id, $source.score, $source.relevance, $source.freshness, $source.authority)
                }
            } catch {
                Log "Context source scoring failed: $_" "Yellow"
            }
        }
        
        # 1. L3: Persona (Toujours chargé)
        $personaPath = & $MEMORY_SERVICE -Action Path -Name PERSONA
        if (Test-Path $personaPath) {
            $results += "`n[L3 Persona]"
            $results += (& $MEMORY_SERVICE -Action ReadText -Name PERSONA | Out-String).TrimEnd()
        }
        
        # 2. L2: Scenarios (Filtré par TaskType)
        $scenarioFile = & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType $TaskType
        if (Test-Path $scenarioFile) {
            $results += "`n[L2 Scenario: $TaskType]"
            $results += (& $MEMORY_SERVICE -Action ReadText -Name SCENARIO -TaskType $TaskType | Out-String).TrimEnd()
        } else {
            # Fallback sur general
            $generalScenario = & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType "devcore"
            if (Test-Path $generalScenario) {
                $results += "`n[L2 Scenario: devcore]"
                $results += (& $MEMORY_SERVICE -Action ReadText -Name SCENARIO -TaskType "devcore" | Out-String).TrimEnd()
            }
        }
        
        # 3. L1: Qdrant vector DB search (si disponible)
        # Note: on utilise les scripts existants ou curl pour chercher dans décisions/lessons/patterns
        # On va tenter une recherche Qdrant rapide
        $qdrantUrl = "http://localhost:6333"
        
        $hasVectorResult = $false
        
        # On obtient l'embedding via Gemini Router (Port 20130)
        $maxAttempts = 3
        $vector = $null
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            try {
                Log "Attempting to get query embedding (attempt $attempt/$maxAttempts)..." "Gray"
                $bodyObj = @{
                    model = "gemini-embedding-001"
                    input = $Query
                }
                $jsonStr = $bodyObj | ConvertTo-Json
                $bodyJson = [System.Text.Encoding]::UTF8.GetBytes($jsonStr)
                $apiKey = "dummy_key"
                $headers = @{
                    "Authorization" = "Bearer $apiKey"
                }
                $embedRes = Invoke-RestMethod -Uri "http://127.0.0.1:20130/v1/embeddings" -Method Post -Body $bodyJson -ContentType "application/json; charset=utf-8" -Headers $headers -TimeoutSec 10
                
                if ($embedRes -and $embedRes.data -and $embedRes.data.Count -gt 0 -and $embedRes.data[0].embedding) {
                    $vector = $embedRes.data[0].embedding
                    Log "Query embedding retrieved successfully (vector size: $($vector.Count))" "Green"
                    break
                }
                throw "No embedding found in response"
            } catch {
                Log "Embedding query failed on attempt ${attempt}: $_" "Yellow"
                if ($attempt -lt $maxAttempts) {
                    Start-Sleep -Seconds 1
                }
            }
        }
        
        if ($vector) {
            try {
                $roundedVector = $vector | ForEach-Object { "{0:F6}" -f [double]$_ }
                $vectorStr = $roundedVector -join ','
                
                # Chercher dans la collection "decisions" et "lessons"
                foreach ($col in @("decisions", "lessons", "patterns")) {
                    Log "Searching collection '$col' in Qdrant..." "Gray"
                    $searchJson = '{"vector":[' + $vectorStr + '],"limit":3,"with_payload":true}'
                    $tempSearchFile = "$env:TEMP\qdrant_search_$(Get-Date -Format 'yyyyMMddHHmmss').json"
                    $Utf8NoBom = New-Object System.Text.UTF8Encoding $False
                    [System.IO.File]::WriteAllText($tempSearchFile, $searchJson, $Utf8NoBom)
                    
                    $searchRes = & curl.exe --max-time 10 -s -X POST "$qdrantUrl/collections/$col/points/search" -H 'Content-Type: application/json' --data-binary "@$tempSearchFile"
                    Remove-Item $tempSearchFile -Force -ErrorAction SilentlyContinue
                    
                    $searchObj = $searchRes | ConvertFrom-Json
                    if ($searchObj.result) {
                        $matchCount = 0
                        foreach ($point in $searchObj.result) {
                            if ($point.score -gt 0.75) {
                                $results += "`n[L1 Atom: $col (Score: $($point.score))]"
                                $results += $point.payload.preview
                                $hasVectorResult = $true
                                $matchCount++
                            }
                        }
                        Log "Found $matchCount matches with score > 0.75 in collection '$col'" "Green"
                    } else {
                        Log "No results returned for collection '$col'" "Yellow"
                    }
                }
            } catch {
                Log "Qdrant search query failed: $_" "Red"
            }
        } else {
            Log "Skipping Qdrant vector search due to missing embedding." "Yellow"
        }
        
        # 4. L0: SQLite full-text search fallback (si aucun résultat Qdrant satisfaisant)
        if (-not $hasVectorResult) {
            try {
                $pySearch = @"
import sqlite3
import json
conn = sqlite3.connect(r'$DB_PATH')
c = conn.cursor()
query = "$Query"
# FTS5 search
try:
    c.execute("SELECT project, task_id, content FROM conversations_fts WHERE content MATCH ? LIMIT 3", (query,))
    rows = c.fetchall()
    if rows:
        print("MATCHES:")
        for r in rows:
            print(f"- [{r[0]}/{r[1]}] {r[2][:300]}...")
except Exception as e:
    # FTS5 not supported or table empty
    c.execute("SELECT project, task_id, content FROM conversations WHERE content LIKE ? LIMIT 3", (f"%{query}%",))
    rows = c.fetchall()
    if rows:
        print("MATCHES:")
        for r in rows:
            print(f"- [{r[0]}/{r[1]}] {r[2][:300]}...")
conn.close()
"@
                $tempPy = "$env:TEMP\sqlite_search_$(Get-Date -Format 'yyyyMMddHHmmss').py"
                $pySearch | Set-Content $tempPy -Encoding UTF8
                $sqlRes = & python.exe $tempPy 2>$null
                Remove-Item $tempPy -Force -ErrorAction SilentlyContinue
                
                if ($sqlRes -match "MATCHES:") {
                    $results += "`n[L0 Conversation Fallback]"
                    $results += $sqlRes -replace "MATCHES:", ""
                }
            } catch {}
        }
        
        # Output everything
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
