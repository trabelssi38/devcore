# task_add.ps1 -- Thin wrapper for devcore_engine task add
param(
    [Parameter(Mandatory=$true)]
    [string]$Title,
    [ValidateSet("coding", "reasoning", "bulk")]
    [string]$Mode = "coding",
    [int]$Steps = 1,
    [string]$Project = "devcore"
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m devcore_engine task add "$Title" --mode $Mode --steps $Steps --project $Project
exit $LASTEXITCODE
