# task_list.ps1 -- SQL task board for one project
param(
    [string]$Project
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

$taskArgs = @("-m", "devcore_engine", "task", "board")
if ($Project) { $taskArgs += @("--project", $Project) }
& $pythonExe @taskArgs
exit $LASTEXITCODE
