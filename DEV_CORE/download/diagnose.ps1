# Legacy diagnostic entry point: delegate to the current diagnostic engine.
$target = Join-Path (Split-Path -Parent $PSScriptRoot) 'Scripts\diagnose.ps1'
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "Diagnostic lifecycle unavailable: $target"
}
& $target @args
exit $LASTEXITCODE
