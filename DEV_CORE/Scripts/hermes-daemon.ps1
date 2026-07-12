# hermes-daemon.ps1 -- DEV_CORE v9.0 + Hermes Standalone Daemon
# Service Windows pour HERMES en daemon avec cron DEV_CORE

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Test,
    [switch]$SyncJobs
)

$ErrorActionPreference = "Stop"
$HERMES_HOME  = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" }
$DEVCORE_ROOT = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$LOG_DIR      = "$DEVCORE_ROOT\..\DEV_CORE_DATA\Logs\hermes"
$LOG_FILE     = "$LOG_DIR\daemon_$(Get-Date -Format 'yyyy-MM-dd').log"

# Creer dossier logs si absent
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LOG_FILE -Value $logLine -ErrorAction SilentlyContinue
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "SUCCESS" { "Green" }
        default { "Gray" }
    }
    Write-Host "  $logLine" -ForegroundColor $color
}

function Test-PythonExecutable {
    param([string]$Path)
    if (-not $Path) { return $false }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Path
        $psi.Arguments = "-c `"import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)`""
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($psi)
        $p.WaitForExit(10000) | Out-Null
        if (-not $p.HasExited) {
            $p.Kill()
            return $false
        }
        return $p.ExitCode -eq 0
    } catch {
        return $false
    }
}

function Resolve-HermesPython {
    $candidates = @()

    if ($env:HERMES_PYTHON) { $candidates += $env:HERMES_PYTHON }
    if ($env:DEVCORE_PYTHON) { $candidates += $env:DEVCORE_PYTHON }

    $hermesPython = "C:\devcore\hermes\.venv\Scripts\python.exe"
    if (Test-Path $hermesPython) { $candidates += $hermesPython }

    $pathPython = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pathPython -and $pathPython.Source) { $candidates += $pathPython.Source }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pyLauncher -and $pyLauncher.Source) { $candidates += $pyLauncher.Source }

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if ((Test-Path $candidate) -and (Test-PythonExecutable -Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Aucun Python compatible trouve. Definir HERMES_PYTHON ou DEVCORE_PYTHON vers python.exe."
}

function Quote-CommandArgument {
    param([string]$Value)
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Get-HermesCronProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(python|pythonw)\.exe$' -and $_.CommandLine -match 'hermes_cron_tick\.py'
    }
}

function Get-HermesCronRootProcesses {
    $procs = @(Get-HermesCronProcesses)
    $ids = @($procs | Select-Object -ExpandProperty ProcessId)
    $procs | Where-Object { $ids -notcontains $_.ParentProcessId }
}

# ========== COMMANDS ==========

function Do-Install {
    Write-Log "Installation du daemon HERMES DEV_CORE (Tick loop standalone)" "INFO"

    # Desinstaller les anciennes taches planifiees individuelles si presentes pour eviter les doublons
    $oldTasks = @("DEV_CORE_Daily_Launch", "DEV_CORE_Daily_Endday", "DEV_CORE_Weekly_Maintenance", "DEV_CORE_Event_Watcher", "DEV_CORE_Integrity_Check")
    foreach ($ot in $oldTasks) {
        if (Get-ScheduledTask -TaskName $ot -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $ot -Confirm:$false -ErrorAction SilentlyContinue
            Write-Log "  Ancienne tache planifiee $ot supprimee (remplacee par Hermes)" "WARN"
        }
    }

    # Unique scheduled task for starting the lightweight tick daemon at login
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -File `"$PSScriptRoot\hermes-daemon.ps1`" -Start"

    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    try {
        Register-ScheduledTask -TaskName "HERMES_Daemon" `
            -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
        Write-Log "  Unique Scheduled Task 'HERMES_Daemon' creee avec succes" "SUCCESS"
    } catch {
        Write-Log "  Scheduled Task HERMES_Daemon non creee ($($_.Exception.Message))" "WARN"
        $startupDir = [Environment]::GetFolderPath("Startup")
        $startupScript = Join-Path $startupDir "DEV_CORE_HERMES_Daemon.cmd"
        $daemonScript = Join-Path $PSScriptRoot "hermes-daemon.ps1"
        $cmd = "@echo off`r`npowershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$daemonScript`" -Start`r`n"
        Set-Content -LiteralPath $startupScript -Value $cmd -Encoding ASCII
        Write-Log "  Fallback non-admin cree dans Startup: $startupScript" "SUCCESS"
    }

    # Synchroniser les tâches cron config
    Do-SyncJobs

    Write-Log "Installation terminee. Le daemon s'exécutera au demarrage du PC." "SUCCESS"
}

