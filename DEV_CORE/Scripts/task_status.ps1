# task_status.ps1 -- DEV_CORE single client
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (-not (Test-Path $tFile)) { Write-Host "  Aucun tasks.json -- dc new task 'titre'" -ForegroundColor Yellow; exit 0 }

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$done  = ($board.tasks | Where-Object { $_.status -eq "done" }).Count
$total = $board.tasks.Count
$pct   = if ($total -gt 0) { [math]::Round(($done/$total)*100) } else { 0 }
$bar   = "#" * [math]::Round($pct/5) + "-" * (20 - [math]::Round($pct/5))

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Task Board" -ForegroundColor Cyan
Write-Host "  Projet : $($board.project) | $(Get-Date -f 'yyyy-MM-dd HH:mm')" -ForegroundColor DarkGray
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ("  {0,-6} {1,-12} {2,-10} {3}" -f "ID","Mode","Status","Titre") -ForegroundColor DarkGray
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray

foreach ($t in $board.tasks) {
    $icon  = switch ($t.status) { "done"{"[done]  "}; "active"{"[active]"}; "todo"{"[todo]  "}; default{$t.status} }
    $color = switch ($t.status) { "done"{"Green"}; "active"{"Cyan"}; "todo"{"Gray"}; default{"Gray"} }
    $steps = if ($t.PSObject.Properties["steps_total"] -and $t.steps_total -gt 1) { " [$($t.steps_done)/$($t.steps_total)]" } else { "" }
    $wtTag = if ($t.PSObject.Properties["worktree"] -and $t.worktree -ne "main") { "[$($t.worktree)] " } else { "" }
    $title = "$wtTag$($t.title)$steps"
    if ($title.Length -gt 30) { $title = $title.Substring(0,27) + "..." }
    $pre   = if ($t.id -eq $board.current_task) { ">" } else { " " }
    Write-Host ("$pre {0,-6} {1,-12} " -f $t.id, $t.mode) -NoNewline -ForegroundColor White
    Write-Host ("{0,-10} " -f $icon) -NoNewline -ForegroundColor $color
    Write-Host $title -ForegroundColor White
}
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  [$bar] $pct% ($done/$total done)" -ForegroundColor Cyan
Write-Host ""

