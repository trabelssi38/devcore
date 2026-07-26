# task_scan.ps1 -- DEV_CORE -- Lance les 3 scanners et affiche les suggestions
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$AUTO          = "$DEV_CORE\Scripts\Auto"
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

Write-Host ""
Write-Host "  $($PLATFORM.title) -- TASK SCAN" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

Write-Host "  [1/3] Git scanner..." -ForegroundColor Cyan
& "$AUTO\task_git_scanner.ps1"
Write-Host ""

Write-Host "  [2/3] Spec parser..." -ForegroundColor Cyan
& "$AUTO\task_spec_parser.ps1"
Write-Host ""

Write-Host "  [3/3] Prompt analyzer..." -ForegroundColor Cyan
& "$AUTO\task_prompt_analyzer.ps1"
Write-Host ""

Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Scan termine" -ForegroundColor Green
Write-Host "  dc task sync pour integrer les suggestions" -ForegroundColor Cyan
Write-Host ""
