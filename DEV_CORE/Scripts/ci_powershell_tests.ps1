# ci_powershell_tests.ps1 -- portable PowerShell test runner
param(
    [string[]]$Tests,
    [int]$PerTestTimeoutSeconds = 120,
    [string]$ProgressPath,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$defaultTests = @(
    "test_verify_ci.ps1",
    "test_ci_workflow.ps1",
    "test_ci_timeout_contract.ps1",
    "test_benchmark_pipeline.ps1",
    "test_network_bind_contract.ps1",
    "test_launch_qdrant_startup.ps1",
    "test_dashboard_auth_contract.ps1",
    "test_dashboard_mutation_methods.ps1",
    "test_dashboard_security_contract.ps1",
    "test_runtime_state_contract.ps1",
    "test_test_exit_contract.ps1",
    "test_platform_version.ps1",
    "test_embedding_contract.ps1",
    "test_health_report.ps1",
    "test_diagnose_gate.ps1",
    "test_guided_recovery.ps1",
    "test_secret_scan.ps1",
    "test_dc_dispatch.ps1",
    "test_task_service.ps1",
    "test_task_list_adapter.ps1",
    "test_gateway.ps1",
    "test_context_service.ps1",
    "test_memory_service.ps1",
    "test_metrics_service.ps1",
    "test_endday_nonblocking.ps1",
    "test_event_bus.ps1",
    "test_dashboard_read_model.ps1",
    "test_knowledge_graph.ps1",
    "test_plugin_service.ps1",
    "test_plugin_isolation.ps1",
    "test_skills_runtime.ps1",
    "test_auto_skills_pipeline.ps1",
    "test_skill_agent_spec.ps1",
    "test_internal_plugins.ps1",
    "test_hermes_daemon.ps1",
    "test_hermes_hardening.ps1",
    "test_repowise_workspace_hermes.ps1",
    "test_repowise_ui_proxy.ps1",
    "test_repowise_ipv6_proxy.ps1",
    "test_repowise_watch_worker.ps1"
)

if (-not $Tests -or $Tests.Count -eq 0) {
    $Tests = $defaultTests
}
if ([string]::IsNullOrWhiteSpace($ProgressPath)) {
    $dataRoot = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
    $ProgressPath = Join-Path $dataRoot "Logs\scripts\ci_powershell_tests.last.json"
}

function Write-ProgressReport {
    param([object[]]$Results, [string]$Current = "")
    $dir = Split-Path -Parent $ProgressPath
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $failCount = @($Results | Where-Object status -eq "FAIL").Count
    $okCount = @($Results | Where-Object status -eq "OK").Count
    [pscustomobject]@{
        schema_version = "1.0"
        generated_at = (Get-Date).ToString("o")
        current = $Current
        overall = if ($failCount -gt 0) { "FAIL" } else { "RUNNING" }
        ok = $okCount
        fail = $failCount
        duration_ms = [int]((Get-Date) - $started).TotalMilliseconds
        per_test_timeout_seconds = $PerTestTimeoutSeconds
        tests = @($Results)
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ProgressPath -Encoding UTF8
}

function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Limit-Output {
    param([string]$Value, [int]$Limit = 4000)
    if ($null -eq $Value) { return "" }
    $trimmed = $Value.Trim()
    if ($trimmed.Length -le $Limit) { return $trimmed }
    return $trimmed.Substring($trimmed.Length - $Limit)
}

function Quote-ProcessArgument {
    param([string]$Value)
    if ($null -eq $Value) { return '""' }
    return '"' + ($Value -replace '\\', '\\' -replace '"', '\"') + '"'
}

$started = Get-Date
$results = @()

foreach ($test in $Tests) {
    $path = if ([System.IO.Path]::IsPathRooted($test)) { $test } else { Join-Path $PSScriptRoot $test }
    $name = Split-Path -Leaf $path
    $testStarted = Get-Date

    if (-not (Test-Path -LiteralPath $path)) {
        $results += [pscustomobject]@{
            name = $name
            status = "FAIL"
            reason = "missing_script"
            exit_code = 66
            duration_ms = 0
            output = "Missing PowerShell test: $test"
        }
        continue
    }

    Write-ProgressReport -Results $results -Current $name
    if (-not $Json) { Write-Host "[TEST] $name" -ForegroundColor Cyan }
    $argumentList = @(
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        (Quote-ProcessArgument $path)
    )
    $stdoutPath = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-ps-test-out-" + [guid]::NewGuid().ToString("N") + ".log")
    $stderrPath = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-ps-test-err-" + [guid]::NewGuid().ToString("N") + ".log")
    $process = Start-Process -FilePath "powershell" -ArgumentList $argumentList -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

    $completed = $process.WaitForExit($PerTestTimeoutSeconds * 1000)
    $exitCode = 124
    $reason = "timeout"
    if ($completed) {
        $process.Refresh()
        $exitCode = [int]$process.ExitCode
        $reason = if ($exitCode -eq 0) { "passed" } else { "exit_code" }
    } else {
        Stop-ProcessTree -ProcessId $process.Id
    }
    $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { "" }
    $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { "" }
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue

    $status = if ($reason -eq "passed") { "OK" } else { "FAIL" }
    $output = (($stdout, $stderr) -join "`n")
    $result = [pscustomobject]@{
        name = $name
        status = $status
        reason = $reason
        exit_code = [int]$exitCode
        duration_ms = [int]((Get-Date) - $testStarted).TotalMilliseconds
        output = Limit-Output -Value $output
    }
    $results += $result
    Write-ProgressReport -Results $results -Current $name

    if (-not $Json) {
        $color = if ($status -eq "OK") { "Green" } else { "Red" }
        Write-Host ("[{0}] {1} -- {2} ({3}ms)" -f $status, $name, $reason, $result.duration_ms) -ForegroundColor $color
        if ($status -eq "FAIL" -and $result.output) { Write-Host $result.output -ForegroundColor DarkGray }
    }

    if ($status -eq "FAIL") { break }
}

$failCount = @($results | Where-Object status -eq "FAIL").Count
$okCount = @($results | Where-Object status -eq "OK").Count
$report = [pscustomobject]@{
    schema_version = "1.0"
    generated_at = (Get-Date).ToString("o")
    overall = if ($failCount -gt 0) { "FAIL" } else { "OK" }
    ok = $okCount
    fail = $failCount
    duration_ms = [int]((Get-Date) - $started).TotalMilliseconds
    per_test_timeout_seconds = $PerTestTimeoutSeconds
    tests = @($results)
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
} elseif ($failCount -eq 0) {
    Write-Host "[OK] PowerShell tests passed" -ForegroundColor Green
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ProgressPath -Encoding UTF8

if ($failCount -gt 0) { exit 1 }
exit 0
