# ci_python_tests.ps1 -- portable Python test runner
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$tests = @(
    "DEV_CORE/Scripts/test_dashboard_api.py",
    "DEV_CORE/Scripts/Auto/test_model_pricing_sync.py",
    "DEV_CORE/Scripts/Auto/test_token_report_clients.py"
)

$existingTests = @()
foreach ($test in $tests) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $test)) {
        $existingTests += $test
    }
}

if ($existingTests.Count -eq 0) {
    Write-Host "[FAIL] No Python tests configured" -ForegroundColor Red
    exit 1
}

& python -m pytest @existingTests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[OK] Python tests passed" -ForegroundColor Green
exit 0
