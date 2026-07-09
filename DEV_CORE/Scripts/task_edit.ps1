# task_edit.ps1 -- DEV_CORE v9.0 single client
param(
    [Parameter(Mandatory=$true)][string]$Id,
    [string]$Title,
    [string]$Mode,
    [int]$Steps
)

$editArgs = @{
    Action = "Edit"
    Id = $Id
}

if ($PSBoundParameters.ContainsKey("Title")) { $editArgs.Title = $Title }
if ($PSBoundParameters.ContainsKey("Mode"))  { $editArgs.Mode = $Mode }
if ($PSBoundParameters.ContainsKey("Steps")) { $editArgs.Steps = $Steps }

& "$PSScriptRoot\task_service.ps1" @editArgs
& "$PSScriptRoot\gen_dashboard.ps1"
