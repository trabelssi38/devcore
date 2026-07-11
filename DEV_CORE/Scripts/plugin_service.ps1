# plugin_service.ps1 -- DEV_CORE v11.2 -- Plugin SDK registry service
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Install", "List", "Disable", "Diagnose", "Check", "Health")]
    [string]$Action,
    [string]$ManifestPath = "",
    [string]$Id = "",
    [int]$TimeoutSeconds = 10,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$PLUGINS_DIR = Join-Path $DEV_CORE_DATA "Plugins"
$INSTALLED_DIR = Join-Path $PLUGINS_DIR "installed"
$REGISTRY_PATH = Join-Path $PLUGINS_DIR "plugins_registry.json"

function Ensure-PluginDirs {
    New-Item -ItemType Directory -Path $INSTALLED_DIR -Force | Out-Null
    if (-not (Test-Path -LiteralPath $REGISTRY_PATH)) {
        [pscustomobject][ordered]@{
            schema_version = 1
            generated_at = (Get-Date).ToString("o")
            plugins_count = 0
            plugins = @()
        } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $REGISTRY_PATH -Encoding UTF8
    }
}

function Read-Registry {
    Ensure-PluginDirs
    return Get-Content -LiteralPath $REGISTRY_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-Registry {
    param($Registry)

    $Registry.generated_at = (Get-Date).ToString("o")
    $Registry.plugins_count = @($Registry.plugins).Count
    $Registry | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $REGISTRY_PATH -Encoding UTF8
}

function Get-RequiredString {
    param($Object, [string]$Name)

    if (-not $Object.PSObject.Properties[$Name] -or [string]::IsNullOrWhiteSpace([string]$Object.$Name)) {
        throw "Plugin manifest field '$Name' is required."
    }
    return [string]$Object.$Name
}

function Get-PluginDataRoot {
    param([string]$PluginId)

    return (Join-Path $PLUGINS_DIR $PluginId)
}

function Resolve-ScopeRoot {
    param([string]$PluginId, [string]$Root)

    $pluginDataRoot = Get-PluginDataRoot -PluginId $PluginId
    if ([string]::IsNullOrWhiteSpace($Root)) { return $pluginDataRoot }
    if ([System.IO.Path]::IsPathRooted($Root)) {
        return [System.IO.Path]::GetFullPath($Root)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $pluginDataRoot $Root))
}

