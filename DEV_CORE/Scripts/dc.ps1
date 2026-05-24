# dc.ps1 -- DEV_CORE v7.3 -- Single client -- ASCII safe
# Alias : Set-Alias dc 'C:\devcore\DEV_CORE\Scripts\dc.ps1'
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$SCRIPTS  = "$DEV_CORE\Scripts"
$cmd = ($Args -join " ").ToLower().Trim()

switch -Regex ($cmd) {

    # -- TASKS (nouveau systeme single client)
    "^next task$|^nt$"                          { & "$SCRIPTS\task_next.ps1" }
    "^task done$|^td$|^done$"                   { & "$SCRIPTS\task_done.ps1" }
    "^task status$|^ts$|^status$"               { & "$SCRIPTS\task_status.ps1" }
    "^task list$|^tl$|^list$"                   { & "$SCRIPTS\task_list.ps1" }
    "^task edit (T-\d+)(.*)$"                   { Invoke-Expression "& `"$SCRIPTS\task_edit.ps1`" -Id $($Matches[1]) $($Matches[2])" }
    "^task pause$"                              { & "$SCRIPTS\task_pause.ps1" }
    "^task skip$"                               { & "$SCRIPTS\task_skip.ps1" }
    "^task scan$"                               { & "$SCRIPTS\task_scan.ps1" }
    "^task sync$"                               { & "$SCRIPTS\task_sync.ps1" }
    "^toon convert-tasks$|^toon ct$" {
        $DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { 'C:\devcore\DEV_CORE_DATA' }
        & "$SCRIPTS\toonify.ps1" -InputFile "$DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json" -StatsSave
    }
    "^toon encode (.+)$" { & "$SCRIPTS\toonify.ps1" -InputFile $Matches[1] -StatsSave }
    "^toon decode (.+)$" { & "$SCRIPTS\toonify.ps1" -InputFile $Matches[1] -Decode }
    "^toon session$" {
        $DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { 'C:\devcore\DEV_CORE_DATA' }
        Get-Content "$DATA\Logs\scripts\session_context.toon" -ErrorAction SilentlyContinue
    }
    "^toon$" {
        $DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { 'C:\devcore\DEV_CORE_DATA' }
        & "$SCRIPTS\toonify.ps1" -InputFile "$DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json" -StatsSave
    }
    
    # -- RTK (Result Tool Kit)
    "^rtk\s+(.+)$" {
        $execCmd = $Matches[1]
        Invoke-Expression $execCmd 2>&1 | & "$SCRIPTS\rtk.ps1" -StatsSave
    }
    "^step done(\s+\d+)?$|^sd(\s+\d+)?$"        {
        $n = if ($Matches[1]) { [int]$Matches[1].Trim() } elseif ($Matches[2]) { [int]$Matches[2].Trim() } else { 0 }
        & "$SCRIPTS\task_step_done.ps1" -StepNumber $n
    }
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
    "^check --fix$"  { & "$SCRIPTS\diagnose.ps1" -Fix }
    "^check$"        { & "$SCRIPTS\diagnose.ps1" }

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
        Write-Host "  DEV_CORE v7.3 -- Single Client Mode" -ForegroundColor Cyan
        Write-Host "  -------------------------------------------" -ForegroundColor DarkGray
        Write-Host "  TACHES" -ForegroundColor White
        Write-Host "  dc next task (nt)              Prochaine tache + mode auto" -ForegroundColor Gray
        Write-Host "  dc task done (td)              Valide + sync memoire auto" -ForegroundColor Gray
        Write-Host "  dc task status (ts)            Dashboard taches" -ForegroundColor Gray
        Write-Host "  dc task list (tl)              Liste des taches todo" -ForegroundColor Gray
        Write-Host "  dc task edit [id] -mode ...    Editer une tache" -ForegroundColor Gray
        Write-Host "  dc task pause                  Pause sans valider" -ForegroundColor Gray
        Write-Host "  dc task skip                   Passe a la suivante" -ForegroundColor Gray
        Write-Host "  dc task scan                   Scan git+spec+prompts -> suggestions" -ForegroundColor Gray
        Write-Host "  dc task sync                   Sync suggestions dans tasks.json" -ForegroundColor Gray
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
        Write-Host "  TOON" -ForegroundColor White
        Write-Host "  dc toon                         tasks.json -> tasks.toon (avec stats)" -ForegroundColor Gray
        Write-Host "  dc toon convert-tasks (ct)      Idem avec rapport KPI" -ForegroundColor Gray
        Write-Host "  dc toon encode [fichier]        JSON -> TOON" -ForegroundColor Gray
        Write-Host "  dc toon decode [fichier]        TOON -> JSON" -ForegroundColor Gray
        Write-Host "  dc toon session                 Affiche session_context.toon" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  RTK (Result Tool Kit)" -ForegroundColor White
        Write-Host "  dc rtk [commande]               Execute et compresse la sortie (-40%)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  STEPS" -ForegroundColor White
        Write-Host "  dc step done [N] (sd)          Marque step N done (auto si N=0)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  AUTOMATION" -ForegroundColor White
        Write-Host "  session_start  -> launch + task_next + scan (auto)" -ForegroundColor DarkGray
        Write-Host "  post_tool_hook -> git detect + step incr + integrity (auto)" -ForegroundColor DarkGray
        Write-Host "  task_done      -> lesson + qdrant + obsidian + next (auto)" -ForegroundColor DarkGray
        Write-Host "  session_end    -> sync + endday (auto)" -ForegroundColor DarkGray
        Write-Host "  post-commit    -> step++ + auto-complete (auto)" -ForegroundColor DarkGray
        Write-Host "  weekly         -> audit + backup + report (scheduled)" -ForegroundColor DarkGray
        Write-Host ""
    }

    default { Write-Host "  Inconnu : '$cmd' -- dc help" -ForegroundColor Yellow }
}


