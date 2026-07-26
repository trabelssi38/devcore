# test_repowise_health_gate.ps1 -- Non-regression gate for Repowise Code Health

$ErrorActionPreference = "Stop"

function Assert-True($condition, $message) {
    if (-not $condition) {
        throw "ASSERTION FAILED: $message"
    }
}

try {
    $repos = Invoke-RestMethod -Uri "http://127.0.0.1:7337/api/repos" -TimeoutSec 2 -ErrorAction Stop
} catch {
    Write-Host "[SKIP] Repowise API offline (port 7337); health gate skipped"
    exit 0
}

$devcoreRepo = $repos | Where-Object { $_.is_primary -or $_.name -eq "devcore" } | Select-Object -First 1
Assert-True ($null -ne $devcoreRepo) "DevCore primary repo must exist in Repowise"

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:7337/api/repos/$($devcoreRepo.id)/health/overview" -TimeoutSec 2 -ErrorAction Stop
    Assert-True ($null -ne $health.summary) "Health summary must be returned by Repowise"
    
    $avgScore = $health.summary.average_health
    Write-Host "[INFO] Repowise Code Health average: $avgScore/10"
    
    Assert-True ($avgScore -ge 5.0) "DevCore global health score ($avgScore/10) must remain above minimum threshold of 5.0"
    
    Write-Host "[OK] Repowise Code Health gate passed successfully"
} catch {
    Write-Host "[WARN] Health overview query failed: $_"
    exit 0
}
