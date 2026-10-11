# Prépare une demande en français dans le contexte SQL du projet sélectionné.
param(
    [Parameter(Mandatory=$true)][string]$PromptFr,
    [string]$Project
)

$ErrorActionPreference = "Stop"
$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} else {
    Split-Path -Parent $PSScriptRoot
}
$projectCwd = (Get-Location).Path
if ([string]::IsNullOrWhiteSpace($Project)) {
    $Project = (& (Join-Path $PSScriptRoot "Get-ActiveProject.ps1") | Select-Object -Last 1).Trim()
}
if ([string]::IsNullOrWhiteSpace($Project)) { throw "Projet requis." }
if ($Project -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') { throw "Identifiant de projet invalide." }

$toolsRoot = Join-Path $platformRoot "Tools"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$toolsRoot;$platformRoot;$env:PYTHONPATH" } else { "$toolsRoot;$platformRoot" }
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
$env:DEVCORE_ASK_PROMPT_FR = $PromptFr
$env:DEVCORE_ASK_CWD = $projectCwd
$env:DEVCORE_ASK_PROJECT = $Project
$env:DEVCORE_ASK_MISSION_ID = ""

$boardJson = & $pythonExe -m devcore_engine.cli task board --project $Project --json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$board = ($boardJson | Out-String) | ConvertFrom-Json
if ([string]$board.project -cne $Project) { throw "Board du mauvais projet : attendu $Project." }
$selectedVersion = $null
if ($board.current_task) {
    $env:DEVCORE_ASK_MISSION_ID = [string]$board.current_task
    $selected = @($board.tasks | Where-Object { [string]$_.id -ceq $env:DEVCORE_ASK_MISSION_ID })
    if ($selected.Count -ne 1 -or $selected[0].status -cne 'in_progress' -or
        [string]$selected[0].version -notmatch '^[1-9][0-9]*$') {
        throw "Tâche active du board invalide."
    }
    $selectedVersion = [string]$selected[0].version
}

$code = "import json,os; from devcore.cli import build_french_launch_payload; print(json.dumps(build_french_launch_payload(prompt_fr=os.environ['DEVCORE_ASK_PROMPT_FR'],cwd=os.environ['DEVCORE_ASK_CWD'],project_id=os.environ['DEVCORE_ASK_PROJECT'],mission_id=os.environ.get('DEVCORE_ASK_MISSION_ID') or None),ensure_ascii=False))"
$json = & $pythonExe -c $code
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$payload = ($json | Out-String) | ConvertFrom-Json
Write-Output $payload.confirmation_text
$confirm = Read-Host
if ($confirm -match "^n$|^N$") { Write-Output "Launch cancelled."; exit 0 }
$latestBoardJson = & $pythonExe -m devcore_engine.cli task board --project $Project --json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$latestBoard = ($latestBoardJson | Out-String) | ConvertFrom-Json
if ([string]$latestBoard.project -cne $Project) { throw "Board du mauvais projet après confirmation : attendu $Project." }
if ([string]$latestBoard.current_task -ne $env:DEVCORE_ASK_MISSION_ID) {
    throw "La tâche active du projet a changé pendant la confirmation. Relancez la demande."
}
if ($selectedVersion) {
    $latestTask = @($latestBoard.tasks | Where-Object { [string]$_.id -ceq $env:DEVCORE_ASK_MISSION_ID })
    if ($latestTask.Count -ne 1 -or $latestTask[0].status -cne 'in_progress' -or
        [string]$latestTask[0].version -cne $selectedVersion) {
        throw "La version de la tâche active a changé pendant la confirmation. Relancez la demande."
    }
}
$env:DEVCORE_ASK_INTERPRETATION = $payload.interpretation | ConvertTo-Json -Depth 5 -Compress
$prepareCode = "import json,os; from devcore.cli import prepare_french_launch_payload; print(json.dumps(prepare_french_launch_payload(interpretation=json.loads(os.environ['DEVCORE_ASK_INTERPRETATION']),mission_id=os.environ.get('DEVCORE_ASK_MISSION_ID') or None),ensure_ascii=False))"
$prepareJson = & $pythonExe -c $prepareCode
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output (($prepareJson | Out-String) | ConvertFrom-Json | ConvertTo-Json -Depth 5)
