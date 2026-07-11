# test_repowise_watch_worker.ps1 -- smoke checks for Repowise watcher docs refresh
$ErrorActionPreference = "Stop"

$worker = Join-Path $PSScriptRoot "repowise_watch_worker.ps1"
$content = Get-Content -LiteralPath $worker -Raw -Encoding UTF8

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

[scriptblock]::Create($content) | Out-Null

Assert-True ($content -match "function Invoke-RepowiseDocsRefresh") "worker should define docs refresh function"
Assert-True ($content -match "function Import-GeminiKeyForDocsRefresh") "worker should load Gemini key files for docs refresh"
Assert-True ($content -match "Config\\gemini_api_key.txt") "worker should use DEV_CORE Config gemini_api_key.txt fallback"
Assert-True ($content -match "update --index-only --no-docs --no-workspace") "worker should keep lightweight index-only update"
Assert-True ($content -match '@\("update", "--docs", "--no-workspace"\)') "worker should force a docs-capable update"
Assert-True ($content -match '@\("update", "--full", "--docs", "--no-workspace"\)') "worker should use full backfill when wiki docs are empty"
Assert-True ($content -match "last_docs_commit") "worker should persist last docs commit"
Assert-True ($content -match "REPOWISE_DOCS_REFRESH_MINUTES") "worker should expose docs refresh throttle"
Assert-True ($content -match "provider_missing") "worker should avoid blocking docs refresh when no non-interactive provider is configured"
Assert-True ($content -match "docs_disabled_or_empty") "worker should retry docs refresh when Repowise state has no wiki pages"

$docsRefreshLine = ($content -split "`n" | Where-Object { $_ -match "RepowisePath @docsArgs" } | Select-Object -First 1)
Assert-True (-not [string]::IsNullOrWhiteSpace($docsRefreshLine)) "docs refresh should execute computed docs args"

Write-Host "[OK] repowise watch worker smoke tests passed"
