# task_list.ps1 -- DEV_CORE v6 single client
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json." -ForegroundColor Yellow; exit 0 }

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$todos = $board.tasks | Where-Object { $_.status -in @("todo","active","paused") }

Write-Host ""
Write-Host "  DEV_CORE v6 -- Backlog (todo)" -ForegroundColor Cyan
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ("  {0,-6} {1,-12} {2,-10} {3}" -f "ID","Mode","Status","Titre") -ForegroundColor DarkGray
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray

foreach ($t in $todos) {
    $icon  = switch ($t.status) { "active"{"[active]"}; "paused"{"[paused]"}; default{"[todo]  "} }
    $color = switch ($t.status) { "active"{"Cyan"}; "paused"{"Yellow"}; default{"Gray"} }
    $title = $t.title
    if ($title.Length -gt 40) { $title = $title.Substring(0,37) + "..." }
    $pre   = if ($t.id -eq $board.current_task) { ">" } else { " " }
    Write-Host ("$pre {0,-6} {1,-12} " -f $t.id, $t.mode) -NoNewline -ForegroundColor White
    Write-Host ("{0,-10} " -f $icon) -NoNewline -ForegroundColor $color
    Write-Host $title -ForegroundColor White
}
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
