# skill_lint.ps1 -- DEV_CORE v11.2 -- static gate for generated skills
param(
    [string]$Name = "",
    [string]$Path = "",
    [switch]$AgentSpec,
    [switch]$StrictAgentSpec,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$REGISTRY_PATH = Join-Path $DEV_CORE "Skills\skills_registry.json"
$CANDIDATES_ROOT = Join-Path $DEV_CORE_DATA "Skills\Candidates"

function Resolve-SkillPath {
    if ($Path) {
        if ((Test-Path -LiteralPath $Path -PathType Container)) {
            return (Join-Path $Path "SKILL.md")
        }
        return $Path
    }
    if (-not [string]::IsNullOrWhiteSpace($Name)) {
        if (Test-Path -LiteralPath $REGISTRY_PATH) {
            try {
                $registry = Get-Content -LiteralPath $REGISTRY_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
                $entry = @($registry.skills) | Where-Object { $_.name -eq $Name -or $_.id -eq $Name } | Select-Object -First 1
                if ($entry -and $entry.skill_path) { return [string]$entry.skill_path }
            } catch {}
        }
        $candidatePath = Join-Path $CANDIDATES_ROOT "$Name\SKILL.md"
        if (Test-Path -LiteralPath $candidatePath) { return $candidatePath }
        $activePath = Join-Path $DEV_CORE "Skills\$Name\SKILL.md"
        if (Test-Path -LiteralPath $activePath) { return $activePath }
    }
    throw "Skill path not found. Provide -Name or -Path."
}

function Get-FrontMatter {
    param([string[]]$Lines)
    if ($Lines.Count -lt 3 -or $Lines[0].Trim() -ne "---") {
        return [pscustomobject]@{ ok = $false; values = @{} }
    }
    $values = @{}
    for ($i = 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -eq "---") { return [pscustomobject]@{ ok = $true; values = $values } }
        if ($Lines[$i] -match "^\s*([^:#]+)\s*:\s*(.*)$") {
            $values[$Matches[1].Trim()] = $Matches[2].Trim().Trim('"', "'")
        }
    }
    return [pscustomobject]@{ ok = $false; values = $values }
}

function Test-AgentSkillSpec {
    param(
        [string]$SkillPath,
        [string]$Text,
        [string[]]$Lines,
        $FrontMatter
    )

    $specErrors = @()
    $specWarnings = @()
    $skillDirName = Split-Path -Leaf (Split-Path -Parent $SkillPath)
    $skillName = if ($FrontMatter.values.ContainsKey("name")) { [string]$FrontMatter.values["name"] } else { "" }
    $description = if ($FrontMatter.values.ContainsKey("description")) { [string]$FrontMatter.values["description"] } else { "" }

    if ($skillName.Length -gt 64) { $specErrors += "Agent Skills name must be <= 64 characters" }
    if ($skillName -notmatch "^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$" -or $skillName -match "--") {
        $specErrors += "Agent Skills name must use lowercase letters, numbers, hyphens only, and not start/end with hyphen"
    }
    if ($skillDirName -ne $skillName) {
        $specErrors += "Agent Skills name must match parent directory name"
    }
    if ([string]::IsNullOrWhiteSpace($description) -or $description.Length -gt 1024) {
        $specErrors += "Agent Skills description must be non-empty and <= 1024 characters"
    }
    if ($Lines.Count -gt 500) {
        $specWarnings += "Agent Skills recommends keeping SKILL.md under 500 lines"
    }
    if ($Text -match "\]\((references|scripts|assets)/[^)\s]+/[^)\s]+\)") {
        $specWarnings += "Agent Skills recommends one-level-deep file references from SKILL.md"
    }

    $status = if ($specErrors.Count -gt 0) { "FAIL" } elseif ($specWarnings.Count -gt 0) { "WARN" } else { "PASS" }
    [pscustomobject][ordered]@{
        status = $status
        errors = @($specErrors)
        warnings = @($specWarnings)
    }
}

if ($StrictAgentSpec) { $AgentSpec = $true }

$skillPath = Resolve-SkillPath
$errors = @()
$warnings = @()
$agentSpecResult = [pscustomobject][ordered]@{ status = "SKIP"; errors = @(); warnings = @() }

if (-not (Test-Path -LiteralPath $skillPath)) {
    $errors += "SKILL.md not found: $skillPath"
} else {
    $text = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
    $lines = @($text -split "`r?`n")
    $frontMatter = Get-FrontMatter -Lines $lines
    if (-not $frontMatter.ok) { $errors += "frontmatter missing or invalid" }
    foreach ($required in @("name", "description")) {
        if (-not $frontMatter.values.ContainsKey($required) -or [string]::IsNullOrWhiteSpace([string]$frontMatter.values[$required])) {
            $errors += "frontmatter '$required' is required"
        }
    }
    foreach ($section in @("## Trigger", "## Workflow", "## Safety")) {
        if ($text -notmatch [regex]::Escape($section)) { $warnings += "section missing: $section" }
    }
    if ($text -match "(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*['""]?[^`r`n\s]+" ) {
        $errors += "possible secret literal detected"
    }
    if ($text -match "(?i)(Remove-Item\s+-Recurse|git\s+reset\s+--hard|rm\s+-rf|del\s+/s)") {
        $errors += "destructive command detected"
    }
    if ($text.Length -gt 12000) { $warnings += "skill is long; consider splitting references" }

    if ($AgentSpec) {
        $agentSpecResult = Test-AgentSkillSpec -SkillPath $skillPath -Text $text -Lines $lines -FrontMatter $frontMatter
        if ($StrictAgentSpec) {
            foreach ($err in @($agentSpecResult.errors)) { $errors += "agent-spec: $err" }
            foreach ($warn in @($agentSpecResult.warnings)) { $warnings += "agent-spec: $warn" }
        } elseif ($agentSpecResult.status -ne "PASS") {
            foreach ($err in @($agentSpecResult.errors)) { $warnings += "agent-spec: $err" }
            foreach ($warn in @($agentSpecResult.warnings)) { $warnings += "agent-spec: $warn" }
        }
    }
}

$status = if ($errors.Count -gt 0) { "FAIL" } elseif ($warnings.Count -gt 0) { "WARN" } else { "PASS" }
$result = [pscustomobject][ordered]@{
    schema_version = 1
    name = $Name
    skill_path = $skillPath
    status = $status
    errors = @($errors)
    warnings = @($warnings)
    agent_spec_status = $agentSpecResult.status
    agent_spec_errors = @($agentSpecResult.errors)
    agent_spec_warnings = @($agentSpecResult.warnings)
}

if ($Json) { $result | ConvertTo-Json -Depth 10 }
else { Write-Host "[SKILL_LINT] $status -- $skillPath" }
if ($status -eq "FAIL") { exit 1 } else { exit 0 }
