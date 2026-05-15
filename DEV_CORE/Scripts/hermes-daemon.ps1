# hermes-daemon.ps1 -- DEV_CORE v6.1 + Hermes Agent Daemon
# Service Windows pour HERMES en daemon avec cron DEV_CORE
# Option A: PowerShell Service

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Test
)

$ErrorActionPreference = "Stop"
$HERMES_HOME = "$env:USERPROFILE\.hermes"
$DEVCORE_ROOT = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$HERMES_BIN   = if ($env:HERMES_BIN) { $env:HERMES_BIN } else { "C:\devcore\hermes_temp\.venv\Scripts\hermes.exe" }
$LOG_DIR = "$DEVCORE_ROOT\Logs\hermes"
$LOG_FILE = "$LOG_DIR\daemon_$(Get-Date -Format 'yyyy-MM-dd').log"

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

function Get-ScheduledTaskStatus {
    $tasks = @("DEV_CORE_Daily_Launch", "DEV_CORE_Daily_Endday", "DEV_CORE_Weekly_Maintenance", "HERMES_Daemon")
    $status = @()
    foreach ($taskName in $tasks) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            $info = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
            $status += [PSCustomObject]@{
                Name = $taskName
                State = $task.State
                LastRun = $info.LastRunTime
                NextRun = $info.NextRunTime
            }
        }
    }
    return $status
}

# ========== COMMANDS ==========

