# test_knowledge_graph.ps1 -- smoke tests for DEV_CORE Knowledge Graph
$ErrorActionPreference = "Stop"

$knowledgeGraphScript = Join-Path $PSScriptRoot "knowledge_graph.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_knowledge_graph_test_" + [guid]::NewGuid().ToString("n"))
$dataRoot = Join-Path $tmpRoot "DEV_CORE_DATA"
$repoRoot = Join-Path $tmpRoot "repo"
$env:DEVCORE_DATA_ROOT = $dataRoot

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path $dataRoot,$repoRoot -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $repoRoot "DEV_CORE\Scripts") -Force | Out-Null
    "Write-Host 'foo'" | Set-Content -LiteralPath (Join-Path $repoRoot "DEV_CORE\Scripts\foo.ps1") -Encoding UTF8

    git -C $repoRoot init | Out-Null
    git -C $repoRoot config user.email "devcore@example.local"
    git -C $repoRoot config user.name "DEV_CORE Test"
    git -C $repoRoot add .
    git -C $repoRoot commit -m "feat: update foo [T-01]" | Out-Null

    $taskDir = Join-Path $dataRoot "Memory\devcore"
    New-Item -ItemType Directory -Path $taskDir -Force | Out-Null
    @{
        project = "devcore"
        current_task = $null
        tasks = @(
            @{
                id = "T-01"
                title = "update foo"
                mode = "coding"
                status = "done"
                steps_done = 1
                steps_total = 1
                completed_at = "2026-07-11T01:00:00+01:00"
            }
        )
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $taskDir "tasks.json") -Encoding UTF8

    $eventDir = Join-Path $dataRoot "Bus\events"
    New-Item -ItemType Directory -Path $eventDir -Force | Out-Null
    @{
        schema_version = 1
        id = "event-1"
        timestamp = "2026-07-11T01:00:01+01:00"
        source = "test"
        event_type = "TaskCompleted"
        project = "devcore"
        task_id = "T-01"
        correlation_id = "corr-1"
        payload = @{ status = "done" }
    } | ConvertTo-Json -Depth 10 -Compress | Set-Content -LiteralPath (Join-Path $eventDir "events-2026-07-11.jsonl") -Encoding UTF8

    $metricDir = Join-Path $dataRoot "Logs\metrics"
    New-Item -ItemType Directory -Path $metricDir -Force | Out-Null
    @{
        schema_version = 1
        id = "metric-1"
        event_type = "MetricRecorded"
        timestamp = "2026-07-11T01:00:02+01:00"
        source = "test"
        project = "devcore"
        task_id = "T-01"
        metric_type = "tokens"
        value = 42
        unit = "tokens"
        payload = @{ component = "foo" }
    } | ConvertTo-Json -Depth 10 -Compress | Set-Content -LiteralPath (Join-Path $metricDir "metrics-2026-07-11.jsonl") -Encoding UTF8

    $decisionDir = Join-Path $dataRoot "Vault\Daily Notes"
    New-Item -ItemType Directory -Path $decisionDir -Force | Out-Null
    "# Daily`n`n## Decisions`n- Decision: keep foo in Scripts service." | Set-Content -LiteralPath (Join-Path $decisionDir "2026-07-11.md") -Encoding UTF8

    $buildJson = & $knowledgeGraphScript -Action Build -RepoRoot $repoRoot -Json | Out-String
    $graph = $buildJson | ConvertFrom-Json
    Assert-True ($graph.nodes_count -ge 6) "graph should contain task, commit, file, service, event and metric nodes"
    Assert-True ($graph.edges_count -ge 5) "graph should contain core relationships"
    Assert-True (Test-Path -LiteralPath (Join-Path $dataRoot "Knowledge\graph.json")) "graph.json should be written"

    $edgeTypes = @($graph.edges | ForEach-Object { $_.type })
    foreach ($type in @("task_commit","commit_file","file_service","metric_task","event_task")) {
        Assert-True ($edgeTypes -contains $type) "graph should contain edge type $type"
    }

    $impactJson = & $knowledgeGraphScript -Action ImpactAnalysis -RepoRoot $repoRoot -Target "DEV_CORE/Scripts/foo.ps1" -Json | Out-String
    $impact = $impactJson | ConvertFrom-Json
    Assert-True ($impact.related_tasks -contains "T-01") "impact analysis should return related task"
    Assert-True ($impact.services -contains "Scripts") "impact analysis should return related service"
    Assert-True ($impact.blast_radius -gt 0) "impact analysis should compute non-zero blast radius"

    Write-Host "[OK] knowledge graph smoke tests passed"
} finally {
    Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
