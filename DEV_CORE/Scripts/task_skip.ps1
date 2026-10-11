param(
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Project,
    [string]$Id,
    [string]$Reason = "",
    [int]$ExpectedVersion
)

$taskArgs = @{ Action = "Skip"; Project = $Project; Id = $Id; Reason = $Reason }
if ($PSBoundParameters.ContainsKey("ExpectedVersion")) { $taskArgs.ExpectedVersion = $ExpectedVersion }
& (Join-Path $PSScriptRoot "task_service.ps1") @taskArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $PSScriptRoot "task_next.ps1") --project $Project
exit $LASTEXITCODE
