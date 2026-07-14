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
    "DEV_CORE\requirements-ci.txt",
    "ci_python_tests.ps1",
    "ci_powershell_tests.ps1",
    "secret_scan.ps1",
    "ci_contract_tests.ps1",
    "benchmark_reference.ps1",
    "actions/upload-artifact"
)) {
    Assert-True ($workflow -match [regex]::Escape($required)) "CI workflow missing required command: $required"
}

Assert-True ($workflow -match "(?m)^\s*timeout-minutes:\s*25\s*$") "CI verify job should have a bounded total timeout"
Assert-True (-not ($workflow -match [regex]::Escape('dc.ps1 "verify --ci --json"'))) "CI workflow should not re-run the full verify gate after explicit steps"

foreach ($step in @(
    "Checkout",
    "Setup Python",
    "Install Python test dependencies",
    "Lint PowerShell and Python",
    "Run Python tests",
    "Run PowerShell tests",
    "Secret scan",
    "Contract checks",
    "Reference benchmarks",
    "Upload benchmark artifacts"
)) {
    $pattern = "(?ms)- name:\s*" + [regex]::Escape($step) + "\s*\r?\n\s*timeout-minutes:\s*\d+"
    Assert-True ($workflow -match $pattern) "CI workflow step should have timeout-minutes: $step"
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
