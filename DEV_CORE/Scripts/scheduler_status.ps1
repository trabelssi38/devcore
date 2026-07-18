# scheduler_status.ps1 -- DEV_CORE -- Show scheduler status
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
& "$PSScriptRoot\dc.ps1" scheduler status
