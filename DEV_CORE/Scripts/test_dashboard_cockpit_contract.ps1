# test_dashboard_cockpit_contract.ps1 -- cockpit project/status rendering contract
$ErrorActionPreference = "Stop"

$generatorPath = Join-Path $PSScriptRoot "gen_dashboard.py"
$templatePath = Join-Path (Split-Path -Parent $PSScriptRoot) "Dashboard\template.html"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$generator = Get-Content -LiteralPath $generatorPath -Raw -Encoding UTF8
$template = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8

Assert-True ($generator -match 'excluded_projects\s*=\s*\[') "gen_dashboard.py should define excluded cockpit projects"
Assert-True ($generator -match '"scripts"') "gen_dashboard.py should exclude internal scripts project from project cards"
Assert-True ($template -match '\.status-degraded-badge') "template should define compact degraded badge"
Assert-True ($generator -match 'model_costs') "gen_dashboard.py should read model costs"
Assert-True ($generator -match 'fallback') "gen_dashboard.py should badge fallback-priced models"

Write-Host "[OK] dashboard cockpit contract tests passed" -ForegroundColor Green
