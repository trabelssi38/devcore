# test_runtime_state_contract.ps1 -- secrets/config/runtime separation contract
$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

$adaptClient = Get-Content -LiteralPath (Join-Path $PSScriptRoot "adapt_client.ps1") -Raw
$launch = Get-Content -LiteralPath (Join-Path $PSScriptRoot "launch.ps1") -Raw
$obsidianSync = Get-Content -LiteralPath (Join-Path $PSScriptRoot "Auto\obsidian_sync.ps1") -Raw
$pathsDoc = Get-Content -LiteralPath (Join-Path $PSScriptRoot "..\Config\PATHS.md") -Raw

Assert-True ($adaptClient -match '\$DEV_CORE_DATA\\Runtime') "adapt_client should use DEV_CORE_DATA\\Runtime for active client state"
Assert-True ($adaptClient -notmatch '\$ACTIVE_FILE\s*=\s*"\$CONFIG_DIR\\active_client\.txt"') "adapt_client should not write active_client under Config"
Assert-True ($launch -match 'DEV_CORE_DATA.*Runtime.*active_client\.txt') "launch should read active_client from runtime state"
Assert-True ($obsidianSync -match 'DEV_CORE_DATA.*Runtime.*active_client\.txt') "obsidian sync should read active_client from runtime state"
Assert-True ($pathsDoc -match 'ACTIVE_CLIENT\s+=\s+C:\\devcore\\DEV_CORE_DATA\\Runtime\\active_client\.txt') "PATHS.md should document runtime active client path"

Write-Host "[OK] runtime state contract tests passed" -ForegroundColor Green
exit 0
