# test_network_bind_contract.ps1 -- local-first network bind contract
$ErrorActionPreference = "Stop"

$platformRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $platformRoot "Config\network.json"
$dashboardApiPath = Join-Path $PSScriptRoot "dashboard_api.py"
$geminiRouterPath = Join-Path $PSScriptRoot "gemini_router.py"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $configPath) "network.json should exist"
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

Assert-True ($config.default_bind_host -eq "127.0.0.1") "default_bind_host should be loopback"
foreach ($service in @("dashboard_api", "gemini_router", "headroom_proxy", "repowise")) {
    Assert-True ($config.services.$service.host -eq "127.0.0.1") "$service should bind to loopback by default"
}

$dashboardSource = Get-Content -LiteralPath $dashboardApiPath -Raw -Encoding UTF8
Assert-True ($dashboardSource -match "def get_bind_host") "dashboard_api.py should expose get_bind_host"
Assert-True ($dashboardSource -notmatch 'server_class\(\("",\s*PORT\)') "dashboard_api.py must not bind to all interfaces"
Assert-True ($dashboardSource -match "DEVCORE_ALLOW_PUBLIC_BIND") "dashboard_api.py should require explicit public bind opt-in"

$routerSource = Get-Content -LiteralPath $geminiRouterPath -Raw -Encoding UTF8
Assert-True ($routerSource -match "def get_bind_host") "gemini_router.py should expose get_bind_host"
Assert-True ($routerSource -match "DEVCORE_ALLOW_PUBLIC_BIND") "gemini_router.py should require explicit public bind opt-in"
Assert-True ($routerSource -match "uvicorn\.run\(app, host=get_bind_host\(\), port=20130\)") "gemini_router.py should bind through get_bind_host"

Write-Host "[OK] network bind contract tests passed" -ForegroundColor Green
