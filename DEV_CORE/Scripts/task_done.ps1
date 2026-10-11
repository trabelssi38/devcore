# Complete one task through the transactional service for an explicit project.
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$')]
    [ValidateNotNullOrEmpty()]
    [string]$Project,
    [string]$TaskId,
    [int]$ExpectedVersion,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Project)) { throw 'Projet requis.' }

$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and
    (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT 'devcore_engine\cli.py') -PathType Leaf)) {
    [IO.Path]::GetFullPath($env:DEVCORE_PLATFORM_ROOT)
} else {
    [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$platformRoot*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$platformRoot;$env:PYTHONPATH" } else { $platformRoot }
}
$pythonExe = if ($env:DEVCORE_PYTHON -and (Test-Path -LiteralPath $env:DEVCORE_PYTHON -PathType Leaf)) {
    $env:DEVCORE_PYTHON
} else {
    $pythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pythonCommand) { $pythonCommand.Source }
}
if (-not $pythonExe) { throw 'Runtime Python DevCore introuvable.' }

$completeArgs = @('task', 'complete')
if ($TaskId) { $completeArgs += $TaskId }
$completeArgs += @('--project', $Project)
if ($PSBoundParameters.ContainsKey('ExpectedVersion')) {
    $completeArgs += @('--expected-version', [string]$ExpectedVersion)
}
# -Force is accepted for old callers but never bypasses project/version checks.
& $pythonExe -m devcore_engine.cli @completeArgs
exit $LASTEXITCODE
