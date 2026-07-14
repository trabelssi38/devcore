# test_ci_timeout_contract.ps1 -- bounded CI runner and verify timeout contracts
$ErrorActionPreference = "Stop"

$ciRunner = Join-Path $PSScriptRoot "ci_powershell_tests.ps1"
$verifyScript = Join-Path $PSScriptRoot "verify.ps1"
$taskNextScript = Join-Path $PSScriptRoot "task_next.ps1"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-ci-timeout-" + [guid]::NewGuid().ToString("N"))

$oldVerifyChecks = $env:DEVCORE_VERIFY_CHECKS_JSON
$oldVerifyTimeout = $env:DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$oldPlatformRoot = $env:DEVCORE_PLATFORM_ROOT

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Invoke-JsonCommand {
    param([scriptblock]$Action, [int]$ExpectedExitCode)
    $output = & $Action | Out-String
    $actual = $LASTEXITCODE
    if ($ExpectedExitCode -eq -1) {
        if ($actual -eq 0) { throw "Expected non-zero exit code, got 0. Output: $output" }
    } elseif ($actual -ne $ExpectedExitCode) {
        throw "Expected exit code $ExpectedExitCode, got $actual. Output: $output"
    }
    return ($output | ConvertFrom-Json)
}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

    $slowScript = Join-Path $tempRoot "slow.ps1"
    $chattyScript = Join-Path $tempRoot "chatty.ps1"
    @"
Start-Sleep -Seconds 5
Write-Host '[OK] too late'
exit 0
"@ | Set-Content -LiteralPath $slowScript -Encoding UTF8
    @"
1..1000 | ForEach-Object { Write-Host "line `$_" }
Write-Host '[OK] chatty passed'
exit 0
"@ | Set-Content -LiteralPath $chattyScript -Encoding UTF8

    $runnerReport = Invoke-JsonCommand -ExpectedExitCode -1 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ciRunner -Tests @($slowScript) -PerTestTimeoutSeconds 1 -Json
    }
    Assert-True ($runnerReport.overall -eq "FAIL") "PowerShell CI runner should fail on timeout"
    Assert-True ($runnerReport.fail -eq 1) "PowerShell CI runner should count timeout as failure"
    Assert-True ($runnerReport.tests[0].reason -eq "timeout") "PowerShell CI runner should report timeout reason"
    Assert-True ($runnerReport.tests[0].duration_ms -lt 5000) "PowerShell CI runner should stop timed-out test before full sleep"

    $chattyRunnerReport = Invoke-JsonCommand -ExpectedExitCode 0 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $ciRunner -Tests @($chattyScript) -PerTestTimeoutSeconds 30 -Json
    }
    Assert-True ($chattyRunnerReport.overall -eq "OK") "PowerShell CI runner should not deadlock on large stdout"
    Assert-True ($chattyRunnerReport.tests[0].reason -eq "passed") "PowerShell CI runner should pass chatty test"

    $env:DEVCORE_VERIFY_CHECKS_JSON = @(
        @{ name = "slow-check"; script = $slowScript; arguments = @() }
    ) | ConvertTo-Json -Depth 6 -Compress
    $env:DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS = "1"

    $verifyReport = Invoke-JsonCommand -ExpectedExitCode 1 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $verifyScript -Ci -Json
    }
    Assert-True ($verifyReport.overall -eq "FAIL") "verify should fail on timed-out check"
    Assert-True ($verifyReport.checks[0].reason -eq "timeout") "verify should expose timeout reason"
    Assert-True ($verifyReport.checks[0].duration_ms -lt 5000) "verify should stop timed-out check before full sleep"

    $env:DEVCORE_VERIFY_CHECKS_JSON = @(
        @{ name = "chatty-check"; script = $chattyScript; arguments = @() }
    ) | ConvertTo-Json -Depth 6 -Compress
    $env:DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS = "30"

    $chattyVerifyReport = Invoke-JsonCommand -ExpectedExitCode 0 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $verifyScript -Ci -Json
    }
    Assert-True ($chattyVerifyReport.overall -eq "OK") "verify should not deadlock on large stdout"
    Assert-True ($chattyVerifyReport.checks[0].reason -eq "passed") "verify should pass chatty check"

    $fakeData = Join-Path $tempRoot "data"
    $fakePlatform = Join-Path $tempRoot "platform"
    $fakeScripts = Join-Path $fakePlatform "Scripts"
    $fakeProject = Join-Path $fakeData "Memory\devcore"
    New-Item -ItemType Directory -Path $fakeScripts, $fakeProject, (Join-Path $fakeData "Logs\scripts") -Force | Out-Null

    "devcore" | Set-Content -LiteralPath (Join-Path $fakeScripts "Get-ActiveProject.ps1") -Encoding UTF8
    @'
param([string]$InputFile)
exit 0
'@ | Set-Content -LiteralPath (Join-Path $fakeScripts "toonify.ps1") -Encoding UTF8
    @'
exit 0
'@ | Set-Content -LiteralPath (Join-Path $fakeScripts "gen_dashboard.ps1") -Encoding UTF8
    @'
param([string]$Action, [switch]$Json)
if ($Action -eq "Next") { "null"; exit 0 }
exit 0
'@ | Set-Content -LiteralPath (Join-Path $fakeScripts "task_service.ps1") -Encoding UTF8

    @{
        project = "devcore"
        current_task = "T-DONE"
        tasks = @(
            @{ id = "T-DONE"; title = "done task"; mode = "coding"; status = "done"; steps_done = 1; steps_total = 1 }
        )
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $fakeProject "tasks.json") -Encoding UTF8

    $env:DEVCORE_DATA_ROOT = $fakeData
    $env:DEVCORE_PLATFORM_ROOT = $fakePlatform
    $taskNextOutput = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskNextScript | Out-String
    Assert-True ($LASTEXITCODE -eq 0) "task_next should exit cleanly when all tasks are done"

    $sessionContext = Get-Content -LiteralPath (Join-Path $fakeData "Logs\scripts\session_context.txt") -Raw -Encoding UTF8
    Assert-True ($sessionContext -match "Aucune tache active") "task_next should refresh session_context.txt when no task is active"
    Assert-True ($sessionContext -notmatch "T-DONE") "task_next should not leave stale done task in session_context.txt"

    Write-Host "[OK] CI timeout contracts passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldVerifyChecks) { Remove-Item Env:\DEVCORE_VERIFY_CHECKS_JSON -ErrorAction SilentlyContinue } else { $env:DEVCORE_VERIFY_CHECKS_JSON = $oldVerifyChecks }
    if ($null -eq $oldVerifyTimeout) { Remove-Item Env:\DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS -ErrorAction SilentlyContinue } else { $env:DEVCORE_VERIFY_CHECK_TIMEOUT_SECONDS = $oldVerifyTimeout }
    if ($null -eq $oldDataRoot) { Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue } else { $env:DEVCORE_DATA_ROOT = $oldDataRoot }
    if ($null -eq $oldPlatformRoot) { Remove-Item Env:\DEVCORE_PLATFORM_ROOT -ErrorAction SilentlyContinue } else { $env:DEVCORE_PLATFORM_ROOT = $oldPlatformRoot }
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
