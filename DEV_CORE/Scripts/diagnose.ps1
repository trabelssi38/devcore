# Delegator wrapper for Python devcore_engine diagnose
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$env:PYTHONPATH = $DEV_CORE
$pythonExe = if (Get-Command "python" -ErrorAction SilentlyContinue) { "python" } else { "C:\Program Files\Python313\python.exe" }
$ErrorActionPreference = "Continue"
$mappedArgs = @()
foreach ($a in $args) {
    if ($a -eq "-Gate" -or $a -eq "-gate") { $mappedArgs += "--gate" }
    elseif ($a -eq "-Json" -or $a -eq "-json") { $mappedArgs += "--json" }
    else { $mappedArgs += $a }
}
& $pythonExe -m devcore_engine.cli diagnose $mappedArgs
exit $LASTEXITCODE
