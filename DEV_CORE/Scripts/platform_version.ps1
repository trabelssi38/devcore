# platform_version.ps1 -- canonical DEV_CORE platform version
param(
    [switch]$Raw,
    [switch]$Title
)

# --- Portable DEVCORE_DATA_ROOT Auto-Detection ---
$isDefaultOrMissing = (-not $env:DEVCORE_DATA_ROOT) -or 
                      ($env:DEVCORE_DATA_ROOT -like "*C:\devcore\DEV_CORE_DATA*") -or 
                      ($env:DEVCORE_DATA_ROOT -like "*\DEV_CORE\DEV_CORE_DATA*") -or 
                      (-not (Test-Path -LiteralPath $env:DEVCORE_DATA_ROOT))

if ($isDefaultOrMissing) {
    $appData = $env:APPDATA
    if ($appData) {
        $dbJsonPath = Join-Path $appData "Dropbox\info.json"
        if (Test-Path -LiteralPath $dbJsonPath) {
            try {
                $dbJson = Get-Content -LiteralPath $dbJsonPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
                $dbPath = $dbJson.personal.path
                if ($dbPath -and (Test-Path -LiteralPath $dbPath)) {
                    $dropboxData = Join-Path $dbPath "DEV_CORE_DATA"
                    $env:DEVCORE_DATA_ROOT = $dropboxData
                    [System.Environment]::SetEnvironmentVariable("DEVCORE_DATA_ROOT", $dropboxData, "Process")
                }
            } catch {}
        }
    }
}

$ScriptPlatformRoot = Split-Path -Parent $PSScriptRoot
$EnvPlatformRoot = $env:DEVCORE_PLATFORM_ROOT
$PlatformRoot = if ($EnvPlatformRoot -and (Test-Path -LiteralPath (Join-Path $EnvPlatformRoot "Config\platform.json"))) {
    $EnvPlatformRoot
} else {
    $ScriptPlatformRoot
}
$PlatformConfigPath = Join-Path $PlatformRoot "Config\platform.json"

function Get-DevCorePlatformInfo {
    if (-not (Test-Path -LiteralPath $PlatformConfigPath)) {
        throw "Platform config not found: $PlatformConfigPath"
    }

    $config = Get-Content -LiteralPath $PlatformConfigPath -Raw | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($config.name)) {
        throw "Platform config missing name"
    }
    if ([string]::IsNullOrWhiteSpace($config.version)) {
        throw "Platform config missing version"
    }

    [PSCustomObject]@{
        schema_version = [int]$config.schema_version
        name           = [string]$config.name
        version        = [string]$config.version
        display_version = "v$($config.version)"
        title          = "$($config.name) v$($config.version)"
    }
}

function Get-DevCorePlatformTitle {
    (Get-DevCorePlatformInfo).title
}

$info = Get-DevCorePlatformInfo
if ($Raw) {
    Write-Output $info.version
} elseif ($Title) {
    Write-Output $info.title
}
