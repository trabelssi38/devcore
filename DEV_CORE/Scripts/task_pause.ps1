# task_pause.ps1 -- DEV_CORE v9.0 single client
& "$PSScriptRoot\task_service.ps1" -Action Pause
Start-Process powershell -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$PSScriptRoot\gen_dashboard.ps1`"" -WindowStyle Hidden
