param(
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Project,
    [string]$Id,
    [int]$ExpectedVersion
)

$taskArgs = @{ Action = "Resume"; Project = $Project; Id = $Id }
if ($PSBoundParameters.ContainsKey("ExpectedVersion")) { $taskArgs.ExpectedVersion = $ExpectedVersion }
& (Join-Path $PSScriptRoot "task_service.ps1") @taskArgs
exit $LASTEXITCODE
