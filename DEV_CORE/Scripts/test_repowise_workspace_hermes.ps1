param(
    [string]$WorkspacePath = "C:\devcore\.repowise-workspace.yaml",
    [string]$HermesPath = "C:\devcore\hermes"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $WorkspacePath)) {
    Write-Host "[OK] Repowise workspace file absent; nothing to validate"
    exit 0
}

$source = Get-Content -LiteralPath $WorkspacePath -Raw

if ($source -match "(?m)^\s*alias:\s*hermes_temp\s*$" -or $source -match "(?m)^\s*-?\s*path:\s*hermes_temp\s*$") {
    throw "Repowise workspace must not reference obsolete hermes_temp"
}

if (Test-Path -LiteralPath $HermesPath) {
    if ($source -notmatch "(?m)^\s*alias:\s*hermes\s*$") {
        throw "Repowise workspace should expose restored Hermes runtime as alias 'hermes'"
    }
    if ($source -notmatch "(?m)^\s*-?\s*path:\s*(hermes|C:\\devcore\\hermes)\s*$") {
        throw "Repowise workspace should point Hermes alias to path 'hermes'"
    }
}

Write-Host "[OK] Repowise workspace Hermes contract"
