# gen_dashboard.ps1 -- Thin wrapper for Python gen_dashboard.py
param(
    [switch]$SkipTokenRefresh,
    [switch]$Json
)

$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

$pyScript = Join-Path $PSScriptRoot "gen_dashboard.py"
$argsList = @()
if ($SkipTokenRefresh) { $argsList += "--skip-token-refresh" }
if ($Json) { $argsList += "--json" }

& "C:\Program Files\Python313\python.exe" $pyScript @argsList
exit $LASTEXITCODE
