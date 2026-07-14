# test_guided_recovery.ps1 -- guided onboarding/diagnostic/recovery contract
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "guided_recovery.ps1"
$playbookPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Config\guided_recovery.json"
$gatewayScript = Join-Path $PSScriptRoot "gateway.ps1"
$dcScript = Join-Path $PSScriptRoot "dc.ps1"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $scriptPath) "guided_recovery.ps1 should exist"
Assert-True (Test-Path -LiteralPath $playbookPath) "guided_recovery.json should exist"

$playbook = Get-Content -LiteralPath $playbookPath -Raw -Encoding UTF8 | ConvertFrom-Json
Assert-True ($playbook.schema_version -eq 1) "Playbook schema_version should be 1"
Assert-True ($playbook.playbook_version -match "^\d{4}\.\d{2}\.\d{2}$") "Playbook should be date-versioned"
Assert-True (@($playbook.flows).Count -ge 3) "Playbook should define onboarding, diagnostic and recovery flows"

foreach ($flow in @($playbook.flows)) {
    Assert-True (-not [string]::IsNullOrWhiteSpace($flow.id)) "Flow should declare id"
    Assert-True (@("onboarding", "diagnostic", "recovery") -contains $flow.type) "Flow type should be guided"
    Assert-True (@($flow.steps).Count -gt 0) "Flow should declare steps"
    foreach ($step in @($flow.steps)) {
        Assert-True (-not [string]::IsNullOrWhiteSpace($step.id)) "Step should declare id"
        Assert-True (-not [string]::IsNullOrWhiteSpace($step.command)) "Step should declare command"
        Assert-True (-not [string]::IsNullOrWhiteSpace($step.recovery_hint)) "Step should declare recovery hint"
    }
}

$json = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath -Flow onboarding -Json | Out-String
$result = $json | ConvertFrom-Json
Assert-True ($result.ok -eq $true) "Guided recovery JSON should report ok"
Assert-True ($result.flow.id -eq "first-run") "Onboarding flow should resolve first-run"
Assert-True (@($result.flow.steps).Count -gt 0) "Onboarding flow should include steps"

$listJson = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath -List -Json | Out-String
$list = $listJson | ConvertFrom-Json
Assert-True (@($list.flows).Count -ge 3) "List should expose all guided flows"

$gatewayJson = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gatewayScript -List -Json | Out-String
$gateway = $gatewayJson | ConvertFrom-Json
Assert-True (($gateway.commands.command -join "|") -match "guide onboarding") "Gateway should expose guide onboarding"
Assert-True (($gateway.commands.command -join "|") -match "guide recovery") "Gateway should expose guide recovery"

$dcOutput = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript "guide onboarding --json" | Out-String
$dcResult = $dcOutput | ConvertFrom-Json
Assert-True ($dcResult.flow.type -eq "onboarding") "dc guide onboarding should dispatch guided recovery JSON"

Write-Host "[OK] guided recovery contract tests passed" -ForegroundColor Green
