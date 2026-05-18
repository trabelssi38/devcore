# gen_dashboard.ps1 -- DEV_CORE v6 Multi-Projet
# Genere le fichier index.html du dashboard dynamiquement

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$DASHBOARD_DIR = "$DEV_CORE\Dashboard"
$TEMPLATE_FILE = "$DASHBOARD_DIR\template.html"
$OUTPUT_FILE   = "$DASHBOARD_DIR\index.html"
$MEMORY_DIR    = "$DEV_CORE_DATA\Memory"

# 1. & 2. Parcourir les projets et extraire les donnees
$projects = @()
if (Test-Path $MEMORY_DIR) {
    $folders = Get-ChildItem -Path $MEMORY_DIR -Directory
    foreach ($folder in $folders) {
        $tasksFile = Join-Path $folder.FullName "tasks.json"
        if (Test-Path $tasksFile) {
            $board = Get-Content $tasksFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $total = $board.tasks.Count
            $done  = ($board.tasks | Where-Object { $_.status -eq "done" }).Count
            $pct   = if ($total -gt 0) { [math]::Round(($done / $total) * 100) } else { 0 }
            
            $activeTask = $board.tasks | Where-Object { $_.id -eq $board.current_task }
            $activeId   = if ($activeTask) { $activeTask.id } else { "Aucune" }
            $activeMode = if ($activeTask) { $activeTask.mode } else { "N/A" }
            $activeSteps = if ($activeTask -and $activeTask.PSObject.Properties["steps_total"]) {
                "$($activeTask.steps_done)/$($activeTask.steps_total)"
            } else { "" }

            $lastDate = [datetime]::MinValue
            foreach ($t in $board.tasks) {
                $d = $null
                if ($t.PSObject.Properties["started_at"] -and $t.started_at) { try { $d = [datetime]::Parse($t.started_at) } catch {} }
                if (-not $d -and $t.PSObject.Properties["completed_at"] -and $t.completed_at) { try { $d = [datetime]::Parse($t.completed_at) } catch {} }
                if ($d -and $d -gt $lastDate) { $lastDate = $d }
            }

            $projects += [PSCustomObject]@{
                Name        = $folder.Name
                ActiveTask  = $activeId
                Mode        = $activeMode
                Progress    = $pct
                Steps       = $activeSteps
                Tasks       = $board.tasks
                LastDate    = $lastDate
            }
        }
    }
}

$projects = $projects | Sort-Object LastDate -Descending


# 3. Generer le HTML
$cardsHtml = ""
$tasksHtml = ""

