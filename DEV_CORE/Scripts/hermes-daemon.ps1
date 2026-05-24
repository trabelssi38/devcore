# hermes-daemon.ps1 -- DEV_CORE v7.3 + Hermes Standalone Daemon
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
$HERMES_HOME  = "$env:USERPROFILE\.hermes"
$DEVCORE_ROOT = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$PYTHON_BIN   = "C:\devcore\hermes_temp\.venv\Scripts\python.exe"
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

    Register-ScheduledTask -TaskName "HERMES_Daemon" `
        -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Log "  Unique Scheduled Task 'HERMES_Daemon' creee avec succes" "SUCCESS"

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

    Do-Stop
    Write-Log "Desinstallation terminee" "SUCCESS"
}

function Do-Start {
    Write-Log "Demarrage du daemon HERMES Tick Loop" "INFO"

    # Verifier si deja running
    $proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hermes_cron_tick.py' }
    if ($proc) {
        Write-Log "  Le daemon HERMES tourne deja (PID: $($proc.ProcessId))" "WARN"
        return
    }

    # Configurer les variables d'environnement
    $env:DEVCORE_PLATFORM_ROOT = "C:\devcore\DEV_CORE"
    $env:DEVCORE_DATA_ROOT = "C:\devcore\DEV_CORE_DATA"

    # Lancer hermes_cron_tick.py en background (mode detache WMI)
    if (Test-Path $PYTHON_BIN) {
        $tickScript = "$DEVCORE_ROOT\Scripts\hermes_cron_tick.py"
        Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "$PYTHON_BIN $tickScript" } | Out-Null
        Write-Log "  Daemon hermes_cron_tick.py lance avec succes en tâche de fond" "SUCCESS"
    } else {
        Write-Log "  Python binaire non trouve a $PYTHON_BIN" "ERROR"
    }
}

function Do-Stop {
    Write-Log "Arret du daemon HERMES Tick Loop" "INFO"

    # Trouver et arreter la tache
    $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hermes_cron_tick.py' }
    if ($procs) {
        foreach ($p in $procs) {
            Stop-Process -Id $p.ProcessId -Force
            Write-Log "  Daemon arrete (PID: $($p.ProcessId))" "SUCCESS"
        }
    } else {
        Write-Log "  Aucun daemon running trouve" "INFO"
    }
}

function Do-Status {
    Write-Log "Status du daemon HERMES" "INFO"

    # Trouver le processus
    $proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hermes_cron_tick.py' }
    if ($proc) {
        Write-Log "  Daemon Status: RUNNING (PID: $($proc.ProcessId))" "SUCCESS"
        Write-Log "  Command line: $($proc.CommandLine)" "Gray"
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
    if (Test-Path $PYTHON_BIN) {
        $syncScript = "$DEVCORE_ROOT\Scripts\Auto\sync_cron_jobs.py"
        $result = subprocess_run -FilePath $PYTHON_BIN -ArgumentList $syncScript
        Write-Log "  Jobs synchronises avec jobs.json avec succes." "SUCCESS"
    } else {
        Write-Log "  Python binaire manquant" "ERROR"
    }
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
    if (Test-Path $PYTHON_BIN) {
        Write-Log "  Python binaire: OK" "SUCCESS"
    } else {
        Write-Log "  Python binaire: NON TROUVE" "ERROR"
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
Write-Host "  HERMES DEV_CORE Daemon Manager v7.3" -ForegroundColor Cyan
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