# platform_version.ps1 -- canonical DEV_CORE platform version
param(
    [switch]$Raw,
    [switch]$Title
)

# --- Portable DEVCORE_DATA_ROOT Auto-Detection ---
$_isDefaultOrMissing = (-not $env:DEVCORE_DATA_ROOT) -or
                       ($env:DEVCORE_DATA_ROOT -like "*C:\devcore\DEV_CORE_DATA*") -or
                       ($env:DEVCORE_DATA_ROOT -like "*\DEV_CORE\DEV_CORE_DATA*") -or
                       (-not (Test-Path -LiteralPath $env:DEVCORE_DATA_ROOT))

if ($_isDefaultOrMissing) {
    # Dropbox stores info.json in LOCALAPPDATA on modern installs, fallback to APPDATA
    $_dbJsonCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Dropbox\info.json"),
        (Join-Path $env:APPDATA "Dropbox\info.json")
    )
    foreach ($_dbJsonPath in $_dbJsonCandidates) {
        if (Test-Path -LiteralPath $_dbJsonPath) {
            try {
                $_dbJson = Get-Content -LiteralPath $_dbJsonPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
                $_dbPath = $_dbJson.personal.path
                if ($_dbPath -and (Test-Path -LiteralPath $_dbPath)) {
                    $_dropboxData = Join-Path $_dbPath "DEV_CORE_DATA"
                    $env:DEVCORE_DATA_ROOT = $_dropboxData
                    [System.Environment]::SetEnvironmentVariable("DEVCORE_DATA_ROOT", $_dropboxData, "User")
                    break
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

function Get-DevCorePython {
    if ($env:DEVCORE_PYTHON -and (Test-Path -LiteralPath $env:DEVCORE_PYTHON)) {
        return $env:DEVCORE_PYTHON
    }
    $cmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }
    $cmdPy = Get-Command "py" -ErrorAction SilentlyContinue
    if ($cmdPy) {
        return "py"
    }
    $cmd3 = Get-Command "python3" -ErrorAction SilentlyContinue
    if ($cmd3 -and $cmd3.Source) {
        return $cmd3.Source
    }
    $candidates = @(
        (Get-ChildItem -Path "C:\Python*" -Filter "python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName),
        (Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName),
        (Get-ChildItem -Path "C:\Program Files\Python*\python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
    )
    foreach ($cand in $candidates) {
        if ($cand -and (Test-Path -LiteralPath $cand)) {
            return $cand
        }
    }
    return "python"
}

if (-not $env:DEVCORE_PYTHON) {
    $env:DEVCORE_PYTHON = Get-DevCorePython
}

$info = Get-DevCorePlatformInfo
if ($Raw) {
    Write-Output $info.version
} elseif ($Title) {
    Write-Output $info.title
}
