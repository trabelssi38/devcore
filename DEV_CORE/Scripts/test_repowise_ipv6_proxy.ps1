# test_repowise_ipv6_proxy.ps1 -- Repowise localhost IPv6 proxy contract
$ErrorActionPreference = "Stop"

$proxy = Join-Path $PSScriptRoot "repowise_ipv6_proxy.py"
$ensure = Join-Path $PSScriptRoot "ensure_repowise_ipv6_proxy.ps1"
$launch = Join-Path $PSScriptRoot "launch.ps1"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $proxy) "repowise_ipv6_proxy.py must exist"
Assert-True (Test-Path -LiteralPath $ensure) "ensure_repowise_ipv6_proxy.ps1 must exist"

$proxySource = Get-Content -LiteralPath $proxy -Raw -Encoding UTF8
Assert-True ($proxySource -match 'LISTEN_HOST = "::1"') "proxy must listen on IPv6 loopback"
Assert-True ($proxySource -match 'TARGET_HOST = "127\.0\.0\.1"') "proxy must forward to IPv4 Repowise API"
Assert-True ($proxySource -match 'LISTEN_PORT = 7337') "proxy must preserve Repowise API port"

$ensureSource = Get-Content -LiteralPath $ensure -Raw -Encoding UTF8
Assert-True ($ensureSource -match 'repowise_ipv6_proxy\.py') "ensure script must launch the proxy script"
Assert-True ($ensureSource -match '::1') "ensure script must test IPv6 loopback"

$launchSource = Get-Content -LiteralPath $launch -Raw -Encoding UTF8
Assert-True ($launchSource -match 'ensure_repowise_ipv6_proxy\.ps1') "launch.ps1 must ensure the IPv6 localhost proxy"

Write-Host "[OK] Repowise IPv6 proxy contract"
