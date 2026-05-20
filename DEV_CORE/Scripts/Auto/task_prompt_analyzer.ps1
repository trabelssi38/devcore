# task_prompt_analyzer.ps1 -- DEV_CORE v6 Auto layer
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\task_prompt_analyzer_$TODAY.log"

function Log { param($msg,$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Log "task_prompt_analyzer -- delegating to Python Live Antigravity prompt analyzer" "Cyan"
try {
    python "$DEV_CORE\Scripts\Auto\task_prompt_analyzer.py"
} catch {
    Log "Erreur lors du lancement de task_prompt_analyzer.py : $_" "Red"
}
