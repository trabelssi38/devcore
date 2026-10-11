# Legacy entry point: use the project-scoped transactional task adapter.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [ValidateNotNullOrEmpty()]
    [string]$Project,
    [string]$TaskId,
    [int]$ExpectedVersion,
    [switch]$Force
)

$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\task_done.ps1'
& $target @PSBoundParameters
exit $LASTEXITCODE
