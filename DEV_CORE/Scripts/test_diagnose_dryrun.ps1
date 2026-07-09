# test_diagnose_dryrun.ps1 -- smoke tests for diagnose dry-run repairs
$ErrorActionPreference = "Stop"

$diagnoseScript = Join-Path $PSScriptRoot "diagnose.ps1"
$dcScript = Join-Path $PSScriptRoot "dc.ps1"

function Invoke-WithMissingRoots {
    param([scriptblock]$Action)

    $oldPlatformRoot = $env:DEVCORE_PLATFORM_ROOT
    $oldDataRoot = $env:DEVCORE_DATA_ROOT
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-diagnose-dryrun-" + [guid]::NewGuid().ToString("N"))

    try {
        $env:DEVCORE_PLATFORM_ROOT = Join-Path $tempRoot "missing-platform"
        $env:DEVCORE_DATA_ROOT = Join-Path $tempRoot "missing-data"
        & $Action $tempRoot
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

        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Invoke-WithMissingRoots {
    param($TempRoot)

    $output = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $diagnoseScript -Fix -DryRun 2>&1 | Out-String
    if ($output -notmatch "MODE DRY-RUN ACTIVE") {
        throw "diagnose -Fix -DryRun should print dry-run mode"
    }
    if ($output -notmatch "\[DRYRUN\]") {
        throw "diagnose -Fix -DryRun should report skipped fixes"
    }
    if (Test-Path -LiteralPath $TempRoot) {
        throw "diagnose -Fix -DryRun should not create missing root directories"
    }
}

$dcOutput = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript "check --fix --dry-run" 2>&1 | Out-String
if ($dcOutput -notmatch "MODE DRY-RUN ACTIVE") {
    throw "dc check --fix --dry-run should dispatch diagnose dry-run mode"
}

Write-Host "[OK] diagnose dry-run smoke tests passed" -ForegroundColor Green
