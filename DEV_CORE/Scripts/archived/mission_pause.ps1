# mission_pause.ps1 — DEV_CORE v6
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\DEV_CORE_DATA" }
$mFile = "$DEV_CORE_DATA\Memory\missions.json"
$board = Get-Content $mFile -Raw | ConvertFrom-Json
$current = $board.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1
if (-not $current) { Write-Host "  Aucune mission active." -ForegroundColor Yellow; exit 0 }
$current.status = "paused"
$board | ConvertTo-Json -Depth 10 | Set-Content $mFile -Encoding UTF8
Write-Host "  ⏸ Mission $($current.id) mise en pause." -ForegroundColor Yellow
Write-Host "  Reprendre : dc next mission" -ForegroundColor DarkGray
