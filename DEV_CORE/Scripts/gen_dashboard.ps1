# gen_dashboard.ps1 -- DEV_CORE v9.0 Multi-Projet
# Genere le fichier index.html du dashboard dynamiquement

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$DASHBOARD_DIR = "$DEV_CORE\Dashboard"
$TEMPLATE_FILE = "$DASHBOARD_DIR\template.html"
$OUTPUT_FILE   = "$DASHBOARD_DIR\index.html"
$MEMORY_DIR    = "$DEV_CORE_DATA\Memory"
$inv           = [System.Globalization.CultureInfo]::InvariantCulture

# 0. Rafraîchir les métriques de tokens en temps réel
try {
    & python "$DEV_CORE\Scripts\Auto\token_report.py" 2>&1 | Out-Null
} catch {
    Write-Host "  [WARN] Real-time token report execution failed: $_" -ForegroundColor Yellow
}

$tokenSummary = $null
$jsonPath = "$DEV_CORE_DATA\Logs\token_reports\token_metrics_summary.json"
if (Test-Path $jsonPath) {
    try {
        $tokenSummary = Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Host "  [WARN] Failed to parse ${jsonPath}: $_" -ForegroundColor Yellow
    }
}

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
$allDetailsMap = @{}

foreach ($p in $projects) {
    $statusClass = if ($p.Progress -eq 100) { "status-ok" } elseif ($p.Progress -gt 0) { "status-warn" } else { "status-todo" }
    $activeTaskHtml = if ($p.ActiveTask -eq "Aucune") { 
        '<span style="color:#64748b">Aucune</span>' 
    } else { 
        "<span style='color:#a5b4fc; font-weight:600;'>$($p.ActiveTask)</span> <span style='font-size:9px; color:#64748b;'>($($p.Mode))</span>" 
    }
    $cardsHtml += @"
  <div class="project-row" data-project="$($p.Name)" onclick="toggleProjectFilter(this, '$($p.Name)')" title="Cliquer pour filtrer les taches du projet : $($p.Name) | progression : $($p.Progress)%">
    <div style="display:flex; flex-direction:column; gap:4px; flex:1; min-width:0; padding-right:12px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="project-dot $($statusClass)"></span>
        <span style="font-size:11px; font-weight:600; color:#f8fafc;">$($p.Name)</span>
      </div>
      <div style="font-size:9.5px; font-family:'JetBrains Mono',monospace; color:#64748b; padding-left:16px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
        $activeTaskHtml
      </div>
    </div>
    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
      <div style="font-size:11px; font-weight:600; color:#cbd5e1; display:flex; align-items:center; gap:6px;">
        $($p.Progress)%
      </div>
      <div style="width:45px; height:3px; background:#1e293b; border-radius:1.5px; overflow:hidden;">
        <div style="width:$($p.Progress)%; height:100%; background:linear-gradient(90deg, #6366f1, #a5b4fc); border-radius:1.5px;"></div>
      </div>
    </div>
  </div>
"@

    # Groupement par Projet et Worktree avec accordéons
    $tasksHtml += "<details open class='project-tasks-group' data-project='$($p.Name)'><summary><h2 style='color:#6366f1; cursor:pointer; padding:5px; background:#1a1d27; border-radius:4px;'>Projet : $($p.Name)</h2></summary><div style='padding: 10px 0;'>`n"
    
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
            
            # Badges de tokens et coûts pour la tâche
            $taskTokensStr = ""
            $taskCostStr = ""
            if ($tokenSummary -and $tokenSummary.tasks -and $tokenSummary.tasks.PSObject.Properties[$t.id]) {
                $taskStats = $tokenSummary.tasks.PSObject.Properties[$t.id].Value
                $tTokens = [double]$taskStats.tokens
                $tTokensStr = if ($tTokens -gt 1000000) { "$([math]::Round($tTokens/1000000, 2))M" } else { "$([math]::Round($tTokens/1000, 1))K" }
                $tCost = [double]$taskStats.cost_usd
                $tCostFormatted = '{0:F2}' -f $tCost
                $taskTokensStr = "<span class='badge' style='background:rgba(99, 102, 241, 0.12); border:1px solid rgba(99, 102, 241, 0.25); color:#cbd5e1; margin-left:6px; font-family:monospace; font-size:9px; font-weight:400; padding:1px 4px;' title='Tokens consomm&eacute;s par l''agent'>$tTokensStr</span>"
                $taskCostStr = "<span class='badge' style='background:rgba(251, 191, 36, 0.12); border:1px solid rgba(251, 191, 36, 0.25); color:#fde68a; margin-left:4px; font-family:monospace; font-size:9px; font-weight:400; padding:1px 4px;' title='Co&ucirc;t estim&eacute; (USD)'>`$$tCostFormatted</span>"
            }

            # Gestion du bloc de description (details)
            $detailsButton = ""
            if ($t.PSObject.Properties["details"] -and $t.details) {
                $key = "$($p.Name)_$($t.id)"
                $allDetailsMap[$key] = $t.details
                $detailsButton = "<button class='btn-action btn-details' onclick='showDetails(`"$($p.Name)`", `"$($t.id)`", `"$($t.status)`", this, event)' title='Voir les d&eacute;tails'>D&eacute;tails</button>"
            }

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
            $taskDate = if ($t.PSObject.Properties["started_at"] -and $t.started_at) { $t.started_at } elseif ($t.PSObject.Properties["completed_at"] -and $t.completed_at) { $t.completed_at } else { (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss") }

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
                '<button class="btn-action btn-done" title="Cl&ocirc;turer" onclick="completeTask(''{0}'', ''{1}'')">&#10004;</button>' -f $p.Name, $t.id
            } else { "" }
            $deleteButton = '<button class="btn-action btn-delete" title="Supprimer" onclick="deleteTask(''{0}'', ''{1}'')">&#128465;</button>' -f $p.Name, $t.id

            $tasksHtml += @"
<div class="mission $activeClass $($t.status)" data-date="$taskDate">
  <div class="mission-header" style="display:flex; gap:10px; align-items:center; width:100%">
    <span class="badge $badgeClass">$badgeText</span>
    <div style="flex:1; min-width: 0;">
      <div class="mission-title" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
        <span style="text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="$($t.id): $($t.title)">$($t.id): $($t.title)</span>
        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
          <div style="display:flex; align-items:center; gap:2px;">$taskTokensStr$taskCostStr$detailsButton</div>
          <div style="display:flex; align-items:center; gap:2px;">$doneButton$deleteButton</div>
        </div>
      </div>
      <div style="font-size:10px;color:#64748b;margin-top:2px">Mode: $($t.mode) - $stepsStr</div>
      $datesHtml
    </div>
  </div>
  $stepsDetailHtml
</div>
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
        $result = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(1000, $true)
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
$tickLog = "$DEV_CORE_DATA\Logs\hermes\cron_tick.log"
$isDaemonRunning = $false
if (Test-Path $tickLog) {
    $lastWrite = (Get-Item $tickLog).LastWriteTime
    if (((Get-Date) - $lastWrite).TotalMinutes -lt 2.5) {
        $isDaemonRunning = $true
    }
}
$infraHtml += Get-StatusHTML "Gemini Router (Primary)" "Port 20130" (Check-Port 20130)
$infraHtml += Get-StatusHTML "Dashboard API Server" "Port 20129" (Check-Port 20129)
$infraHtml += Get-StatusHTML "9Router (Fallback)" "Port 20128" (Check-Port 20128)
$infraHtml += Get-StatusHTML "Headroom Proxy" "Port 8787" (Check-Port 8787)
$infraHtml += Get-StatusHTML "Hermes Cron Daemon" "Standalone Tick Loop" $isDaemonRunning
$infraHtml += Get-StatusHTML "Qdrant Vector DB" "Port 6333" (Check-Port 6333)
$infraHtml += Get-StatusHTML "Ollama Embeddings" "Port 11434 (Desactive)" (Check-Port 11434)

$infraHtml += "<h2>Hermes Background Jobs</h2>`n"
$jobsFile = "$env:USERPROFILE\.hermes\cron\jobs.json"
if (Test-Path $jobsFile) {
    try {
        $jobs = Get-Content $jobsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($j in $jobs.jobs) {
            $statusClass = if ($j.enabled) { "status-ok" } else { "status-warn" }
            $lastRun = if ($j.last_run_at) {
                try { [datetime]::Parse($j.last_run_at).ToString("yyyy-MM-dd HH:mm:ss") } catch { $j.last_run_at }
            } else { "Jamais" }
            $lastStatus = if ($j.last_status) { $j.last_status.ToUpper() } else { "N/A" }
            $lastStatusClass = if ($j.last_status -eq "success") { "color:#22c55e" } elseif ($j.last_status -eq "error") { "color:#ef4444" } else { "color:#94a3b8" }
            
            $infraHtml += @"
<div class="component" style="padding: 8px 10px; margin-bottom: 6px; background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.02); border-radius: 6px; display:flex; justify-content:space-between; align-items:center;">
  <div style="flex: 1; min-width: 0; padding-right:8px;">
    <div class="component-name" style="font-size: 11px; font-weight: 600; color: #f8fafc; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" title="$($j.name)">$($j.name)</div>
    <div style="font-size: 9px; color: #64748b; margin-top: 2px;">
      Freq: $($j.schedule_display) | Last: $lastRun | <span style="$lastStatusClass; font-weight:bold;">$lastStatus</span>
    </div>
  </div>
  <div class="$statusClass" style="font-size: 10px; font-weight: bold; flex-shrink:0;">$(if ($j.enabled) { 'ON' } else { 'OFF' })</div>
</div>
"@
        }
    } catch {
        $infraHtml += "<div style='font-size:9px; color:#ef4444; padding:5px;'>Erreur parsing jobs.json</div>`n"
    }
} else {
    $infraHtml += "<div style='font-size:9px; color:#94a3b8; padding:5px;'>Aucune tache (jobs.json absent)</div>`n"
}

$hooksHtml = ""
$syncLog = Get-LastLogTime "task_sync"
$syncOk = ($syncLog -ne $null -and ((Get-Date) - $syncLog).TotalDays -lt 1)
$hooksHtml += Get-StatusHTML "task_sync" ("Dernier: " + (Format-TimeAgo $syncLog)) $syncOk

$startLog = Get-LastLogTime "session_start"
$startOk = ($startLog -ne $null -and ((Get-Date) - $startLog).TotalDays -lt 2)
$hooksHtml += Get-StatusHTML "session_start" ("Dernier: " + (Format-TimeAgo $startLog)) $startOk

$endLog = Get-LastLogTime "session_end"
$endOk = ($endLog -ne $null -and ((Get-Date) - $endLog).TotalDays -lt 2)
$hooksHtml += Get-StatusHTML "session_end" ("Dernier: " + (Format-TimeAgo $endLog)) $endOk

# 4.5 Rapport d'activité & consommation tokens dynamique (Option A)
$tokenReportHtml = ""
if ($tokenSummary) {
    $totTokens = [double]$tokenSummary.totals.tokens
    $totCache = [double]$tokenSummary.totals.cache_hits
    $totCost = [double]$tokenSummary.totals.cost_usd
    $totCostFormatted = '{0:F2}' -f $totCost
    
    $totTokensStr = if ($totTokens -gt 1000000) { "$([math]::Round($totTokens/1000000, 2))M" } else { "$([math]::Round($totTokens/1000, 1))K" }
    $totCachePct = if ($totTokens -gt 0) { [math]::Round(($totCache / $totTokens) * 100) } else { 0 }
    
    # Barre de répartition par Projet
    $projectAllocHtml = ""
    if ($tokenSummary.projects) {
        $projectAllocHtml += '<div class="project-bar-container" style="display:flex; height:6px; border-radius:3px; overflow:hidden; background:#1e293b; margin:12px 0 8px;">'
        $colors = @("#6366f1", "#10b981", "#fbbf24", "#ec4899", "#8b5cf6")
        $idx = 0
        $projList = $tokenSummary.projects.PSObject.Properties
        
        foreach ($proj in $projList) {
            $pct = [math]::Round(($proj.Value.tokens / $totTokens) * 100)
            if ($pct -gt 0) {
                $col = $colors[$idx % $colors.Count]
                $projectAllocHtml += "<div style='width:$pct%; background:$col;' title='$($proj.Name): $pct% ($([int]$proj.Value.tokens/1000)k tks)'></div>"
                $idx++
            }
        }
        $projectAllocHtml += '</div>'
        
        $projectAllocHtml += '<div style="display:flex; flex-wrap:wrap; gap:10px; font-size:10px; color:#94a3b8; margin-bottom:16px;">'
        $idx = 0
        foreach ($proj in $projList) {
            $pct = [math]::Round(($proj.Value.tokens / $totTokens) * 100)
            if ($pct -gt 0) {
                $col = $colors[$idx % $colors.Count]
                $projectAllocHtml += "<span style='display:flex; align-items:center; gap:4px;'><span style='width:6px; height:6px; border-radius:50%; background:$col;'></span>$($proj.Name) ($pct%)</span>"
                $idx++
            }
        }
        $projectAllocHtml += '</div>'
    }
    
    # Sessions
    $sessionsHtml = ""
    $recentSess = $tokenSummary.sessions
    if (-not $recentSess -or $recentSess.Count -eq 0) {
        $sessionsHtml = '<div style="font-size: 11px; font-style: italic; color: #64748b; text-align: center; padding: 10px;">Aucune session active enregistrée.</div>'
    } else {
        foreach ($s in $recentSess) {
            $sTokens = [double]$s.tokens
            $sTokensStr = if ($sTokens -gt 1000000) { "$([math]::Round($sTokens/1000000, 2))M" } else { "$([math]::Round($sTokens/1000, 1))K" }
            $sCost = [double]$s.cost_usd
            $sCostFormatted = '{0:F2}' -f $sCost
            $sCachePct = if ($sTokens -gt 0) { [math]::Round(($s.cache_hits / $sTokens) * 100) } else { 0 }
            $tasksJoined = $s.tasks -join ", "
            
            $sessionsHtml += @"
      <div style="background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.03); border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s; font-size: 11px; margin-bottom: 6px;">
        <div style="flex: 1; min-width: 0; padding-right: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="width: 6px; height: 6px; border-radius: 50%; background: #6366f1; box-shadow: 0 0 6px #6366f1;"></span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #cbd5e1; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;" title="$($s.id)">$($s.id.Substring(0, 8))...</span>
            <span style="font-size: 9px; padding: 1px 4px; border-radius: 3px; background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.3); color: #cbd5e1;">$($s.project)</span>
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 3px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            $($s.date) | $($s.start_time) - $($s.end_time) ($($s.duration))
          </div>
          <div style="font-size: 10px; color: #64748b; margin-top: 2px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
            <span style="color:#6366f1">T&acirc;ches:</span> $tasksJoined
          </div>
        </div>
        <div style="text-align: right; font-family: 'JetBrains Mono', monospace; min-width: 80px;">
          <div style="color: #cbd5e1; font-weight: 500;">$sTokensStr tks</div>
          <div style="font-size: 9px; color: #64748b; margin-top: 2px;">`$$sCostFormatted | $sCachePct%</div>
        </div>
      </div>
"@
        }
    }
    
    $tokenReportHtml = @"
<details open style="margin-top: 24px; border: 1px solid #2d3148; border-radius: 8px; background: #111420; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
  <summary style="padding: 12px 16px; background: #1a1d27; border-bottom: 1px solid #2d3148; cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none;">
    <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: #6366f1; letter-spacing: 0.05em; display: flex; align-items: center; gap: 8px;">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
      Rapport de Consommation & Activit&eacute; Agent
    </span>
    <span style="font-size: 11px; color: #cbd5e1; font-family: monospace;">Co&ucirc;t total : `$$totCostFormatted USD</span>
  </summary>
  <div style="padding: 16px;">
    <!-- M&eacute;triques globales -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
        <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Tokens Totaux</div>
        <div style="font-size: 16px; font-weight: 600; color: #f8fafc; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">$totTokensStr</div>
      </div>
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
        <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Cache Hits</div>
        <div style="font-size: 16px; font-weight: 600; color: #10b981; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">$totCachePct%</div>
      </div>
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
        <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Co&ucirc;t Global</div>
        <div style="font-size: 16px; font-weight: 600; color: #fbbf24; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">`$$totCostFormatted</div>
      </div>
    </div>
    
    <!-- R&eacute;partition par Projet -->
    <h3 style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 12px 0 6px;">R&eacute;partition par Projet</h3>
    $projectAllocHtml
    
    <!-- Sessions Actives -->
    <h3 style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 16px 0 8px;">D&eacute;tail des Sessions</h3>
    <div style="display: flex; flex-direction: column; max-height: 250px; overflow-y: auto; padding-right: 4px;">
      $sessionsHtml
    </div>
  </div>
</details>
"@
}

# 5. Injecter dans template.html et ecrire index.html
if (Test-Path $TEMPLATE_FILE) {
    $detailsJson = if ($allDetailsMap.Count -gt 0) {
        $allDetailsMap | ConvertTo-Json -Depth 10 -Compress
    } else {
        "{}"
    }

    $template = Get-Content $TEMPLATE_FILE -Raw -Encoding UTF8
    $template = $template.Replace('{{PROJECT_CARDS}}', $cardsHtml)
    $template = $template.Replace('{{TASKS_PIPELINE}}', $tasksHtml)
    $template = $template.Replace('{{SERVICES_MONITORING}}', $infraHtml)
    $template = $template.Replace('{{AUTOMATION_HOOKS}}', $hooksHtml)
    $template = $template.Replace('{{TOKEN_ACTIVITY_REPORT}}', $tokenReportHtml)
    $template = $template.Replace('{{TASK_DETAILS_MAP}}', $detailsJson)

    $template | Set-Content $OUTPUT_FILE -Encoding UTF8
    Write-Host "Dashboard genere : $OUTPUT_FILE" -ForegroundColor Green
} else {
    Write-Host "Erreur : template.html introuvable" -ForegroundColor Red
}
