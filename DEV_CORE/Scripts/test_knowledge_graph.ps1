# test_knowledge_graph.ps1 -- Thin wrapper for devcore_engine test_knowledge_graph
$DEV_CORE_ROOT = Split-Path -Parent $PSScriptRoot
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE_ROOT*") {
    $env:PYTHONPATH = "$DEV_CORE_ROOT;$env:PYTHONPATH"
}

& "C:\Program Files\Python313\python.exe" -m unittest devcore_engine.tests.test_knowledge_graph
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] knowledge graph smoke tests passed" -ForegroundColor Green
}
exit $LASTEXITCODE
