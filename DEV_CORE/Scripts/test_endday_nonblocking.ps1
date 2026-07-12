# test_endday_nonblocking.ps1 -- endday agent-safe execution contract
$ErrorActionPreference = "Stop"

$enddayScript = Join-Path $PSScriptRoot "endday.ps1"
$ciPowerShellTests = Join-Path $PSScriptRoot "ci_powershell_tests.ps1"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$source = Get-Content -LiteralPath $enddayScript -Raw -Encoding UTF8
$ciSource = Get-Content -LiteralPath $ciPowerShellTests -Raw -Encoding UTF8

Assert-True ($source -match '\[switch\]\$AgentMode') "endday.ps1 should expose AgentMode for non-blocking agent closes"
Assert-True ($source -match '\[int\]\$StepTimeoutSeconds') "endday.ps1 should expose per-step timeout"
Assert-True ($source -match '\$SkipBackup\.IsPresent\s*-and\s*-not\s+\$Full\.IsPresent') "SkipBackup should imply bounded agent mode unless Full is explicit"
Assert-True ($source -match 'Runtime.*endday\.lock') "endday.ps1 should use a runtime lock file"
Assert-True ($source -match 'Acquire-EnddayLock') "endday.ps1 should acquire an endday lock"
Assert-True ($source -match 'Release-EnddayLock') "endday.ps1 should release the endday lock"
Assert-True ($source -match 'Invoke-EnddayStep') "endday.ps1 should route steps through timeout-aware execution"
Assert-True ($source -match 'Wait-Job\s+-Timeout') "endday steps should enforce timeout"
Assert-True ($source -match 'AgentMode.*Rapport token SKIP') "AgentMode should skip full token report"
Assert-True ($source -match 'AgentMode.*Task scan \+ sync final SKIP') "AgentMode should skip full task scan/sync"
Assert-True ($ciSource -match 'test_endday_nonblocking\.ps1') "PowerShell CI should run endday non-blocking contract"

Write-Host "[OK] endday non-blocking tests passed" -ForegroundColor Green
