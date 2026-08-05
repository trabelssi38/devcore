# Delegator wrapper for Python devcore_engine task service
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$env:PYTHONPATH = $DEV_CORE
$pythonExe = if (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } else { "C:\Program Files\Python313\python.exe" }
& $pythonExe -m devcore_engine.cli task $args
exit $LASTEXITCODE