function Do-Uninstall {
    Write-Log "Desinstallation du daemon HERMES" "WARN"

    $tasks = @("HERMES_Daemon", "DEV_CORE_Daily_Launch", "DEV_CORE_Daily_Endday", "DEV_CORE_Weekly_Maintenance", "DEV_CORE_Event_Watcher", "DEV_CORE_Integrity_Check")

    foreach ($taskName in $tasks) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Log "  Tache planifiee $taskName supprimee" "INFO"
        }
    }

    $startupScript = Join-Path ([Environment]::GetFolderPath("Startup")) "DEV_CORE_HERMES_Daemon.cmd"
    if (Test-Path $startupScript) {
        Remove-Item -LiteralPath $startupScript -Force
        Write-Log "  Fallback Startup supprime: $startupScript" "INFO"
    }

    Do-Stop
    Write-Log "Desinstallation terminee" "SUCCESS"
}

function Do-Start {
    Write-Log "Demarrage du daemon HERMES Tick Loop" "INFO"

    # Verifier si deja running
    $proc = Get-HermesCronRootProcesses
    if ($proc) {
        Write-Log "  Le daemon HERMES tourne deja (PID: $($proc.ProcessId))" "WARN"
        return
    }

    # Configurer les variables d'environnement
    $env:DEVCORE_PLATFORM_ROOT = "C:\devcore\DEV_CORE"
    $env:DEVCORE_DATA_ROOT = "C:\devcore\DEV_CORE_DATA"

    # Lancer les services DEV_CORE (launch.ps1) en arrière-plan au démarrage
    $launchScript = "$DEVCORE_ROOT\Scripts\launch.ps1"
    if (Test-Path $launchScript) {
        Write-Log "  Lancement des services DEV_CORE (launch.ps1) en arriere-plan..." "INFO"
        Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launchScript`"" } | Out-Null
    } else {
        Write-Log "  Script de lancement non trouve a $launchScript" "WARN"
    }

    # Lancer hermes_cron_tick.py en background (mode detache WMI)
    $pythonBin = Resolve-HermesPython
    $tickScript = "$DEVCORE_ROOT\Scripts\hermes_cron_tick.py"
    if (-not (Test-Path $tickScript)) {
        Write-Log "  Tick loop script non trouve a $tickScript" "ERROR"
        return
    }

    $commandLine = "$(Quote-CommandArgument $pythonBin) $(Quote-CommandArgument $tickScript)"
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $commandLine } | Out-Null
    Write-Log "  Daemon hermes_cron_tick.py lance avec succes en tache de fond via $pythonBin" "SUCCESS"
}

function Do-Stop {
    Write-Log "Arret du daemon HERMES Tick Loop" "INFO"

    # Trouver et arreter la tache
    $procs = @(Get-HermesCronProcesses | Sort-Object ParentProcessId -Descending)
    if ($procs) {
        foreach ($p in $procs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log "  Daemon arrete (PID: $($p.ProcessId))" "SUCCESS"
        }
    } else {
        Write-Log "  Aucun daemon running trouve" "INFO"
    }
}

function Do-Status {
    Write-Log "Status du daemon HERMES" "INFO"

    # Trouver le processus
    $proc = Get-HermesCronRootProcesses
    if ($proc) {
        $pids = ($proc | Select-Object -ExpandProperty ProcessId) -join ","
        Write-Log "  Daemon Status: RUNNING (PID: $pids)" "SUCCESS"
        foreach ($p in $proc) {
            Write-Log "  Command line [$($p.ProcessId)]: $($p.CommandLine)" "Gray"
        }
    } else {
        Write-Log "  Daemon Status: STOPPED" "WARN"
    }

    # Afficher l'etat des taches dans jobs.json
    $jobsFile = "$HERMES_HOME\cron\jobs.json"
    if (Test-Path $jobsFile) {
        Write-Log "" "INFO"
        Write-Log "Taches planifiees enregistrees dans Hermes (jobs.json):" "INFO"
        try {
            $jobs = Get-Content $jobsFile -Raw | ConvertFrom-Json
            foreach ($j in $jobs.jobs) {
                $statusColor = if ($j.enabled) { "SUCCESS" } else { "WARN" }
                $lastStatus = if ($j.last_status) { $j.last_status } else { "never run" }
                Write-Log "  - $($j.name) : $(if($j.enabled){'Actif'}else{'Desactive'}) | Schedule: $($j.schedule_display) | Dernier run: $lastStatus (Next: $($j.next_run_at))" $statusColor
            }
        } catch {
            Write-Log "  Erreur de lecture de jobs.json" "ERROR"
        }
    }
}

function Do-SyncJobs {
    Write-Log "Synchronisation des tâches dans Hermes..." "INFO"
    $pythonBin = Resolve-HermesPython
    $syncScript = "$DEVCORE_ROOT\Scripts\Auto\sync_cron_jobs.py"
    $result = subprocess_run -FilePath $pythonBin -ArgumentList (Quote-CommandArgument $syncScript)
    Write-Log "  Jobs synchronises avec jobs.json avec succes via $pythonBin." "SUCCESS"
}

# Helper pour executer de maniere synchrone sous powershell
function subprocess_run {
    param($FilePath, $ArgumentList)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = $ArgumentList
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.WaitForExit()
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    if ($p.ExitCode -ne 0) {
        throw "Script failed: $err"
    }
    return $out
}

function Do-Test {
    Write-Log "Test de la configuration du daemon" "INFO"
    try {
        $pythonBin = Resolve-HermesPython
        Write-Log "  Python binaire: OK ($pythonBin)" "SUCCESS"
    } catch {
        Write-Log "  Python binaire: NON TROUVE ($($_.Exception.Message))" "ERROR"
    }
    
    $tickScript = "$DEVCORE_ROOT\Scripts\hermes_cron_tick.py"
    if (Test-Path $tickScript) {
        Write-Log "  Tick loop script: OK" "SUCCESS"
    } else {
        Write-Log "  Tick loop script: NON TROUVE" "ERROR"
    }
}

# ========== MAIN ==========

Write-Host ""
Write-Host "  HERMES DEV_CORE Daemon Manager v9.0" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

switch ($true) {
    { $Install }    { Do-Install }
    { $Uninstall }  { Do-Uninstall }
    { $Start }       { Do-Start }
    { $Stop }        { Do-Stop }
    { $Status }     { Do-Status }
    { $Test }       { Do-Test }
    { $SyncJobs }   { Do-SyncJobs }
    default {
        Write-Log "Usage: hermes-daemon.ps1 [-Install|-Uninstall|-Start|-Stop|-Status|-Test|-SyncJobs]" "WARN"
        Write-Log "" "INFO"
        Write-Log "Commands:" "INFO"
        Write-Log "  -Install     Installe le unique daemon + scheduled task" "INFO"
        Write-Log "  -Uninstall  Desinstalle tout le daemon" "INFO"
        Write-Log "  -Start       Demarre le daemon de tick en background" "INFO"
        Write-Log "  -Stop        Arrete le daemon de tick" "INFO"
        Write-Log "  -Status      Affiche le status du tick loop + jobs" "INFO"
        Write-Log "  -SyncJobs    Force la synchronisation hermes_cron.yaml" "INFO"
        Write-Log "  -Test        Test la configuration" "INFO"
    }
}

Write-Host ""
