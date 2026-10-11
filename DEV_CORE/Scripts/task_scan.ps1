# task_scan.ps1 -- scan Git SQL du projet ; suggestions historiques sur demande
param(
    [Parameter(Mandatory=$true)][string]$Project,
    [string]$RepoPath,
    [switch]$IncludeLegacySuggestions
)
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
$AUTO          = "$DEV_CORE\Scripts\Auto"
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

if ([string]::IsNullOrWhiteSpace($Project)) { throw "Un projet explicite est requis." }
if (-not $RepoPath) {
    $gitRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $gitRoot) { throw "Aucune racine Git detectee ; indiquez -RepoPath." }
    $RepoPath = ($gitRoot | Select-Object -Last 1).Trim()
}
$python = Get-DevCorePython
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}

Write-Host ""
Write-Host "  $($PLATFORM.title) -- TASK SCAN" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

Write-Host "  Git scanner SQL: $Project" -ForegroundColor Cyan
& $python -m devcore_engine.infra.multi_project_git_scanner --project $Project --repo $RepoPath
if ($LASTEXITCODE -ne 0) { throw "Le scan Git SQL a echoue (code $LASTEXITCODE)." }

if ($IncludeLegacySuggestions) {
    Write-Warning "Les scanners historiques peuvent ecrire des queues dans DEVCORE_DATA_ROOT."
    & "$AUTO\task_spec_parser.ps1" -Project $Project -RepoPath $RepoPath
    & "$AUTO\task_prompt_analyzer.ps1" -Project $Project
}

Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Scan termine" -ForegroundColor Green
Write-Host ""
