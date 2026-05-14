# session_end.ps1 -- DEV_CORE v6.1
# Execute a la fin de session Claude Code
# 1. Sync Qdrant
# 2. Sync Obsidian
# 3. Genere metrics

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$TODAY = Get-Date -Format "yyyy-MM-dd"

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Session End" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host "  Date: $TODAY" -ForegroundColor White
Write-Host ""

Write-Host "  [1/3] Sync Qdrant..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\qdrant_sync.ps1" 2>$null

Write-Host "  [2/3] Sync Obsidian..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\obsidian_sync.ps1" 2>$null

Write-Host "  [3/3] Generation metrics..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\gen_metrics.ps1" 2>$null

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  Session end complete               ||" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
