# mission_done.ps1 — DEV_CORE v6
param([switch]$Force)
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
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$AUTO = "$DEV_CORE\Scripts\Auto"; $TODAY = Get-Date -Format "yyyy-MM-dd"
$mFile = "$DEV_CORE_DATA\Memory\missions.json"

if (-not (Test-Path $mFile)) { Write-Host "  Aucun missions.json." -ForegroundColor Red; exit 1 }
$board = Get-Content $mFile -Raw | ConvertFrom-Json
$current = $board.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1
if (-not $current) { Write-Host "  Aucune mission active — dc next mission" -ForegroundColor Yellow; exit 0 }

$stepsTotal = if ($current.PSObject.Properties["steps_total"]) { $current.steps_total } else { 1 }
$stepsDone  = if ($current.PSObject.Properties["steps_done"])  { $current.steps_done  } else { 1 }

if ($stepsDone -lt $stepsTotal -and -not $Force) {
    Write-Host "  ⚠ $stepsDone/$stepsTotal étapes complétées" -ForegroundColor Yellow
    $c = Read-Host "  Valider quand même ? (o/N)"
    if ($c -notmatch "^o|^y") { Write-Host "  Mission non validée." -ForegroundColor DarkGray; exit 0 }
}

# Marquer done
$current.status = "done"
$current | Add-Member -NotePropertyName "completed_at" -NotePropertyValue (Get-Date -Format "o") -Force
$done_ids = ($board.missions | Where-Object { $_.status -eq "done" }).id
$nextMission = $board.missions | Where-Object {
    $_.status -eq "todo" -and (-not $_.depends_on -or $done_ids -contains $_.depends_on)
} | Select-Object -First 1
$board | ConvertTo-Json -Depth 10 | Set-Content $mFile -Encoding UTF8

Write-Host ""; Write-Host "  DEV_CORE v6 — MISSION VALIDÉE" -ForegroundColor Green; Write-Host ""
Write-Host "  1/6 Handoff..." -ForegroundColor Cyan
$nextAgent = if ($nextMission) { $nextMission.agent } else { "—" }
$nextId    = if ($nextMission) { $nextMission.id }    else { "—" }
$handoff = @"
## Handoff — $($current.id) → $nextId
Date : $TODAY | De : $($current.agent) | Pour : $nextAgent

### Mission complétée
ID : $($current.id) | $($current.title) | Steps : $stepsDone/$stepsTotal

### Context
[Décisions prises pendant cette mission]

### Done
$(1..$stepsDone | ForEach-Object { "- [x] Étape $_" })

### Next — $nextId
$(if ($nextMission) { "- [ ] $($nextMission.title)" } else { "- Fin du projet" })

### Qdrant query
"$($current.title.ToLower())"

### Budget estimé
~6k tokens
"@
$naPath = "$DEV_CORE_DATA\Memory\next_actions.md"
$handoff | Set-Content $naPath -Encoding UTF8
Write-Host "    Handoff : $naPath" -ForegroundColor Green

Write-Host "  2/6 Leçons..." -ForegroundColor Cyan
if (Test-Path "$AUTO\lesson_extractor.ps1") { & "$AUTO\lesson_extractor.ps1" }
Write-Host "  3/6 Qdrant..." -ForegroundColor Cyan
if (Test-Path "$AUTO\qdrant_sync.ps1") { & "$AUTO\qdrant_sync.ps1" }
Write-Host "  4/6 Obsidian..." -ForegroundColor Cyan
if (Test-Path "$AUTO\obsidian_sync.ps1") { & "$AUTO\obsidian_sync.ps1" }
Write-Host "  5/6 Mémoire..." -ForegroundColor Cyan
if (Test-Path "$AUTO\memory_rotate.ps1") { & "$AUTO\memory_rotate.ps1" }
Write-Host "  6/6 Notification..." -ForegroundColor Cyan
try {
    Add-Type -AssemblyName System.Windows.Forms
    $n = New-Object System.Windows.Forms.NotifyIcon
    $n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true
    $n.ShowBalloonTip(5000,"DEV_CORE v6","Mission $($current.id) done. Suivant : $nextId → $nextAgent",[System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -Seconds 1; $n.Dispose()
} catch {}

$done = ($board.missions | Where-Object { $_.status -eq "done" }).Count
$total = $board.missions.Count
Write-Host ""
Write-Host "  ✓ $($current.id) DONE | $done/$total missions | Prochaine : $nextId" -ForegroundColor Green
if ($nextMission) { Write-Host "  Lance : dc next mission" -ForegroundColor Cyan }
Write-Host ""
