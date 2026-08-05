# task_list.ps1 -- Thin wrapper for devcore_engine task board
param(
    [string]$Project = "devcore"
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m devcore_engine task board --project $Project
exit $LASTEXITCODE