function Test-IsUnderPath {
    param([string]$Child, [string]$Parent)

    $childFull = [System.IO.Path]::GetFullPath($Child).TrimEnd('\')
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\')
    return ($childFull -eq $parentFull -or $childFull.StartsWith($parentFull + "\", [System.StringComparison]::OrdinalIgnoreCase))
}

function Get-ScopeViolations {
    param($Plugin)

    $violations = @()
    $pluginDataRoot = Get-PluginDataRoot -PluginId ([string]$Plugin.id)
    $allowOutOfScope = $false
    if ($Plugin.permissions -and $null -ne $Plugin.permissions.allow_out_of_scope_write) {
        $allowOutOfScope = [bool]$Plugin.permissions.allow_out_of_scope_write
    }

    $roots = @()
    if ($Plugin.permissions -and $null -ne $Plugin.permissions.write_roots) {
        $roots = @($Plugin.permissions.write_roots | Where-Object { $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_) })
    }

    foreach ($root in $roots) {
        $resolved = Resolve-ScopeRoot -PluginId ([string]$Plugin.id) -Root ([string]$root)
        if (-not $allowOutOfScope -and -not (Test-IsUnderPath -Child $resolved -Parent $pluginDataRoot)) {
            $violations += [pscustomobject][ordered]@{
                root = [string]$root
                resolved = $resolved
                allowed_root = $pluginDataRoot
                reason = "write root outside plugin scope"
            }
        }
    }

    return @($violations)
}

function Get-ArrayField {
    param($Object, [string]$Name)

    if ($Object -and $Object.PSObject.Properties[$Name] -and $null -ne $Object.$Name) {
        return @($Object.$Name | Where-Object { $null -ne $_ -and -not [string]::IsNullOrWhiteSpace([string]$_) })
    }
    return @()
}

function ConvertTo-Slug {
    param([string]$Value, [string]$Fallback = "check")

    $clean = $Value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
    $clean = $clean.Trim("-")
    if ([string]::IsNullOrWhiteSpace($clean)) { return $Fallback }
    if ($clean.Length -gt 64) { $clean = $clean.Substring(0, 64).Trim("-") }
    return $clean
}

function Get-ObjectBool {
    param($Object, [string]$Name, [bool]$Default)

    if ($Object -and $Object.PSObject.Properties[$Name] -and $null -ne $Object.$Name) {
        return [bool]$Object.$Name
    }
    return $Default
}

function Get-ObjectInt {
    param($Object, [string]$Name, [int]$Default)

    if ($Object -and $Object.PSObject.Properties[$Name] -and $null -ne $Object.$Name) {
        $value = 0
        if ([int]::TryParse([string]$Object.$Name, [ref]$value)) { return $value }
    }
    return $Default
}

function Get-ObjectString {
    param($Object, [string]$Name, [string]$Default = "")

    if ($Object -and $Object.PSObject.Properties[$Name] -and $null -ne $Object.$Name) {
        return [string]$Object.$Name
    }
    return $Default
}

function Get-HealthChecksField {
    param($Object, [string]$Name)

    $checks = @()
    if (-not ($Object -and $Object.PSObject.Properties[$Name] -and $null -ne $Object.$Name)) {
        return @()
    }

    $index = 0
    foreach ($raw in @($Object.$Name)) {
        if ($null -eq $raw) { continue }
        $index++

        $command = ""
        $id = ""
        $description = ""
        $required = $true
        $timeout = 10
        $shell = "powershell"

        if ($raw -is [string]) {
            $command = [string]$raw
            $id = ConvertTo-Slug -Value $command -Fallback "check-$index"
        } else {
            $command = Get-ObjectString -Object $raw -Name "command"
            $id = Get-ObjectString -Object $raw -Name "id"
            $description = Get-ObjectString -Object $raw -Name "description"
            $required = Get-ObjectBool -Object $raw -Name "required" -Default $true
            $timeout = Get-ObjectInt -Object $raw -Name "timeout_seconds" -Default 10
            $shell = Get-ObjectString -Object $raw -Name "shell" -Default "powershell"
        }

        if ([string]::IsNullOrWhiteSpace($command)) { continue }
        if ([string]::IsNullOrWhiteSpace($id)) {
            $id = ConvertTo-Slug -Value $command -Fallback "check-$index"
        }
        if ($timeout -lt 1) { $timeout = 1 }
        if ($timeout -gt 120) { $timeout = 120 }

        $checks += [pscustomobject][ordered]@{
            id = $id
            command = $command
            shell = $shell
            required = $required
            timeout_seconds = $timeout
            description = $description
        }
    }

    return @($checks)
}

function Normalize-PluginManifest {
    param($Manifest, [string]$SourcePath)

    $id = Get-RequiredString -Object $Manifest -Name "id"
    if ($id -notmatch "^[a-z0-9][a-z0-9._-]*$") {
        throw "Plugin id '$id' is invalid."
    }

    $capabilities = if ($Manifest.PSObject.Properties["capabilities"] -and $Manifest.capabilities) {
        $Manifest.capabilities
    } else {
        [pscustomobject]@{}
    }

    $permissions = if ($Manifest.PSObject.Properties["permissions"] -and $Manifest.permissions) {
        $Manifest.permissions
    } else {
        [pscustomobject]@{ write_roots = @(); allow_out_of_scope_write = $false }
    }

    [pscustomobject][ordered]@{
        schema_version = if ($Manifest.PSObject.Properties["schema_version"]) { [int]$Manifest.schema_version } else { 1 }
        id = $id
        name = Get-RequiredString -Object $Manifest -Name "name"
        version = Get-RequiredString -Object $Manifest -Name "version"
        description = if ($Manifest.PSObject.Properties["description"]) { [string]$Manifest.description } else { "" }
        enabled = $true
        installed_at = (Get-Date).ToString("o")
        source_manifest_path = [System.IO.Path]::GetFullPath($SourcePath)
        installed_manifest_path = Join-Path (Join-Path $INSTALLED_DIR $id) "plugin.json"
        capabilities = [pscustomobject][ordered]@{
            commands = Get-ArrayField -Object $capabilities -Name "commands"
            hooks = Get-ArrayField -Object $capabilities -Name "hooks"
            skills = Get-ArrayField -Object $capabilities -Name "skills"
            health_checks = Get-HealthChecksField -Object $capabilities -Name "health_checks"
            widgets = Get-ArrayField -Object $capabilities -Name "widgets"
            templates = Get-ArrayField -Object $capabilities -Name "templates"
        }
        permissions = [pscustomobject][ordered]@{
            write_roots = Get-ArrayField -Object $permissions -Name "write_roots"
            allow_out_of_scope_write = if ($permissions.PSObject.Properties["allow_out_of_scope_write"]) { [bool]$permissions.allow_out_of_scope_write } else { $false }
        }
    }
}

function Install-Plugin {
    if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
        Write-Error "ManifestPath is required for Install."
        exit 64
    }
    if (-not (Test-Path -LiteralPath $ManifestPath)) {
        Write-Error "Plugin manifest not found: $ManifestPath"
        exit 66
    }

    Ensure-PluginDirs
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $plugin = Normalize-PluginManifest -Manifest $manifest -SourcePath $ManifestPath
    $violations = @(Get-ScopeViolations -Plugin $plugin)
    if ($violations.Count -gt 0) {
        $message = "Plugin scope violation: $($violations[0].root)"
        if ($Json) {
            [pscustomobject][ordered]@{
                ok = $false
                error = $message
                scope_violations = $violations
            } | ConvertTo-Json -Depth 20
        } else {
            Write-Host "[PLUGIN] install rejected -- $message" -ForegroundColor Red
        }
        exit 66
    }

    $pluginDir = Join-Path $INSTALLED_DIR $plugin.id
    New-Item -ItemType Directory -Path $pluginDir -Force | Out-Null
    $plugin | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $plugin.installed_manifest_path -Encoding UTF8

    $registry = Read-Registry
    $remaining = @($registry.plugins | Where-Object { $_.id -ne $plugin.id })
    $registry.plugins = @($remaining + $plugin)
    Write-Registry -Registry $registry

    [pscustomobject][ordered]@{
        ok = $true
        action = "Install"
        plugin = $plugin
        installed_manifest_path = $plugin.installed_manifest_path
        registry_path = $REGISTRY_PATH
    }
}

function Get-Plugins {
    $registry = Read-Registry
    [pscustomobject][ordered]@{
        schema_version = 1
        registry_path = $REGISTRY_PATH
        plugins_count = @($registry.plugins).Count
        plugins = @($registry.plugins)
    }
}

function Find-Plugin {
    param([string]$PluginId)

    $registry = Read-Registry
    return $registry.plugins | Where-Object { $_.id -eq $PluginId } | Select-Object -First 1
}

function Invoke-HealthCheckCommand {
    param($Check)

    $startedAt = Get-Date
    $command = [string]$Check.command
    $timeout = [int]$Check.timeout_seconds
    if ($TimeoutSeconds -gt 0 -and $TimeoutSeconds -lt $timeout) { $timeout = $TimeoutSeconds }
    if ($timeout -lt 1) { $timeout = 1 }

    if ([string]$Check.shell -ne "powershell") {
        return [pscustomobject][ordered]@{
            id = [string]$Check.id
            ok = $false
            required = [bool]$Check.required
            command = $command
            shell = [string]$Check.shell
            exit_code = $null
            timed_out = $false
            duration_ms = 0
            stdout = ""
            stderr = "unsupported health check shell: $($Check.shell)"
            started_at = $startedAt.ToString("o")
        }
    }

    $process = $null
    try {
        $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($command))
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "powershell.exe"
        $psi.Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true

        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $psi
        [void]$process.Start()
        $completed = $process.WaitForExit($timeout * 1000)
        $timedOut = -not $completed
        if ($timedOut) {
            try { $process.Kill() } catch {}
        }

        $stdout = $process.StandardOutput.ReadToEnd().Trim()
        $stderr = $process.StandardError.ReadToEnd().Trim()
        $exitCode = if ($timedOut) { $null } else { $process.ExitCode }
        $duration = [int]((Get-Date) - $startedAt).TotalMilliseconds
        $ok = (-not $timedOut -and $exitCode -eq 0)

        return [pscustomobject][ordered]@{
            id = [string]$Check.id
            ok = $ok
            required = [bool]$Check.required
            command = $command
            shell = [string]$Check.shell
            exit_code = $exitCode
            timed_out = $timedOut
            duration_ms = $duration
            stdout = $stdout
            stderr = $stderr
            started_at = $startedAt.ToString("o")
        }
    } catch {
        $duration = [int]((Get-Date) - $startedAt).TotalMilliseconds
        return [pscustomobject][ordered]@{
            id = [string]$Check.id
            ok = $false
            required = [bool]$Check.required
            command = $command
            shell = [string]$Check.shell
            exit_code = $null
            timed_out = $false
            duration_ms = $duration
            stdout = ""
            stderr = [string]$_
            started_at = $startedAt.ToString("o")
        }
    } finally {
        if ($process) { $process.Dispose() }
    }
}

