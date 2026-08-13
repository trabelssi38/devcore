# verify.ps1 -- DEV_CORE deterministic CI verification gate
param(
    [switch]$Ci,
    [switch]$Json,
    [int]$CheckTimeoutSeconds = 0,
    [int]$TotalTimeoutSeconds = 0
)

$ErrorActionPreference = "Stop"
$started = Get-Date
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$SCRIPTS = Join-Path $DEV_CORE "Scripts"
. "$SCRIPTS\platform_version.ps1"
$platform = Get-DevCorePlatformInfo

if ($CheckTimeoutSeconds -le 0) {
    $CheckTimeoutSeconds = if ($env:DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS) { [int]$env:DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS } else { 600 }
}
if ($TotalTimeoutSeconds -le 0) {
    $TotalTimeoutSeconds = if ($env:DEVCORE_VERIFY_TOTAL_TIMEOUT_SECONDS) { [int]$env:DEVCORE_VERIFY_TOTAL_TIMEOUT_SECONDS } else { 1200 }
}

function Get-DefaultChecks {
    return @(
        [pscustomobject]@{ name = "diagnose-gate"; script = (Join-Path $SCRIPTS "diagnose.ps1"); arguments = @("-Gate") },
        [pscustomobject]@{ name = "dc-dispatch"; script = (Join-Path $SCRIPTS "test_dc_dispatch.ps1"); arguments = @() },
        [pscustomobject]@{ name = "diagnose-gate-tests"; script = (Join-Path $SCRIPTS "test_diagnose_gate.ps1"); arguments = @() },
        [pscustomobject]@{ name = "verify-ci-tests"; script = (Join-Path $SCRIPTS "test_verify_ci.ps1"); arguments = @() },
        [pscustomobject]@{ name = "test-exit-contract"; script = (Join-Path $SCRIPTS "test_test_exit_contract.ps1"); arguments = @() },
        [pscustomobject]@{ name = "ci-workflow-contract"; script = (Join-Path $SCRIPTS "test_ci_workflow.ps1"); arguments = @() },
        [pscustomobject]@{ name = "platform-version-tests"; script = (Join-Path $SCRIPTS "test_platform_version.ps1"); arguments = @() },
        [pscustomobject]@{ name = "embedding-contract-tests"; script = (Join-Path $SCRIPTS "test_embedding_contract.ps1"); arguments = @() },
        [pscustomobject]@{ name = "qdrant-vector-contract"; script = (Join-Path $SCRIPTS "test_qdrant_vector_contract.ps1"); arguments = @() },
        [pscustomobject]@{ name = "health-report-tests"; script = (Join-Path $SCRIPTS "test_health_report.ps1"); arguments = @() },
        [pscustomobject]@{ name = "secret-scan-tests"; script = (Join-Path $SCRIPTS "test_secret_scan.ps1"); arguments = @() }
    )
}

function Get-CiChecks {
    return @(
        [pscustomobject]@{ name = "lint"; script = (Join-Path $SCRIPTS "ci_lint.ps1"); arguments = @() },
        [pscustomobject]@{ name = "python-tests"; script = (Join-Path $SCRIPTS "ci_python_tests.ps1"); arguments = @() },
        [pscustomobject]@{ name = "powershell-tests"; script = (Join-Path $SCRIPTS "ci_powershell_tests.ps1"); arguments = @() },
        [pscustomobject]@{ name = "secret-scan"; script = (Join-Path $SCRIPTS "secret_scan.ps1"); arguments = @("-Path", (Split-Path -Parent $DEV_CORE)) },
        [pscustomobject]@{ name = "contracts"; script = (Join-Path $SCRIPTS "ci_contract_tests.ps1"); arguments = @() },
        [pscustomobject]@{ name = "benchmarks"; script = (Join-Path $SCRIPTS "benchmark_reference.ps1"); arguments = @("-Json") }
    )
}

function Get-ConfiguredChecks {
    if ([string]::IsNullOrWhiteSpace($env:DEVCORE_VERIFY_CHECKS_JSON)) {
        if ($Ci) {
            return @(Get-CiChecks)
        }
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

function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Quote-ProcessArgument {
    param([string]$Value)
    if ($null -eq $Value) { return '""' }
    return '"' + ($Value -replace '\\', '\\' -replace '"', '\"') + '"'
}

function Quote-PowerShellLiteral {
    param([string]$Value)
    if ($null -eq $Value) { return "''" }
    return "'" + ($Value -replace "'", "''") + "'"
}

function Invoke-CheckProcess {
    param(
        [string]$ScriptPath,
        [string[]]$Arguments,
        [int]$TimeoutSeconds
    )

    $stdoutPath = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-verify-out-" + [guid]::NewGuid().ToString("N") + ".log")
    $stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-verify-err-" + [guid]::NewGuid().ToString("N") + ".log")
    $commandParts = @("&", (Quote-PowerShellLiteral $ScriptPath))
    foreach ($arg in $Arguments) { $commandParts += (Quote-PowerShellLiteral $arg) }
    $command = (($commandParts -join " ") + " 1> " + (Quote-PowerShellLiteral $stdoutPath) + " 2> " + (Quote-PowerShellLiteral $stderrPath) + "; exit `$LASTEXITCODE")
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "powershell"
    $startInfo.Arguments = (("-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", $command | ForEach-Object { Quote-ProcessArgument $_ }) -join " ")
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $completed = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $completed) {
        Stop-ProcessTree -ProcessId $process.Id
        $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
        $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
        return [pscustomobject]@{
            exit_code = 124
            reason = "timeout"
            output = (($stdout, $stderr) -join "`n")
        }
    }

    $process.WaitForExit()
    $process.Refresh()
    $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
    $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    $output = (($stdout, $stderr) -join "`n")
    $exitCode = [int]$process.ExitCode
    $reason = if ($exitCode -ne 0) {
        "exit_code"
    } elseif ($output -match "(?mi)^\s*\[FAIL\]") {
        "failure_marker"
    } else {
        "passed"
    }
    return [pscustomobject]@{
        exit_code = [int]$exitCode
        reason = $reason
        output = $output
    }
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

    $elapsedSeconds = ((Get-Date) - $started).TotalSeconds
    if ($elapsedSeconds -ge $TotalTimeoutSeconds) {
        $exitCode = 124
        $reason = "total_timeout"
        $output = "Verify total timeout reached before running $name"
    } elseif (Test-Path -LiteralPath $scriptPath) {
        try {
            $remainingTotal = [Math]::Max(1, [int]($TotalTimeoutSeconds - $elapsedSeconds))
            $effectiveTimeout = [Math]::Min($CheckTimeoutSeconds, $remainingTotal)
            $checkResult = Invoke-CheckProcess -ScriptPath $scriptPath -Arguments $arguments -TimeoutSeconds $effectiveTimeout
            $exitCode = [int]$checkResult.exit_code
            $reason = [string]$checkResult.reason
            $output = [string]$checkResult.output
        } catch {
            $ErrorActionPreference = "Stop"
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
    platform_version = $platform.version
    generated_at = (Get-Date).ToString("o")
    mode = if ($Ci) { "ci" } else { "local" }
    overall = if ($failCount -gt 0) { "FAIL" } else { "OK" }
    ok = $okCount
    fail = $failCount
    duration_ms = [int]((Get-Date) - $started).TotalMilliseconds
    check_timeout_seconds = $CheckTimeoutSeconds
    total_timeout_seconds = $TotalTimeoutSeconds
    checks = @($results)
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
} else {
    Write-Host ""
    Write-Host "  $($platform.title) -- Verify" -ForegroundColor Cyan
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
