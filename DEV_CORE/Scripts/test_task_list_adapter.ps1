# Contrat : la liste PowerShell lit l'état SQL du projet demandé.
$ErrorActionPreference = "Stop"
$taskListScript = Join-Path $PSScriptRoot "task_list.ps1"
$platformRoot = Split-Path -Parent $PSScriptRoot
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-task-list-" + [guid]::NewGuid().ToString("N"))
$savedData = $env:DEVCORE_DATA_ROOT
$savedLocal = $env:DEVCORE_LOCAL_ROOT
$savedPlatform = $env:DEVCORE_PLATFORM_ROOT
$savedPython = $env:DEVCORE_PYTHON
$savedPythonPath = $env:PYTHONPATH

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $env:DEVCORE_DATA_ROOT = Join-Path $tempRoot "shared"
    $env:DEVCORE_LOCAL_ROOT = Join-Path $tempRoot "local"
    $env:DEVCORE_PLATFORM_ROOT = $platformRoot
    $env:DEVCORE_PYTHON = (Get-Command python -ErrorAction Stop).Source
    $env:PYTHONPATH = $platformRoot
    New-Item -ItemType Directory -Path $env:DEVCORE_DATA_ROOT, $env:DEVCORE_LOCAL_ROOT -Force | Out-Null

    $boardDir = Join-Path $env:DEVCORE_DATA_ROOT "Memory\alpha"
    New-Item -ItemType Directory -Path $boardDir -Force | Out-Null
    @{
        project = "alpha"
        tasks = @(@{ id = "T-01"; title = "Legacy stale"; status = "active"; mode = "coding" })
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $boardDir "tasks.json") -Encoding UTF8

    & $env:DEVCORE_PYTHON -m devcore_engine.cli task add "SQL task" --project alpha | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "SQL task setup failed" }
    $output = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $taskListScript -Project alpha | Out-String
    if ($LASTEXITCODE -ne 0) { throw "task_list.ps1 failed" }
    if ($output -notmatch "T-01" -or $output -notmatch "sql task") { throw "SQL task not shown" }
    if ($output -match "Legacy stale") { throw "Stale JSON task shown" }
    $adapter = Join-Path $platformRoot "API\compat_task_list.py"
    $sqlBoard = (& $env:DEVCORE_PYTHON $adapter --project alpha --json | Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $sqlBoard.tasks[0].title -ne "sql task") { throw "Compatibility adapter did not read SQLite" }
    $legacyBoard = (& $env:DEVCORE_PYTHON $adapter --project alpha --json --legacy-json | Out-String) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $legacyBoard.tasks[0].title -ne "Legacy stale") { throw "Explicit legacy mode failed" }
    $legacy = Get-Content -LiteralPath (Join-Path $boardDir "tasks.json") -Raw
    if ($legacy -notmatch "Legacy stale") { throw "Legacy JSON was modified" }

    Write-Host "[OK] task_list reads project-scoped SQLite state" -ForegroundColor Green
} finally {
    foreach ($entry in @(
        @{ Name = "DEVCORE_DATA_ROOT"; Value = $savedData },
        @{ Name = "DEVCORE_LOCAL_ROOT"; Value = $savedLocal },
        @{ Name = "DEVCORE_PLATFORM_ROOT"; Value = $savedPlatform },
        @{ Name = "DEVCORE_PYTHON"; Value = $savedPython },
        @{ Name = "PYTHONPATH"; Value = $savedPythonPath }
    )) {
        if ($null -eq $entry.Value) {
            Remove-Item -Path ("Env:" + $entry.Name) -ErrorAction SilentlyContinue
        } else {
            Set-Item -Path ("Env:" + $entry.Name) -Value $entry.Value
        }
    }
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
