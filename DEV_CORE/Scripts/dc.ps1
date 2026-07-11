# dc.ps1 -- DEV_CORE single client dispatcher -- ASCII safe
# Alias : Set-Alias dc 'C:\devcore\DEV_CORE\Scripts\dc.ps1'
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

$DEV_CORE = Split-Path -Parent $PSScriptRoot
$SCRIPTS  = "$DEV_CORE\Scripts"
. "$SCRIPTS\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$PLATFORM_TITLE = $PLATFORM.title
$cmd = ($Args -join " ").ToLower().Trim()

function Invoke-TaskEditSafe {
    param(
        [Parameter(Mandatory=$true)][string]$Id,
        [string]$OptionsText = ""
    )

    $editArgs = @{ Id = $Id }
    $tokens = @()
    if (-not [string]::IsNullOrWhiteSpace($OptionsText)) {
        $tokens = $OptionsText.Trim() -split "\s+"
    }

    for ($i = 0; $i -lt $tokens.Count; $i++) {
        switch ($tokens[$i]) {
            "-title" {
                if ($i + 1 -ge $tokens.Count) {
                    Write-Host "  Valeur manquante pour -Title." -ForegroundColor Red
                    return
                }
                $editArgs.Title = ($tokens[($i + 1)..($tokens.Count - 1)] -join " ")
                $i = $tokens.Count
            }
            "-mode" {
                if ($i + 1 -ge $tokens.Count) {
                    Write-Host "  Valeur manquante pour -Mode." -ForegroundColor Red
                    return
                }
                $editArgs.Mode = $tokens[$i + 1]
                $i++
            }
            "-steps" {
                if ($i + 1 -ge $tokens.Count) {
                    Write-Host "  Valeur manquante pour -Steps." -ForegroundColor Red
                    return
                }
                $stepsValue = 0
                if (-not [int]::TryParse($tokens[$i + 1], [ref]$stepsValue)) {
                    Write-Host "  Valeur invalide pour -Steps: $($tokens[$i + 1])" -ForegroundColor Red
                    return
                }
                $editArgs.Steps = $stepsValue
                $i++
            }
            default {
                Write-Host "  Option task edit inconnue: $($tokens[$i])" -ForegroundColor Yellow
                Write-Host "  Exemple: dc task edit T-05 -Mode bulk -Steps 5" -ForegroundColor DarkGray
                return
            }
        }
    }

    & "$SCRIPTS\task_edit.ps1" @editArgs
}

function Invoke-RtkSafe {
    param([Parameter(Mandatory=$true)][string]$CommandText)

    & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command $CommandText 2>&1 |
        & "$SCRIPTS\rtk.ps1" -StatsSave
}

function Invoke-SkillsSafe {
    param([Parameter(Mandatory=$true)][string]$OptionsText)

    $tokens = @()
    if (-not [string]::IsNullOrWhiteSpace($OptionsText)) {
        $tokens = $OptionsText.Trim() -split "\s+"
    }
    $sub = if ($tokens.Count -gt 0) { $tokens[0].ToLowerInvariant() } else { "status" }

    switch ($sub) {
        "list"       { & "$SCRIPTS\auto_skill_service.ps1" -Action List; return }
        "candidates" { & "$SCRIPTS\auto_skill_service.ps1" -Action Candidates; return }
        "detect"     { & "$SCRIPTS\auto_skill_service.ps1" -Action Detect; return }
        "status"     { & "$SCRIPTS\auto_skill_service.ps1" -Action Status; return }
        "lint" {
            if ($tokens.Count -lt 2) { Write-Host "  Usage: dc skills lint <name>" -ForegroundColor Yellow; return }
            & "$SCRIPTS\skill_lint.ps1" -Name $tokens[1]
            return
        }
        "eval" {
            if ($tokens.Count -lt 2) { Write-Host "  Usage: dc skills eval <name>" -ForegroundColor Yellow; return }
            & "$SCRIPTS\skill_eval.ps1" -Name $tokens[1]
            return
        }
        "promote" {
            if ($tokens.Count -lt 2) { Write-Host "  Usage: dc skills promote <name>" -ForegroundColor Yellow; return }
            & "$SCRIPTS\auto_skill_service.ps1" -Action Promote -Name $tokens[1]
            return
        }
        "reject" {
            if ($tokens.Count -lt 2) { Write-Host "  Usage: dc skills reject <name>" -ForegroundColor Yellow; return }
            & "$SCRIPTS\auto_skill_service.ps1" -Action Reject -Name $tokens[1]
            return
        }
        default {
            Write-Host "  Usage: dc skills list|candidates|detect|lint <name>|eval <name>|promote <name>|reject <name>|status" -ForegroundColor Yellow
            return
        }
    }
}

