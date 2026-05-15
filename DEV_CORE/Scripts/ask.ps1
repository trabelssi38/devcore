# ask.ps1 — DEV_CORE v6.2 (migre vers tasks.json)
param([Parameter(Mandatory=$true)][string]$PromptFr)

$ErrorActionPreference = 'Stop'
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$projectCwd    = (Get-Location).Path
Set-Location $DEV_CORE
$env:PYTHONPATH        = (Join-Path $DEV_CORE "Tools")
$env:DEVCORE_ASK_PROMPT_FR = $PromptFr
$env:DEVCORE_ASK_CWD       = $projectCwd

# Injecter task_id courant si disponible
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $active = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
    if ($active) { $env:DEVCORE_MISSION_ID = $active.id }
}

$json = python -c "import json,os; from devcore.cli import build_french_launch_payload; print(json.dumps(build_french_launch_payload(prompt_fr=os.environ['DEVCORE_ASK_PROMPT_FR'],cwd=os.environ['DEVCORE_ASK_CWD']),ensure_ascii=False))"
$payload = $json | ConvertFrom-Json
Write-Output $payload.confirmation_text
$confirm = Read-Host
if ($confirm -match "^n$|^N$") { Write-Output "Launch cancelled."; exit 0 }
Write-Output ($payload.prepare | ConvertTo-Json -Depth 5)
