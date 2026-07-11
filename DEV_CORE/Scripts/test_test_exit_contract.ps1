# test_test_exit_contract.ps1 -- soft-assert test harnesses must fail their process
$ErrorActionPreference = "Stop"

$violations = @()
$testScripts = Get-ChildItem -LiteralPath $PSScriptRoot -Filter "test_*.ps1" -File
foreach ($testScript in $testScripts) {
    if ($testScript.FullName -eq $PSCommandPath) { continue }
    $source = Get-Content -LiteralPath $testScript.FullName -Raw -Encoding UTF8
    $usesSoftFailure = (
        $source -match '(?mi)Write-Host\s+[^\r\n]*\[FAIL\]' -or
        $source -match '(?mi)\$icon\s*=\s*if[^\r\n]*\[FAIL\]'
    )
    if (-not $usesSoftFailure) { continue }

    $hasFailureExit = $source -match '(?mi)^\s*if\s*\([^\r\n]*(fail|failed)[^\r\n]*-gt\s+0[^\r\n]*\)\s*\{?[^\r\n]*exit\s+1'
    $hasSuccessExit = $source -match '(?mi)^\s*exit\s+0\s*$'
    if (-not ($hasFailureExit -and $hasSuccessExit)) {
        $violations += $testScript.Name
    }
}

if ($violations.Count -gt 0) {
    throw "Soft-assert test scripts without explicit exit contract: $($violations -join ', ')"
}

Write-Host "[OK] test exit-code contract passed" -ForegroundColor Green