foreach ($p in $projects) {
    $statusClass = if ($p.Progress -eq 100) { "status-ok" } elseif ($p.Progress -gt 0) { "status-warn" } else { "" }
    $cardsHtml += @"
  <div class="card">
    <div class="card-title">Projet : $($p.Name)</div>
    <div class="card-val" style="font-size:20px">$($p.ActiveTask)</div>
    <div class="card-sub">Mode: $($p.Mode) | $($p.Progress)% <span class="$statusClass">*</span></div>
  </div>
"@

    # Groupement par Projet et Worktree avec accordéons
    $tasksHtml += "<details open><summary><h2 style='color:#6366f1; cursor:pointer; padding:5px; background:#1a1d27; border-radius:4px;'>Projet : $($p.Name)</h2></summary><div style='padding: 10px 0;'>`n"
    
    $groups = $p.Tasks | Group-Object worktree | Sort-Object {
        $maxId = 0
        foreach ($t in $_.Group) {
            if ($t.id) {
                $idNum = [int]($t.id -replace "\D", "")
                if ($idNum -gt $maxId) { $maxId = $idNum }
            }
        }
        $maxId
    } -Descending
    foreach ($group in $groups) {
        $tasksHtml += "<details open style='margin-left: 15px; margin-bottom: 10px; border-left: 2px solid #2d3148; padding-left: 12px;'><summary><h3 style='font-size:11px; color:#94a3b8; margin-bottom:8px;'>Worktree: $($group.Name)</h3></summary>`n"
        
        $sortedTasks = $group.Group | Sort-Object { [int]($_.id -replace "\D", "") } -Descending
        foreach ($t in $sortedTasks) {
            $badgeClass = switch ($t.status) { "done"{"done"}; "active"{"active"}; default{"todo"} }
            $badgeText  = $t.status.ToUpper()
            $activeClass = if ($t.status -eq "active") { "active-task" } else { "" }
            $stepsStr   = if ($t.PSObject.Properties["steps_total"] -and $t.steps_total -gt 1) { "$($t.steps_done)/$($t.steps_total) steps" } else { "" }
            
            # Gestion des étapes détaillées
            $stepsDetailHtml = ""
            if ($t.PSObject.Properties["steps"]) {
                $stepsDetailHtml = "<div class='steps-container'>"
                foreach ($s in $t.steps) {
                    $icon = if ($s.done) { "<b style='color:#22c55e'>[v]</b>" } else { "<span style='color:#475569'>[ ]</span>" }
                    $stepClass = if ($s.done) { "step-done" } else { "" }
                    $stepsDetailHtml += "<div class='step-item $stepClass'>$icon $($s.title)</div>"
                }
                $stepsDetailHtml += "</div>"
            }

            # Gestion de la date pour le filtrage JS
            $taskDate = if ($t.PSObject.Properties["started_at"]) { $t.started_at } elseif ($t.PSObject.Properties["completed_at"]) { $t.completed_at } else { (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss") }

            # Formatage des dates pour l'affichage
            $datesHtml = ""
            $startDate = ""
            $endDate = ""
            if ($t.PSObject.Properties["started_at"] -and $t.started_at) {
                try { $startDate = "Debut: " + [datetime]::Parse($t.started_at).ToString("yyyy-MM-dd HH:mm:ss") } catch { }
            }
            if ($t.PSObject.Properties["completed_at"] -and $t.completed_at) {
                try { $endDate = "Fin: " + [datetime]::Parse($t.completed_at).ToString("yyyy-MM-dd HH:mm:ss") } catch { }
            }
            if ($startDate -or $endDate) {
                $datesHtml = "<div style='font-size:9px;color:#475569;margin-top:2px;font-family:monospace'>"
                if ($startDate) { $datesHtml += $startDate }
                if ($startDate -and $endDate) { $datesHtml += " | " }
                if ($endDate) { $datesHtml += $endDate }
                $datesHtml += "</div>"
            }

            $doneButton = if ($t.status -ne "done") {
                '<button style="background:#14532d; border:1px solid #22c55e; color:#86efac; padding:4px 8px; border-radius:4px; font-size:12px; cursor:pointer; margin-right:6px;" title="Clôturer" onclick="completeTask(''{0}'', ''{1}'')">&#10004;</button>' -f $p.Name, $t.id
            } else { "" }
            $deleteButton = '<button style="background:#7f1d1d; border:1px solid #ef4444; color:#fca5a5; padding:4px 8px; border-radius:4px; font-size:12px; cursor:pointer;" title="Supprimer" onclick="deleteTask(''{0}'', ''{1}'')">&#128465;</button>' -f $p.Name, $t.id
            
            $actionsHtml = @"
  <div style="margin-top: 10px; padding: 6px 10px; background: rgba(0,0,0,0.2); border-radius: 4px; display: flex; gap: 8px; align-items: center; border-top: 1px solid #2d3148;">
    $doneButton
    $deleteButton
  </div>
"@

            $tasksHtml += @"
<details class="mission $activeClass $($t.status)" data-date="$taskDate">
  <summary style="display:flex; gap:10px; align-items:center; width:100%">
    <span class="badge $badgeClass">$badgeText</span>
    <div style="flex:1">
      <div class="mission-title">$($t.id): $($t.title)</div>
      <div style="font-size:10px;color:#64748b;margin-top:2px">Mode: $($t.mode) - $stepsStr</div>
      $datesHtml
    </div>
  </summary>
  $stepsDetailHtml
  $actionsHtml
</details>
"@
        }
        $tasksHtml += "</details>"
    }
    $tasksHtml += "</div></details>"
}

# 4. Generer HTML des services
function Check-Port {
    param([int]$Port)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect("127.0.0.1", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(200, $true)
        if ($success) { $tcp.EndConnect($result) }
        $tcp.Close()
        return $success
    } catch {
        return $false
    }
}

function Get-LastLogTime {
    param([string]$Prefix)
    $files = Get-ChildItem -Path "$DEV_CORE_DATA\Logs\scripts\" -Filter "$Prefix*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($files) {
        return $files[0].LastWriteTime
    }
    return $null
}

function Format-TimeAgo {
    param($Time)
    if (-not $Time) { return "Jamais" }
    $ts = (Get-Date) - $Time
    if ($ts.TotalDays -ge 1) { return "$([math]::Round($ts.TotalDays)) jours" }
    if ($ts.TotalHours -ge 1) { return "$([math]::Round($ts.TotalHours)) heures" }
    if ($ts.TotalMinutes -ge 1) { return "$([math]::Round($ts.TotalMinutes)) mins" }
    return "$([math]::Round($ts.TotalSeconds)) s"
}

function Get-StatusHTML {
    param($Title, $Desc, $IsOk)
    $statusClass = if ($IsOk) { "status-ok" } else { "status-error" }
    $statusIcon = if ($IsOk) { "&#10003;" } else { "&#10007;" }
    return @"
<div class="component">
  <div>
    <div class="component-name">$Title</div>
    <div class="component-detail">$Desc</div>
  </div>
  <div class="$statusClass">$statusIcon</div>
</div>
"@
}

# Auto-démarrer le serveur API du Dashboard si absent
$apiPort = 20129
if (-not (Check-Port $apiPort)) {
    Write-Host "Demarrage du serveur API Dashboard en arriere-plan..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "$DEV_CORE\Scripts\dashboard_api.py" -NoNewWindow -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

$infraHtml = "<h2>Services & Infrastructure</h2>`n"
$infraHtml += Get-StatusHTML "Hermes Agent" "Port 20128" (Check-Port 20128)
$infraHtml += Get-StatusHTML "Dashboard API Server" "Port 20129" (Check-Port 20129)
$infraHtml += Get-StatusHTML "Qdrant Vector DB" "Port 6333" (Check-Port 6333)
$infraHtml += Get-StatusHTML "Ollama Embeddings" "Port 11434" (Check-Port 11434)

$infraHtml += "<h2>Automation Hooks</h2>`n"
$syncLog = Get-LastLogTime "task_sync"
$syncOk = ($syncLog -ne $null -and ((Get-Date) - $syncLog).TotalDays -lt 1)
$infraHtml += Get-StatusHTML "task_sync" ("Dernier: " + (Format-TimeAgo $syncLog)) $syncOk

$startLog = Get-LastLogTime "session_start"
$startOk = ($startLog -ne $null -and ((Get-Date) - $startLog).TotalDays -lt 2)
$infraHtml += Get-StatusHTML "session_start" ("Dernier: " + (Format-TimeAgo $startLog)) $startOk

$endLog = Get-LastLogTime "session_end"
$endOk = ($endLog -ne $null -and ((Get-Date) - $endLog).TotalDays -lt 2)
$infraHtml += Get-StatusHTML "session_end" ("Dernier: " + (Format-TimeAgo $endLog)) $endOk

# 5. Injecter dans template.html et ecrire index.html
if (Test-Path $TEMPLATE_FILE) {
    $template = Get-Content $TEMPLATE_FILE -Raw -Encoding UTF8
    $template = $template -replace '\{\{PROJECT_CARDS\}\}', $cardsHtml
    $template = $template -replace '\{\{TASKS_PIPELINE\}\}', $tasksHtml
    $template = $template -replace '\{\{SERVICES_MONITORING\}\}', $infraHtml

    $template | Set-Content $OUTPUT_FILE -Encoding UTF8
    Write-Host "Dashboard genere : $OUTPUT_FILE" -ForegroundColor Green
} else {
    Write-Host "Erreur : template.html introuvable" -ForegroundColor Red
}
