# scheduler_sync.ps1 -- DEV_CORE -- Run Python scheduler syncer
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$platform_root = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
python "$platform_root\Scheduler\scheduler_sync.py"
