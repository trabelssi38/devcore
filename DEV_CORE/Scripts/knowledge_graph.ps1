# knowledge_graph.ps1 -- Thin wrapper for devcore_engine knowledge
param(
    [string]$Action = "Stats"
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m devcore_engine knowledge stats
exit $LASTEXITCODE
