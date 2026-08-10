# Delegator wrapper for Python devcore_engine task next
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "devcore_engine"))) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
$pythonExe = if (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } else { "C:\Program Files\Python313\python.exe" }
& $pythonExe -m devcore_engine.cli task next $args
exit $LASTEXITCODE
