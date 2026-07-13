# test_repowise_ui_proxy.ps1 -- Repowise UI proxy contract
$ErrorActionPreference = "Stop"

$script = Join-Path $PSScriptRoot "ensure_repowise_web_proxy.ps1"
$launch = Join-Path $PSScriptRoot "launch.ps1"
$diagnose = Join-Path $PSScriptRoot "diagnose.ps1"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $script) "ensure_repowise_web_proxy.ps1 must exist"

$source = Get-Content -LiteralPath $script -Raw -Encoding UTF8
[scriptblock]::Create($source) | Out-Null

Assert-True ($source -match "http://127\.0\.0\.1:7337") "Repowise UI proxy patch must target IPv4 loopback API"
Assert-True ($source -match 'UTF8Encoding\(\$false\)') "Repowise UI proxy patch must preserve UTF-8 without BOM"
Assert-True ($source -match "localhost:7337") "Repowise UI proxy patch must replace localhost:7337"

$launchSource = Get-Content -LiteralPath $launch -Raw -Encoding UTF8
Assert-True ($launchSource -match "ensure_repowise_web_proxy\.ps1") "launch.ps1 must apply Repowise UI proxy patch"
Assert-True ($launchSource -match "serve --host 127\.0\.0\.1 --port 7337 --ui-port 3101") "launch.ps1 must start Repowise with explicit API/UI ports"

$diagnoseSource = Get-Content -LiteralPath $diagnose -Raw -Encoding UTF8
Assert-True ($diagnoseSource -match "ensure_repowise_web_proxy\.ps1") "diagnose.ps1 fallback must apply Repowise UI proxy patch"
Assert-True ($diagnoseSource -match "serve --host 127\.0\.0\.1 --port 7337 --ui-port 3101") "diagnose.ps1 fallback must start Repowise with explicit API/UI ports"

Write-Host "[OK] Repowise UI proxy contract"
