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

. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython

& $pythonExe $pyScript @argsList
exit $LASTEXITCODE
