# test_task_service.ps1 -- Thin wrapper for devcore_engine test_task_service
$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m unittest devcore_engine.tests.test_task_service
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] task service smoke tests passed" -ForegroundColor Green
}
exit $LASTEXITCODE
