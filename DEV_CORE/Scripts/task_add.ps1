# task_add.ps1 -- DEV_CORE v10 Task Service adapter
param(
    [Parameter(Mandatory=$true)][string]$Title,
    [ValidateSet("reasoning","coding","bulk")][string]$Mode = "coding",
    [string]$DependsOn = ""
)

& "$PSScriptRoot\task_service.ps1" -Action Add -Title $Title -Mode $Mode -DependsOn $DependsOn

& "$PSScriptRoot\gen_dashboard.ps1"
