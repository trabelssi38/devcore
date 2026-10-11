param(
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Id,
    [string]$Title,
    [ValidateSet("coding", "reasoning", "bulk")][string]$Mode,
    [int]$Steps,
    [int]$ExpectedVersion
)

$editArgs = @{ Action = "Edit"; Project = $Project; Id = $Id }
if ($PSBoundParameters.ContainsKey("Title")) { $editArgs.Title = $Title }
if ($PSBoundParameters.ContainsKey("Mode")) { $editArgs.Mode = $Mode }
if ($PSBoundParameters.ContainsKey("Steps")) { $editArgs.Steps = $Steps }
if ($PSBoundParameters.ContainsKey("ExpectedVersion")) { $editArgs.ExpectedVersion = $ExpectedVersion }
& (Join-Path $PSScriptRoot "task_service.ps1") @editArgs
exit $LASTEXITCODE
