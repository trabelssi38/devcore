# Delegator wrapper for Python devcore_engine diagnose
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "devcore_engine"))) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
$ErrorActionPreference = "Continue"
$mappedArgs = @()
foreach ($a in $args) {
    if ($a -eq "-Gate" -or $a -eq "-gate") { $mappedArgs += "--gate" }
    elseif ($a -eq "-Json" -or $a -eq "-json") { $mappedArgs += "--json" }
    else { $mappedArgs += $a }
}
& $pythonExe -m devcore_engine.cli diagnose $mappedArgs
exit $LASTEXITCODE
