# test_plugin_isolation.ps1 -- contract tests for isolated plugin execution
$ErrorActionPreference = "Stop"

$pluginServiceScript = Join-Path $PSScriptRoot "plugin_service.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_plugin_isolation_test_" + [guid]::NewGuid().ToString("n"))
$dataRoot = Join-Path $tmpRoot "DEV_CORE_DATA"
$packageRoot = Join-Path $tmpRoot "packages\isolated-plugin"
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$oldLeak = $env:DEVCORE_LEAK_TEST

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    $env:DEVCORE_DATA_ROOT = $dataRoot
    $env:DEVCORE_LEAK_TEST = "parent-secret-should-not-leak"
    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null

    $manifestPath = Join-Path $packageRoot "plugin.json"
    [pscustomobject][ordered]@{
        schema_version = 1
        id = "isolated-plugin"
        name = "Isolated Plugin"
        version = "0.1.0"
        description = "Plugin isolation test"
        capabilities = [ordered]@{
            commands = @()
            skills = @()
            health_checks = @(
                [ordered]@{
                    id = "isolation-contract"
                    command = @'
Write-Output "cwd=$((Get-Location).Path)"
Write-Output "plugin=$env:DEVCORE_PLUGIN_ID"
Write-Output "data=$env:DEVCORE_PLUGIN_DATA_ROOT"
if ($env:DEVCORE_LEAK_TEST) { Write-Output "leak=$env:DEVCORE_LEAK_TEST" }
'@
                    required = $true
                    timeout_seconds = 5
                }
            )
            widgets = @()
            templates = @()
        }
        permissions = [ordered]@{
            write_roots = @("data")
            allow_out_of_scope_write = $false
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $installJson = & $pluginServiceScript -Action Install -ManifestPath $manifestPath -Json | Out-String
    $install = $installJson | ConvertFrom-Json
    Assert-True ($install.ok -eq $true) "Install should succeed"

    $checkJson = & $pluginServiceScript -Action Check -Id "isolated-plugin" -Json | Out-String
    $check = $checkJson | ConvertFrom-Json
    Assert-True ($check.ok -eq $true) "Isolated health check should pass"

    $health = $check.health_checks | Select-Object -First 1
    $expectedDataRoot = Join-Path $dataRoot "Plugins\isolated-plugin"

    Assert-True ($health.isolated_process -eq $true) "Health check should report isolated_process=true"
    Assert-True ($health.process_id -gt 0) "Health check should report child process id"
    Assert-True ($health.working_directory -eq $expectedDataRoot) "Health check should run from plugin data root"
    Assert-True ($health.stdout -match [regex]::Escape("cwd=$expectedDataRoot")) "Plugin stdout should show isolated cwd"
    Assert-True ($health.stdout -match "plugin=isolated-plugin") "Plugin env should expose plugin id"
    Assert-True ($health.stdout -match [regex]::Escape("data=$expectedDataRoot")) "Plugin env should expose plugin data root"
    Assert-True ($health.stdout -notmatch "parent-secret-should-not-leak") "Plugin process must not inherit parent leak variable"

    Write-Host "[OK] plugin isolation tests passed"
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    if ($null -eq $oldLeak) {
        Remove-Item Env:\DEVCORE_LEAK_TEST -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_LEAK_TEST = $oldLeak
    }

    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
