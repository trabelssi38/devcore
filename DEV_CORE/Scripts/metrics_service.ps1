# Local metrics entry point. The events CLI does not implement this contract.
$ErrorActionPreference = 'Stop'
$pythonExe = if ($env:DEVCORE_PYTHON -and (Test-Path -LiteralPath $env:DEVCORE_PYTHON)) {
    $env:DEVCORE_PYTHON
} else {
    $command = Get-Command python -ErrorAction Stop
    $command.Source
}
& $pythonExe (Join-Path $PSScriptRoot 'metrics_service.py') @args
exit $LASTEXITCODE
