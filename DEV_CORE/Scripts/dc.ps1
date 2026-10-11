# Delegator wrapper for Python devcore_engine CLI
if ($args.Count -gt 0 -and $args[0] -ceq 'individual') {
    # Never source platform_version.ps1: its historical bootstrap discovers Dropbox.
    $individualPython = if ($env:DEVCORE_PYTHON -and (Test-Path -LiteralPath $env:DEVCORE_PYTHON -PathType Leaf)) {
        $env:DEVCORE_PYTHON
    } else {
        $individualPythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
        if ($individualPythonCommand) { $individualPythonCommand.Source }
    }
    if (-not $individualPython) {
        Write-Output '{"success":false,"code":"invalid_configuration","error":"Python executable required"}'
        exit 2
    }
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
    $individualArguments = @($args | Select-Object -Skip 1)
    & $individualPython (Join-Path $PSScriptRoot 'individual_project_client.py') @individualArguments
    exit $LASTEXITCODE
}

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$DEV_CORE*") {
    $env:PYTHONPATH = if ($env:PYTHONPATH) { "$DEV_CORE;$env:PYTHONPATH" } else { $DEV_CORE }
}
. (Join-Path $PSScriptRoot "platform_version.ps1")
$pythonExe = Get-DevCorePython
& $pythonExe -m devcore_engine.cli $args
exit $LASTEXITCODE
