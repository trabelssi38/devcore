# test_verify_ci.ps1 -- verify gate aggregates exit codes and textual failures
$ErrorActionPreference = "Stop"

$verifyScript = Join-Path $PSScriptRoot "verify.ps1"
$dcScript = Join-Path $PSScriptRoot "dc.ps1"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-verify-ci-" + [guid]::NewGuid().ToString("N"))
$oldChecks = $env:DEVCORE_VERIFY_CHECKS_JSON

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Invoke-JsonCommand {
    param([scriptblock]$Action, [int]$ExpectedExitCode)

    $output = & $Action | Out-String
    $actualExitCode = $LASTEXITCODE
    if ($actualExitCode -ne $ExpectedExitCode) {
        throw "Expected exit code $ExpectedExitCode, got $actualExitCode. Output: $output"
    }
    return ($output | ConvertFrom-Json)
}

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $passScript = Join-Path $tempRoot "pass.ps1"
    $softFailScript = Join-Path $tempRoot "soft-fail.ps1"
    $hardFailScript = Join-Path $tempRoot "hard-fail.ps1"

    "Write-Output '[OK] fixture passed'; exit 0" | Set-Content -LiteralPath $passScript -Encoding UTF8
    "Write-Output '[FAIL] fixture lied about its exit code'; exit 0" | Set-Content -LiteralPath $softFailScript -Encoding UTF8
    "Write-Output 'fixture failed'; exit 7" | Set-Content -LiteralPath $hardFailScript -Encoding UTF8

    $env:DEVCORE_VERIFY_CHECKS_JSON = @(
        @{ name = "pass"; script = $passScript; arguments = @() },
        @{ name = "soft-fail"; script = $softFailScript; arguments = @() },
        @{ name = "hard-fail"; script = $hardFailScript; arguments = @() }
    ) | ConvertTo-Json -Depth 6 -Compress

    $failedReport = Invoke-JsonCommand -ExpectedExitCode 1 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $verifyScript -Ci -Json
    }
    Assert-True ($failedReport.overall -eq "FAIL") "verify should fail when any check fails"
    Assert-True ($failedReport.fail -eq 2) "verify should detect hard and textual failures"
    Assert-True (($failedReport.checks | Where-Object name -eq "soft-fail").reason -eq "failure_marker") "verify should report a textual failure marker"
    Assert-True (($failedReport.checks | Where-Object name -eq "hard-fail").exit_code -eq 7) "verify should preserve child exit codes"

    $env:DEVCORE_VERIFY_CHECKS_JSON = "[]"
    $emptyReport = Invoke-JsonCommand -ExpectedExitCode 1 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $verifyScript -Ci -Json
    }
    Assert-True ($emptyReport.overall -eq "FAIL") "verify should fail closed when no checks are configured"
    Assert-True (($emptyReport.checks | Where-Object name -eq "configuration").reason -eq "no_checks") "verify should explain an empty check configuration"

    $env:DEVCORE_VERIFY_CHECKS_JSON = @(
        @{ name = "pass"; script = $passScript; arguments = @() }
    ) | ConvertTo-Json -Depth 6 -Compress

    $passedReport = Invoke-JsonCommand -ExpectedExitCode 0 -Action {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript "verify --ci --json"
    }
    Assert-True ($passedReport.overall -eq "OK") "dc verify --ci should dispatch the verify gate"
    Assert-True ($passedReport.fail -eq 0) "passing verify report should contain no failures"

    Write-Host "[OK] verify CI smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldChecks) {
        Remove-Item Env:\DEVCORE_VERIFY_CHECKS_JSON -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_VERIFY_CHECKS_JSON = $oldChecks
    }
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
