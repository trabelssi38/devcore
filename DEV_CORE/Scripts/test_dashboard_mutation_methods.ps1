# test_dashboard_mutation_methods.ps1 -- Dashboard API mutation methods contract
$ErrorActionPreference = "Stop"

$dashboardApiPath = Join-Path $PSScriptRoot "dashboard_api.py"
$templatePath = Join-Path (Split-Path -Parent $PSScriptRoot) "Dashboard\template.html"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$apiSource = Get-Content -LiteralPath $dashboardApiPath -Raw -Encoding UTF8
$templateSource = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8
$getHandlerSource = ($apiSource -split '    def do_POST')[0]

Assert-True ($apiSource -match 'def do_DELETE') "dashboard_api.py should implement DELETE handlers"
Assert-True ($apiSource -match 'if path == "/api/done"') "dashboard_api.py should keep /api/done route"
Assert-True ($apiSource -match 'if path == "/api/delete"') "dashboard_api.py should keep /api/delete route"
Assert-True ($getHandlerSource -notmatch 'complete_task') "/api/done must not mutate from GET"
Assert-True ($getHandlerSource -notmatch 'delete_task') "/api/delete must not mutate from GET"

Assert-True ($templateSource -match 'apiFetch') "template should use apiFetch wrapper"
Assert-True ($templateSource -match 'apiFetch\(`\$\{API_BASE\}/api/done') "completeTask should call /api/done"
Assert-True ($templateSource -match "method:\s*'POST'") "completeTask should use POST"
Assert-True ($templateSource -match 'apiFetch\(`\$\{API_BASE\}/api/delete') "deleteTask should call /api/delete"
Assert-True ($templateSource -match "method:\s*'DELETE'") "deleteTask should use DELETE"
Assert-True ($templateSource -notmatch '/api/done\?project=') "template must not call /api/done as query-string GET"
Assert-True ($templateSource -notmatch '/api/delete\?project=') "template must not call /api/delete as query-string GET"

Write-Host "[OK] dashboard mutation method contract tests passed" -ForegroundColor Green
