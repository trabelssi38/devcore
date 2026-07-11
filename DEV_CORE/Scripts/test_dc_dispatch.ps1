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

function Invoke-DcJson {
    param([string]$Command)

    $output = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $dcScript $Command | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "dc command failed with exit code ${LASTEXITCODE}: $Command`n$output"
    }
    return ($output | ConvertFrom-Json)
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-dc-dispatch-" + [guid]::NewGuid().ToString("N"))
$projectMemory = Join-Path $tempRoot "Memory\devcore"
$packageRoot = Join-Path $tempRoot "packages\dispatcher-plugin"
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$oldPlatformRoot = $env:DEVCORE_PLATFORM_ROOT
$oldWorktree = $env:DEVCORE_ACTIVE_WORKTREE_NAME
$oldSkipDashboard = $env:DEVCORE_SKIP_DASHBOARD
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
    $env:DEVCORE_PLATFORM_ROOT = Join-Path $repoRoot "DEV_CORE"
    $env:DEVCORE_ACTIVE_WORKTREE_NAME = "test"
    $env:DEVCORE_SKIP_DASHBOARD = "1"

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

    New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
    $manifestPath = Join-Path $packageRoot "plugin.json"
    [pscustomobject][ordered]@{
        schema_version = 1
        id = "dispatcher-plugin"
        name = "Dispatcher Plugin"
        version = "0.1.0"
        capabilities = [ordered]@{
            commands = @("dispatcher:test")
            skills = @()
            health_checks = @()
            widgets = @()
            templates = @()
        }
        permissions = [ordered]@{
            write_roots = @("data")
            allow_out_of_scope_write = $false
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $pluginHealth = Invoke-DcJson "plugin health --json"
    Assert-True ($pluginHealth.ok -eq $true) "dc plugin health should return plugin service health"

    $pluginInstall = Invoke-DcJson "plugin install $manifestPath --json"
    Assert-True ($pluginInstall.ok -eq $true) "dc plugin install should install manifest"
    Assert-True ($pluginInstall.plugin.id -eq "dispatcher-plugin") "dc plugin install should preserve plugin id"

    $pluginList = Invoke-DcJson "plugin list --json"
    Assert-True ($pluginList.plugins_count -eq 1) "dc plugin list should return installed plugins"

    $pluginDiagnose = Invoke-DcJson "plugin diagnose dispatcher-plugin --json"
    Assert-True ($pluginDiagnose.ok -eq $true) "dc plugin diagnose should pass for installed plugin"

    $pluginDisable = Invoke-DcJson "plugin disable dispatcher-plugin --json"
    Assert-True ($pluginDisable.ok -eq $true) "dc plugin disable should disable installed plugin"
    Assert-True ($pluginDisable.plugin.enabled -eq $false) "dc plugin disable should mark plugin disabled"

    $dcSource = Get-Content $dcScript -Raw -Encoding UTF8
    Assert-True (-not ($dcSource -match "Invoke-Expression")) "dc.ps1 must not use Invoke-Expression"

    Write-Host "[OK] dc dispatch smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    if ($null -eq $oldPlatformRoot) {
        Remove-Item Env:\DEVCORE_PLATFORM_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_PLATFORM_ROOT = $oldPlatformRoot
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

    if ($hadDashboard) {
        $dashboardBackup | Set-Content $dashboardIndex -Encoding UTF8
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
