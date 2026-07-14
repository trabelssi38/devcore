# test_dashboard_cockpit_contract.ps1 -- cockpit project/status rendering contract
$ErrorActionPreference = "Stop"

$generatorPath = Join-Path $PSScriptRoot "gen_dashboard.ps1"
$templatePath = Join-Path (Split-Path -Parent $PSScriptRoot) "Dashboard\template.html"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$generator = Get-Content -LiteralPath $generatorPath -Raw -Encoding UTF8
$template = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8

Assert-True ($generator -match '\$ExcludedDashboardProjects\s*=\s*@\(') "gen_dashboard.ps1 should define excluded cockpit projects"
Assert-True ($generator -match '"scripts"') "gen_dashboard.ps1 should exclude internal scripts project from project cards"
Assert-True ($generator -match '\$ExcludedDashboardProjects\s+-contains\s+\$folder\.Name') "gen_dashboard.ps1 should skip excluded project folders"
Assert-True ($generator -match '\$ExcludedDashboardProjects\s+-notcontains\s+\$_.Name') "token project allocation should exclude internal projects"
Assert-True ($generator -match '\$ExcludedDashboardProjects\s+-notcontains\s+\$_.project') "token sessions should exclude internal projects"

Assert-True ($template -match '\.status-degraded-badge') "template should define compact degraded badge"
Assert-True ($generator -match '\$isDegraded\s*=\s*\(\$IsOk\s+-is\s+\[string\]\)\s+-and\s+\(\$IsOk\s+-eq\s+"degraded"\)') "degraded check should not coerce boolean true to degraded"
Assert-True ($generator -match 'status-degraded-badge') "gen_dashboard.ps1 should render degraded with compact badge class"
Assert-True ($generator -match 'aria-label="\$statusLabel"') "service status should expose accessible status label"
Assert-True ($generator -match 'model_costs\.unregistered') "gen_dashboard.ps1 should read unregistered model list"
Assert-True ($generator -match '\$topModelRows\s*=.*Select-Object -First 12') "gen_dashboard.ps1 should still cap the main model cost list"
Assert-True ($generator -match '\$fallbackModelRows\s*=') "gen_dashboard.ps1 should append fallback-priced models outside the top cost list"
Assert-True ($generator -match 'fallback') "gen_dashboard.ps1 should badge fallback-priced models"
Assert-True ($template -match 'getUnregisteredModels') "template should expose fallback-priced model metadata to live updates"
Assert-True ($template -match 'project_unregistered') "template should support project-level fallback-priced model updates"

Write-Host "[OK] dashboard cockpit contract tests passed" -ForegroundColor Green
