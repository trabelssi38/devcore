# test_dashboard_auth_contract.ps1 -- Dashboard API local auth contract
$ErrorActionPreference = "Stop"

$dashboardApiPath = Join-Path $PSScriptRoot "dashboard_api.py"
$rotateScript = Join-Path $PSScriptRoot "rotate_dashboard_token.ps1"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

Assert-True (Test-Path -LiteralPath $dashboardApiPath) "dashboard_api.py should exist"
Assert-True (Test-Path -LiteralPath $rotateScript) "rotate_dashboard_token.ps1 should exist"

$source = Get-Content -LiteralPath $dashboardApiPath -Raw -Encoding UTF8
foreach ($required in @(
    "def ensure_api_token",
    "def rotate_api_token",
    "def validate_api_token",
    "def requires_authentication",
    "def is_authorized",
    "WWW-Authenticate",
    "--rotate-token"
)) {
    Assert-True ($source -match [regex]::Escape($required)) "dashboard_api.py missing auth contract: $required"
}

$tempData = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-auth-contract-" + [guid]::NewGuid().ToString("N"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT
try {
    New-Item -ItemType Directory -Path $tempData -Force | Out-Null
    $env:DEVCORE_DATA_ROOT = $tempData
    $output = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rotateScript | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "rotate_dashboard_token.ps1 should exit 0. Output: $output"
    }

    Assert-True ($output -match "\[OK\] Dashboard API token rotated") "rotation script should report success"
    $tokenStore = Join-Path $tempData "Security\dashboard_api_token.json"
    $bootstrap = Join-Path $tempData "Security\dashboard_api_token.bootstrap"
    Assert-True (Test-Path -LiteralPath $tokenStore) "rotation should create token hash store"
    Assert-True (Test-Path -LiteralPath $bootstrap) "rotation should create local bootstrap token"
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }
    Remove-Item -LiteralPath $tempData -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "[OK] dashboard auth contract tests passed" -ForegroundColor Green
