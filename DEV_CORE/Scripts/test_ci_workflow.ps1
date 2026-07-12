# test_ci_workflow.ps1 -- CI workflow contract tests
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workflowPath = Join-Path $repoRoot ".github\workflows\ci.yml"
$verifyScript = Join-Path $PSScriptRoot "verify.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $workflowPath) "CI workflow should exist at .github/workflows/ci.yml"

$workflow = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
foreach ($required in @(
    "ci_lint.ps1",
    "ci_python_tests.ps1",
    "ci_powershell_tests.ps1",
    "secret_scan.ps1",
    "ci_contract_tests.ps1",
    "benchmark_reference.ps1",
    "actions/upload-artifact",
    "verify --ci --json"
)) {
    Assert-True ($workflow -match [regex]::Escape($required)) "CI workflow missing required command: $required"
}

$verifySource = Get-Content -LiteralPath $verifyScript -Raw -Encoding UTF8
foreach ($requiredCheck in @(
    "lint",
    "python-tests",
    "powershell-tests",
    "secret-scan",
    "contracts",
    "benchmarks"
)) {
    Assert-True ($verifySource -match "name\s*=\s*`"$requiredCheck`"") "verify.ps1 missing CI check: $requiredCheck"
}

Write-Host "[OK] CI workflow contract tests passed" -ForegroundColor Green
