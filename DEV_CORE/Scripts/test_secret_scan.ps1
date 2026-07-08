# test_secret_scan.ps1 -- smoke tests for tracked secret detection
$ErrorActionPreference = "Stop"

$secretScan = Join-Path $PSScriptRoot "secret_scan.ps1"

function Assert-ExitCode {
    param(
        [int]$Expected,
        [scriptblock]$Action,
        [string]$Message
    )

    & $Action | Out-Null
    if ($LASTEXITCODE -ne $Expected) {
        throw "$Message (expected exit $Expected, got $LASTEXITCODE)"
    }
}

$tempRepo = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-secret-scan-" + [guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Force -Path $tempRepo | Out-Null
    git -C $tempRepo init | Out-Null

    "no secrets here" | Set-Content (Join-Path $tempRepo "safe.txt") -Encoding UTF8
    git -C $tempRepo add safe.txt | Out-Null
    Assert-ExitCode 0 { powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $secretScan -Path $tempRepo -Quiet } "clean repo should pass"

    $fakeSecret = "sk-" + ("a" * 24)
    "token=$fakeSecret" | Set-Content (Join-Path $tempRepo "leak.txt") -Encoding UTF8
    git -C $tempRepo add leak.txt | Out-Null
    Assert-ExitCode 1 { powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $secretScan -Path $tempRepo -Quiet } "repo with tracked token should fail"

    Write-Host "[OK] secret scan smoke tests passed" -ForegroundColor Green
} finally {
    Remove-Item -LiteralPath $tempRepo -Recurse -Force -ErrorAction SilentlyContinue
}
