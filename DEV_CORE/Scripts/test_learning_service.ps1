# test_learning_service.ps1 -- smoke tests for DEV_CORE Learning Service
$ErrorActionPreference = "Stop"

$learningServiceScript = Join-Path $PSScriptRoot "learning_service.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_learning_service_test_" + [guid]::NewGuid().ToString("n"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Write-JsonLine {
    param($Path, $Value)
    ($Value | ConvertTo-Json -Depth 20 -Compress) | Add-Content -LiteralPath $Path -Encoding UTF8
}

try {
    $env:DEVCORE_DATA_ROOT = $tmpRoot
    $metricsDir = Join-Path $tmpRoot "Logs\metrics"
    $eventsDir = Join-Path $tmpRoot "Bus\events"
    New-Item -ItemType Directory -Path $metricsDir,$eventsDir -Force | Out-Null

    $date = Get-Date -Format "yyyy-MM-dd"
    $metricsFile = Join-Path $metricsDir "metrics-$date.jsonl"
    $eventsFile = Join-Path $eventsDir "events-$date.jsonl"

    Write-JsonLine $metricsFile @{
        schema_version = 1
        timestamp = "2026-07-11T08:00:00+01:00"
        source = "token_report"
        project = "devcore"
        task_id = "T-125"
        metric_type = "cost"
        value = 12
        unit = "usd"
        payload = @{ mode = "coding"; model = "gemini-pro" }
    }
    Write-JsonLine $metricsFile @{
        schema_version = 1
        timestamp = "2026-07-11T08:01:00+01:00"
        source = "token_report"
        project = "devcore"
        task_id = "T-126"
        metric_type = "cost"
        value = 3
        unit = "usd"
        payload = @{ mode = "bulk"; model = "gemini-flash" }
    }
    Write-JsonLine $metricsFile @{
        schema_version = 1
        timestamp = "2026-07-11T08:02:00+01:00"
        source = "agent_feedback"
        project = "devcore"
        task_id = "T-125"
        metric_type = "corrections"
        value = 4
        unit = "count"
        payload = @{ mode = "coding"; task_type = "debug" }
    }

    Write-JsonLine $eventsFile @{
        schema_version = 1
        id = "event-health-1"
        timestamp = "2026-07-11T08:03:00+01:00"
        source = "dashboard_api"
        event_type = "HealthCheckFailed"
        project = "devcore"
        task_id = "T-125"
        correlation_id = "health-1"
        payload = @{ status = "fail" }
    }

    Assert-True (Test-Path -LiteralPath $learningServiceScript) "learning_service.ps1 should exist"

    $healthJson = & $learningServiceScript -Action Health -Json | Out-String
    $health = $healthJson | ConvertFrom-Json
    Assert-True ($health.ok -eq $true) "Learning Service health should be OK"
    Assert-True (Test-Path -LiteralPath $health.learning_dir) "Learning Service health should create learning dir"

    $analysisJson = & $learningServiceScript -Action Analyze -Json | Out-String
    $analysis = $analysisJson | ConvertFrom-Json
    Assert-True ($analysis.recommendations_count -ge 3) "Analyze should emit cost, correction and reliability recommendations"
    Assert-True ($analysis.baseline.cost_by_mode.coding.average -eq 12) "Analyze should expose coding cost baseline"
    Assert-True ($analysis.baseline.cost_by_mode.bulk.average -eq 3) "Analyze should expose bulk cost baseline"

    $types = @($analysis.recommendations | ForEach-Object { $_.type })
    Assert-True ($types -contains "routing") "Analyze should include a routing recommendation"
    Assert-True ($types -contains "cost") "Analyze should include a cost recommendation"
    Assert-True ($types -contains "reliability") "Analyze should include a reliability recommendation"

    foreach ($recommendation in @($analysis.recommendations)) {
        Assert-True ($recommendation.confidence -gt 0) "Recommendation should expose confidence"
        Assert-True ($recommendation.evidence.Count -gt 0) "Recommendation should expose evidence"
    }

    Assert-True (Test-Path -LiteralPath $analysis.report_path) "Analyze should write a report file"

    $statusJson = & $learningServiceScript -Action Status -Json | Out-String
    $status = $statusJson | ConvertFrom-Json
    Assert-True ($status.health.ok -eq $true) "Status should include health"
    Assert-True ($status.latest_report.recommendations_count -ge 3) "Status should include latest report"

    Write-Host "[OK] learning service smoke tests passed"
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }
    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
