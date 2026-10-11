# Contexte de session propre à un projet, généré depuis la base locale.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$Project
)

$ErrorActionPreference = "Stop"
$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} else {
    Split-Path -Parent $PSScriptRoot
}
if ([string]::IsNullOrWhiteSpace($Project)) { throw "Projet requis." }

$localRoot = if ($env:DEVCORE_LOCAL_ROOT) {
    $env:DEVCORE_LOCAL_ROOT
} elseif ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "DEV_CORE_LOCAL"
} else {
    Join-Path ([System.IO.Path]::GetTempPath()) "DEV_CORE_LOCAL"
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$platformRoot*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$platformRoot;$env:PYTHONPATH" } else { $platformRoot }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
$taskJson = & $pythonExe -m devcore_engine.cli task board --project $Project --json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$board = ($taskJson | Out-String) | ConvertFrom-Json
if ($board.project -ne $Project) { throw "Board d'un autre projet refusé." }
$task = @($board.tasks | Where-Object { $_.id -eq $board.current_task -and $_.status -eq "in_progress" }) | Select-Object -First 1

$sha = [System.Security.Cryptography.SHA256]::Create()
$projectKey = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Project))).Replace('-', '').Substring(0, 16)
$sha.Dispose()
$contextDir = Join-Path (Join-Path $localRoot "Runtime\projects") $projectKey
New-Item -ItemType Directory -Path $contextDir -Force | Out-Null
$contextFile = Join-Path $contextDir "session_context.txt"

if (-not $task) {
    $content = "[DEV_CORE] Projet : $Project`n[DEV_CORE] Aucune tâche active`n"
    $content | Set-Content -LiteralPath $contextFile -Encoding UTF8
    Write-Host "  [DEV_CORE] Aucune tâche active pour $Project" -ForegroundColor Yellow
    return
}

$budget = switch ($task.mode) {
    "reasoning" { "32k" }
    "coding"    { "8k" }
    "bulk"      { "16k" }
    default     { "16k" }
}
$content = @"
[DEV_CORE] Projet : $Project
[DEV_CORE] Task active : $($task.id)
[DEV_CORE] Titre  : $($task.title)
[DEV_CORE] Mode   : $($task.mode)
[DEV_CORE] Budget : $budget tokens
[DEV_CORE] Steps  : $($task.steps_done)/$($task.steps_total)
[DEV_CORE] Tag git: [$($task.id)]
"@

$sharedRoot = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { Join-Path $platformRoot "DEV_CORE_DATA" }
$canvasPath = Join-Path (Join-Path (Join-Path $sharedRoot "Refs") $Project) "canvas.md"
if (Test-Path -LiteralPath $canvasPath) {
    $canvas = Get-Content -LiteralPath $canvasPath -Raw -Encoding UTF8
    $limit = if ($env:DEVCORE_CONTEXT_BLOCK_MAX_CHARS) { [int]$env:DEVCORE_CONTEXT_BLOCK_MAX_CHARS } else { 10000 }
    if ($limit -gt 0 -and $canvas.Length -gt $limit) {
        $canvas = $canvas.Substring(0, $limit) + "`n[DEV_CORE] Canvas tronqué."
    }
    $content += "`n[DEV_CORE] Context Canvas (Mermaid):`n$canvas"
}

$content | Set-Content -LiteralPath $contextFile -Encoding UTF8
Write-Host "  [DEV_CORE] Contexte local généré pour ${Project} : $($task.id)" -ForegroundColor Green
