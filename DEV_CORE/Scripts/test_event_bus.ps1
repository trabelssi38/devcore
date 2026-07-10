# test_event_bus.ps1 -- smoke tests for DEV_CORE Event Bus
$ErrorActionPreference = "Stop"

$eventBusScript = Join-Path $PSScriptRoot "event_bus.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_event_bus_test_" + [guid]::NewGuid().ToString("n"))
$env:DEVCORE_DATA_ROOT = $tmpRoot

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path $tmpRoot -Force | Out-Null

    $healthJson = & $eventBusScript -Action Health -Json | Out-String
    $health = $healthJson | ConvertFrom-Json
    Assert-True ($health.ok -eq $true) "event_bus health should be ok"

    $payload = '{"api_key":"secret","message":"large prompt","safe":"ok"}'
    $firstJson = & $eventBusScript -Action Publish -Id "evt-test-1" -Source "test" -Project "devcore" -TaskId "T-120" -EventType "TaskCreated" -CorrelationId "corr-1" -PayloadJson $payload -Json | Out-String
    $first = $firstJson | ConvertFrom-Json
    Assert-True ($first.event.id -eq "evt-test-1") "published event should preserve explicit id"
    Assert-True ($first.duplicate -eq $false) "first publish should not be duplicate"
    Assert-True ($first.event.payload.api_key -eq "[REDACTED]") "secret payload values should be redacted"
    Assert-True ($first.event.payload.message -eq "[REDACTED_CONTEXT]") "context payload values should be redacted"

    $dupJson = & $eventBusScript -Action Publish -Id "evt-test-1" -Source "test" -Project "devcore" -TaskId "T-120" -EventType "TaskCreated" -CorrelationId "corr-1" -PayloadJson '{"safe":"again"}' -Json | Out-String
    $dup = $dupJson | ConvertFrom-Json
    Assert-True ($dup.duplicate -eq $true) "second publish with same id should be duplicate"

    & $eventBusScript -Action Publish -Id "evt-test-2" -Source "test" -Project "devcore" -TaskId "T-120" -EventType "DashboardRefreshed" -CorrelationId "corr-2" -PayloadJson '{"status":"success"}' | Out-Null

    $readJson = & $eventBusScript -Action Read -EventType "TaskCreated" -Json | Out-String
    $read = $readJson | ConvertFrom-Json
    Assert-True ($read.events_count -eq 1) "read should filter by event type"
    Assert-True ($read.errors_count -eq 0) "read should report zero parse errors"

    $tailJson = & $eventBusScript -Action Tail -Limit 1 -Json | Out-String
    $tail = $tailJson | ConvertFrom-Json
    Assert-True ($tail.events_count -eq 1) "tail should respect limit"
    Assert-True ($tail.events[0].event_type -eq "DashboardRefreshed") "tail should return newest event"

    $file = Join-Path $tmpRoot "Bus\events\events-$(Get-Date -Format 'yyyy-MM-dd').jsonl"
    Assert-True ((Get-Content -LiteralPath $file).Count -eq 2) "duplicates should not append new JSONL lines"

    Write-Host "[OK] event bus smoke tests passed"
} finally {
    Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
