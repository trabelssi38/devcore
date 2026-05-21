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

Write-Host "  [1/6] Sync Qdrant..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\qdrant_sync.ps1"

Write-Host "  [2/6] Sync Obsidian..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\obsidian_sync.ps1"

Write-Host "  [3/6] Generation metrics..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\gen_metrics.ps1"

Write-Host "  [4/6] Task scan..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\task_scan.ps1"

Write-Host "  [5/6] Task sync + Dashboard..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\task_sync.ps1"

Write-Host "  [6/6] Endday check..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\endday_check.ps1" 2>$null

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  Session end complete               ||" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""

