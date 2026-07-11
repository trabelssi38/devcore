# test_internal_plugins.ps1 -- smoke tests for bundled DEV_CORE plugin manifests
$ErrorActionPreference = "Stop"

$pluginServiceScript = Join-Path $PSScriptRoot "plugin_service.ps1"
$platformRoot = Split-Path -Parent $PSScriptRoot
$pluginsRoot = Join-Path $platformRoot "Plugins"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_internal_plugins_test_" + [guid]::NewGuid().ToString("n"))
$dataRoot = Join-Path $tmpRoot "DEV_CORE_DATA"
$oldDataRoot = $env:DEVCORE_DATA_ROOT

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    $env:DEVCORE_DATA_ROOT = $dataRoot

    $expectedPlugins = @(
        "python-fastapi",
        "web-react",
        "android-gradle"
    )

    foreach ($pluginId in $expectedPlugins) {
        $manifestPath = Join-Path $pluginsRoot "$pluginId\plugin.json"
        Assert-True (Test-Path -LiteralPath $manifestPath) "Internal plugin manifest missing: $pluginId"

        $installJson = & $pluginServiceScript -Action Install -ManifestPath $manifestPath -Json | Out-String
        $install = $installJson | ConvertFrom-Json
        Assert-True ($install.ok -eq $true) "Internal plugin should install: $pluginId"
        Assert-True ($install.plugin.id -eq $pluginId) "Installed plugin id mismatch: $pluginId"
        Assert-True ($install.plugin.enabled -eq $true) "Internal plugin should be enabled by default: $pluginId"
    }

    $listJson = & $pluginServiceScript -Action List -Json | Out-String
    $list = $listJson | ConvertFrom-Json
    Assert-True ($list.plugins_count -eq 3) "List should include three internal plugins"

    foreach ($pluginId in $expectedPlugins) {
        $diagnoseJson = & $pluginServiceScript -Action Diagnose -Id $pluginId -Json | Out-String
        $diagnose = $diagnoseJson | ConvertFrom-Json
        Assert-True ($diagnose.ok -eq $true) "Internal plugin should diagnose cleanly: $pluginId"
        Assert-True ($diagnose.scope_violations_count -eq 0) "Internal plugin should stay within scope: $pluginId"
    }

    Write-Host "[OK] internal plugin manifests smoke tests passed"
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
