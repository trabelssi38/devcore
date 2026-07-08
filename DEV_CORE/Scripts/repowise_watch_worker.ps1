# repowise_watch_worker.ps1 -- long-running Repowise watcher for one repo
param(
    [Parameter(Mandatory=$true)][string]$ProjectName,
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [Parameter(Mandatory=$true)][string]$RepowisePath,
    [Parameter(Mandatory=$true)][string]$LogDir
)

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = if ($env:PYTHONIOENCODING) { $env:PYTHONIOENCODING } else { "utf-8" }

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$safeName = $ProjectName -replace '[\\/:*?"<>| ]', '_'
$logPath = Join-Path $LogDir "$safeName.log"

function Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $logPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

try {
    $resolvedProjectPath = (Resolve-Path $ProjectPath).Path
    Log "START project=$ProjectName path=$resolvedProjectPath"

    if (-not (Test-Path $RepowisePath)) {
        Log "ERROR repowise not found: $RepowisePath"
        exit 1
    }

    $env:REPOWISE_EMBEDDER = if ($env:REPOWISE_EMBEDDER) { $env:REPOWISE_EMBEDDER } else { "mock" }

    $statePath = Join-Path $resolvedProjectPath ".repowise\state.json"
    if (-not (Test-Path $statePath)) {
        Log "INIT index-only fast"
        & $RepowisePath init --index-only --mode fast --no-workspace -y --no-claude-md --no-agents --no-codex $resolvedProjectPath *>> $logPath
        Log "INIT exit=$LASTEXITCODE"
    } else {
        Log "UPDATE index-only no-docs"
        & $RepowisePath update --index-only --no-docs --no-workspace $resolvedProjectPath *>> $logPath
        Log "UPDATE exit=$LASTEXITCODE"
    }

    Log "WATCH starting"
    & $RepowisePath watch --no-workspace $resolvedProjectPath *>> $logPath
    Log "WATCH exited exit=$LASTEXITCODE"
    exit $LASTEXITCODE
} catch {
    Log "ERROR $($_.Exception.Message)"
    exit 1
}