function Invoke-PluginHealthChecks {
    param($Plugin)

    $checks = @()
    if ($Plugin.capabilities -and $Plugin.capabilities.PSObject.Properties["health_checks"]) {
        $checks = @($Plugin.capabilities.health_checks)
    }

    $results = @()
    foreach ($check in $checks) {
        $results += Invoke-HealthCheckCommand -Check $check
    }

    $requiredFailures = @($results | Where-Object { $_.required -eq $true -and $_.ok -ne $true })
    [pscustomobject][ordered]@{
        health_checks_count = @($results).Count
        required_failures = @($requiredFailures).Count
        ok = (@($requiredFailures).Count -eq 0)
        health_checks = @($results)
    }
}

function Disable-Plugin {
    if ([string]::IsNullOrWhiteSpace($Id)) {
        Write-Error "Id is required for Disable."
        exit 64
    }

    $registry = Read-Registry
    $plugin = $registry.plugins | Where-Object { $_.id -eq $Id } | Select-Object -First 1
    if (-not $plugin) {
        Write-Error "Plugin not found: $Id"
        exit 66
    }

    $plugin.enabled = $false
    Write-Registry -Registry $registry
    if ($plugin.installed_manifest_path) {
        $plugin | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $plugin.installed_manifest_path -Encoding UTF8
    }

    [pscustomobject][ordered]@{
        ok = $true
        action = "Disable"
        plugin = $plugin
        registry_path = $REGISTRY_PATH
    }
}

