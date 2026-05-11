# mission_status.ps1 — DEV_CORE v6
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\DEV_CORE_DATA" }
$mFile = "$DEV_CORE_DATA\Memory\missions.json"
if (-not (Test-Path $mFile)) { Write-Host "  Aucun missions.json — dc new mission 'titre'" -ForegroundColor Yellow; exit 0 }
$board = Get-Content $mFile -Raw | ConvertFrom-Json
$done  = ($board.missions | Where-Object { $_.status -eq "done" }).Count
$total = $board.missions.Count
$pct   = if ($total -gt 0) { [math]::Round(($done/$total)*100) } else { 0 }
$bar   = "█" * [math]::Round($pct/5) + "░" * (20-[math]::Round($pct/5))

Write-Host ""; Write-Host "  DEV_CORE v6 — Mission Board" -ForegroundColor Cyan
Write-Host "  Projet : $($board.project) | $(Get-Date -f 'yyyy-MM-dd HH:mm')" -ForegroundColor DarkGray
Write-Host "  ──────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ("  {0,-6} {1,-13} {2,-10} {3}" -f "ID","Agent","Status","Titre") -ForegroundColor DarkGray
Write-Host "  ──────────────────────────────────────────────────────" -ForegroundColor DarkGray
foreach ($m in $board.missions) {
    $icon  = switch($m.status){"done"{"✓ Done  "};"active"{"⚡ Active"};"todo"{"○ Todo  "};"paused"{"⏸ Paused"};default{$m.status}}
    $color = switch($m.status){"done"{"Green"};"active"{"Cyan"};"todo"{"Gray"};"paused"{"Yellow"};default{"Gray"}}
    $steps = if ($m.PSObject.Properties["steps_total"] -and $m.steps_total -gt 1) { " [$($m.steps_done)/$($m.steps_total)]" } else { "" }
    $title = "$($m.title)$steps"; if ($title.Length -gt 34) { $title = $title.Substring(0,31)+"..." }
    $pre   = if ($m.id -eq $board.current_mission) { "► " } else { "  " }
    Write-Host ("$pre{0,-6} {1,-13} " -f $m.id,$m.agent) -NoNewline -ForegroundColor White
    Write-Host ("{0,-10} " -f $icon) -NoNewline -ForegroundColor $color
    Write-Host $title -ForegroundColor White
}
Write-Host "  ──────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  [$bar] $pct% ($done/$total done) | Client: $($board.active_client)" -ForegroundColor Cyan
Write-Host ""
