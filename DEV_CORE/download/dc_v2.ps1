# dc.ps1 -- DEV_CORE v6 -- Single client -- ASCII safe
# Alias : Set-Alias dc 'C:\DEV_CORE\Scripts\dc.ps1'
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$SCRIPTS  = "$DEV_CORE\Scripts"
$cmd = ($Args -join " ").ToLower().Trim()

switch -Regex ($cmd) {

    # -- TASKS (nouveau systeme single client)
    "^next task$|^nt$"                          { & "$SCRIPTS\task_next.ps1" }
    "^task done$|^td$|^done$"                   { & "$SCRIPTS\task_done.ps1" }
    "^task status$|^ts$|^status$"               { & "$SCRIPTS\task_status.ps1" }
    "^task pause$"                              { & "$SCRIPTS\task_pause.ps1" }
    "^task skip$"                               { & "$SCRIPTS\task_skip.ps1" }
    "^new task (.+) -(reasoning|coding|bulk)$"  {
        & "$SCRIPTS\task_add.ps1" -Title $Matches[1] -Mode $Matches[2]
    }
    "^new task (.+)$"                           {
        & "$SCRIPTS\task_add.ps1" -Title $Matches[1]
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
    "^launch$"  { & "$SCRIPTS\launch.ps1" }
    "^endday$"  { & "$SCRIPTS\endday.ps1" }
    "^weekly$"  { & "$SCRIPTS\Auto\weekly_maintenance.ps1" }

    # -- DIAGNOSTIC
    "^check$"   { & "$SCRIPTS\diagnose.ps1" }

    # -- ASK (routing mode auto)
    "^ask (.+)$" { & "$SCRIPTS\ask.ps1" -PromptFr $Matches[1] }

    # -- COMPAT anciens alias missions (redirige vers tasks)
    "^next mission$|^nm$"                        {
        Write-Host "  [INFO] Redirected: dc next task (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_next.ps1"
    }
    "^mission validee$|^mv$"                    {
        Write-Host "  [INFO] Redirected: dc task done (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_done.ps1"
    }
    "^mission status$|^ms$"                     {
        Write-Host "  [INFO] Redirected: dc task status (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_status.ps1"
    }

    # -- HELP
    "^help$|^h$" {
        Write-Host ""
        Write-Host "  DEV_CORE v6 -- Single Client Mode" -ForegroundColor Cyan
        Write-Host "  -------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  TACHES" -ForegroundColor White
        Write-Host "  dc next task (nt)              Prochaine tache + mode auto" -ForegroundColor Gray
        Write-Host "  dc task done (td)              Valide + sync memoire auto" -ForegroundColor Gray
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
