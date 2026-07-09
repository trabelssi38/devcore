# test_task_service.ps1 -- smoke tests for DEV_CORE Task Service
$ErrorActionPreference = "Stop"

$taskServiceScript = Join-Path $PSScriptRoot "task_service.ps1"
$taskAddScript = Join-Path $PSScriptRoot "task_add.ps1"
$taskEditScript = Join-Path $PSScriptRoot "task_edit.ps1"
$taskPauseScript = Join-Path $PSScriptRoot "task_pause.ps1"
$taskSkipScript = Join-Path $PSScriptRoot "task_skip.ps1"

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
$oldSkipDashboard = $env:DEVCORE_SKIP_DASHBOARD

try {
    $env:DEVCORE_DATA_ROOT = $tempRoot
    $env:DEVCORE_ACTIVE_WORKTREE_NAME = "service-test"
    $env:DEVCORE_SKIP_DASHBOARD = "1"

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

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Add -Title "Blocked Task" -Mode coding -DependsOn "99" | Out-Null
    $nextJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Next -Json | Out-String
    $next = $nextJson | ConvertFrom-Json
    Assert-True ($next.id -eq "T-01") "Task Service next should activate first eligible todo task"
    Assert-True ($next.status -eq "active") "Task Service next should return active task"

    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.current_task -eq "T-01") "Task Service next should update current_task"
    Assert-True ($board.tasks[0].status -eq "active") "Task Service next should persist active status"
    Assert-True ($board.tasks[2].status -eq "todo") "Task Service next should not activate blocked dependencies"

    $completeJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Complete -Force -Json | Out-String
    $completed = $completeJson | ConvertFrom-Json
    Assert-True ($completed.completed.id -eq "T-01") "Task Service complete should return completed task"
    Assert-True ($completed.next.id -eq "T-02") "Task Service complete should return next eligible task"

    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.tasks[0].status -eq "done") "Task Service complete should persist done status"
    Assert-True ($board.tasks[0].steps_done -eq $board.tasks[0].steps_total) "Task Service complete -Force should correct incomplete steps"
    Assert-True (-not [string]::IsNullOrWhiteSpace([string]$board.tasks[0].completed_at)) "Task Service complete should set completed_at"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Next -Json | Out-Null
    $stepJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Step -Json | Out-String
    $stepResult = $stepJson | ConvertFrom-Json
    Assert-True ($stepResult.task.id -eq "T-02") "Task Service step should return active task"
    Assert-True ($stepResult.task.steps_done -eq 1) "Task Service step should increment steps_done"
    Assert-True ($stepResult.complete -eq $true) "Task Service step should report complete when steps_done reaches total"

    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.tasks[1].steps_done -eq 1) "Task Service step should persist progress"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Edit -Id "T-02" -Title "Edited Service Task" -Mode reasoning -Steps 3 | Out-Null
    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.tasks[1].title -eq "Edited Service Task") "Task Service edit should update title"
    Assert-True ($board.tasks[1].mode -eq "reasoning") "Task Service edit should update mode"
    Assert-True ($board.tasks[1].steps_total -eq 3) "Task Service edit should update steps_total"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskEditScript -Id "T-02" -Mode bulk -Steps 4 | Out-Null
    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.tasks[1].mode -eq "bulk") "task_edit adapter should delegate mode update to Task Service"
    Assert-True ($board.tasks[1].steps_total -eq 4) "task_edit adapter should delegate steps update to Task Service"

    $pauseJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Pause -Json | Out-String
    $pauseResult = $pauseJson | ConvertFrom-Json
    Assert-True ($pauseResult.task.id -eq "T-02") "Task Service pause should return paused task"
    Assert-True ($pauseResult.task.status -eq "paused") "Task Service pause should update status"

    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.current_task -eq $null) "Task Service pause should clear current_task"
    Assert-True (-not [string]::IsNullOrWhiteSpace([string]$board.tasks[1].paused_at)) "Task Service pause should set paused_at"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Add -Title "Skip Service Task" -Mode coding | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Next -Json | Out-Null
    $skipJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Skip -Reason "not needed" -Json | Out-String
    $skipResult = $skipJson | ConvertFrom-Json
    Assert-True ($skipResult.task.status -eq "skipped") "Task Service skip should update status"
    Assert-True ($skipResult.task.skipped_reason -eq "not needed") "Task Service skip should preserve reason"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Add -Title "Pause Adapter Task" -Mode coding | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Next -Json | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskPauseScript | Out-Null
    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.tasks[4].status -eq "paused") "task_pause adapter should delegate to Task Service"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Add -Title "Skip Adapter Task" -Mode coding | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskServiceScript -Action Next -Json | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskSkipScript -Reason "adapter skip" | Out-Null
    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($board.tasks[5].status -eq "skipped") "task_skip adapter should delegate to Task Service"
    Assert-True ($board.tasks[5].skipped_reason -eq "adapter skip") "task_skip adapter should preserve reason"

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

    if ($null -eq $oldSkipDashboard) {
        Remove-Item Env:\DEVCORE_SKIP_DASHBOARD -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_SKIP_DASHBOARD = $oldSkipDashboard
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
