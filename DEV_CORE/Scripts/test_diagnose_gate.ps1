# test_diagnose_gate.ps1 -- smoke tests for diagnose release gate exit codes
$ErrorActionPreference = "Stop"

$diagnoseScript = Join-Path $PSScriptRoot "diagnose.ps1"
$dcScript = Join-Path $PSScriptRoot "dc.ps1"

function Assert-ExitCode {
    param(
        [int]$Expected,
        [scriptblock]$Action,
        [string]$Message
    )
    & $Action | Out-Null
    if ($LASTEXITCODE -ne $Expected) {
        throw "$Message (expected $Expected, got $LASTEXITCODE)"
    }
}

Assert-ExitCode 0 {
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $diagnoseScript -Gate
} "diagnose -Gate should pass in current DEV_CORE environment"

Assert-ExitCode 0 {
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript "check --gate"
} "dc check --gate should dispatch diagnose gate"

$oldPlatformRoot = $env:DEVCORE_PLATFORM_ROOT
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-diagnose-gate-" + [guid]::NewGuid().ToString("N"))

try {
    $env:DEVCORE_PLATFORM_ROOT = Join-Path $tempRoot "missing-platform"
    $env:DEVCORE_DATA_ROOT = Join-Path $tempRoot "missing-data"
    Assert-ExitCode 1 {
        powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $diagnoseScript -Gate
    } "diagnose -Gate should fail when critical paths/scripts are missing"
} finally {
    if ($null -eq $oldPlatformRoot) {
        Remove-Item Env:\DEVCORE_PLATFORM_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_PLATFORM_ROOT = $oldPlatformRoot
    }

    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }
}

Write-Host "[OK] diagnose gate smoke tests passed" -ForegroundColor Green