function Diagnose-Plugin {
    if ([string]::IsNullOrWhiteSpace($Id)) {
        Write-Error "Id is required for Diagnose."
        exit 64
    }

    $plugin = Find-Plugin -PluginId $Id
    if (-not $plugin) {
        Write-Error "Plugin not found: $Id"
        exit 66
    }

    $violations = @(Get-ScopeViolations -Plugin $plugin)
    $manifestExists = $plugin.installed_manifest_path -and (Test-Path -LiteralPath $plugin.installed_manifest_path)
    $ok = ($manifestExists -and $violations.Count -eq 0)
    $healthChecks = @()
    if ($plugin.capabilities -and $plugin.capabilities.PSObject.Properties["health_checks"]) {
        $healthChecks = @($plugin.capabilities.health_checks)
    }

    [pscustomobject][ordered]@{
        ok = $ok
        action = "Diagnose"
        plugin = $plugin
        manifest_exists = [bool]$manifestExists
        scope_violations_count = $violations.Count
        scope_violations = $violations
        health_checks_count = @($healthChecks).Count
        health_checks_executable = (@($healthChecks).Count -gt 0)
    }
}

function Check-Plugin {
    if ([string]::IsNullOrWhiteSpace($Id)) {
        Write-Error "Id is required for Check."
        exit 64
    }

    $plugin = Find-Plugin -PluginId $Id
    if (-not $plugin) {
        Write-Error "Plugin not found: $Id"
        exit 66
    }

    $diagnose = Diagnose-Plugin
    if (-not $diagnose.ok) {
        return [pscustomobject][ordered]@{
            ok = $false
            action = "Check"
            plugin = $plugin
            diagnose = $diagnose
            health_checks_count = 0
            required_failures = 0
            health_checks = @()
        }
    }

    $checkResult = Invoke-PluginHealthChecks -Plugin $plugin
    [pscustomobject][ordered]@{
        ok = $checkResult.ok
        action = "Check"
        plugin = $plugin
        health_checks_count = $checkResult.health_checks_count
        required_failures = $checkResult.required_failures
        health_checks = $checkResult.health_checks
    }
}

function Get-Health {
    Ensure-PluginDirs
    $canWrite = $false
    try {
        $probe = Join-Path $PLUGINS_DIR ".health"
        "ok" | Set-Content -LiteralPath $probe -Encoding UTF8
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
        $canWrite = $true
    } catch {
        $canWrite = $false
    }

    [pscustomobject][ordered]@{
        schema_version = 1
        ok = $canWrite
        plugins_dir = $PLUGINS_DIR
        registry_path = $REGISTRY_PATH
        writable = $canWrite
    }
}

$result = switch ($Action) {
    "Install" { Install-Plugin }
    "List" { Get-Plugins }
    "Disable" { Disable-Plugin }
    "Diagnose" { Diagnose-Plugin }
    "Check" { Check-Plugin }
    "Health" { Get-Health }
}

if ($Json) {
    $result | ConvertTo-Json -Depth 30
} else {
    if ($Action -eq "List") {
        Write-Host "[PLUGIN] list OK -- $($result.plugins_count) plugin(s)"
    } elseif ($Action -eq "Health") {
        Write-Host "[PLUGIN] health OK -- writable=$($result.writable)"
    } else {
        Write-Host "[PLUGIN] $Action OK"
    }
}

if ($result.PSObject.Properties["ok"] -and -not $result.ok) { exit 1 }
exit 0
