# test_secret_scan.ps1 -- smoke tests for tracked secret detection
$ErrorActionPreference = "Stop"

$secretScan = Join-Path $PSScriptRoot "secret_scan.ps1"

function Assert-ExitCode {
    param(
        [int]$Expected,
        [string]$FileName,
        [string]$Arguments,
        [string]$Message
    )

    $p = Start-Process -FilePath $FileName -ArgumentList $Arguments -NoNewWindow -PassThru -Wait
    if ($p.ExitCode -ne $Expected) {
        throw "$Message (expected exit $Expected, got $($p.ExitCode))"
    }
}

$tempRepo = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-secret-scan-" + [guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Force -Path $tempRepo | Out-Null
    git -C $tempRepo init | Out-Null
    git -C $tempRepo config user.name "Test"
    git -C $tempRepo config user.email "test@test.com"

    "no secrets here" | Set-Content (Join-Path $tempRepo "safe.txt") -Encoding UTF8
    git -C $tempRepo add safe.txt | Out-Null
    git -C $tempRepo commit -m "initial" | Out-Null
    Assert-ExitCode 0 "powershell" "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$secretScan`" -Path `"$tempRepo`" -Quiet" "clean repo should pass"

    $fakeSecret = "sk-" + ("a" * 24)
    "token=$fakeSecret" | Set-Content (Join-Path $tempRepo "leak.txt") -Encoding UTF8
    git -C $tempRepo add leak.txt | Out-Null
    git -C $tempRepo commit -m "leak" | Out-Null
    Assert-ExitCode 1 "powershell" "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$secretScan`" -Path `"$tempRepo`" -Quiet" "repo with tracked token should fail"

    Write-Host "[OK] secret scan smoke tests passed" -ForegroundColor Green
} finally {
    Remove-Item -LiteralPath $tempRepo -Recurse -Force -ErrorAction SilentlyContinue
}
