# test_launch_qdrant_startup.ps1 -- Docker Desktop discovery and Qdrant readiness contract
$ErrorActionPreference = "Stop"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw $Message
    }
}

$launch = Get-Content -LiteralPath (Join-Path $PSScriptRoot "launch.ps1") -Raw -Encoding UTF8

Assert-True ($launch -match '\$env:LOCALAPPDATA\\Programs\\DockerDesktop\\Docker Desktop\.exe') "launch.ps1 should discover per-user Docker Desktop installs"
Assert-True ($launch -match 'Get-Command\s+docker') "launch.ps1 should use docker.exe location as a fallback discovery source"
Assert-True ($launch -match 'function\s+Wait-QdrantReady') "launch.ps1 should wait for Qdrant API readiness, not only port 6333"
Assert-True ($launch -match 'http://localhost:6333/collections') "launch.ps1 should poll Qdrant /collections readiness"
Assert-True ($launch -notmatch 'docker start \$cId \| Out-Null\s*\r?\n\s*Start-Sleep -Seconds 3') "launch.ps1 should not rely on a fixed 3s sleep after docker start"
Assert-True ($launch -match 'TimeoutSec 5') "launch.ps1 should use bounded Qdrant readiness HTTP checks"

Write-Host "[OK] launch Qdrant startup contract tests passed" -ForegroundColor Green
exit 0
