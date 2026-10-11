# Legacy entry point: add a task in one explicit project through TaskService.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [string]$Project,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Title,
    [ValidateSet('reasoning', 'coding', 'bulk')][string]$Mode = 'coding',
    [string]$DependsOn = ''
)

$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\task_add.ps1'
$taskArgs = @{ Project = $Project; Title = $Title; Mode = $Mode }
if ($DependsOn) { $taskArgs.DependsOn = $DependsOn }
& $target @taskArgs
exit $LASTEXITCODE
