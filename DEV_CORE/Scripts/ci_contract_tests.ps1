# ci_contract_tests.ps1 -- CI contract and schema checks
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workflowPath = Join-Path $repoRoot ".github\workflows\ci.yml"
$tasksSchemaPath = Join-Path $repoRoot "DEV_CORE\Config\tasks.schema.json"
$workflowTest = Join-Path $PSScriptRoot "test_ci_workflow.ps1"

& powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $workflowTest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$schema = Get-Content -LiteralPath $tasksSchemaPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $schema.'$schema') {
    Write-Host "[FAIL] tasks.schema.json should declare a JSON schema dialect" -ForegroundColor Red
    exit 1
}
if (-not $schema.properties.tasks) {
    Write-Host "[FAIL] tasks.schema.json should define tasks property" -ForegroundColor Red
    exit 1
}

$workflow = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
if ($workflow -notmatch "windows-latest") {
    Write-Host "[FAIL] CI workflow should run on windows-latest for PowerShell parity" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] CI contract checks passed" -ForegroundColor Green
exit 0
