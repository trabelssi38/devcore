# test_task_service.ps1 -- smoke tests for DEV_CORE Task Service
$ErrorActionPreference = "Stop"

$taskServiceScript = Join-Path $PSScriptRoot "task_service.ps1"
$taskAddScript = Join-Path $PSScriptRoot "task_add.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

if (-not (Test-Path -LiteralPath $taskServiceScript)) {
    throw "task_service.ps1 should exist"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-task-service-" + [guid]::NewGuid().ToString("N"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$oldWorktree = $env:DEVCORE_ACTIVE_WORKTREE_NAME

try {
    $env:DEVCORE_DATA_ROOT = $tempRoot
    $env:DEVCORE_ACTIVE_WORKTREE_NAME = "service-test"

    $boardPath = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Path | Select-Object -First 1
    Assert-True ($boardPath -like (Join-Path $tempRoot "Memory\devcore\tasks.json")) "Task Service should resolve active project board path"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Add -Title "Service Task" -Mode coding | Out-Null
    Assert-True (Test-Path -LiteralPath $boardPath) "Task Service add should create tasks.json"

    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True (($board.tasks | Measure-Object).Count -eq 1) "Task Service add should create exactly one task"
    Assert-True ($board.tasks[0].id -eq "T-01") "Task Service add should allocate T-01"
    Assert-True ($board.tasks[0].title -eq "Service Task") "Task Service add should preserve title"
    Assert-True ($board.tasks[0].worktree -eq "service-test") "Task Service add should preserve worktree"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskAddScript -Title "Adapter Task" -Mode bulk | Out-Null
    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True (($board.tasks | Measure-Object).Count -eq 2) "task_add adapter should delegate to Task Service"
    Assert-True ($board.tasks[1].id -eq "T-02") "task_add adapter should allocate next task through service"
    Assert-True ($board.tasks[1].mode -eq "bulk") "task_add adapter should preserve mode"

    Write-Host "[OK] task service smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    if ($null -eq $oldWorktree) {
        Remove-Item Env:\DEVCORE_ACTIVE_WORKTREE_NAME -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_ACTIVE_WORKTREE_NAME = $oldWorktree
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
