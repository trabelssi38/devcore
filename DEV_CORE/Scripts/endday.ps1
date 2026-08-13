# Delegator wrapper for Python devcore_engine endday
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
& $pythonExe -m devcore_engine.cli endday $args
exit $LASTEXITCODE
