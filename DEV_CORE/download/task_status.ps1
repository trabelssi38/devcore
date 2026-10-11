# Legacy entry point: display the board for one explicit project.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$Project
)

$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\task_status.ps1'
& $target -Project $Project
exit $LASTEXITCODE
