# task_add.ps1 -- DEV_CORE v6 single client
param(
    [Parameter(Mandatory=$true)][string]$Title,
    [ValidateSet("reasoning","coding","bulk")][string]$Mode = "coding",
    [string]$DependsOn = ""
)
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) {
    @{ project="default"; current_task=$null; tasks=@() } |
        ConvertTo-Json -Depth 5 | Set-Content $tFile -Encoding UTF8
}

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$nums  = $board.tasks | Where-Object { $_.id -match "^T-(\d+)$" } |
         ForEach-Object { [int]($_.id -replace "T-","") }
$next  = if ($nums) { [int](($nums | Measure-Object -Maximum).Maximum) + 1 } else { 1 }
$id    = "T-{0:D2}" -f $next

$t = [PSCustomObject]@{
    id         = $id
    title      = $Title
    mode       = $Mode
    status     = "todo"
    steps_total= 1
    steps_done = 0
    depends_on = if ($DependsOn) { "T-$DependsOn" } else { $null }
    worktree   = if ($env:DEVCORE_ACTIVE_WORKTREE_NAME) { $env:DEVCORE_ACTIVE_WORKTREE_NAME } else { "main" }
}
$board.tasks += $t
$board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
Write-Host "  [OK] Tache ajoutee : $id [$Mode] -- $Title" -ForegroundColor Green


& "$PSScriptRoot\gen_dashboard.ps1"
