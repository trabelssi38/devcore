# task_step_done.ps1 -- DEV_CORE v9.0 -- Marquer une step individuelle
# Usage : dc step done [N]  ou  dc sd [N]
# Si N=0 ou absent, marque la prochaine step non-faite
param([int]$StepNumber = 0)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$tFile         = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Red; exit 1 }

$resultJson = & "$PSScriptRoot\task_service.ps1" -Action Step -StepNumber $StepNumber -Json
$result = if ($resultJson -and (($resultJson -join "`n").Trim()) -ne "null") {
    ($resultJson | Out-String) | ConvertFrom-Json
} else {
    $null
}

if (-not $result) { Write-Host "  Aucune tache active." -ForegroundColor Yellow; exit 0 }

Write-Host "  [OK] $($result.message)" -ForegroundColor Green
Write-Host "  Progress : $($result.task.steps_done)/$($result.task.steps_total)" -ForegroundColor Cyan

# Auto-backup avant ecriture
$bkpDir = "$DEV_CORE_DATA\Backups\auto"
if (-not (Test-Path $bkpDir)) { New-Item -ItemType Directory -Path $bkpDir -Force | Out-Null }
Copy-Item $tFile "$bkpDir\tasks_$(Get-Date -f 'yyyyMMdd_HHmmss').json" -Force -ErrorAction SilentlyContinue

# Auto-complete si toutes les steps sont faites
if ($result.complete) {
    Write-Host "  [AUTO] Toutes les steps terminees ! Validation automatique..." -ForegroundColor Cyan
    & "$DEV_CORE\Scripts\task_done.ps1" -Force
}


& "$PSScriptRoot\gen_dashboard.ps1"
