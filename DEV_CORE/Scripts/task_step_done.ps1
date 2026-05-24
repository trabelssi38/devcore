# task_step_done.ps1 -- DEV_CORE v7.3 -- Marquer une step individuelle
# Usage : dc step done [N]  ou  dc sd [N]
# Si N=0 ou absent, marque la prochaine step non-faite
param([int]$StepNumber = 0)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$tFile         = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Red; exit 1 }

$board   = Get-Content $tFile -Raw | ConvertFrom-Json
$current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $current) { Write-Host "  Aucune tache active." -ForegroundColor Yellow; exit 0 }

# Verifier que la tache a des steps detaillees
if (-not $current.steps -or $current.steps.Count -eq 0) {
    # Pas de steps detaillees : incrementer steps_done directement
    $current.steps_done = [math]::Min($current.steps_done + 1, $current.steps_total)
    Write-Host "  [OK] Step $($current.steps_done)/$($current.steps_total) pour $($current.id)" -ForegroundColor Green
} else {
    # Trouver la step cible
    if ($StepNumber -eq 0) {
        $step = $current.steps | Where-Object { -not $_.done } | Select-Object -First 1
    } else {
        $step = $current.steps | Where-Object { $_.id -eq $StepNumber } | Select-Object -First 1
    }

    if (-not $step) {
        Write-Host "  Toutes les steps sont deja terminees." -ForegroundColor Yellow
    } else {
        $step.done = $true
        $current.steps_done = @($current.steps | Where-Object { $_.done }).Count
        Write-Host "  [OK] Step $($step.id) done : $($step.title)" -ForegroundColor Green
        Write-Host "  Progress : $($current.steps_done)/$($current.steps_total)" -ForegroundColor Cyan
    }
}

# Auto-backup avant ecriture
$bkpDir = "$DEV_CORE_DATA\Backups\auto"
if (-not (Test-Path $bkpDir)) { New-Item -ItemType Directory -Path $bkpDir -Force | Out-Null }
Copy-Item $tFile "$bkpDir\tasks_$(Get-Date -f 'yyyyMMdd_HHmmss').json" -Force -ErrorAction SilentlyContinue

$board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

# Auto-complete si toutes les steps sont faites
if ($current.steps_done -ge $current.steps_total) {
    Write-Host "  [AUTO] Toutes les steps terminees ! Validation automatique..." -ForegroundColor Cyan
    & "$DEV_CORE\Scripts\task_done.ps1" -Force
}


& "$PSScriptRoot\gen_dashboard.ps1"
