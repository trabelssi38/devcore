# test_platform_version.ps1 -- platform version consistency tests
$ErrorActionPreference = "Stop"

$platformScript = Join-Path $PSScriptRoot "platform_version.ps1"
$healthScript = Join-Path $PSScriptRoot "health_report.ps1"
$verifyScript = Join-Path $PSScriptRoot "verify.ps1"

. $platformScript

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) { throw $Message }
}

$platform = Get-DevCorePlatformInfo
Assert-True ($platform.name -eq "DEV_CORE") "platform name should be DEV_CORE"
Assert-True ($platform.version -eq "10.0") "platform version should be 10.0"
Assert-True ($platform.title -eq "DEV_CORE v10.0") "platform title should be canonical"

$healthJson = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $healthScript -Json
if ($LASTEXITCODE -ne 0) { throw "health_report.ps1 -Json failed with exit code $LASTEXITCODE" }
$health = $healthJson | ConvertFrom-Json
Assert-True ($health.platform_version -eq $platform.version) "health report should expose canonical platform_version"

$checkScript = Join-Path $env:TEMP "devcore_platform_version_check.ps1"
"Write-Host '[OK] platform version check'" | Set-Content -LiteralPath $checkScript -Encoding ASCII
$env:DEVCORE_VERIFY_CHECKS_JSON = @(
    [pscustomobject]@{ name = "platform-version-check"; script = $checkScript; arguments = @() }
) | ConvertTo-Json -Compress
try {
    $verifyJson = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $verifyScript -Ci -Json
    if ($LASTEXITCODE -ne 0) { throw "verify.ps1 -Ci -Json failed with exit code $LASTEXITCODE" }
    $verify = $verifyJson | ConvertFrom-Json
    Assert-True ($verify.platform_version -eq $platform.version) "verify report should expose canonical platform_version"
} finally {
    Remove-Item Env:\DEVCORE_VERIFY_CHECKS_JSON -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $checkScript -ErrorAction SilentlyContinue
}

$runtimeFiles = @(
    "adapt_client.ps1",
    "dc.ps1",
    "diagnose.ps1",
    "endday.ps1",
    "health_report.ps1",
    "launch.ps1",
    "new_project.ps1",
    "verify.ps1"
)

foreach ($file in $runtimeFiles) {
    $path = Join-Path $PSScriptRoot $file
    $text = Get-Content -LiteralPath $path -Raw
    Assert-True (-not ($text -match "DEV_CORE v9\.0")) "$file should not display DEV_CORE v9.0"
    Assert-True (-not ($text -match "DEV_CORE v10(?!\.0)")) "$file should display DEV_CORE v10.0, not v10"
}

Write-Host "[OK] platform version consistency tests passed" -ForegroundColor Green
