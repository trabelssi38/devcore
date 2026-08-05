# Delegator wrapper for Python unittest test_ci_workflow.py
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$env:PYTHONPATH = $DEV_CORE
$pythonExe = if (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } else { "C:\Program Files\Python313\python.exe" }
$ErrorActionPreference = "Continue"
& $pythonExe -m unittest (Join-Path $DEV_CORE "devcore_engine/tests/test_ci_workflow.py")
exit $LASTEXITCODE
