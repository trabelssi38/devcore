# test_dashboard_read_model.ps1 -- incremental Dashboard read model contract
$ErrorActionPreference = "Stop"

$eventBusScript = Join-Path $PSScriptRoot "event_bus.ps1"
$readModelScript = Join-Path $PSScriptRoot "dashboard_read_model.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_dashboard_read_model_test_" + [guid]::NewGuid().ToString("n"))
$env:DEVCORE_DATA_ROOT = $tmpRoot

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path $tmpRoot -Force | Out-Null

    & $eventBusScript -Action Publish -Id "evt-rm-1" -Source "task_service" -Project "devcore" -TaskId "T-148" -EventType "TaskCreated" -CorrelationId "rm-1" -PayloadJson '{"title":"build read model"}' | Out-Null
    & $eventBusScript -Action Publish -Id "evt-rm-2" -Source "metrics_service" -Project "devcore" -TaskId "T-148" -EventType "MetricRecorded" -CorrelationId "rm-2" -PayloadJson '{"metric_type":"tokens","value":42,"unit":"tokens"}' | Out-Null
    & $eventBusScript -Action Publish -Id "evt-rm-3" -Source "gen_dashboard" -Project "devcore" -TaskId "T-148" -EventType "DashboardRefreshed" -CorrelationId "rm-3" -PayloadJson '{"status":"success","duration_seconds":0.12}' | Out-Null

    $json = & $readModelScript -Action Rebuild -Json | Out-String
    $model = $json | ConvertFrom-Json

    Assert-True ($model.schema_version -eq 1) "read model should expose schema_version 1"
    Assert-True ($model.events.cursor.total_events -eq 3) "read model cursor should count processed events"
    Assert-True ($model.events.by_type.TaskCreated -eq 1) "read model should count TaskCreated"
    Assert-True ($model.events.by_type.MetricRecorded -eq 1) "read model should count MetricRecorded"
    Assert-True ($model.events.by_source.task_service -eq 1) "read model should count task_service source"
    Assert-True ($model.tasks.active.id -eq "T-148") "read model should expose latest task id"
    Assert-True ($model.metrics.latest.tokens.value -eq 42) "read model should expose latest metric snapshot"
    Assert-True ($model.dashboard.last_refresh.status -eq "success") "read model should expose dashboard refresh state"

    $snapshotPath = Join-Path $tmpRoot "Dashboard\read_model.json"
    Assert-True (Test-Path -LiteralPath $snapshotPath) "read model should persist snapshot"

    $readJson = & $readModelScript -Action Read -Json | Out-String
    $read = $readJson | ConvertFrom-Json
    Assert-True ($read.events.cursor.total_events -eq 3) "Read action should return persisted snapshot"

    Write-Host "[OK] dashboard read model tests passed" -ForegroundColor Green
} finally {
    Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
