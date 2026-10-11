# Legacy Claude hook entry point: use the current per-project session lifecycle.
$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\session_start.ps1'
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "Session lifecycle unavailable: $target"
}
& $target @args
exit $LASTEXITCODE
