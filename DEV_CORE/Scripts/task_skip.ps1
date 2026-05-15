# task_skip.ps1 -- DEV_CORE v6 single client
param([string]$Reason="")

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"

if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Red; exit 1 }

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $current) { Write-Host "  Aucune tache active a passer." -ForegroundColor Yellow; exit 0 }

if (-not $Reason) {
    $Reason = Read-Host "  Raison du skip (optionnel)"
}

$current.status = "skipped"
$current | Add-Member -NotePropertyName "skipped_at" -NotePropertyValue (Get-Date -Format "o") -Force
if ($Reason) {
    $current | Add-Member -NotePropertyName "skipped_reason" -NotePropertyValue $Reason -Force
}

$board.current_task = $null
$board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

Write-Host "  [OK] Tache $($current.id) passee (skipped)." -ForegroundColor Green
& "$DEV_CORE\Scripts\task_next.ps1"
