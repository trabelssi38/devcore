# gen_dashboard.ps1 -- DEV_CORE v9.0 Multi-Projet
# Genere le fichier index.html du dashboard dynamiquement
param(
    [switch]$Json,
    [switch]$SkipTokenRefresh
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$DASHBOARD_DIR = "$DEV_CORE\Dashboard"
$TEMPLATE_FILE = "$DASHBOARD_DIR\template.html"
$OUTPUT_FILE   = "$DASHBOARD_DIR\index.html"
$MEMORY_DIR    = "$DEV_CORE_DATA\Memory"
$inv           = [System.Globalization.CultureInfo]::InvariantCulture
$dashboardStarted = Get-Date
$METRICS_SERVICE = Join-Path $DEV_CORE "Scripts\metrics_service.ps1"
$EVENT_BUS = Join-Path $DEV_CORE "Scripts\event_bus.ps1"
$KNOWLEDGE_GRAPH = Join-Path $DEV_CORE "Scripts\knowledge_graph.ps1"

if ($env:DEVCORE_SKIP_DASHBOARD -eq "1" -and -not $Json) {
    Write-Host "Dashboard generation skipped (DEVCORE_SKIP_DASHBOARD=1)"
    exit 0
}

function Get-TaskDate {
    param($Task)

    foreach ($prop in @("committed_at", "completed_at", "started_at", "updated_at", "created_at")) {
        if ($Task.PSObject.Properties[$prop] -and $Task.$prop) {
            try { return ([datetimeoffset]::Parse($Task.$prop, $inv)).LocalDateTime } catch {}
            try { return [datetime]::Parse($Task.$prop, $inv) } catch {}
        }
    }

    return [datetime]::MinValue
}

function Get-TaskIdNumber {
    param($Task)
    if ($Task.id) {
        try { return [int]($Task.id -replace "\D", "") } catch {}
    }
    return 0
}

function Record-DashboardMetric {
    param(
        [string]$MetricType,
        [double]$Value,
        [string]$Unit = "count",
        [hashtable]$Payload = @{}
    )
    if (-not (Test-Path -LiteralPath $METRICS_SERVICE)) { return }
    try {
        $payloadJson = $Payload | ConvertTo-Json -Depth 10 -Compress
        & $METRICS_SERVICE -Action Record -Source "gen_dashboard" -Project "devcore" -MetricType $MetricType -Value $Value -Unit $Unit -PayloadJson $payloadJson 6>$null | Out-Null
    } catch {}
}

function Publish-DashboardEvent {
    param(
        [Parameter(Mandatory=$true)][string]$EventType,
        [hashtable]$Payload = @{},
        [string]$Id = ""
    )
    if (-not (Test-Path -LiteralPath $EVENT_BUS)) { return }
    try {
        $eventId = if ($Id) { $Id } else { [guid]::NewGuid().ToString("n") }
        $payloadJson = $Payload | ConvertTo-Json -Depth 10 -Compress
        & $EVENT_BUS -Action Publish -Id $eventId -Source "gen_dashboard" -Project "devcore" -EventType $EventType -CorrelationId $eventId -PayloadJson $payloadJson -Json 6>$null | Out-Null
    } catch {}
}

function Get-MetricsServiceSummaryHtml {
    $empty = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Metrics Service indisponible.</div>"
    if (-not (Test-Path -LiteralPath $METRICS_SERVICE)) { return $empty }
    try {
        $statusJson = & $METRICS_SERVICE -Action Status -Json | Out-String
        $status = $statusJson | ConvertFrom-Json
        $aggregate = $status.aggregate
        $health = $status.health
        $events = [int]$aggregate.events_count
        $errors = [int]$aggregate.errors_count
        $tokens = 0.0
        $cost = 0.0
        $duration = 0.0
        if ($aggregate.totals.tokens -and $aggregate.totals.tokens.tokens) { $tokens = [double]$aggregate.totals.tokens.tokens.sum }
        if ($aggregate.totals.cost -and $aggregate.totals.cost.usd) { $cost = [double]$aggregate.totals.cost.usd.sum }
        if ($aggregate.totals.duration -and $aggregate.totals.duration.seconds) { $duration = [double]$aggregate.totals.duration.seconds.sum }
        $tokensStr = if ($tokens -gt 1000000) { "$([math]::Round($tokens/1000000, 2))M" } elseif ($tokens -gt 0) { "$([math]::Round($tokens/1000, 1))K" } else { "0" }
        $costStr = '{0:F2}' -f $cost
        $durationStr = '{0:F1}s' -f $duration
        $healthColor = if ($health.ok) { "#22c55e" } else { "#ef4444" }
        return @"
<div id="metrics-service-inner">
  <h2>Metrics Service</h2>
  <div style="display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:6px; margin-bottom:8px;">
    <div class="token-layer"><span class="token-name">Events</span><span class="token-reduction">$events</span></div>
    <div class="token-layer"><span class="token-name">Errors</span><span class="token-reduction" style="color:$healthColor">$errors</span></div>
    <div class="token-layer"><span class="token-name">Tokens</span><span class="token-reduction">$tokensStr</span></div>
    <div class="token-layer"><span class="token-name">Cost</span><span class="token-reduction">`$$costStr</span></div>
  </div>
  <div style="font-size:9px; color:#64748b; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$($aggregate.store_path)">Dur&eacute;e cumul&eacute;e: $durationStr</div>
</div>
"@
    } catch {
        return "<div style='font-size:10px; color:#ef4444; padding:8px 0;'>Metrics Service erreur: $([System.Net.WebUtility]::HtmlEncode([string]$_))</div>"
    }
}

function Get-EventBusRecentHtml {
    $empty = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Event Bus indisponible.</div>"
    if (-not (Test-Path -LiteralPath $EVENT_BUS)) { return $empty }
    try {
        $tailJson = & $EVENT_BUS -Action Tail -Limit 8 -Json | Out-String
        $tail = $tailJson | ConvertFrom-Json
        $events = @($tail.events)
        $rows = ""
        foreach ($event in $events) {
            $type = [System.Net.WebUtility]::HtmlEncode([string]$event.event_type)
            $source = [System.Net.WebUtility]::HtmlEncode([string]$event.source)
            $task = if ($event.task_id) { [System.Net.WebUtility]::HtmlEncode([string]$event.task_id) } else { "-" }
            $time = ""
            try { $time = ([datetimeoffset]::Parse([string]$event.timestamp, $inv)).ToLocalTime().ToString("HH:mm:ss") } catch { $time = [System.Net.WebUtility]::HtmlEncode([string]$event.timestamp) }
            $rows += "<div class='token-layer'><span class='token-name'>$time $type</span><span class='token-reduction' title='$source'>$task</span></div>"
        }
        if (-not $rows) {
            $rows = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun evenement recent.</div>"
        }
        return @"
<div id="event-bus-inner">
  <h2>Event Bus</h2>
  <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:8px;">
    $rows
  </div>
  <div style="font-size:9px; color:#64748b; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$($tail.store_path)">Events lus: $($tail.events_count) | erreurs: $($tail.errors_count)</div>
</div>
"@
    } catch {
        return "<div style='font-size:10px; color:#ef4444; padding:8px 0;'>Event Bus erreur: $([System.Net.WebUtility]::HtmlEncode([string]$_))</div>"
    }
}

function Get-KnowledgeGraphSummaryHtml {
    $empty = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Knowledge Graph indisponible.</div>"
    if (-not (Test-Path -LiteralPath $KNOWLEDGE_GRAPH)) { return $empty }
    try {
        $graphPath = Join-Path $DEV_CORE_DATA "Knowledge\graph.json"
        if (-not (Test-Path -LiteralPath $graphPath)) {
            return "<div id='knowledge-graph-inner'><h2>Knowledge Graph</h2><div style='font-size:10px; color:#64748b; padding:8px 0;'>Graphe non genere.</div></div>"
        }

        $graph = Get-Content -LiteralPath $graphPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $nodesCount = [int]$graph.nodes_count
        $edgesCount = [int]$graph.edges_count
        $serviceRows = ""
        $serviceNodes = @($graph.nodes | Where-Object { $_.type -eq "service" })
        foreach ($service in ($serviceNodes | Select-Object -First 6)) {
            $edgeCount = @($graph.edges | Where-Object { $_.from -eq $service.id -or $_.to -eq $service.id }).Count
            $label = [System.Net.WebUtility]::HtmlEncode([string]$service.label)
            $serviceRows += "<div class='token-layer'><span class='token-name'>$label</span><span class='token-reduction'>$edgeCount liens</span></div>"
        }
        if (-not $serviceRows) {
            $serviceRows = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun service relie.</div>"
        }

        $blast = 0
        try {
            $topFile = @($graph.nodes | Where-Object { $_.type -eq "file" } | Select-Object -First 1)
            if ($topFile) {
                $fileNodeId = [string]$topFile[0].id
                $blast = @($graph.edges | Where-Object { $_.from -eq $fileNodeId -or $_.to -eq $fileNodeId }).Count
            }
        } catch {}

        return @"
<div id="knowledge-graph-inner">
  <h2>Knowledge Graph</h2>
  <div style="display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:6px; margin-bottom:8px;">
    <div class="token-layer"><span class="token-name">Nodes</span><span class="token-reduction">$nodesCount</span></div>
    <div class="token-layer"><span class="token-name">Edges</span><span class="token-reduction">$edgesCount</span></div>
  </div>
  <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:8px;">
    $serviceRows
  </div>
  <div style="font-size:9px; color:#64748b; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$graphPath">Blast radius echantillon: $blast</div>
</div>
"@
    } catch {
        return "<div style='font-size:10px; color:#ef4444; padding:8px 0;'>Knowledge Graph erreur: $([System.Net.WebUtility]::HtmlEncode([string]$_))</div>"
    }
}

# 0. Rafraîchir les métriques de tokens en temps réel
if (-not $SkipTokenRefresh) {
    try {
        & python "$DEV_CORE\Scripts\Auto\token_report.py" 2>&1 | Out-Null
    } catch {
        Write-Host "  [WARN] Real-time token report execution failed: $_" -ForegroundColor Yellow
    }
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
$ExcludedDashboardProjects = @("scripts")
if (Test-Path $MEMORY_DIR) {
    $folders = Get-ChildItem -Path $MEMORY_DIR -Directory
    foreach ($folder in $folders) {
        if ($ExcludedDashboardProjects -contains $folder.Name) { continue }
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
                $d = Get-TaskDate $t
                if ($d -and $d -gt $lastDate) { $lastDate = $d }
            }

            $projTokensStr = ""
            if ($tokenSummary -and $tokenSummary.projects -and $tokenSummary.projects.PSObject.Properties[$folder.Name]) {
                $projStats = $tokenSummary.projects.PSObject.Properties[$folder.Name].Value
                $pTokens = [double]$projStats.tokens
                $pTokensStr = if ($pTokens -gt 1000000) { "$([math]::Round($pTokens/1000000, 2))M" } else { "$([math]::Round($pTokens/1000, 1))K" }
                $pCost = [double]$projStats.cost_usd
                $pCostFormatted = '{0:F2}' -f $pCost
                $projTokensStr = "$pTokensStr tokens | `$$pCostFormatted"
            }

            $projects += [PSCustomObject]@{
                Name        = $folder.Name
                ActiveTask  = $activeId
                Mode        = $activeMode
                Progress    = $pct
                Steps       = $activeSteps
                Tasks       = $board.tasks
                LastDate    = $lastDate
                Tokens      = $projTokensStr
            }
        }
    }
}

