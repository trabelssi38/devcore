# test_routing_profile.ps1 -- routing profile contract tests
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\routing_profile.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) { throw $Message }
}

$coding = Resolve-DevCoreRoutingProfile -Mode "coding"
Assert-True ($coding.mode -eq "coding") "coding should resolve to coding"
Assert-True ($coding.budget -eq "8k tokens") "coding should keep 8k budget"
Assert-True ($coding.model -eq "devcore-coding") "coding should expose devcore-coding model profile"
Assert-True ($coding.gemini_model -eq "gemini-2.5-pro") "coding should target Gemini Pro"

$bulk = Resolve-DevCoreRoutingProfile -Mode "bulk"
Assert-True ($bulk.mode -eq "bulk") "bulk should resolve to bulk"
Assert-True ($bulk.gemini_model -eq "gemini-2.5-flash") "bulk should target Gemini Flash"

$plan = Resolve-DevCoreRoutingProfile -Mode "plan"
Assert-True ($plan.requested_mode -eq "plan") "alias should keep requested mode"
Assert-True ($plan.mode -eq "reasoning") "plan should alias to reasoning"
Assert-True ($plan.model -eq "devcore-reasoning") "plan alias should expose reasoning model profile"

$unknown = Resolve-DevCoreRoutingProfile -Mode "unknown"
Assert-True ($unknown.mode -eq "coding") "unknown mode should fallback to default coding"

Write-Host "[OK] routing profile unit tests passed" -ForegroundColor Green
