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

$projName = & "$DEV_CORE\Scripts\Get-ActiveProject.ps1"

switch ($Action) {
    "Query" {
        if (-not $Query) {
            Write-Error "Argument Query manquant pour Query."
            exit 1
        }
        
        $results = @()
        $results += "=== MEMORY HIERARCHY SEARCH RESULTS ==="
        
        # 1. L3: Persona (Toujours chargé)
        $personaPath = "$DEV_CORE_DATA\Memory\persona.md"
        if (Test-Path $personaPath) {
            $results += "`n[L3 Persona]"
            $results += Get-Content $personaPath -Raw
        }
        
        # 2. L2: Scenarios (Filtré par TaskType)
        $scenarioFile = "$DEV_CORE_DATA\Memory\Scenarios\${TaskType}.md"
        if (Test-Path $scenarioFile) {
            $results += "`n[L2 Scenario: $TaskType]"
            $results += Get-Content $scenarioFile -Raw
        } else {
            # Fallback sur general
            $generalScenario = "$DEV_CORE_DATA\Memory\Scenarios\devcore.md"
            if (Test-Path $generalScenario) {
                $results += "`n[L2 Scenario: devcore]"
                $results += Get-Content $generalScenario -Raw
            }
        }
        
        # 3. L1: Qdrant vector DB search (si disponible)
        # Note: on utilise les scripts existants ou curl pour chercher dans décisions/lessons/patterns
        # On va tenter une recherche Qdrant rapide
        $qdrantUrl = "http://localhost:6333"
        $ollamaUrl = "http://localhost:11434"
        
        $hasVectorResult = $false
        
        # On obtient l'embedding via Gemini Router (Port 20129)
        try {
            $bodyObj = @{
                model = "gemini-embedding-001"
                input = $Query
            }
            $bodyJson = $bodyObj | ConvertTo-Json
            $apiKey = "dummy_key"
            $headers = @{
                "Authorization" = "Bearer $apiKey"
                "Content-Type" = "application/json"
            }
            $embedRes = Invoke-RestMethod -Uri "http://127.0.0.1:20129/v1/embeddings" -Method Post -Body $bodyJson -ContentType "application/json" -Headers $headers -TimeoutSec 10
            
            if ($embedRes -and $embedRes.data -and $embedRes.data.Count -gt 0 -and $embedRes.data[0].embedding) {
                $vector = $embedRes.data[0].embedding
                $roundedVector = $vector | ForEach-Object { "{0:F6}" -f [double]$_ }
                $vectorStr = $roundedVector -join ','
                
                # Chercher dans la collection "decisions" et "lessons"
                foreach ($col in @("decisions", "lessons", "patterns")) {
                    $searchJson = '{"vector":[' + $vectorStr + '],"limit":3,"with_payload":true}'
                    $tempSearchFile = "$env:TEMP\qdrant_search_$(Get-Date -Format 'yyyyMMddHHmmss').json"
                    $Utf8NoBom = New-Object System.Text.UTF8Encoding $False
                    [System.IO.File]::WriteAllText($tempSearchFile, $searchJson, $Utf8NoBom)
                    
                    $searchRes = & curl.exe -s -X POST "$qdrantUrl/collections/$col/points/search" -H 'Content-Type: application/json' --data-binary "@$tempSearchFile"
                    Remove-Item $tempSearchFile -Force -ErrorAction SilentlyContinue
                    
                    $searchObj = $searchRes | ConvertFrom-Json
                    if ($searchObj.result) {
                        foreach ($point in $searchObj.result) {
                            if ($point.score -gt 0.75) {
                                $results += "`n[L1 Atom: $col (Score: $($point.score))]"
                                $results += $point.payload.preview
                                $hasVectorResult = $true
                            }
                        }
                    }
                }
            }
        } catch {
            # Qdrant ou Ollama down, pas grave on passe
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
        Write-Host "Agrégation de la mémoire hiérarchique L1 -> L2..."
        # Ce script agrège les décisions, leçons et patterns récents
        # dans les fichiers de Scenarios correspondants.
        
        # Créer scenarios si absents
        $scenariosDir = "$DEV_CORE_DATA\Memory\Scenarios"
        if (-not (Test-Path $scenariosDir)) {
            New-Item -ItemType Directory -Path $scenariosDir -Force | Out-Null
        }
        
        # Lister les fichiers sources
        $decisionsFile = "$DEV_CORE_DATA\Memory\DECISIONS.md"
        $lessonsFile = "$DEV_CORE_DATA\Memory\LESSONS.md"
        $patternsFile = "$DEV_CORE_DATA\Memory\PATTERNS.md"
        
        # Types de tâches cibles
        $types = @("auth", "api", "ui", "deploy", "debug", "devcore")
        
        foreach ($t in $types) {
            $scenarioPath = "$scenariosDir\${t}.md"
            $content = "# Scenario: " + $t.ToUpper() + "`n`n"
            
            # 1. Decisions
            if (Test-Path $decisionsFile) {
                $decisions = Get-Content $decisionsFile | Where-Object { $_ -match $t }
                if ($decisions) {
                    $content += "## Decisions`n"
                    $content += ($decisions -join "`n") + "`n`n"
                }
            }
            
            # 2. Lessons
            if (Test-Path $lessonsFile) {
                $lessons = Get-Content $lessonsFile | Where-Object { $_ -match $t }
                if ($lessons) {
                    $content += "## Lessons`n"
                    $content += ($lessons -join "`n") + "`n`n"
                }
            }
            
            # Enregistrer le scénario s'il contient des infos, sinon écrire un squelette
            if ($content.Length -gt 50) {
                $content | Set-Content $scenarioPath -Encoding UTF8
                Write-Host "  Scénario mis à jour : $t" -ForegroundColor Green
            }
        }
        
        # Mettre à jour le persona.md en y injectant les 5 derniers patterns
        $personaPath = "$DEV_CORE_DATA\Memory\persona.md"
        if (Test-Path $personaPath -and (Test-Path $patternsFile)) {
            $patterns = Get-Content $patternsFile | Select-Object -Last 5
            if ($patterns) {
                $persona = Get-Content $personaPath -Raw
                # Remplacer la section Patterns récurrents
                $newPatterns = "## Patterns récurrents`n" + ($patterns -join "`n")
                if ($persona -match "## Patterns récurrents[\s\S]*") {
                    $persona = $persona -replace "## Patterns récurrents[\s\S]*", $newPatterns
                } else {
                    $persona += "`n`n" + $newPatterns
                }
                $persona | Set-Content $personaPath -Encoding UTF8
                Write-Host "  Persona.md mis à jour avec les derniers patterns." -ForegroundColor Green
            }
        }
    }
    
    "LogConversation" {
        if (-not $Role -or -not $Content) {
            Write-Error "Arguments manquants pour LogConversation: Role et Content requis."
            exit 1
        }
        
        try {
            $escContent = $Content -replace '"', '\"' -replace "`n", '\n' -replace "`r", ""
            $escRole = $Role -replace '"', '\"'
            $escProj = $projName -replace '"', '\"'
            $escTaskId = if ($TaskId) { $TaskId } else { "None" }
            
            # Insérer dans SQLite
            $pyInsert = @"
import sqlite3
conn = sqlite3.connect(r'$DB_PATH')
c = conn.cursor()
c.execute(
    "INSERT INTO conversations (session_date, project, task_id, role, content, tokens_estimate) VALUES (?, ?, ?, ?, ?, ?)",
    ('$TODAY', '$escProj', '$escTaskId', '$escRole', """$escContent""", len('$escContent')//4)
)
conn.commit()
conn.close()
"@
            $tempPy = "$env:TEMP\sqlite_insert_$(Get-Date -Format 'yyyyMMddHHmmss').py"
            $pyInsert | Set-Content $tempPy -Encoding UTF8
            python.exe $tempPy 2>$null
            Remove-Item $tempPy -Force -ErrorAction SilentlyContinue
            Write-Host "Log conversation enregistré dans SQLite."
        } catch {
            Write-Warning "Impossible d'enregistrer la conversation dans SQLite: $_"
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