function Invoke-PluginSafe {
    param([string]$OptionsText = "")

    $tokens = @()
    if (-not [string]::IsNullOrWhiteSpace($OptionsText)) {
        $tokens = $OptionsText.Trim() -split "\s+"
    }

    $json = $false
    $filtered = @()
    foreach ($token in $tokens) {
        if ($token -eq "--json" -or $token -eq "-json") {
            $json = $true
        } else {
            $filtered += $token
        }
    }

    $sub = if ($filtered.Count -gt 0) { $filtered[0].ToLowerInvariant() } else { "list" }
    $serviceArgs = @{}
    if ($json) { $serviceArgs.Json = $true }

    switch ($sub) {
        "list" {
            $serviceArgs.Action = "List"
            & "$SCRIPTS\plugin_service.ps1" @serviceArgs
            return
        }
        "health" {
            $serviceArgs.Action = "Health"
            & "$SCRIPTS\plugin_service.ps1" @serviceArgs
            return
        }
        "install" {
            if ($filtered.Count -lt 2) { Write-Host "  Usage: dc plugin install <plugin.json> [--json]" -ForegroundColor Yellow; return }
            $serviceArgs.Action = "Install"
            $serviceArgs.ManifestPath = $filtered[1]
            & "$SCRIPTS\plugin_service.ps1" @serviceArgs
            return
        }
        "disable" {
            if ($filtered.Count -lt 2) { Write-Host "  Usage: dc plugin disable <id> [--json]" -ForegroundColor Yellow; return }
            $serviceArgs.Action = "Disable"
            $serviceArgs.Id = $filtered[1]
            & "$SCRIPTS\plugin_service.ps1" @serviceArgs
            return
        }
        "diagnose" {
            if ($filtered.Count -lt 2) { Write-Host "  Usage: dc plugin diagnose <id> [--json]" -ForegroundColor Yellow; return }
            $serviceArgs.Action = "Diagnose"
            $serviceArgs.Id = $filtered[1]
            & "$SCRIPTS\plugin_service.ps1" @serviceArgs
            return
        }
        "check" {
            if ($filtered.Count -lt 2) { Write-Host "  Usage: dc plugin check <id> [--json]" -ForegroundColor Yellow; return }
            $serviceArgs.Action = "Check"
            $serviceArgs.Id = $filtered[1]
            & "$SCRIPTS\plugin_service.ps1" @serviceArgs
            return
        }
        default {
            Write-Host "  Usage: dc plugin list|health|install <plugin.json>|diagnose <id>|check <id>|disable <id> [--json]" -ForegroundColor Yellow
            return
        }
    }
}

