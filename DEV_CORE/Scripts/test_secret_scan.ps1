# Delegator wrapper for Python unittest test_secret_scan.py
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$env:PYTHONPATH = $DEV_CORE
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
$ErrorActionPreference = "Continue"
& $pythonExe -m unittest (Join-Path $DEV_CORE "devcore_engine/tests/test_secret_scan.py")
exit $LASTEXITCODE
