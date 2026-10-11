# Compatibility launcher for the project-local Python post-tool hook.
# Project selection is made only from .devcore/project.json in the caller's cwd;
# the machine-wide active-project setting and legacy tasks.json are never read.
$platformRoot = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT 'devcore_engine\hooks\post_tool.py'))) {
    [IO.Path]::GetFullPath($env:DEVCORE_PLATFORM_ROOT)
} else {
    [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
}
$hook = Join-Path $platformRoot 'devcore_engine\hooks\post_tool.py'
if (-not (Test-Path -LiteralPath $hook -PathType Leaf)) {
    Write-Warning "Project-scoped post-tool hook unavailable: $hook"
    exit 0
}

$pythonExe = if ($env:DEVCORE_PYTHON -and (Test-Path -LiteralPath $env:DEVCORE_PYTHON -PathType Leaf)) {
    $env:DEVCORE_PYTHON
} else {
    $pythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pythonCommand) { $pythonCommand.Source }
}
if (-not $pythonExe) {
    Write-Warning 'Project-scoped post-tool hook skipped: Python runtime unavailable.'
    exit 0
}

& $pythonExe $hook
exit $LASTEXITCODE
