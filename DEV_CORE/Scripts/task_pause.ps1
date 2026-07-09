# task_pause.ps1 -- DEV_CORE v9.0 single client
& "$PSScriptRoot\task_service.ps1" -Action Pause
& "$PSScriptRoot\gen_dashboard.ps1"
