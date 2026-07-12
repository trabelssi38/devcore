# test_dashboard_security_contract.ps1 -- Dashboard API CORS/CSRF/body-limit contract
$ErrorActionPreference = "Stop"

$platformRoot = Split-Path -Parent $PSScriptRoot
$dashboardApiPath = Join-Path $PSScriptRoot "dashboard_api.py"
$securityConfigPath = Join-Path $platformRoot "Config\security.json"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $securityConfigPath) "security.json should exist"
$config = Get-Content -LiteralPath $securityConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

Assert-True ($config.cors.allowed_origins -contains "http://127.0.0.1:20129") "CORS should allow 127.0.0.1 dashboard origin"
Assert-True ($config.cors.allowed_origins -contains "http://localhost:20129") "CORS should allow localhost dashboard origin"
Assert-True (-not ($config.cors.allowed_origins -contains "*")) "CORS must not use wildcard origin"
Assert-True ([int]$config.limits.max_request_body_bytes -le 1048576) "request body limit should be <= 1 MiB"

$source = Get-Content -LiteralPath $dashboardApiPath -Raw -Encoding UTF8
foreach ($required in @(
    "def get_allowed_origins",
    "def is_origin_allowed",
    "def ensure_csrf_token",
    "def validate_csrf_token",
    "def requires_csrf",
    "def is_request_too_large",
    "send_csrf_error_response",
    "send_payload_too_large_response",
    "Access-Control-Allow-Origin",
    "X-CSRF-Token"
)) {
    Assert-True ($source -match [regex]::Escape($required)) "dashboard_api.py missing security contract: $required"
}

Assert-True (-not ($source -match "Access-Control-Allow-Origin', '\\*'")) "dashboard_api.py must not emit wildcard CORS"

Write-Host "[OK] dashboard security contract tests passed" -ForegroundColor Green
