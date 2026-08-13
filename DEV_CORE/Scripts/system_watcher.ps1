# system_watcher.ps1 -- DEV_CORE Automated Watchdog Wrapper
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
& $pythonExe -m devcore_engine.infra.system_watcher
exit $LASTEXITCODE
