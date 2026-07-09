# test_gateway.ps1 -- smoke tests for DEV_CORE command gateway
$ErrorActionPreference = "Stop"

$gatewayScript = Join-Path $PSScriptRoot "gateway.ps1"
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

function Assert-Match {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Message
    )

    if ($Text -notmatch $Pattern) {
        throw $Message
    }
}

if (-not (Test-Path -LiteralPath $gatewayScript)) {
    throw "gateway.ps1 should exist"
}

$listJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gatewayScript -List -Json
$commands = $listJson | ConvertFrom-Json
Assert-Match (($commands.commands.command) -join "|") "^check\|check --fix\|check --gate" "gateway should expose diagnostic command registry"

$healthJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gatewayScript -Command "health --json" | Out-String
$health = $healthJson | ConvertFrom-Json
if (-not $health.overall) {
    throw "gateway health --json should return health report JSON"
}

$dryRunOutput = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gatewayScript -Command "check --fix --dry-run" | Out-String
Assert-Match $dryRunOutput "MODE DRY-RUN ACTIVE" "gateway should dispatch dry-run diagnose"

$dcDryRunOutput = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript "check --fix --dry-run" | Out-String
Assert-Match $dcDryRunOutput "MODE DRY-RUN ACTIVE" "dc should route diagnostic commands through gateway"

Assert-ExitCode 64 {
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gatewayScript -Command "check --unknown"
} "gateway should reject unknown command variants"

Write-Host "[OK] gateway smoke tests passed" -ForegroundColor Green
