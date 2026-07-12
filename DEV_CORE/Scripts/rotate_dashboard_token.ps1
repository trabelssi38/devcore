# rotate_dashboard_token.ps1 -- rotate local Dashboard API bearer token
$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { Split-Path -Parent $PSScriptRoot }
$dashboardApi = Join-Path $DEV_CORE "Scripts\dashboard_api.py"

if (-not (Test-Path -LiteralPath $dashboardApi)) {
    Write-Host "[FAIL] dashboard_api.py not found: $dashboardApi" -ForegroundColor Red
    exit 1
}

$token = & python $dashboardApi --rotate-token
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($token)) {
    Write-Host "[FAIL] Unable to rotate Dashboard API token" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Dashboard API token rotated" -ForegroundColor Green
Write-Host $token
exit 0
