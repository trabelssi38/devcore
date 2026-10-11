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

foreach ($mode in @('coding', 'reasoning', 'plan')) {
    $native = Resolve-DevCoreRoutingProfile -Mode $mode
    Assert-True ($native.route -eq 'native') "$mode must remain native"
    Assert-True (-not $native.model -and -not $native.gemini_model) "$mode cannot replace the application model"
    Assert-True ($native.preserve_requested_model) "$mode must preserve its model"
    Assert-True ($native.endpoint -eq 'http://127.0.0.1:8787/v1') 'Native endpoint required'
}
$bulk = Resolve-DevCoreRoutingProfile -Mode 'bulk'
Assert-True ($bulk.route -eq 'auxiliary' -and $bulk.model -eq 'devcore-bulk') 'Bulk is explicitly auxiliary'
Assert-True ($bulk.endpoint -eq 'http://127.0.0.1:8789/v1') 'Auxiliary endpoint required'
$refused = $false
try { Resolve-DevCoreRoutingProfile -Mode 'unknown' | Out-Null } catch { $refused = $true }
Assert-True $refused 'Unknown mode must be refused'
Write-Output '[OK] Native/auxiliary PowerShell routing profiles'
