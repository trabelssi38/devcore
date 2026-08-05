# task_sync.ps1 -- Thin wrapper for gen_dashboard
param(
    [switch]$SkipTokenRefresh,
    [switch]$Json
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

$genScript = Join-Path $PSScriptRoot "gen_dashboard.ps1"
& $genScript @PSBoundParameters
exit $LASTEXITCODE
