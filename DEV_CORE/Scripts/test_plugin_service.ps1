# test_plugin_service.ps1 -- smoke tests for DEV_CORE Plugin SDK v1
$ErrorActionPreference = "Stop"

$pluginServiceScript = Join-Path $PSScriptRoot "plugin_service.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_plugin_service_test_" + [guid]::NewGuid().ToString("n"))
$dataRoot = Join-Path $tmpRoot "DEV_CORE_DATA"
$packageRoot = Join-Path $tmpRoot "packages\python-fastapi"
$oldDataRoot = $env:DEVCORE_DATA_ROOT

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    $env:DEVCORE_DATA_ROOT = $dataRoot
    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null

    $manifestPath = Join-Path $packageRoot "plugin.json"
    [pscustomobject][ordered]@{
        schema_version = 1
        id = "python-fastapi"
        name = "Python FastAPI"
        version = "0.1.0"
        description = "FastAPI project helpers"
        capabilities = [ordered]@{
            commands = @("python-api:new-endpoint")
            skills = @("python_api")
            health_checks = @(
                [ordered]@{
                    id = "required-pass"
                    command = "Write-Output 'plugin-ok'"
                    required = $true
                    timeout_seconds = 5
                },
                [ordered]@{
                    id = "optional-fail"
                    command = "exit 7"
                    required = $false
                    timeout_seconds = 5
                }
            )
            widgets = @()
            templates = @("fastapi-endpoint")
        }
        permissions = [ordered]@{
            write_roots = @("data", "cache")
            allow_out_of_scope_write = $false
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Assert-True (Test-Path -LiteralPath $pluginServiceScript) "plugin_service.ps1 should exist"

    $installJson = & $pluginServiceScript -Action Install -ManifestPath $manifestPath -Json | Out-String
    $install = $installJson | ConvertFrom-Json
    Assert-True ($install.ok -eq $true) "Install should succeed for scoped plugin"
    Assert-True ($install.plugin.id -eq "python-fastapi") "Install should preserve plugin id"
    Assert-True (Test-Path -LiteralPath $install.installed_manifest_path) "Install should write installed manifest"

    $listJson = & $pluginServiceScript -Action List -Json | Out-String
    $list = $listJson | ConvertFrom-Json
    Assert-True ($list.plugins_count -eq 1) "List should return installed plugin"
    Assert-True ($list.plugins[0].enabled -eq $true) "Installed plugin should be enabled by default"

    $diagnoseJson = & $pluginServiceScript -Action Diagnose -Id "python-fastapi" -Json | Out-String
    $diagnose = $diagnoseJson | ConvertFrom-Json
    Assert-True ($diagnose.ok -eq $true) "Diagnose should pass for scoped plugin"
    Assert-True ($diagnose.scope_violations_count -eq 0) "Diagnose should report zero scope violations"
    Assert-True ($diagnose.health_checks_count -eq 2) "Diagnose should report plugin health check count"

    $checkJson = & $pluginServiceScript -Action Check -Id "python-fastapi" -Json | Out-String
    $check = $checkJson | ConvertFrom-Json
    Assert-True ($check.ok -eq $true) "Check should pass when required checks pass"
    Assert-True ($check.health_checks_count -eq 2) "Check should execute both declared health checks"
    Assert-True ($check.required_failures -eq 0) "Optional health check failures should not fail plugin check"
    $requiredPass = $check.health_checks | Where-Object { $_.id -eq "required-pass" } | Select-Object -First 1
    $optionalFail = $check.health_checks | Where-Object { $_.id -eq "optional-fail" } | Select-Object -First 1
    Assert-True ($requiredPass.ok -eq $true) "Required passing health check should be ok"
    Assert-True ($optionalFail.ok -eq $false) "Optional failing health check should report failure"
    Assert-True ($optionalFail.required -eq $false) "Optional health check should remain optional"
    $lastCheckPath = Join-Path $dataRoot "Plugins\checks\python-fastapi-last.json"
    Assert-True (Test-Path -LiteralPath $lastCheckPath) "Check should persist the latest dashboard-readable result"
    $lastCheck = Get-Content -LiteralPath $lastCheckPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($lastCheck.plugin.id -eq "python-fastapi") "Persisted check should include plugin identity"
    Assert-True ($lastCheck.health_checks_count -eq 2) "Persisted check should include health check summary"

    $disableJson = & $pluginServiceScript -Action Disable -Id "python-fastapi" -Json | Out-String
    $disable = $disableJson | ConvertFrom-Json
    Assert-True ($disable.ok -eq $true) "Disable should succeed"
    Assert-True ($disable.plugin.enabled -eq $false) "Disable should mark plugin disabled"

    $badPackageRoot = Join-Path $tmpRoot "packages\bad-plugin"
    New-Item -ItemType Directory -Path $badPackageRoot -Force | Out-Null
    $badManifestPath = Join-Path $badPackageRoot "plugin.json"
    [pscustomobject][ordered]@{
        schema_version = 1
        id = "bad-plugin"
        name = "Bad Plugin"
        version = "0.1.0"
        capabilities = [ordered]@{ commands = @(); skills = @(); health_checks = @(); widgets = @(); templates = @() }
        permissions = [ordered]@{
            write_roots = @("..\..\outside")
            allow_out_of_scope_write = $false
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $badManifestPath -Encoding UTF8

    $badOutput = & $pluginServiceScript -Action Install -ManifestPath $badManifestPath -Json 2>&1 | Out-String
    Assert-True ($LASTEXITCODE -ne 0) "Install should reject out-of-scope write roots"
    Assert-True ($badOutput -match "scope") "Out-of-scope rejection should mention scope"

    Write-Host "[OK] plugin service smoke tests passed"
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
