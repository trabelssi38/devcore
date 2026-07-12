# test_task_list_adapter.ps1 -- task_list compatibility adapter contract
$ErrorActionPreference = "Stop"

$taskListScript = Join-Path $PSScriptRoot "task_list.ps1"
$ciPowerShellTests = Join-Path $PSScriptRoot "ci_powershell_tests.ps1"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-task-list-adapter-" + [guid]::NewGuid().ToString("N"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT

try {
    $env:DEVCORE_DATA_ROOT = $tempRoot
    $boardDir = Join-Path $tempRoot "Memory\devcore"
    New-Item -ItemType Directory -Path $boardDir -Force | Out-Null
    @{
        project = "devcore"
        current_task = "T-158"
        tasks = @(
            @{
                id = "T-158"
                title = "Adapter task list"
                status = "active"
                mode = "coding"
                steps_done = 0
                steps_total = 1
            }
        )
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $boardDir "tasks.json") -Encoding UTF8

    $output = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskListScript | Out-String
    Assert-True ($output -match "T-158") "task_list adapter should render tasks from the Python port"
    Assert-True ($output -match "Adapter task list") "task_list adapter should preserve task titles"

    $source = Get-Content -LiteralPath $taskListScript -Raw -Encoding UTF8
    Assert-True ($source -match "compat_task_list.py") "task_list.ps1 should delegate to the Python compatibility adapter"
    Assert-True ($source -notmatch "Get-Content\\s+\\$tFile") "task_list.ps1 should not read tasks.json directly"

    $ciSource = Get-Content -LiteralPath $ciPowerShellTests -Raw -Encoding UTF8
    Assert-True ($ciSource -match "test_task_list_adapter.ps1") "PowerShell CI should run task list adapter contract"

    Write-Host "[OK] task list adapter tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
