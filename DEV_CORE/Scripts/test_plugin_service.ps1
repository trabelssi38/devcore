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
            migrations = @("001-initial-install")
        }
        permissions = [ordered]@{
            write_roots = @("data", "cache")
            allow_out_of_scope_write = $false
        }
        provenance = [ordered]@{
            source = "local-test-package"
            publisher = "DEV_CORE Tests"
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Assert-True (Test-Path -LiteralPath $pluginServiceScript) "plugin_service.ps1 should exist"

    $installJson = & $pluginServiceScript -Action Install -ManifestPath $manifestPath -Json | Out-String
    $install = $installJson | ConvertFrom-Json
    Assert-True ($install.ok -eq $true) "Install should succeed for scoped plugin"
    Assert-True ($install.plugin.id -eq "python-fastapi") "Install should preserve plugin id"
    Assert-True (Test-Path -LiteralPath $install.installed_manifest_path) "Install should write installed manifest"
    Assert-True ($install.plugin.package_integrity.algorithm -eq "SHA256") "Install should record package checksum algorithm"
    Assert-True ($install.plugin.package_integrity.manifest_sha256 -match "^[a-f0-9]{64}$") "Install should record manifest sha256"
    Assert-True ($install.plugin.package_integrity.package_sha256 -match "^[a-f0-9]{64}$") "Install should record package sha256"
    Assert-True ($install.plugin.provenance.source -eq "local-test-package") "Install should preserve provenance source"
    Assert-True ($install.plugin.provenance.installed_by -eq "plugin_service") "Install should record installer provenance"
    Assert-True ($install.plugin.provenance.source_manifest_path -eq ([System.IO.Path]::GetFullPath($manifestPath))) "Install should record source manifest path"
    Assert-True ($install.plugin.migrations.applied_count -eq 1) "Install should audit applied migrations"
    Assert-True ($install.plugin.migrations.items[0].id -eq "001-initial-install") "Install should preserve migration id"
    Assert-True ($install.transaction.atomic -eq $true) "Install should report atomic transaction"
    Assert-True ($install.transaction.rollback_available -eq $true) "Install should report rollback availability"

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

    $tamperedPackageRoot = Join-Path $tmpRoot "packages\tampered-plugin"
    New-Item -ItemType Directory -Path $tamperedPackageRoot -Force | Out-Null
    $tamperedManifestPath = Join-Path $tamperedPackageRoot "plugin.json"
    [pscustomobject][ordered]@{
        schema_version = 1
        id = "tampered-plugin"
        name = "Tampered Plugin"
        version = "0.1.0"
        capabilities = [ordered]@{ commands = @(); skills = @(); health_checks = @(); widgets = @(); templates = @() }
        permissions = [ordered]@{
            write_roots = @("data")
            allow_out_of_scope_write = $false
        }
        package_integrity = [ordered]@{
            package_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tamperedManifestPath -Encoding UTF8

    $tamperedOutput = & $pluginServiceScript -Action Install -ManifestPath $tamperedManifestPath -Json 2>&1 | Out-String
    Assert-True ($LASTEXITCODE -ne 0) "Install should reject declared checksum mismatch"
    Assert-True ($tamperedOutput -match "checksum") "Checksum mismatch should mention checksum"

    $upgradePackageRoot = Join-Path $tmpRoot "packages\python-fastapi-upgrade"
    New-Item -ItemType Directory -Path $upgradePackageRoot -Force | Out-Null
    $upgradeManifestPath = Join-Path $upgradePackageRoot "plugin.json"
    [pscustomobject][ordered]@{
        schema_version = 1
        id = "python-fastapi"
        name = "Python FastAPI"
        version = "0.2.0"
        description = "FastAPI project helpers upgrade"
        capabilities = [ordered]@{
            commands = @("python-api:new-endpoint")
            skills = @("python_api")
            health_checks = @()
            widgets = @()
            templates = @("fastapi-endpoint")
            migrations = @(
                [ordered]@{
                    id = "002-upgrade"
                    description = "Upgrade plugin metadata"
                    required = $true
                }
            )
        }
        permissions = [ordered]@{
            write_roots = @("data", "cache")
            allow_out_of_scope_write = $false
        }
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $upgradeManifestPath -Encoding UTF8

    $env:DEVCORE_PLUGIN_INSTALL_FAIL_AT = "after_manifest"
    $upgradeOutput = & $pluginServiceScript -Action Install -ManifestPath $upgradeManifestPath -Json 2>&1 | Out-String
    Remove-Item Env:\DEVCORE_PLUGIN_INSTALL_FAIL_AT -ErrorAction SilentlyContinue
    Assert-True ($LASTEXITCODE -ne 0) "Failed upgrade should return a non-zero exit code"
    Assert-True ($upgradeOutput -match "rollback") "Failed upgrade should mention rollback"

    $installedAfterRollback = Get-Content -LiteralPath $install.installed_manifest_path -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($installedAfterRollback.version -eq "0.1.0") "Rollback should restore installed manifest version"

    $listAfterRollbackJson = & $pluginServiceScript -Action List -Json | Out-String
    $listAfterRollback = $listAfterRollbackJson | ConvertFrom-Json
    $pluginAfterRollback = $listAfterRollback.plugins | Where-Object { $_.id -eq "python-fastapi" } | Select-Object -First 1
    Assert-True ($pluginAfterRollback.version -eq "0.1.0") "Rollback should restore registry plugin version"

    Write-Host "[OK] plugin service smoke tests passed"
} finally {
    Remove-Item Env:\DEVCORE_PLUGIN_INSTALL_FAIL_AT -ErrorAction SilentlyContinue
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
