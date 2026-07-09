# task_service.ps1 -- DEV_CORE v10 -- Task Service adapter
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Path", "Read", "Add", "Next")]
    [string]$Action,
    [string]$Title = "",
    [ValidateSet("reasoning", "coding", "bulk")]
    [string]$Mode = "coding",
    [string]$DependsOn = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }

function Get-TaskServiceProject {
    $currentPath = (Get-Location).Path
    if ($env:DEVCORE_ACTIVE_PROJECT_NAME -and $env:DEVCORE_ACTIVE_PROJECT_PWD -eq $currentPath) {
        return $env:DEVCORE_ACTIVE_PROJECT_NAME
    }

    $projectScript = Join-Path $PSScriptRoot "Get-ActiveProject.ps1"
    if (Test-Path -LiteralPath $projectScript) {
        return ((& $projectScript) | Select-Object -First 1).Trim()
    }
    return "devcore"
}

function Get-TaskBoardPath {
    $project = Get-TaskServiceProject
    return (Join-Path $DEV_CORE_DATA "Memory\$project\tasks.json")
}

function Initialize-TaskBoard {
    param([string]$Path)

    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if (-not (Test-Path -LiteralPath $Path)) {
        [pscustomobject]@{
            project = Get-TaskServiceProject
            current_task = $null
            tasks = @()
        } | ConvertTo-Json -Depth 5 | Set-Content $Path -Encoding UTF8
    }
}

function Read-TaskBoard {
    $path = Get-TaskBoardPath
    Initialize-TaskBoard -Path $path
    return Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-TaskBoard {
    param($Board)

    $path = Get-TaskBoardPath
    $Board | ConvertTo-Json -Depth 10 | Set-Content $path -Encoding UTF8
}

function Add-Task {
    param(
        [Parameter(Mandatory=$true)][string]$TaskTitle,
        [Parameter(Mandatory=$true)][string]$TaskMode,
        [string]$TaskDependsOn = ""
    )

    if ([string]::IsNullOrWhiteSpace($TaskTitle)) {
        Write-Host "  Task Service: titre requis" -ForegroundColor Red
        exit 64
    }

    $requestedWorktree = $env:DEVCORE_ACTIVE_WORKTREE_NAME
    $board = Read-TaskBoard
    $nums = $board.tasks | Where-Object { $_.id -match "^T-(\d+)$" } |
        ForEach-Object { [int]($_.id -replace "T-", "") }
    $next = if ($nums) { [int](($nums | Measure-Object -Maximum).Maximum) + 1 } else { 1 }
    $id = "T-{0:D2}" -f $next

    $task = [pscustomobject]@{
        id = $id
        title = $TaskTitle
        mode = $TaskMode
        status = "todo"
        steps_total = 1
        steps_done = 0
        depends_on = if ($TaskDependsOn) { "T-$TaskDependsOn" } else { $null }
        worktree = if ($requestedWorktree) { $requestedWorktree } elseif ($env:DEVCORE_ACTIVE_WORKTREE_NAME) { $env:DEVCORE_ACTIVE_WORKTREE_NAME } else { "main" }
    }

    $board.tasks += $task
    Write-TaskBoard -Board $board
    return $task
}

function Get-NextTask {
    $board = Read-TaskBoard
    $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

    if (-not $current) {
        $doneIds = ($board.tasks | Where-Object { $_.status -eq "done" }).id
        $current = $board.tasks | Where-Object {
            $_.status -eq "todo" -and (
                -not $_.depends_on -or $doneIds -contains $_.depends_on
            )
        } | Select-Object -First 1
    }

    if (-not $current) {
        return $null
    }

    if ($current.status -eq "todo") {
        $current.status = "active"
        $current | Add-Member -NotePropertyName "started_at" -NotePropertyValue (Get-Date -Format "o") -Force
        $board.current_task = $current.id
        Write-TaskBoard -Board $board
    }

    return $current
}

switch ($Action) {
    "Path" {
        $boardPath = Get-TaskBoardPath
        Write-Output $boardPath
        exit 0
    }
    "Read" {
        $board = Read-TaskBoard
        if ($Json) { $board | ConvertTo-Json -Depth 10 }
        else { Write-Output $board }
        exit 0
    }
    "Add" {
        $task = Add-Task -TaskTitle $Title -TaskMode $Mode -TaskDependsOn $DependsOn
        if ($Json) {
            $task | ConvertTo-Json -Depth 5
        } else {
            Write-Host "  [OK] Tache ajoutee : $($task.id) [$Mode] -- $Title" -ForegroundColor Green
        }
        exit 0
    }
    "Next" {
        $task = Get-NextTask
        if ($Json) {
            if ($task) { $task | ConvertTo-Json -Depth 5 }
            else { "null" }
        } elseif ($task) {
            Write-Host "  [OK] Tache active : $($task.id) [$($task.mode)] -- $($task.title)" -ForegroundColor Green
        } else {
            Write-Host "  Aucune tache disponible." -ForegroundColor Yellow
        }
        exit 0
    }
}
