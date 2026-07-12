param(
    [string]$DevCoreRoot = "C:\devcore\DEV_CORE"
)

$ErrorActionPreference = "Stop"

$daemon = Join-Path $DevCoreRoot "Scripts\hermes-daemon.ps1"
if (-not (Test-Path $daemon)) {
    throw "hermes-daemon.ps1 not found at $daemon"
}

$source = Get-Content $daemon -Raw
if ($source -notmatch "function Resolve-HermesPython") {
    throw "hermes-daemon.ps1 must resolve Python dynamically via Resolve-HermesPython"
}

if ($source -match '\$PYTHON_BIN\s*=\s*"C:\\devcore\\hermes_temp\\\.venv\\Scripts\\python\.exe"') {
    throw "hermes-daemon.ps1 must not hardcode the obsolete hermes_temp Python path"
}

if ($source -notmatch 'C:\\devcore\\hermes\\\.venv\\Scripts\\python\.exe') {
    throw "hermes-daemon.ps1 must prioritize C:\devcore\hermes\.venv\Scripts\python.exe"
}

$output = & powershell -ExecutionPolicy Bypass -NonInteractive -File $daemon -Test 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "hermes-daemon.ps1 -Test exited with code $LASTEXITCODE`n$output"
}

if ($output -notmatch "Python binaire: OK") {
    throw "hermes-daemon.ps1 -Test did not report Python OK`n$output"
}

if ($output -match "NON TROUVE|binaire manquant") {
    throw "hermes-daemon.ps1 -Test still reports missing Python`n$output"
}

Write-Host "[OK] hermes-daemon Python resolution contract"
