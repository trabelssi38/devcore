# Legacy entry point: select a task in one explicit project through TaskService.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$Project
)

$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\task_next.ps1'
& $target --project $Project
exit $LASTEXITCODE
