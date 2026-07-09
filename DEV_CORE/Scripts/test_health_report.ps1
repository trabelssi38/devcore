# test_health_report.ps1 -- smoke tests for v10 health report
$ErrorActionPreference = "Stop"

$healthScript = Join-Path $PSScriptRoot "health_report.ps1"
$dcScript = Join-Path $PSScriptRoot "dc.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) { throw $Message }
}

$jsonText = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $healthScript -Json
if ($LASTEXITCODE -ne 0) {
    throw "health_report.ps1 -Json failed with exit code $LASTEXITCODE"
}

$report = $jsonText | ConvertFrom-Json
Assert-True ($report.schema_version -eq "1.0") "health report schema_version should be 1.0"
Assert-True ($report.duration_ms -ge 0) "health report should include duration_ms"
Assert-True ($report.checks.Count -gt 0) "health report should include checks"

$components = @($report.checks | ForEach-Object { $_.component } | Sort-Object -Unique)
foreach ($required in @("paths", "services", "secrets", "task_board", "memory")) {
    Assert-True ($components -contains $required) "health report missing component: $required"
}

foreach ($check in $report.checks) {
    Assert-True (@("OK", "WARN", "FAIL") -contains $check.status) "invalid status for $($check.name): $($check.status)"
}

$dcOutput = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript "health"
if ($LASTEXITCODE -ne 0) {
    throw "dc health failed with exit code $LASTEXITCODE"
}
Assert-True (($dcOutput -join "`n") -match "DEV_CORE v10 -- Health") "dc health should render health report"

Write-Host "[OK] health report smoke tests passed" -ForegroundColor Green
