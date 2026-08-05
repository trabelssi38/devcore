# test_event_bus.ps1 -- Thin wrapper for devcore_engine test_event_bus
$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m unittest devcore_engine.tests.test_event_bus
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] event bus smoke tests passed" -ForegroundColor Green
}
exit $LASTEXITCODE
