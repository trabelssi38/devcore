# rotate_dashboard_token.ps1 -- rotate local Dashboard API bearer token
$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
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
