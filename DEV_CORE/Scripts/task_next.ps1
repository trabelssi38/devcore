# task_next.ps1 -- DEV_CORE v6 single client
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"

if (-not (Test-Path $tFile)) {
    Write-Host "  Aucun tasks.json -- dc new task 'titre'" -ForegroundColor Yellow; exit 0
}

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $current) {
    $done_ids = ($board.tasks | Where-Object { $_.status -eq "done" }).id
    $current  = $board.tasks | Where-Object {
        $_.status -eq "todo" -and (
            -not $_.depends_on -or $done_ids -contains $_.depends_on
        )
    } | Select-Object -First 1
}

if (-not $current) {
    $done  = ($board.tasks | Where-Object { $_.status -eq "done" }).Count
    $total = $board.tasks.Count
    if ($done -eq $total -and $total -gt 0) { Write-Host "  Toutes les taches accomplies !" -ForegroundColor Green }
    else { Write-Host "  Aucune tache disponible -- verifier les dependances (dc ts)" -ForegroundColor Yellow }
    exit 0
}

# Activer
if ($current.status -eq "todo") {
    $current.status = "active"
    $current | Add-Member -NotePropertyName "started_at" -NotePropertyValue (Get-Date -Format "o") -Force
    $board.current_task = $current.id
    $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
    # Regenerer tasks.toon apres activation (via toonify.ps1 qui gere les paths Windows)
    try { & "$DEV_CORE\Scripts\toonify.ps1" -InputFile $tFile 2>$null | Out-Null } catch {}
}

# Mode -> budget
$budget = switch ($current.mode) {
    "reasoning" { "32k tokens" }
    "coding"    { "8k tokens"  }
    "bulk"      { "16k tokens" }
    default     { "8k tokens"  }
}

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
Write-Host "  |  Steps  : $("$($current.steps_done)/$($current.steps_total)".PadRight(31))|" -ForegroundColor Gray
if ($next) {
    Write-Host "  |  Suivant: $("$($next.id) [$($next.mode)]".PadRight(31))|" -ForegroundColor DarkGray
}
Write-Host "  +------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Mode hints
$hint = switch ($current.mode) {
    "reasoning" { "Skill dev-methodology. Brainstorm -> spec -> plan. Attends validation." }
    "coding"    { "Skill dev-methodology. TDD. Commit [T-XX] apres chaque etape." }
    "bulk"      { "Skill fabric-patterns. Mode bulk -- genere tout sans validation intermediaire." }
    default     { "Charge les skills pertinents et commence." }
}
Write-Host "  Hint : $hint" -ForegroundColor DarkGray
Write-Host ""

# Ecrire le contexte session (isolأ© par projet)
$projDir = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")"
$ctx = @"
[DEV_CORE] Task active : $($current.id)
[DEV_CORE] Titre  : $($current.title)
[DEV_CORE] Mode   : $($current.mode)
[DEV_CORE] Budget : $budget
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
  budget: $budget
  steps_done: $($current.steps_done)
  steps_total: $($current.steps_total)
  git_tag: [$($current.id)]
  project: $($board.project)
"@
$toonCtx | Set-Content "$DEV_CORE_DATA\Logs\scripts\session_context.toon" -Encoding UTF8
$toonCtx | Set-Content "$projDir\session_context.toon" -Encoding UTF8


& \gen_dashboard.ps1
