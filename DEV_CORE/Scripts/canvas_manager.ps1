# Delegator wrapper for Python devcore_engine canvas manager
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$env:PYTHONPATH = $DEV_CORE
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
& $pythonExe -m devcore_engine.cli $args
exit $LASTEXITCODE
