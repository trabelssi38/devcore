# dc.ps1 -- DEV_CORE v6 -- Single client -- ASCII safe
# Alias : Set-Alias dc 'C:\DEV_CORE\Scripts\dc.ps1'
[CmdletBinding(PositionalBinding=$false)]
param(
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$Project,
    [string]$TaskId,
    [int]$ExpectedVersion,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$CommandWords
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$SCRIPTS  = "$DEV_CORE\Scripts"
$cmd = ($CommandWords -join " ").ToLower().Trim()
$taskDoneArgs = @{}
if ($Project) { $taskDoneArgs.Project = $Project }
if ($TaskId) { $taskDoneArgs.TaskId = $TaskId }
if ($PSBoundParameters.ContainsKey('ExpectedVersion')) { $taskDoneArgs.ExpectedVersion = $ExpectedVersion }
if ($cmd -match '^(next task|nt|task done|td|done|task status|ts|status|task pause|task skip|new task |next mission|nm|mission validee|mv|mission status|ms|launch$|endday$|ask )' -and -not $Project) {
    Write-Error 'Projet requis : dc_v2.ps1 -Project <id> <commande>'
    exit 2
}

switch -Regex ($cmd) {

    # -- TASKS (nouveau systeme single client)
    "^next task$|^nt$"                          { & "$SCRIPTS\task_next.ps1" --project $Project; exit $LASTEXITCODE }
    "^task done$|^td$|^done$"                   {
        if (-not $Project) { Write-Error 'Projet requis : dc_v2.ps1 -Project <id> task done'; exit 2 }
        & "$SCRIPTS\task_done.ps1" @taskDoneArgs
        exit $LASTEXITCODE
    }
    "^task status$|^ts$|^status$"               { & "$SCRIPTS\task_status.ps1" -Project $Project; exit $LASTEXITCODE }
    "^task pause$"                              { & "$SCRIPTS\task_pause.ps1" -Project $Project -Id $TaskId; exit $LASTEXITCODE }
    "^task skip$"                               { & "$SCRIPTS\task_skip.ps1" -Project $Project -Id $TaskId; exit $LASTEXITCODE }
    "^new task (.+) -(reasoning|coding|bulk)$"  {
        & "$SCRIPTS\task_add.ps1" -Title $Matches[1] -Mode $Matches[2] -Project $Project
        exit $LASTEXITCODE
    }
    "^new task (.+)$"                           {
        & "$SCRIPTS\task_add.ps1" -Title $Matches[1] -Project $Project
        exit $LASTEXITCODE
    }

    # -- PROJET
    "^new project (.+)$" {
        $parts = $Matches[1] -split "\s+"
        $name  = $parts[0]; $stack = "generic"
        for ($i=1; $i -lt $parts.Length; $i++) {
            if ($parts[$i] -eq "-stack" -and $i+1 -lt $parts.Length) { $stack = $parts[$i+1] }
        }
        & "$SCRIPTS\new_project.ps1" -Name $name -Stack $stack
    }
    "^link project (.+)$" { & "$SCRIPTS\new_project.ps1" -Name $Matches[1] -Path (Get-Location).Path }

    # -- CYCLE JOURNALIER
    "^launch$"  { & "$SCRIPTS\launch.ps1" --project $Project; exit $LASTEXITCODE }
    "^endday$"  { & "$SCRIPTS\endday.ps1" --project $Project; exit $LASTEXITCODE }
    "^weekly$"  { & "$SCRIPTS\Auto\weekly_maintenance.ps1"; exit $LASTEXITCODE }

    # -- DIAGNOSTIC
    "^check$"   { & "$SCRIPTS\diagnose.ps1"; exit $LASTEXITCODE }

    # -- ASK (routing mode auto)
    "^ask (.+)$" { & "$SCRIPTS\ask.ps1" -PromptFr $Matches[1] -Project $Project; exit $LASTEXITCODE }

    # -- COMPAT anciens alias missions (redirige vers tasks)
    "^next mission$|^nm$"                        {
        Write-Host "  [INFO] Redirected: dc next task (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_next.ps1" --project $Project
        exit $LASTEXITCODE
    }
    "^mission validee$|^mv$"                    {
        Write-Host "  [INFO] Redirected: dc task done (single client mode)" -ForegroundColor DarkGray
        if (-not $Project) { Write-Error 'Projet requis : dc_v2.ps1 -Project <id> mission validee'; exit 2 }
        & "$SCRIPTS\task_done.ps1" @taskDoneArgs
        exit $LASTEXITCODE
    }
    "^mission status$|^ms$"                     {
        Write-Host "  [INFO] Redirected: dc task status (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_status.ps1" -Project $Project
        exit $LASTEXITCODE
    }

    # -- HELP
    "^help$|^h$" {
        Write-Host ""
        Write-Host "  DEV_CORE v6 -- Single Client Mode" -ForegroundColor Cyan
        Write-Host "  -------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  TACHES" -ForegroundColor White
        Write-Host "  dc next task (nt)              Prochaine tache + mode auto" -ForegroundColor Gray
        Write-Host "  dc -Project <id> task done      Cloture la tache du projet" -ForegroundColor Gray
        Write-Host "  dc task status (ts)            Dashboard taches" -ForegroundColor Gray
        Write-Host "  dc task pause                  Pause sans valider" -ForegroundColor Gray
        Write-Host "  dc task skip                   Passe a la suivante" -ForegroundColor Gray
        Write-Host "  dc new task [titre] -[mode]    Ajoute une tache" -ForegroundColor Gray
        Write-Host "    modes : -reasoning | -coding | -bulk" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  PROJET" -ForegroundColor White
        Write-Host "  dc new project [nom] -stack [x] Init + lier un projet" -ForegroundColor Gray
        Write-Host "  dc link project [nom]           Lier un projet existant" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  CYCLE" -ForegroundColor White
        Write-Host "  dc launch                       Demarrage journee" -ForegroundColor Gray
        Write-Host "  dc endday                       Cloture + sync auto" -ForegroundColor Gray
        Write-Host "  dc weekly                       Maintenance hebdo" -ForegroundColor Gray
        Write-Host "  dc check                        Diagnostic complet" -ForegroundColor Gray
        Write-Host "  dc ask [prompt]                 Routing mode auto" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  MODES 9ROUTER" -ForegroundColor White
        Write-Host "  reasoning : architecture, spec, decision (32k)" -ForegroundColor Gray
        Write-Host "  coding    : implementation, patch, TDD (8k)" -ForegroundColor Gray
        Write-Host "  bulk      : generation masse, docs, tests (16k)" -ForegroundColor Gray
        Write-Host ""
    }

    default { Write-Host "  Inconnu : '$cmd' -- dc help" -ForegroundColor Yellow }
}
