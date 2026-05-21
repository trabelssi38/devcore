# event_watcher.ps1 -- DEV_CORE v7 -- Hermes Event Bus Consumer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$EVENTS_DIR    = "$DEV_CORE_DATA\Bus\events"
$PROCESSED_DIR = "$DEV_CORE_DATA\Bus\processed"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\event_watcher_$(Get-Date -f 'yyyy-MM-dd').log"

# Créer les dossiers
foreach ($d in @($EVENTS_DIR, $PROCESSED_DIR)) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] [EVENT_WATCHER] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

# Lire les événements non traités
$events = Get-ChildItem "$EVENTS_DIR\*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime
if ($events.Count -eq 0) { exit 0 }

Log "Processing $($events.Count) events" "Cyan"

foreach ($evtFile in $events) {
    try {
        $evt = Get-Content $evtFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        
        switch ($evt.type) {
            "post-commit" {
                Log "POST-COMMIT: task=$($evt.task_id) msg=$($evt.commit_msg)" "Gray"
                # Déclencher scan + sync + dashboard
                & "$DEV_CORE\Scripts\task_scan.ps1" 2>&1 | Out-Null
                & "$DEV_CORE\Scripts\task_sync.ps1" 2>&1 | Out-Null
                Log "Scan + Sync + Dashboard completed" "Green"
            }
            "task_completed" {
                Log "TASK_COMPLETED: $($evt.task_id)" "Gray"
                & "$DEV_CORE\Scripts\task_done.ps1" -Force 2>&1 | Out-Null
            }
            "session_end" {
                Log "SESSION_END" "Gray"
                & "$DEV_CORE\Scripts\session_end.ps1" 2>&1 | Out-Null
            }
            default {
                Log "Unknown event type: $($evt.type)" "Yellow"
            }
        }
        
        # Archiver l'événement traité
        Move-Item $evtFile.FullName "$PROCESSED_DIR\$($evtFile.Name)" -Force
        
    } catch {
        Log "ERROR processing $($evtFile.Name): $_" "Red"
    }
}
