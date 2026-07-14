# routing_profile.ps1 -- DEV_CORE mode/profile resolver
$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$ROUTING_PROFILE_PATH = Join-Path $DEV_CORE "Config\routing_profiles.json"

function Get-DevCoreRoutingProfiles {
    param([string]$Path = $ROUTING_PROFILE_PATH)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Routing profile config not found: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Resolve-DevCoreRoutingProfile {
    param(
        [string]$Mode = "",
        [string]$Path = $ROUTING_PROFILE_PATH
    )

    $config = Get-DevCoreRoutingProfiles -Path $Path
    $requested = if ([string]::IsNullOrWhiteSpace($Mode)) { [string]$config.default_mode } else { $Mode.Trim().ToLowerInvariant() }
    if ([string]::IsNullOrWhiteSpace($requested)) { $requested = "coding" }

    $resolved = $requested
    if ($config.aliases -and $config.aliases.PSObject.Properties[$requested]) {
        $resolved = [string]$config.aliases.$requested
    }

    if (-not $config.profiles.PSObject.Properties[$resolved]) {
        $resolved = [string]$config.default_mode
    }
    if (-not $config.profiles.PSObject.Properties[$resolved]) {
        $resolved = "coding"
    }

    $profile = $config.profiles.$resolved
    return [pscustomobject]@{
        requested_mode = $requested
        mode = [string]$profile.mode
        budget = [string]$profile.budget
        profile = [string]$profile.profile
        model = [string]$profile.model
        gemini_model = [string]$profile.gemini_model
        codex_behavior = [string]$profile.codex_behavior
        hint = [string]$profile.hint
    }
}