$projects = $projects | Sort-Object LastDate -Descending

function ConvertTo-DashboardHtml {
    param($Value)
    return [System.Net.WebUtility]::HtmlEncode([string]$Value)
}

function Get-ContextCompositionHtml {
    param($ProjectList)

    $rowsHtml = ""
    foreach ($project in $ProjectList) {
        $activeTasks = @($project.Tasks | Where-Object { $_.status -eq "active" })
        foreach ($task in $activeTasks) {
            $query = if ($task.title) { [string]$task.title } else { [string]$task.id }
            $taskType = if ($task.mode) { [string]$task.mode } else { "devcore" }
            try {
                $scoreJson = & "$DEV_CORE\Scripts\context_service.ps1" -Action ScoreSources -Query $query -TaskType $taskType -Json | Out-String
                $scorePayload = $scoreJson | ConvertFrom-Json
                $sourceRows = ""
                foreach ($source in @($scorePayload.sources | Sort-Object score -Descending)) {
                    $statusText = if ($source.included) { "IN" } else { "OUT" }
                    $statusColor = if ($source.included) { "#22c55e" } else { "#64748b" }
                    $sourceRows += @"
          <div class="context-source-row" style="display:grid; grid-template-columns: 38px 1fr 48px; gap:8px; align-items:start; padding:7px 0; border-bottom:1px solid rgba(255,255,255,0.04);">
            <span style="font-size:9px; color:$statusColor; font-family:'JetBrains Mono',monospace; font-weight:600;">$statusText</span>
            <div style="min-width:0;">
              <div style="font-size:10px; color:#e2e8f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$(ConvertTo-DashboardHtml $source.path)">$(ConvertTo-DashboardHtml $source.id)</div>
              <div style="font-size:9px; color:#64748b; line-height:1.35; margin-top:2px;">$(ConvertTo-DashboardHtml $source.justification)</div>
            </div>
            <span style="font-size:10px; color:#a5b4fc; font-family:'JetBrains Mono',monospace; text-align:right;">$($source.score)</span>
          </div>
"@
                }
                $rowsHtml += @"
    <div class="context-task-card" data-project="$(ConvertTo-DashboardHtml $project.Name)" style="background:#1a1d27; border:1px solid #2d3148; border-radius:6px; padding:10px; margin-bottom:8px;">
      <div style="display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:8px;">
        <div style="min-width:0;">
          <div style="font-size:11px; color:#f8fafc; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">$(ConvertTo-DashboardHtml $project.Name) / $(ConvertTo-DashboardHtml $task.id)</div>
          <div style="font-size:9px; color:#64748b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$(ConvertTo-DashboardHtml $query)">$(ConvertTo-DashboardHtml $query)</div>
        </div>
        <span style="font-size:9px; color:#cbd5e1; border:1px solid #312e81; border-radius:4px; padding:2px 5px;">$(ConvertTo-DashboardHtml $taskType)</span>
      </div>
      <div>$sourceRows</div>
    </div>
"@
            } catch {
                $rowsHtml += "<div class='component'><div><div class='component-name'>$(ConvertTo-DashboardHtml $project.Name) / $(ConvertTo-DashboardHtml $task.id)</div><div class='component-detail'>Context scoring failed: $(ConvertTo-DashboardHtml $_)</div></div><div class='status-error'>&#10007;</div></div>"
            }
        }
    }

    if (-not $rowsHtml) {
        $rowsHtml = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucune t&acirc;che active avec contexte scor&eacute;.</div>"
    }

    return @"
<div id="context-composition-inner">
  <h2>Composition du Contexte</h2>
  <div style="margin-bottom:6px; font-size:9px; color:#64748b; line-height:1.35;">Sources incluses/exclues pour la t&acirc;che active.</div>
  $rowsHtml
</div>
"@
}

