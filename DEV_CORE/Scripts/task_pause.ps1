# task_pause.ps1 -- DEV_CORE v6 single client
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"

if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Red; exit 1 }

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $current) { Write-Host "  Aucune tache active a mettre en pause." -ForegroundColor Yellow; exit 0 }

# On passe le statut a paused (ou todo si on veut qu'elle soit reprise de suite)
$current.status = "paused"
$current | Add-Member -NotePropertyName "paused_at" -NotePropertyValue (Get-Date -Format "o") -Force

$board.current_task = $null

$board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8

Write-Host "  [OK] Tache $($current.id) mise en pause -- dc next task pour reprendre" -ForegroundColor Green
