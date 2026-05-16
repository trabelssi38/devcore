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
            $board = Get-Content $tasksFile -Raw | ConvertFrom-Json
            $total = $board.tasks.Count
            $done  = ($board.tasks | Where-Object { $_.status -eq "done" }).Count
            $pct   = if ($total -gt 0) { [math]::Round(($done / $total) * 100) } else { 0 }
            
            $activeTask = $board.tasks | Where-Object { $_.id -eq $board.current_task }
            $activeId   = if ($activeTask) { $activeTask.id } else { "Aucune" }
            $activeMode = if ($activeTask) { $activeTask.mode } else { "N/A" }
            $activeSteps = if ($activeTask -and $activeTask.PSObject.Properties["steps_total"]) {
                "$($activeTask.steps_done)/$($activeTask.steps_total)"
            } else { "" }

            $projects += [PSCustomObject]@{
                Name        = $folder.Name
                ActiveTask  = $activeId
                Mode        = $activeMode
                Progress    = $pct
                Steps       = $activeSteps
                Tasks       = $board.tasks
            }
        }
    }
}

# 3. Generer le HTML
$cardsHtml = ""
$tasksHtml = ""

foreach ($p in $projects) {
    $statusClass = if ($p.Progress -eq 100) { "status-ok" } elseif ($p.Progress -gt 0) { "status-warn" } else { "" }
    $cardsHtml += @"
  <div class="card">
    <div class="card-title">Projet : $($p.Name)</div>
    <div class="card-val" style="font-size:20px">$($p.ActiveTask)</div>
    <div class="card-sub">Mode: $($p.Mode) | $($p.Progress)% <span class="$statusClass">●</span></div>
  </div>
"@

    $tasksHtml += "<h2>Tasks Pipeline ($($p.Name))</h2>`n"
    if (-not $p.Tasks -or $p.Tasks.Count -eq 0) {
        $tasksHtml += "<div class=`"mission`"><div style=`"font-size:13px;color:#64748b`">Aucune tâche</div></div>`n"
    } else {
        foreach ($t in $p.Tasks) {
            $badgeClass = switch ($t.status) { "done"{"done"}; "active"{"active"}; default{"todo"} }
            $badgeText  = $t.status.ToUpper()
            $stepsStr   = if ($t.PSObject.Properties["steps_total"] -and $t.steps_total -gt 1) { "$($t.steps_done)/$($t.steps_total) steps" } else { "" }
            $wtStr      = if ($t.PSObject.Properties["worktree"] -and $t.worktree -ne "main") { "[$($t.worktree)] " } else { "" }
            
            $tasksHtml += @"
<div class="mission">
  <span class="badge $badgeClass">$badgeText</span>
  <div style="flex:1">
    <div style="font-size:13px;font-weight:500">$($t.id): $wtStr$($t.title)</div>
    <div style="font-size:11px;color:#64748b;margin-top:2px">Mode: $($t.mode) — $stepsStr</div>
  </div>
</div>
"@
        }
    }
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

$infraHtml = "<h2>Services & Infrastructure</h2>`n"
$infraHtml += Get-StatusHTML "Hermes Agent" "Port 20128" (Check-Port 20128)
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
    Write-Host "Dashboard généré : $OUTPUT_FILE" -ForegroundColor Green
} else {
    Write-Host "Erreur : template.html introuvable" -ForegroundColor Red
}