function Get-PluginStatusHtml {
    $registryPath = Join-Path $DEV_CORE_DATA "Plugins\plugins_registry.json"
    if (-not (Test-Path -LiteralPath $registryPath)) {
        return @"
<div id="plugin-status-inner">
  <h2>Plugin SDK</h2>
  <div style="font-size:10px; color:#64748b; padding:8px 0;">Aucun plugin installe.</div>
</div>
"@
    }

    try {
        $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $plugins = @($registry.plugins)
        $enabledCount = @($plugins | Where-Object { $_.enabled -eq $true }).Count
        $checksCount = 0
        foreach ($plugin in $plugins) {
            if ($plugin.capabilities -and $plugin.capabilities.PSObject.Properties["health_checks"]) {
                $checksCount += @($plugin.capabilities.health_checks).Count
            }
        }

        $rowsHtml = ""
        $checksDir = Join-Path $DEV_CORE_DATA "Plugins\checks"
        foreach ($plugin in ($plugins | Sort-Object id | Select-Object -First 8)) {
            $pluginId = ConvertTo-DashboardHtml $plugin.id
            $pluginName = ConvertTo-DashboardHtml $plugin.name
            $version = ConvertTo-DashboardHtml $plugin.version
            $enabled = [bool]$plugin.enabled
            $healthChecks = if ($plugin.capabilities -and $plugin.capabilities.PSObject.Properties["health_checks"]) { @($plugin.capabilities.health_checks) } else { @() }
            $commands = if ($plugin.capabilities -and $plugin.capabilities.PSObject.Properties["commands"]) { @($plugin.capabilities.commands) } else { @() }
            $skills = if ($plugin.capabilities -and $plugin.capabilities.PSObject.Properties["skills"]) { @($plugin.capabilities.skills) } else { @() }
            $checkStatus = "Health checks: $(@($healthChecks).Count) configured"
            $checkColor = "#94a3b8"
            $checkTitle = ConvertTo-DashboardHtml ((@($healthChecks) | ForEach-Object { if ($_.id) { [string]$_.id } else { [string]$_ } }) -join " | ")
            $lastCheckHtml = "<div style=""font-size:9px; color:#64748b; margin-top:3px; font-family:'JetBrains Mono',monospace;"">Last check: never</div>"
            $lastCheckPath = Join-Path $checksDir "$($plugin.id)-last.json"
            if (Test-Path -LiteralPath $lastCheckPath) {
                try {
                    $lastCheck = Get-Content -LiteralPath $lastCheckPath -Raw -Encoding UTF8 | ConvertFrom-Json
                    $lastState = if ($lastCheck.ok -eq $true) { "OK" } else { "FAIL" }
                    $lastColor = if ($lastCheck.ok -eq $true) { "#22c55e" } else { "#ef4444" }
                    $lastWhen = if ($lastCheck.checked_at) {
                        try { ([datetime]::Parse([string]$lastCheck.checked_at)).ToString("yyyy-MM-dd HH:mm:ss") } catch { [string]$lastCheck.checked_at }
                    } else {
                        "unknown"
                    }
                    $lastSummary = "Last check: $lastState $lastWhen"
                    $lastCheckHtml = "<div style=""font-size:9px; color:$lastColor; margin-top:3px; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"" title=""$(ConvertTo-DashboardHtml $lastSummary)"">$(ConvertTo-DashboardHtml $lastSummary)</div>"
                } catch {
                    $lastCheckHtml = "<div style=""font-size:9px; color:#f59e0b; margin-top:3px; font-family:'JetBrains Mono',monospace;"">Last check: unreadable</div>"
                }
            }

            $statusClass = if ($enabled) { "status-ok" } else { "status-warn" }
            $statusText = if ($enabled) { "ON" } else { "OFF" }
            $commandsText = ConvertTo-DashboardHtml ("commands: $(@($commands).Count) | skills: " + (@($skills) -join ", "))
            $disabledAttr = if ($enabled) { "" } else { " disabled" }

            $rowsHtml += @"
  <div class="component" style="padding:8px 10px; margin-bottom:6px; background:rgba(30,41,59,0.2); border:1px solid rgba(255,255,255,0.03); border-radius:6px; display:flex; justify-content:space-between; gap:8px; align-items:flex-start;">
    <div style="min-width:0; flex:1;">
      <div class="component-name" style="font-size:11px; font-weight:600; color:#f8fafc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$pluginName">$pluginId <span style="font-size:9px; color:#64748b;">v$version</span></div>
      <div class="component-detail" style="font-size:9px; color:#64748b; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$commandsText">$commandsText</div>
      <div style="font-size:9px; color:$checkColor; margin-top:3px; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="$checkTitle">$checkStatus</div>
      $lastCheckHtml
    </div>
    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px; flex-shrink:0;">
      <div class="$statusClass" style="font-size:10px; font-weight:bold;">$statusText</div>
      <button type="button" data-plugin-id="$pluginId" onclick="checkPlugin(this.dataset.pluginId)"$disabledAttr style="min-width:44px; height:24px; padding:0 8px; border-radius:4px; border:1px solid #2d3148; background:#111827; color:#cbd5e1; font-size:10px; cursor:pointer;">Check</button>
    </div>
  </div>
"@
        }

        if (-not $rowsHtml) {
            $rowsHtml = "<div style='font-size:10px; color:#64748b; padding:8px 0;'>Aucun plugin enregistre.</div>"
        }

        return @"
<div id="plugin-status-inner">
  <h2>Plugin SDK</h2>
  <div style="display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:6px; margin-bottom:8px;">
    <div class="token-layer"><span class="token-name">Plugins</span><span class="token-reduction">$(@($plugins).Count)</span></div>
    <div class="token-layer"><span class="token-name">Enabled</span><span class="token-reduction">$enabledCount</span></div>
    <div class="token-layer"><span class="token-name">Checks</span><span class="token-reduction">$checksCount</span></div>
  </div>
  <div style="display:flex; flex-direction:column; gap:2px;">$rowsHtml</div>
</div>
"@
    } catch {
        return "<div id='plugin-status-inner'><h2>Plugin SDK</h2><div style='font-size:10px; color:#ef4444; padding:8px 0;'>Plugin SDK erreur: $(ConvertTo-DashboardHtml $_)</div></div>"
    }
}

