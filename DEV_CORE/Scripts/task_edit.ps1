# task_edit.ps1 -- DEV_CORE v6 single client
param(
    [Parameter(Mandatory=$true)][string]$Id,
    [string]$Title,
    [string]$Mode,
    [int]$Steps
)
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Red; exit 1 }

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$task = $board.tasks | Where-Object { $_.id -eq $Id } | Select-Object -First 1

if (-not $task) { Write-Host "  Tache $Id non trouvee." -ForegroundColor Red; exit 1 }

$updated = $false
if ($Title) { $task.title = $Title; $updated = $true }
if ($Mode)  { $task.mode = $Mode; $updated = $true }
if ($Steps) { $task.steps_total = $Steps; $updated = $true }

if ($updated) {
    $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
    Write-Host "  [OK] Tache $Id mise a jour." -ForegroundColor Green
} else {
    Write-Host "  Aucune modification specifiee. Exemple: dc task edit T-05 -Mode bulk -Steps 5" -ForegroundColor Yellow
}