switch -Regex ($cmd) {

    # -- TASKS (nouveau systeme single client)
    "^next task$|^nt$"                          { & "$SCRIPTS\task_next.ps1"; break }
    "^task done$|^td$|^done$"                   { & "$SCRIPTS\task_done.ps1"; break }
    "^task status$|^ts$|^status$"               { & "$SCRIPTS\task_status.ps1"; break }
    "^task list$|^tl$|^list$"                   { & "$SCRIPTS\task_list.ps1"; break }
    "^task edit (T-\d+)(.*)$"                   { Invoke-TaskEditSafe -Id $Matches[1] -OptionsText $Matches[2]; break }
    "^task pause$"                              { & "$SCRIPTS\task_pause.ps1"; break }
    "^task skip$"                               { & "$SCRIPTS\task_skip.ps1"; break }
    "^task scan$"                               { & "$SCRIPTS\task_scan.ps1"; break }
    "^task sync$"                               { & "$SCRIPTS\task_sync.ps1"; break }
    "^toon convert-tasks$|^toon ct$" {
        $DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { 'C:\devcore\DEV_CORE_DATA' }
        & "$SCRIPTS\toonify.ps1" -InputFile "$DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json" -StatsSave
        break
    }
    "^toon encode (.+)$" { & "$SCRIPTS\toonify.ps1" -InputFile $Matches[1] -StatsSave; break }
    "^toon decode (.+)$" { & "$SCRIPTS\toonify.ps1" -InputFile $Matches[1] -Decode; break }
    "^toon session$" {
        $DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { 'C:\devcore\DEV_CORE_DATA' }
        Get-Content "$DATA\Logs\scripts\session_context.toon" -ErrorAction SilentlyContinue
        break
    }
    "^toon$" {
        $DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { 'C:\devcore\DEV_CORE_DATA' }
        & "$SCRIPTS\toonify.ps1" -InputFile "$DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json" -StatsSave
        break
    }
    
    # -- RTK (Result Tool Kit)
    "^rtk\s+(.+)$" {
        $execCmd = $Matches[1]
        Invoke-RtkSafe -CommandText $execCmd
        break
    }
    "^step done(\s+\d+)?$|^sd(\s+\d+)?$"        {
        $n = if ($Matches[1]) { [int]$Matches[1].Trim() } elseif ($Matches[2]) { [int]$Matches[2].Trim() } else { 0 }
        & "$SCRIPTS\task_step_done.ps1" -StepNumber $n
        break
    }
    "^new task (.+) -(reasoning|coding|bulk)$"  {
        & "$SCRIPTS\task_add.ps1" -Title $Matches[1] -Mode $Matches[2]
        break
    }
    "^new task (.+)$"                           {
        & "$SCRIPTS\task_add.ps1" -Title $Matches[1]
        break
    }

    # -- PROJET
    "^new project (.+)$" {
        $parts = $Matches[1] -split "\s+"
        $name  = $parts[0]; $stack = "generic"
        for ($i=1; $i -lt $parts.Length; $i++) {
            if ($parts[$i] -eq "-stack" -and $i+1 -lt $parts.Length) { $stack = $parts[$i+1] }
        }
        & "$SCRIPTS\new_project.ps1" -Name $name -Stack $stack
        break
    }
    "^link project (.+)$" { & "$SCRIPTS\new_project.ps1" -Name $Matches[1] -Path (Get-Location).Path; break }

    # -- CYCLE JOURNALIER
    "^launch$"  { & "$SCRIPTS\launch.ps1"; break }
    "^endday$"  { & "$SCRIPTS\endday.ps1"; break }
    "^weekly$"  { & "$SCRIPTS\Auto\weekly_maintenance.ps1"; break }

    # -- SKILLS
    "^skills($|\s+.*)" { Invoke-SkillsSafe -OptionsText ($cmd -replace "^skills", ""); break }

    # -- PLUGINS
    "^plugins?($|\s+.*)" { Invoke-PluginSafe -OptionsText ($cmd -replace "^plugins?", ""); break }

    # -- DIAGNOSTIC
    "^check($|\s+.*)|^health($|\s+.*)|^verify($|\s+.*)" {
        & "$SCRIPTS\gateway.ps1" -Command $cmd
        exit $LASTEXITCODE
    }

    # -- ASK (routing mode auto)
    "^ask (.+)$" { & "$SCRIPTS\ask.ps1" -PromptFr $Matches[1]; break }

    # -- COMPAT anciens alias missions (redirige vers tasks)
    "^next mission$|^nm$"                        {
        Write-Host "  [INFO] Redirected: dc next task (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_next.ps1"
        break
    }
    "^mission validee$|^mv$"                    {
        Write-Host "  [INFO] Redirected: dc task done (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_done.ps1"
        break
    }
    "^mission status$|^ms$"                     {
        Write-Host "  [INFO] Redirected: dc task status (single client mode)" -ForegroundColor DarkGray
        & "$SCRIPTS\task_status.ps1"
        break
    }

    # -- HELP
    "^help$|^h$" {
        Write-Host ""
        Write-Host "  $PLATFORM_TITLE -- Single Client Mode" -ForegroundColor Cyan
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
        Write-Host "  dc check --gate                 Diagnostic release gate (exit code)" -ForegroundColor Gray
        Write-Host "  dc check --fix --dry-run        Simule les reparations du diagnostic" -ForegroundColor Gray
        Write-Host "  dc health                       Rapport health v10 court" -ForegroundColor Gray
        Write-Host "  dc health --json                Rapport health v10 JSON" -ForegroundColor Gray
        Write-Host "  dc verify --ci                  Gate CI deterministe" -ForegroundColor Gray
        Write-Host "  dc verify --ci --json           Gate CI JSON" -ForegroundColor Gray
        Write-Host "  dc ask [prompt]                 Routing mode auto" -ForegroundColor Gray
        Write-Host "  dc skills status                Etat Auto-Skills" -ForegroundColor Gray
        Write-Host "  dc skills detect                Detecte candidates depuis events" -ForegroundColor Gray
        Write-Host "  dc skills lint|eval|promote N   Gate et promotion skill" -ForegroundColor Gray
        Write-Host "  dc plugin list|health           Etat Plugin SDK" -ForegroundColor Gray
        Write-Host "  dc plugin install [plugin.json] Installe un plugin" -ForegroundColor Gray
        Write-Host "  dc plugin diagnose|check ID     Verifie ou execute les health checks" -ForegroundColor Gray
        Write-Host "  dc plugin disable ID            Desactive un plugin" -ForegroundColor Gray
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
        break
    }

    default { Write-Host "  Inconnu : '$cmd' -- dc help" -ForegroundColor Yellow; break }
}
