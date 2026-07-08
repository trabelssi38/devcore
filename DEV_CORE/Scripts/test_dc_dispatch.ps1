# test_dc_dispatch.ps1 -- smoke tests for dc.ps1 dispatch safety
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dcScript = Join-Path $PSScriptRoot "dc.ps1"
$dashboardIndex = Join-Path $repoRoot "Dashboard\index.html"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Invoke-DcSmoke {
    param([string]$Command)

    & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript $Command | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "dc command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-dc-dispatch-" + [guid]::NewGuid().ToString("N"))
$projectMemory = Join-Path $tempRoot "Memory\devcore"
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$oldWorktree = $env:DEVCORE_ACTIVE_WORKTREE_NAME
$dashboardBackup = $null
$hadDashboard = Test-Path $dashboardIndex

if ($hadDashboard) {
    $dashboardBackup = Get-Content $dashboardIndex -Raw -Encoding UTF8
}

try {
    New-Item -ItemType Directory -Force -Path $projectMemory | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $tempRoot "Logs\scripts") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $tempRoot "Logs\token_reports") | Out-Null

    @{
        project = "devcore"
        current_task = $null
        tasks = @()
    } | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $projectMemory "tasks.json") -Encoding UTF8

    $env:DEVCORE_DATA_ROOT = $tempRoot
    $env:DEVCORE_ACTIVE_WORKTREE_NAME = "test"

    Invoke-DcSmoke "new task Smoke Task -coding"

    $boardPath = Join-Path $projectMemory "tasks.json"
    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True (($board.tasks | Measure-Object).Count -eq 1) "new task with mode must create exactly one task"
    Assert-True ($board.tasks[0].mode -eq "coding") "new task mode should be coding"
    Assert-True ($board.tasks[0].title -eq "smoke task") "new task title should preserve existing dc lowercase behavior"

    Invoke-DcSmoke "task edit T-01 -Mode bulk -Steps 3"

    $board = Get-Content $boardPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True (($board.tasks | Measure-Object).Count -eq 1) "task edit must not create or duplicate tasks"
    Assert-True ($board.tasks[0].mode -eq "bulk") "task edit should update mode"
    Assert-True ([int]$board.tasks[0].steps_total -eq 3) "task edit should update steps_total"

    $dcSource = Get-Content $dcScript -Raw -Encoding UTF8
    Assert-True (-not ($dcSource -match "Invoke-Expression")) "dc.ps1 must not use Invoke-Expression"

    Write-Host "[OK] dc dispatch smoke tests passed" -ForegroundColor Green
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

    if ($hadDashboard) {
        $dashboardBackup | Set-Content $dashboardIndex -Encoding UTF8
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
