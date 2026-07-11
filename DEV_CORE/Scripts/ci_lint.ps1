# ci_lint.ps1 -- portable CI lint checks for PowerShell and Python
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Get-TrackedFiles {
    param([string]$Pattern)
    & git -C $repoRoot ls-files $Pattern
}

$psFailures = @()
$psFiles = @(Get-TrackedFiles "DEV_CORE/Scripts/*.ps1") + @(Get-TrackedFiles "DEV_CORE/Scripts/Auto/*.ps1")
foreach ($relativePath in ($psFiles | Sort-Object -Unique)) {
    $fullPath = Join-Path $repoRoot $relativePath
    try {
        $source = Get-Content -LiteralPath $fullPath -Raw -Encoding UTF8
        [scriptblock]::Create($source) | Out-Null
    } catch {
        $psFailures += "$relativePath -- $($_.Exception.Message)"
    }
}

if ($psFailures.Count -gt 0) {
    Write-Host "[FAIL] PowerShell parse errors:" -ForegroundColor Red
    foreach ($failure in $psFailures) { Write-Host "  $failure" -ForegroundColor Red }
    exit 1
}

$pyFiles = @(Get-TrackedFiles "DEV_CORE/Scripts/*.py") +
    @(Get-TrackedFiles "DEV_CORE/Scripts/Auto/*.py") +
    @(Get-TrackedFiles "DEV_CORE/MCP/**/*.py") +
    @(Get-TrackedFiles "DEV_CORE/Tools/**/*.py")

if ($pyFiles.Count -gt 0) {
    $compileArgs = @("-m", "py_compile") + @($pyFiles | Sort-Object -Unique)
    & python @compileArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[OK] CI lint checks passed" -ForegroundColor Green
exit 0
