# routing_profile.ps1 -- DEV_CORE mode/profile resolver
$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$ROUTING_PROFILE_PATH = Join-Path $DEV_CORE "Config\routing_profiles.json"
$AI_CAPABILITY_REGISTRY_PATH = Join-Path $DEV_CORE "Config\ai_capability_registry.json"

function Get-DevCoreRoutingProfiles {
    param([string]$Path = $ROUTING_PROFILE_PATH)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Routing profile config not found: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-DevCoreAICapabilityRegistry {
    param([string]$Path = $AI_CAPABILITY_REGISTRY_PATH)

    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{
            schema_version = 1
            default_candidate = "devcore-coding"
            mode_defaults = [pscustomobject]@{ coding = "devcore-coding" }
            aliases = [pscustomobject]@{}
            candidates = [pscustomobject]@{
                "devcore-coding" = [pscustomobject]@{
                    enabled = $true
                    backend_model = "gemini-2.5-pro"
                    workflow_modes = @("coding")
                }
            }
        }
    }

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Resolve-DevCoreCapabilityCandidate {
    param(
        [string]$Mode = "",
        [string]$Model = "",
        [string]$Path = $AI_CAPABILITY_REGISTRY_PATH
    )

    $registry = Get-DevCoreAICapabilityRegistry -Path $Path
    $requestedMode = if ([string]::IsNullOrWhiteSpace($Mode)) { "" } else { $Mode.Trim().ToLowerInvariant() }
    $requestedModel = if ([string]::IsNullOrWhiteSpace($Model)) { "" } else { $Model.Trim().ToLowerInvariant() }
    $candidateId = ""

    if ($requestedModel -and $registry.aliases -and $registry.aliases.PSObject.Properties[$requestedModel]) {
        $candidateId = [string]$registry.aliases.$requestedModel
    } elseif ($requestedModel -and $registry.candidates.PSObject.Properties[$requestedModel]) {
        $candidateId = $requestedModel
    } elseif ($requestedMode -and $registry.mode_defaults -and $registry.mode_defaults.PSObject.Properties[$requestedMode]) {
        $candidateId = [string]$registry.mode_defaults.$requestedMode
    } else {
        $candidateId = [string]$registry.default_candidate
    }

    if (-not $candidateId -or -not $registry.candidates.PSObject.Properties[$candidateId]) {
        $candidateId = [string]$registry.default_candidate
    }
    if (-not $candidateId -or -not $registry.candidates.PSObject.Properties[$candidateId]) {
        $candidateId = "devcore-coding"
    }

    $candidate = $registry.candidates.$candidateId
    if ($candidate.PSObject.Properties["enabled"] -and -not [bool]$candidate.enabled) {
        $candidateId = [string]$registry.default_candidate
        $candidate = $registry.candidates.$candidateId
    }

    return [pscustomobject]@{
        id = $candidateId
        backend_model = [string]$candidate.backend_model
        provider = [string]$candidate.provider
        type = [string]$candidate.type
        context_tokens = if ($candidate.PSObject.Properties["context_tokens"]) { [int64]$candidate.context_tokens } else { 0 }
        cost_tier = if ($candidate.PSObject.Properties["cost_tier"]) { [int]$candidate.cost_tier } else { 3 }
        speed_tier = if ($candidate.PSObject.Properties["speed_tier"]) { [int]$candidate.speed_tier } else { 3 }
        quality_tier = if ($candidate.PSObject.Properties["quality_tier"]) { [int]$candidate.quality_tier } else { 3 }
    }
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
    $capability = Resolve-DevCoreCapabilityCandidate -Mode $resolved -Model ([string]$profile.model)
    return [pscustomobject]@{
        requested_mode = $requested
        mode = [string]$profile.mode
        budget = [string]$profile.budget
        profile = [string]$profile.profile
        model = [string]$profile.model
        gemini_model = if ($capability.backend_model) { [string]$capability.backend_model } else { [string]$profile.gemini_model }
        capability_candidate = [string]$capability.id
        capability_provider = [string]$capability.provider
        capability_context_tokens = [int64]$capability.context_tokens
        capability_cost_tier = [int]$capability.cost_tier
        capability_speed_tier = [int]$capability.speed_tier
        capability_quality_tier = [int]$capability.quality_tier
        codex_behavior = [string]$profile.codex_behavior
        hint = [string]$profile.hint
    }
}
