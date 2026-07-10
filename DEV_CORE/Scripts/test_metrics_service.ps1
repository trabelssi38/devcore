# test_metrics_service.ps1 -- smoke tests for DEV_CORE Metrics Service
$ErrorActionPreference = "Stop"

$metricsServiceScript = Join-Path $PSScriptRoot "metrics_service.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

if (-not (Test-Path -LiteralPath $metricsServiceScript)) {
    throw "metrics_service.ps1 should exist"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-metrics-service-" + [guid]::NewGuid().ToString("N"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT

try {
    $env:DEVCORE_DATA_ROOT = $tempRoot

    $healthJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $metricsServiceScript -Action Health -Json | Out-String
    $health = $healthJson | ConvertFrom-Json
    Assert-True ($health.ok -eq $true) "Metrics Service health should be OK"
    Assert-True (Test-Path -LiteralPath $health.metrics_dir) "Metrics Service health should create metrics dir"

    $payload = '{"api_key":"supersecret","model":"gpt-5.5","tokens":42}'
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $metricsServiceScript -Action Record -Source test -Project devcore -TaskId T-119 -MetricType tokens -Value 42 -Unit tokens -PayloadJson $payload | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $metricsServiceScript -Action Record -Source test -Project devcore -TaskId T-119 -MetricType duration -Value 3.5 -Unit seconds | Out-Null

    $metricsFile = Get-ChildItem -LiteralPath (Join-Path $tempRoot "Logs\metrics") -Filter "metrics-*.jsonl" | Select-Object -First 1
    Assert-True ($null -ne $metricsFile) "Metrics Service should create a daily JSONL file"

    $lines = @(Get-Content -LiteralPath $metricsFile.FullName -Encoding UTF8)
    Assert-True ($lines.Count -eq 2) "Metrics Service should append one JSON object per Record call"
    Assert-True (($lines -join "`n") -notmatch "supersecret") "Metrics Service should redact secret payload values"

    $first = $lines[0] | ConvertFrom-Json
    Assert-True ($first.schema_version -eq 1) "Metric event should expose schema_version 1"
    Assert-True ($first.event_type -eq "MetricRecorded") "Metric event should use MetricRecorded event_type"
    Assert-True ($first.project -eq "devcore") "Metric event should preserve project"
    Assert-True ($first.task_id -eq "T-119") "Metric event should preserve task id"
    Assert-True ($first.metric_type -eq "tokens") "Metric event should preserve metric type"
    Assert-True ($first.payload.api_key -eq "[REDACTED]") "Metric event should redact api_key"

    $aggregateJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $metricsServiceScript -Action Aggregate -Json | Out-String
    $aggregate = $aggregateJson | ConvertFrom-Json
    Assert-True ($aggregate.events_count -eq 2) "Aggregate should count recorded events"
    Assert-True ($aggregate.errors_count -eq 0) "Aggregate should report zero parse errors"
    Assert-True ($aggregate.totals.tokens.tokens.sum -eq 42) "Aggregate should sum token metrics by type and unit"
    Assert-True ($aggregate.projects.devcore.events_count -eq 2) "Aggregate should group by project"

    $statusJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $metricsServiceScript -Action Status -Json | Out-String
    $status = $statusJson | ConvertFrom-Json
    Assert-True ($status.health.ok -eq $true) "Status should include health"
    Assert-True ($status.aggregate.events_count -eq 2) "Status should include aggregate"

    Write-Host "[OK] metrics service smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
