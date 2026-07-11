# verify.ps1 -- DEV_CORE v10 deterministic CI verification gate
param(
    [switch]$Ci,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$started = Get-Date
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$SCRIPTS = Join-Path $DEV_CORE "Scripts"

function Get-DefaultChecks {
    return @(
        [pscustomobject]@{ name = "diagnose-gate"; script = (Join-Path $SCRIPTS "diagnose.ps1"); arguments = @("-Gate") },
        [pscustomobject]@{ name = "dc-dispatch"; script = (Join-Path $SCRIPTS "test_dc_dispatch.ps1"); arguments = @() },
        [pscustomobject]@{ name = "diagnose-gate-tests"; script = (Join-Path $SCRIPTS "test_diagnose_gate.ps1"); arguments = @() },
        [pscustomobject]@{ name = "test-exit-contract"; script = (Join-Path $SCRIPTS "test_test_exit_contract.ps1"); arguments = @() },
        [pscustomobject]@{ name = "health-report-tests"; script = (Join-Path $SCRIPTS "test_health_report.ps1"); arguments = @() },
        [pscustomobject]@{ name = "secret-scan-tests"; script = (Join-Path $SCRIPTS "test_secret_scan.ps1"); arguments = @() }
    )
}

function Get-ConfiguredChecks {
    if ([string]::IsNullOrWhiteSpace($env:DEVCORE_VERIFY_CHECKS_JSON)) {
        return @(Get-DefaultChecks)
    }

    try {
        $parsed = $env:DEVCORE_VERIFY_CHECKS_JSON | ConvertFrom-Json
        foreach ($item in $parsed) {
            Write-Output $item
        }
        return
    } catch {
        throw "DEVCORE_VERIFY_CHECKS_JSON is invalid JSON: $_"
    }
}

function Limit-Output {
    param([string]$Value, [int]$Limit = 4000)
    if ($null -eq $Value) { return "" }
    $trimmed = $Value.Trim()
    if ($trimmed.Length -le $Limit) { return $trimmed }
    return $trimmed.Substring($trimmed.Length - $Limit)
}

$results = @()
$configuredChecks = @(Get-ConfiguredChecks)
if ($configuredChecks.Count -eq 0) {
    $results += [pscustomobject]@{
        name = "configuration"
        status = "FAIL"
        reason = "no_checks"
        exit_code = 64
        duration_ms = 0
        output = "No verification checks are configured"
    }
}

foreach ($check in $configuredChecks) {
    $name = [string]$check.name
    $scriptPath = [string]$check.script
    $arguments = @($check.arguments | ForEach-Object { [string]$_ })
    $checkStarted = Get-Date
    $exitCode = 66
    $output = ""
    $reason = "missing_script"

    if (Test-Path -LiteralPath $scriptPath) {
        try {
            $output = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath @arguments 2>&1 | Out-String
            $exitCode = $LASTEXITCODE
            if ($exitCode -ne 0) {
                $reason = "exit_code"
            } elseif ($output -match "(?mi)^\s*\[FAIL\]") {
                $reason = "failure_marker"
            } else {
                $reason = "passed"
            }
        } catch {
            $exitCode = 70
            $output = $_ | Out-String
            $reason = "exception"
        }
    } else {
        $output = "Script not found: $scriptPath"
    }

    $status = if ($reason -eq "passed") { "OK" } else { "FAIL" }
    $results += [pscustomobject]@{
        name = $name
        status = $status
        reason = $reason
        exit_code = [int]$exitCode
        duration_ms = [int]((Get-Date) - $checkStarted).TotalMilliseconds
        output = Limit-Output -Value $output
    }
}

$failCount = @($results | Where-Object status -eq "FAIL").Count
$okCount = @($results | Where-Object status -eq "OK").Count
$report = [pscustomobject]@{
    schema_version = "1.0"
    generated_at = (Get-Date).ToString("o")
    mode = if ($Ci) { "ci" } else { "local" }
    overall = if ($failCount -gt 0) { "FAIL" } else { "OK" }
    ok = $okCount
    fail = $failCount
    duration_ms = [int]((Get-Date) - $started).TotalMilliseconds
    checks = @($results)
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
} else {
    Write-Host ""
    Write-Host "  DEV_CORE v10 -- Verify" -ForegroundColor Cyan
    Write-Host "  ======================" -ForegroundColor DarkGray
    foreach ($result in $results) {
        $color = if ($result.status -eq "OK") { "Green" } else { "Red" }
        Write-Host ("  [{0}] {1} -- {2} ({3}ms)" -f $result.status, $result.name, $result.reason, $result.duration_ms) -ForegroundColor $color
        if ($result.status -eq "FAIL" -and $result.output) {
            Write-Host $result.output -ForegroundColor DarkGray
        }
    }
    Write-Host ""
    Write-Host ("  Overall: {0} | OK: {1} FAIL: {2} | {3}ms" -f $report.overall, $okCount, $failCount, $report.duration_ms) -ForegroundColor White
    Write-Host ""
}

if ($failCount -gt 0) { exit 1 }
exit 0
