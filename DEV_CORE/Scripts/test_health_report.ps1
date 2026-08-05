# test_health_report.ps1 -- Thin wrapper for devcore_engine test_health_report
$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m unittest devcore_engine.tests.test_health_report
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] health report smoke tests passed" -ForegroundColor Green
}
exit $LASTEXITCODE
