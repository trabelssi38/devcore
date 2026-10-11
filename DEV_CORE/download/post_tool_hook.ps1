# Legacy entry point: use the project-local hook for telemetry only.
$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\post_tool_hook.ps1'
& $target
exit $LASTEXITCODE
