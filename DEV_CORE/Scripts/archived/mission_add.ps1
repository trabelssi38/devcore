# mission_add.ps1 — DEV_CORE v6
param([Parameter(Mandatory=$true)][string]$Title, [string]$Agent="claude", [string]$DependsOn="")
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\DEV_CORE_DATA" }
$mFile = "$DEV_CORE_DATA\Memory\missions.json"
if (-not (Test-Path $mFile)) {
    @{ project="default"; current_mission=$null; active_client="claude"; missions=@() } | ConvertTo-Json -Depth 5 | Set-Content $mFile -Encoding UTF8
}
$board = Get-Content $mFile -Raw | ConvertFrom-Json
$nums  = $board.missions | Where-Object { $_.id -match "^M-(\d+)$" } | ForEach-Object { [int]($_.id -replace "M-","") }
$next  = if ($nums) { ($nums | Measure-Object -Maximum).Maximum + 1 } else { 1 }
$id    = "M-{0:D2}" -f $next
$m     = [PSCustomObject]@{ id=$id; title=$Title; agent=$Agent; status="todo"; steps_total=1; steps_done=0; depends_on=if($DependsOn){"M-$DependsOn"}else{$null} }
$board.missions += $m
$board | ConvertTo-Json -Depth 10 | Set-Content $mFile -Encoding UTF8
Write-Host "  ✓ Mission ajoutée : $id — $Title → $Agent" -ForegroundColor Green
