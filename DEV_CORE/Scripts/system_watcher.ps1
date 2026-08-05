# system_watcher.ps1 -- DEV_CORE Automated Watchdog Wrapper
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$pythonExe = if (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } else { "C:\Program Files\Python313\python.exe" }
& $pythonExe -m devcore_engine.infra.system_watcher
exit $LASTEXITCODE