function Do-Install {
    Write-Log "Installation du daemon HERMES DEV_CORE" "INFO"

    # 1. HERMES daemon (tache planifiee qui lance hermes en background)
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -File `"$PSScriptRoot\hermes-daemon.ps1`" -Start"

    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    Register-ScheduledTask -TaskName "HERMES_Daemon" `
        -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Log "  Tache planifiee HERMES_Daemon creee" "SUCCESS"

    # 2. DEV_CORE cron tasks
    $cronTasks = @(
        @{
            Name = "DEV_CORE_Daily_Launch"
            Time = "10:00"
            Script = "$DEVCORE_ROOT\Scripts\launch.ps1"
            Desc = "Demarrage quotidien DEV_CORE - 10h"
        },
        @{
            Name = "DEV_CORE_Daily_Endday"
            Time = "04:00"
            Script = "$DEVCORE_ROOT\Scripts\endday.ps1"
            Desc = "Cloture quotidienne DEV_CORE - 4h"
        },
        @{
            Name = "DEV_CORE_Weekly_Maintenance"
            DayOfWeek = "Sunday"
            Time = "05:00"
            Script = "$DEVCORE_ROOT\Scripts\Auto\weekly_maintenance.ps1"
            Desc = "Maintenance hebdomadaire DEV_CORE - Dimanche 5h"
        }
    )

    foreach ($task in $cronTasks) {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$($task.Script)`""

        if ($task.DayOfWeek) {
            $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $task.DayOfWeek -At $task.Time
        } else {
            $trigger = New-ScheduledTaskTrigger -Daily -At $task.Time
        }

        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable

        Register-ScheduledTask -TaskName $task.Name `
            -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

        Write-Log "  Tache planifiee $($task.Name) creee - $($task.Desc)" "SUCCESS"
    }

    Write-Log "Installation terminee" "SUCCESS"
}

function Do-Uninstall {
    Write-Log "Desinstallation du daemon HERMES" "WARN"

    $tasks = @("HERMES_Daemon", "DEV_CORE_Daily_Launch", "DEV_CORE_Daily_Endday", "DEV_CORE_Weekly_Maintenance")

    foreach ($taskName in $tasks) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Log "  Tache $taskName supprimee" "INFO"
        }
    }

    Write-Log "Desinstallation terminee" "SUCCESS"
}

function Do-Start {
    Write-Log "Demarrage du daemon HERMES" "INFO"

    # Lancer hermes en mode background
    $hermesArgs = @("daemon", "--config", "$HERMES_HOME\config.yaml")

    # Configurer les variables d'environnement
    $env:DEVCORE_PLATFORM_ROOT = "C:\devcore\DEV_CORE"
    $env:DEVCORE_DATA_ROOT = "C:\devcore\DEV_CORE_DATA"

    # Lancer HERMES
    if (Test-Path $HERMES_BIN) {
        Start-Process -FilePath $HERMES_BIN -ArgumentList $hermesArgs -WindowStyle Hidden -PassThru
        Write-Log "  HERMES lance en background" "SUCCESS"
    } else {
        Write-Log "  HERMES non trouve a $HERMES_BIN" "ERROR"
    }
}

function Do-Stop {
    Write-Log "Arret du daemon HERMES" "INFO"

    # arreter tous les processus hermes
    Get-Process -Name "hermes" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Log "  Processus HERMES arretes" "SUCCESS"
}

function Do-Status {
    Write-Log "Status du daemon HERMES" "INFO"

    # Status HERMES
    $hermesProc = Get-Process -Name "hermes" -ErrorAction SilentlyContinue
    if ($hermesProc) {
        Write-Log "  HERMES: RUNNING (PID: $($hermesProc.Id))" "SUCCESS"
    } else {
        Write-Log "  HERMES: STOPPED" "WARN"
    }

    # Status tache planifiee
    Write-Log "" "INFO"
    Write-Log "Taches planifiees DEV_CORE:" "INFO"
    $status = Get-ScheduledTaskStatus
    foreach ($s in $status) {
        Write-Log "  $($s.Name): $($s.State) | Prochain: $($s.NextRun)" "INFO"
    }
}

function Do-Test {
    Write-Log "Test du daemon HERMES" "INFO"

    # Test Hermes binaire
    if (Test-Path $HERMES_BIN) {
        $version = & $HERMES_BIN --version 2>&1
        Write-Log "  Hermes binaire: OK ($version)" "SUCCESS"
    } else {
        Write-Log "  Hermes binaire: NON TROUVE" "ERROR"
    }

    # Test chemins
    $paths = @(
        "C:\devcore\DEV_CORE\Scripts",
        "C:\devcore\DEV_CORE_DATA\Memory",
        "C:\devcore\DEV_CORE_DATA\Vault",
        "$HERMES_HOME\config.yaml"
    )

    Write-Log "" "INFO"
    Write-Log "Chemins DEV_CORE:" "INFO"
    foreach ($p in $paths) {
        $exists = Test-Path $p
        $color = if ($exists) { "SUCCESS" } else { "ERROR" }
        Write-Log "  $p : $(if ($exists) { 'OK' } else { 'MANQUANT' })" $color
    }

    # Test services
    Write-Log "" "INFO"
    Write-Log "Services:" "INFO"

    # Qdrant
    try {
        $q = Invoke-RestMethod "http://localhost:6333/" -TimeoutSec 3
        Write-Log "  Qdrant (6333): OK" "SUCCESS"
    } catch {
        Write-Log "  Qdrant (6333): NON ACCESSIBLE" "WARN"
    }

    # Ollama
    try {
        $o = Invoke-RestMethod "http://localhost:11434/api/version" -TimeoutSec 3
        Write-Log "  Ollama (11434): OK" "SUCCESS"
    } catch {
        Write-Log "  Ollama (11434): NON ACCESSIBLE" "WARN"
    }

    Write-Log "" "INFO"
    Write-Log "Test termine" "SUCCESS"
}

# ========== MAIN ==========

Write-Host ""
Write-Host "  HERMES DEV_CORE Daemon v6.1" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

switch ($true) {
    { $Install }    { Do-Install }
    { $Uninstall }  { Do-Uninstall }
    { $Start }       { Do-Start }
    { $Stop }        { Do-Stop }
    { $Status }     { Do-Status }
    { $Test }       { Do-Test }
    default {
        Write-Log "Usage: hermes-daemon.ps1 [-Install|-Uninstall|-Start|-Stop|-Status|-Test]" "WARN"
        Write-Log "" "INFO"
        Write-Log "Commands:" "INFO"
        Write-Log "  -Install     Installe le daemon + tache planifiee Windows" "INFO"
        Write-Log "  -Uninstall  Desinstalle le daemon" "INFO"
        Write-Log "  -Start       Demarre HERMES en background" "INFO"
        Write-Log "  -Stop        Arrete HERMES" "INFO"
        Write-Log "  -Status      Affiche le status du daemon" "INFO"
        Write-Log "  -Test        Test la configuration" "INFO"
    }
}

Write-Host ""