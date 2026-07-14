# task_next.ps1 -- DEV_CORE v9.0 single client
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) {
    Write-Host "  Aucun tasks.json -- dc new task 'titre'" -ForegroundColor Yellow; exit 0
}

$currentJson = & "$PSScriptRoot\task_service.ps1" -Action Next -Json
$current = if ($currentJson -and (($currentJson -join "`n").Trim()) -ne "null") {
    ($currentJson | Out-String) | ConvertFrom-Json
} else {
    $null
}
$board = Get-Content $tFile -Raw | ConvertFrom-Json

if (-not $current) {
    $done  = ($board.tasks | Where-Object { $_.status -eq "done" }).Count
    $total = $board.tasks.Count
    if ($done -eq $total -and $total -gt 0) { Write-Host "  Toutes les taches accomplies !" -ForegroundColor Green }
    else { Write-Host "  Aucune tache disponible -- verifier les dependances (dc ts)" -ForegroundColor Yellow }
    $projName = & "$PSScriptRoot\Get-ActiveProject.ps1"
    $projDir = "$DEV_CORE_DATA\Memory\$projName"
    New-Item -ItemType Directory -Path "$DEV_CORE_DATA\Logs\scripts" -Force | Out-Null
    New-Item -ItemType Directory -Path $projDir -Force | Out-Null
    $ctx = @"
[DEV_CORE] Aucune tache active
[DEV_CORE] Toutes les taches accomplies : $done/$total
[DEV_CORE] Commencer par: dc new task 'description' -mode reasoning|coding|bulk
"@
    $ctx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.txt" -Encoding UTF8
    $ctx | Set-Content "$projDir\session_context.txt" -Encoding UTF8
    $toonCtx = @"
session:
  active_task: null
  status: no_active_task
  done: $done
  total: $total
  project: $($board.project)
"@
    $toonCtx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.toon" -Encoding UTF8
    $toonCtx | Set-Content "$projDir\session_context.toon" -Encoding UTF8
    exit 0
}

try { & "$DEV_CORE\Scripts\toonify.ps1" -InputFile $tFile 2>$null | Out-Null } catch {}

# Mode -> routing profile
. "$PSScriptRoot\routing_profile.ps1"
$routingProfile = Resolve-DevCoreRoutingProfile -Mode $current.mode
$budget = $routingProfile.budget

# Tache suivante
$next = $board.tasks | Where-Object { $_.status -eq "todo" -and $_.id -ne $current.id } | Select-Object -First 1

# Affichage
Write-Host ""
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  TASK $($current.id.PadRight(35))|" -ForegroundColor Cyan
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  $($current.title.PadRight(40))  |" -ForegroundColor White
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |  Mode   : $($current.mode.PadRight(31))|" -ForegroundColor Gray
Write-Host "  |  Budget : $($budget.PadRight(31))|" -ForegroundColor Gray
Write-Host "  |  Profile: $($routingProfile.profile.PadRight(31))|" -ForegroundColor Gray
Write-Host "  |  Steps  : $("$($current.steps_done)/$($current.steps_total)".PadRight(31))|" -ForegroundColor Gray
if ($next) {
    Write-Host "  |  Suivant: $("$($next.id) [$($next.mode)]".PadRight(31))|" -ForegroundColor DarkGray
}
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Mode hints
$hint = $routingProfile.hint
Write-Host "  Hint : $hint" -ForegroundColor DarkGray
Write-Host ""

# Ecrire le contexte session (isolأ© par projet)
$projDir = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")"
$ctx = @"
[DEV_CORE] Task active : $($current.id)
[DEV_CORE] Titre  : $($current.title)
[DEV_CORE] Mode   : $($current.mode)
[DEV_CORE] Profile: $($routingProfile.profile)
[DEV_CORE] Budget : $budget
[DEV_CORE] Model  : $($routingProfile.model)
[DEV_CORE] Gemini : $($routingProfile.gemini_model)
[DEV_CORE] Codex  : $($routingProfile.codex_behavior)
[DEV_CORE] Steps  : $($current.steps_done)/$($current.steps_total)
[DEV_CORE] Tag git: [$($current.id)]
"@
New-Item -ItemType Directory -Path "$DEV_CORE_DATA\Logs\scripts" -Force | Out-Null
$ctx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.txt" -Encoding UTF8
# Copie aussi dans le dossier projet
$ctx | Set-Content "$projDir\session_context.txt" -Encoding UTF8

# Ecrire aussi en format TOON pour LLM prompts
$toonCtx = @"
session:
  active_task: $($current.id)
  title: $($current.title)
  mode: $($current.mode)
  resolved_mode: $($routingProfile.mode)
  profile: $($routingProfile.profile)
  budget: $budget
  model: $($routingProfile.model)
  gemini_model: $($routingProfile.gemini_model)
  codex_behavior: $($routingProfile.codex_behavior)
  steps_done: $($current.steps_done)
  steps_total: $($current.steps_total)
  git_tag: [$($current.id)]
  project: $($board.project)
"@
$toonCtx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.toon" -Encoding UTF8
$toonCtx | Set-Content "$projDir\session_context.toon" -Encoding UTF8


& "$PSScriptRoot\gen_dashboard.ps1"