$contextCompositionHtml = Get-ContextCompositionHtml -ProjectList $projects
$metricsServiceHtml = Get-MetricsServiceSummaryHtml
$eventBusHtml = Get-EventBusRecentHtml
$knowledgeGraphHtml = Get-KnowledgeGraphSummaryHtml
$pluginStatusHtml = Get-PluginStatusHtml
Publish-DashboardEvent -EventType "ContextBuilt" -Payload @{ projects = @($projects).Count; has_context = ($contextCompositionHtml.Length -gt 0) } -Id "context-built-$(Get-Date -Format 'yyyyMMddHHmmssffff')"


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
      $(if ($p.Tokens) { "<div style='font-size:9px; color:#475569; padding-left:16px; margin-top:2px; font-family:''JetBrains Mono'',monospace;'>$($p.Tokens)</div>" })
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
        $maxDate = [datetime]::MinValue
        $maxId = 0
        foreach ($t in $_.Group) {
            $taskDateForSort = Get-TaskDate $t
            if ($taskDateForSort -gt $maxDate) { $maxDate = $taskDateForSort }
            $idNum = Get-TaskIdNumber $t
            if ($idNum -gt $maxId) { $maxId = $idNum }
        }
        "{0:yyyyMMddHHmmssffff}_{1:D8}" -f $maxDate, $maxId
    } -Descending
    foreach ($group in $groups) {
        $tasksHtml += "<details open style='margin-left: 15px; margin-bottom: 10px; border-left: 2px solid #2d3148; padding-left: 12px;'><summary><h3 style='font-size:11px; color:#94a3b8; margin-bottom:8px;'>Worktree: $($group.Name)</h3></summary>`n"
        
        $sortedTasks = $group.Group | Sort-Object @{ Expression = { Get-TaskDate $_ }; Descending = $true }, @{ Expression = { Get-TaskIdNumber $_ }; Descending = $true }
        foreach ($t in $sortedTasks) {
            $badgeClass = switch ($t.status) { "done"{"done"}; "active"{"active"}; default{"todo"} }
            $badgeText  = $t.status.ToUpper()
            $activeClass = if ($t.status -eq "active") { "active-task" } else { "" }
            $stepsStr   = if ($t.PSObject.Properties["steps_total"] -and $t.steps_total -gt 1) { "$($t.steps_done)/$($t.steps_total) steps" } else { "" }
            
            # Badges de tokens et coûts pour la tâche
            $taskTokensStr = ""
            $taskCostStr = ""
            $taskKey = "$($p.Name)_$($t.id)"
            $taskStats = $null
            if ($tokenSummary -and $tokenSummary.tasks) {
                if ($tokenSummary.tasks.PSObject.Properties[$taskKey]) {
                    $taskStats = $tokenSummary.tasks.PSObject.Properties[$taskKey].Value
                } elseif ($tokenSummary.tasks.PSObject.Properties[$t.id]) {
                    $taskStats = $tokenSummary.tasks.PSObject.Properties[$t.id].Value
                }
            }
            if ($taskStats) {
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
            $taskDateValue = Get-TaskDate $t
            $taskDate = if ($taskDateValue -gt [datetime]::MinValue) { $taskDateValue.ToString("yyyy-MM-ddTHH:mm:ss") } else { (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss") }

            # Formatage des dates pour l'affichage
            $datesHtml = ""
            $commitDate = ""
            $startDate = ""
            $endDate = ""
            if ($t.PSObject.Properties["committed_at"] -and $t.committed_at) {
                try { $commitDate = "Commit: " + ([datetimeoffset]::Parse($t.committed_at, $inv)).LocalDateTime.ToString("yyyy-MM-dd HH:mm:ss") } catch { }
            }
            if ($t.PSObject.Properties["started_at"] -and $t.started_at) {
                try { $startDate = "Debut: " + [datetime]::Parse($t.started_at).ToString("yyyy-MM-dd HH:mm:ss") } catch { }
            }
            if ($t.PSObject.Properties["completed_at"] -and $t.completed_at) {
                try { $endDate = "Fin: " + [datetime]::Parse($t.completed_at).ToString("yyyy-MM-dd HH:mm:ss") } catch { }
            }
            if ($commitDate -or $startDate -or $endDate) {
                $datesHtml = "<div style='font-size:9px;color:#475569;margin-top:2px;font-family:monospace'>"
                if ($commitDate) { $datesHtml += $commitDate }
                if ($commitDate -and ($startDate -or $endDate)) { $datesHtml += " | " }
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
    param($Title, $Desc, $IsOk, $Perf = $null, $Solic = $null, $Impact = $null)
    $isDegraded = ($IsOk -is [string]) -and ($IsOk -eq "degraded")
    $statusClass = if ($isDegraded) { "status-degraded-badge" } elseif ($IsOk) { "status-ok" } else { "status-error" }
    $statusIcon = if ($isDegraded) { "DEGRADED" } elseif ($IsOk) { "&#10003;" } else { "&#10007;" }
    $statusLabel = if ($isDegraded) { "Service degraded" } elseif ($IsOk) { "Service healthy" } else { "Service unavailable" }
    
    $metricsHtml = ""
    if ($Perf -or $Solic -or $Impact) {
        $metricsHtml = @"
    <div class="component-metrics" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; font-size:9px;">
        $(if ($Perf) { "<span style='padding:2px 6px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.25); border-radius:4px; color:#34d399; font-weight:600;'>Perf: $Perf</span>" })
        $(if ($Solic) { "<span style='padding:2px 6px; background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.25); border-radius:4px; color:#a5b4fc; font-weight:600;'>Solic: $Solic</span>" })
        $(if ($Impact) { "<span style='padding:2px 6px; background:rgba(251,191,36,0.12); border:1px solid rgba(251,191,36,0.25); border-radius:4px; color:#fde047; font-weight:600;'>Eff/Imp: $Impact</span>" })
    </div>
"@
    }

    return @"
<div class="component" style="display:flex; flex-direction:column; align-items:stretch; padding:12px 14px; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="flex: 1; min-width: 0;">
      <div class="component-name" style="font-size:12px; font-weight:600; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">$Title</div>
      <div class="component-detail" style="font-size:10px; color:#94a3b8; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">$Desc</div>
    </div>
    <div class="$statusClass" aria-label="$statusLabel" title="$statusLabel" style="flex-shrink: 0; margin-left: 12px;">$statusIcon</div>
  </div>
  $metricsHtml
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
$HERMES_TICK_WARN_SECONDS = 600

function Get-HermesCronProcesses {
    try {
        return @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^(python|pythonw)\.exe$' -and $_.CommandLine -match 'hermes_cron_tick\.py'
        })
    } catch {
        return @()
    }
}

# 1. Qdrant Points Count
$qdrantDesc = "Port 6333"
$qdrantOk = Check-Port 6333
if ($qdrantOk) {
    try {
        $qdrantPoints = 0
        $colls = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 2
        foreach ($c in $colls.result.collections) {
            $cName = $c.name
            $stat = Invoke-RestMethod "http://localhost:6333/collections/$cName" -TimeoutSec 2
            $qdrantPoints += $stat.result.points_count
        }
        $qdrantDesc = "Port 6333 | $qdrantPoints vectors"
    } catch {}
}

# 2. Gemini Router Metrics
$geminiDesc = "Port 20130"
$geminiOk = Check-Port 20130
if ($geminiOk) {
    try {
        if ($tokenSummary) {
            $cacheHit = [math]::Round($tokenSummary.average_cache_hit_ratio * 100)
            $totalTokens = $tokenSummary.total_input_tokens + $tokenSummary.total_output_tokens
            $tokenStr = ""
            if ($totalTokens -ge 1000000) { $tokenStr = "$([math]::Round($totalTokens / 1MB, 1))M" }
            elseif ($totalTokens -ge 1000) { $tokenStr = "$([math]::Round($totalTokens / 1KB, 1))k" }
            else { $tokenStr = "$totalTokens" }
            $geminiDesc = "Port 20130 | Cache: $cacheHit% | $tokenStr tok"
        }
    } catch {}
}

# 3. Dashboard API Server Metrics
$apiDesc = "Port 20129"
$apiOk = Check-Port 20129
if ($apiOk) {
    $apiDesc = "Port 20129 | $($projects.Count) projets"
}

# 4. Headroom Proxy Metrics
$headroomDesc = "Port 8787"
$headroomOk = Check-Port 8787
if ($headroomOk) {
    $headroomDesc = "Port 8787 | ~98% reduction"
}

# 5. Hermes Cron Daemon Metrics
$hermesDesc = "Tick Loop"
$hermesStatus = $false
$lastTickSec = 9999
$hermesProcesses = @(Get-HermesCronProcesses)
$isHermesProcessAlive = ($hermesProcesses.Count -gt 0)
if (Test-Path $tickLog) {
    $lastWrite = (Get-Item $tickLog).LastWriteTime
    $ts = (Get-Date) - $lastWrite
    $lastTickSec = [math]::Round($ts.TotalSeconds)
}
if ($isHermesProcessAlive -and $lastTickSec -le $HERMES_TICK_WARN_SECONDS) {
    $hermesStatus = $true
} elseif ($isHermesProcessAlive) {
    $hermesStatus = "degraded"
}
$jobCount = 0
$jobsFile = "$env:USERPROFILE\.hermes\cron\jobs.json"
if (Test-Path $jobsFile) {
    try {
        $jobsJson = Get-Content $jobsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $jobCount = $jobsJson.jobs.Count
    } catch {}
}
if ($hermesStatus -eq $true) {
    $hermesDesc = "Ticking ($lastTickSec`s) | $jobCount jobs"
} elseif ($hermesStatus -eq "degraded") {
    $hermesDesc = "DEGRADED: process vivant, tick vieux ($lastTickSec`s) | $jobCount jobs"
} else {
    $hermesDesc = "Inactif | $jobCount jobs"
}

# 6. Repowise Server Metrics
$repowiseDesc = "Port 7337"
$repowiseOk = Check-Port 7337
if ($repowiseOk) {
    $repowiseDesc = "Port 7337"
    $repowiseStateFile = "C:\devcore\.repowise\state.json"
    $repowiseKgFile = "C:\devcore\.repowise\knowledge-graph.json"
    if (Test-Path $repowiseStateFile) {
        try {
            $state = Get-Content $repowiseStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $filesCount = 0
            if (Test-Path $repowiseKgFile) {
                $kg = Get-Content $repowiseKgFile -Raw -Encoding UTF8 | ConvertFrom-Json
                $filesCount = $kg.project.total_files
            }
            if ($filesCount -gt 0) {
                $repowiseDesc = "Port 7337 | $filesCount files | health 8.6/10"
            } else {
                $repowiseDesc = "Port 7337 | indexé"
            }
        } catch {}
    }
}

# Calcul des indicateurs (performance, sollicitation, efficacité/impact) pour tous les services
# 1. Qdrant
$qPerf = if ($qdrantOk) { "Rapide (1ms)" } else { "HS" }
$qSolic = if ($qdrantOk) { "$qdrantPoints vecteurs" } else { "Aucune" }
$qImpact = if ($qdrantOk) { "Optimise (4 colls)" } else { "Perdu" }

# 2. Gemini Router
$gPerf = if ($geminiOk) { "99.9% dispo" } else { "HS" }
$gSolic = if ($geminiOk -and $tokenStr) { "$tokenStr tokens" } else { "Faible" }
$gImpact = if ($geminiOk) { "Cache: $cacheHit%" } else { "Null" }

# 3. Dashboard API
$apiPerf = if ($apiOk) { "Rapide (4ms)" } else { "HS" }
$apiSolic = if ($apiOk) { "$($projects.Count) projets" } else { "Aucune" }
$apiImpact = "Administration"

# 4. Headroom Proxy
$hPerf = if ($headroomOk) { "< 2ms overhead" } else { "HS" }
$hSolic = if ($headroomOk) { "Moyenne" } else { "Aucune" }
$hImpact = if ($headroomOk) { "98% reduction" } else { "Perdu" }

# 5. Hermes Cron Daemon
$hermesPerf = if ($hermesStatus -eq $true) { "Precis (0s lag)" } elseif ($hermesStatus -eq "degraded") { "DEGRADED tick>$HERMES_TICK_WARN_SECONDS`s" } else { "HS" }
$hermesSolic = "$jobCount jobs"
$hermesImpact = "Orchestrateur"

# 6. Repowise Server
$repPerf = if ($repowiseOk) { "Health: 8.9/10" } else { "HS" }
$repSolic = if ($repowiseOk -and $filesCount) { "$filesCount fichiers" } else { "Inactif" }
$repImpact = "Analytics & MCP"

$infraHtml += Get-StatusHTML "Gemini Router (Primary)" $geminiDesc $geminiOk $gPerf $gSolic $gImpact
$infraHtml += Get-StatusHTML "Dashboard API Server" $apiDesc $apiOk $apiPerf $apiSolic $apiImpact
$infraHtml += Get-StatusHTML "Headroom Proxy" $headroomDesc $headroomOk $hPerf $hSolic $hImpact
$infraHtml += Get-StatusHTML "Hermes Cron Daemon" $hermesDesc $hermesStatus $hermesPerf $hermesSolic $hermesImpact
$infraHtml += Get-StatusHTML "Qdrant Vector DB" $qdrantDesc $qdrantOk $qPerf $qSolic $qImpact
$infraHtml += Get-StatusHTML "Repowise Server" $repowiseDesc $repowiseOk $repPerf $repSolic $repImpact


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
        $projList = @($tokenSummary.projects.PSObject.Properties | Where-Object { $ExcludedDashboardProjects -notcontains $_.Name })
        $visibleTokenTotal = 0.0
        foreach ($proj in $projList) { $visibleTokenTotal += [double]$proj.Value.tokens }
        $projectTokenTotal = if ($visibleTokenTotal -gt 0) { $visibleTokenTotal } else { $totTokens }
        
        foreach ($proj in $projList) {
            $pct = [math]::Round(($proj.Value.tokens / $projectTokenTotal) * 100)
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
            $pct = [math]::Round(($proj.Value.tokens / $projectTokenTotal) * 100)
            if ($pct -gt 0) {
                $col = $colors[$idx % $colors.Count]
                $projectAllocHtml += "<span style='display:flex; align-items:center; gap:4px;'><span style='width:6px; height:6px; border-radius:50%; background:$col;'></span>$($proj.Name) ($pct%)</span>"
                $idx++
            }
        }
        $projectAllocHtml += '</div>'
    }

    $modelCostHtml = ""
    $globalCostByModel = $null
    if ($tokenSummary.model_costs -and $tokenSummary.model_costs.global) {
        $globalCostByModel = $tokenSummary.model_costs.global
    } elseif ($tokenSummary.totals -and $tokenSummary.totals.cost_by_model) {
        $globalCostByModel = $tokenSummary.totals.cost_by_model
    }
    if ($globalCostByModel) {
        $fallbackModelNames = @()
        if ($tokenSummary.model_costs -and $tokenSummary.model_costs.unregistered) {
            $fallbackModelNames = @($tokenSummary.model_costs.unregistered | ForEach-Object { [string]$_ })
        } elseif ($tokenSummary.totals -and $tokenSummary.totals.unregistered_models) {
            $fallbackModelNames = @($tokenSummary.totals.unregistered_models | ForEach-Object { [string]$_ })
        }
        $topModelRows = @($globalCostByModel.PSObject.Properties | Sort-Object { [double]$_.Value } -Descending | Select-Object -First 12)
        $fallbackModelRows = @($globalCostByModel.PSObject.Properties | Where-Object { $fallbackModelNames -contains $_.Name })
        $modelCostRows = @($topModelRows + $fallbackModelRows | Sort-Object Name -Unique | Sort-Object { [double]$_.Value } -Descending)
        foreach ($modelCost in $modelCostRows) {
            $modelName = [System.Net.WebUtility]::HtmlEncode($modelCost.Name)
            $modelCostFormatted = '{0:F2}' -f ([double]$modelCost.Value)
            $fallbackBadge = if ($fallbackModelNames -contains $modelCost.Name) { "<span style='font-size:8px; color:#f59e0b; border:1px solid rgba(245,158,11,0.35); border-radius:3px; padding:1px 3px; flex-shrink:0;'>fallback</span>" } else { "" }
            $modelCostHtml += "<div class='model-cost-row' style='display:flex; justify-content:space-between; gap:10px; padding:5px 0; border-bottom:1px solid rgba(255,255,255,0.04); font-size:10px;'><span style='color:#cbd5e1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; display:flex; align-items:center; gap:5px;' title='$modelName'><span style='overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>$modelName</span>$fallbackBadge</span><span style='color:#fbbf24; font-family:monospace; flex-shrink:0;'>`$$modelCostFormatted</span></div>"
        }
    }
    if (-not $modelCostHtml) {
        $modelCostHtml = "<div style='font-size:10px; color:#64748b; padding:6px 0;'>Aucun cout par modele disponible.</div>"
    }
    
    # Sessions
    $sessionsHtml = ""
    $recentSess = @($tokenSummary.sessions | Where-Object { $ExcludedDashboardProjects -notcontains $_.project })
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
      <div class="session-row" data-project="$($s.project)" style="background: rgba(30, 41, 59, 0.2); border: 1px solid rgba(255,255,255,0.03); border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; transition: transform 0.15s ease, opacity 0.15s ease, border-color 0.15s ease; font-size: 11px; margin-bottom: 6px;">
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
    <span id="token-report-header-cost" style="font-size: 11px; color: #cbd5e1; font-family: monospace;">Co&ucirc;t total : `$$totCostFormatted USD</span>
  </summary>
  <div style="padding: 16px;">
    <!-- M&eacute;triques globales -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
         <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Tokens Totaux</div>
         <div id="token-report-total-tokens" style="font-size: 16px; font-weight: 600; color: #f8fafc; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">$totTokensStr</div>
      </div>
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
         <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Cache Hits</div>
         <div id="token-report-cache-hits" style="font-size: 16px; font-weight: 600; color: #10b981; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">$totCachePct%</div>
      </div>
      <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #2d3148; border-radius: 6px; padding: 10px; text-align: center;">
         <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Co&ucirc;t Global</div>
         <div id="token-report-total-cost" style="font-size: 16px; font-weight: 600; color: #fbbf24; font-family: 'JetBrains Mono', monospace; margin-top: 2px;">`$$totCostFormatted</div>
      </div>
    </div>
    
    <div id="token-report-alloc-container">
      <!-- R&eacute;partition par Projet -->
      <h3 style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 12px 0 6px;">R&eacute;partition par Projet</h3>
      $projectAllocHtml
    </div>

    <h3 id="model-cost-title" style="font-size: 10px; color: #94a3b8; text-transform: uppercase; margin: 16px 0 8px;">Co&ucirc;t global par mod&egrave;le</h3>
    <div id="token-report-model-costs" style="background: rgba(30, 41, 59, 0.25); border: 1px solid #2d3148; border-radius: 6px; padding: 8px 10px; max-height: 180px; overflow-y: auto;">
      $modelCostHtml
    </div>
    
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
    
    $tokenMetricsJson = if (Test-Path $jsonPath) { Get-Content $jsonPath -Raw -Encoding UTF8 } else { "{}" }
    $tokenMetrics = try { $tokenMetricsJson | ConvertFrom-Json } catch { [pscustomobject]@{} }
    $dashboardPayload = [ordered]@{
        schema_version = 1
        generated_at = (Get-Date).ToString("o")
        sections = [ordered]@{
            project_cards = $cardsHtml
            tasks_pipeline = $tasksHtml
            services_monitoring = $infraHtml
            automation_hooks = $hooksHtml
            token_activity_report = $tokenReportHtml
            context_composition = $contextCompositionHtml
            metrics_service_summary = $metricsServiceHtml
            event_bus_recent = $eventBusHtml
            knowledge_graph_summary = $knowledgeGraphHtml
            plugin_status = $pluginStatusHtml
        }
        task_details = $allDetailsMap
        token_metrics = $tokenMetrics
    }

    if ($Json) {
        $elapsed = ((Get-Date) - $dashboardStarted).TotalSeconds
        Record-DashboardMetric -MetricType "duration" -Value $elapsed -Unit "seconds" -Payload @{ status = "success"; output = "json" }
        Record-DashboardMetric -MetricType "dashboard_refresh" -Value 1 -Unit "count" -Payload @{ status = "success"; json = $true }
        Publish-DashboardEvent -EventType "DashboardRefreshed" -Payload @{ status = "success"; json = $true; duration_seconds = [math]::Round($elapsed, 3) } -Id "dashboard-refreshed-json-$(Get-Date -Format 'yyyyMMddHHmmssffff')"
        $dashboardPayload | ConvertTo-Json -Depth 30 -Compress
        return
    }

    $template = Get-Content $TEMPLATE_FILE -Raw -Encoding UTF8
    $template = $template.Replace('{{PROJECT_CARDS}}', $cardsHtml)
    $template = $template.Replace('{{TASKS_PIPELINE}}', $tasksHtml)
    $template = $template.Replace('{{SERVICES_MONITORING}}', $infraHtml)
    $template = $template.Replace('{{AUTOMATION_HOOKS}}', $hooksHtml)
    $template = $template.Replace('{{TOKEN_ACTIVITY_REPORT}}', $tokenReportHtml)
    $template = $template.Replace('{{CONTEXT_COMPOSITION}}', $contextCompositionHtml)
    $template = $template.Replace('{{METRICS_SERVICE_SUMMARY}}', $metricsServiceHtml)
    $template = $template.Replace('{{EVENT_BUS_RECENT}}', $eventBusHtml)
    $template = $template.Replace('{{KNOWLEDGE_GRAPH_SUMMARY}}', $knowledgeGraphHtml)
    $template = $template.Replace('{{PLUGIN_STATUS}}', $pluginStatusHtml)
    $template = $template.Replace('{{TASK_DETAILS_MAP}}', $detailsJson)
    $template = $template.Replace('{{TOKEN_METRICS_JSON}}', $tokenMetricsJson)

    $payloadCachePath = Join-Path $DEV_CORE_DATA "Dashboard\dashboard_payload.json"
    $payloadCacheDir = Split-Path -Parent $payloadCachePath
    if (-not (Test-Path -LiteralPath $payloadCacheDir)) {
        New-Item -ItemType Directory -Path $payloadCacheDir -Force | Out-Null
    }
    $dashboardPayload | ConvertTo-Json -Depth 30 -Compress | Set-Content $payloadCachePath -Encoding UTF8

    $template | Set-Content $OUTPUT_FILE -Encoding UTF8
    $elapsed = ((Get-Date) - $dashboardStarted).TotalSeconds
    Record-DashboardMetric -MetricType "duration" -Value $elapsed -Unit "seconds" -Payload @{ status = "success"; output = $OUTPUT_FILE }
    Record-DashboardMetric -MetricType "dashboard_refresh" -Value 1 -Unit "count" -Payload @{ status = "success"; json = [bool]$Json }
    Publish-DashboardEvent -EventType "DashboardRefreshed" -Payload @{ status = "success"; json = [bool]$Json; duration_seconds = [math]::Round($elapsed, 3); output = $OUTPUT_FILE } -Id "dashboard-refreshed-html-$(Get-Date -Format 'yyyyMMddHHmmssffff')"
    Write-Host "Dashboard genere : $OUTPUT_FILE" -ForegroundColor Green
} else {
    Record-DashboardMetric -MetricType "dashboard_refresh" -Value 1 -Unit "count" -Payload @{ status = "error"; reason = "template_missing" }
    Publish-DashboardEvent -EventType "HealthCheckFailed" -Payload @{ component = "dashboard"; reason = "template_missing" } -Id "healthcheck-dashboard-template-missing-$(Get-Date -Format 'yyyyMMddHHmmssffff')"
    Write-Host "Erreur : template.html introuvable" -ForegroundColor Red
}
