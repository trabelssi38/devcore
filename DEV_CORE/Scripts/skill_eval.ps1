# skill_eval.ps1 -- DEV_CORE v11.2 -- evidence-based skill verification
param(
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path (Join-Path $env:DEVCORE_PLATFORM_ROOT "Scripts\platform_version.ps1"))) {
    $env:DEVCORE_PLATFORM_ROOT
} elseif (Test-Path (Join-Path $PSScriptRoot "platform_version.ps1")) {
    Split-Path -Parent $PSScriptRoot
} elseif (Test-Path (Join-Path $PSScriptRoot "Scripts\platform_version.ps1")) {
    $PSScriptRoot
} elseif (Test-Path (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE\Scripts\platform_version.ps1")) {
    Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE"
} else {
    Split-Path -Parent $PSScriptRoot
}
if ($DEV_CORE -match '[/\\]Scripts[/\\]?$') {
    $DEV_CORE = Split-Path -Parent $DEV_CORE
}
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$REGISTRY_PATH = Join-Path $DEV_CORE "Skills\skills_registry.json"
$EVENTS_ROOT = Join-Path $DEV_CORE_DATA "Bus\events"
$SKILL_LINT = Join-Path $PSScriptRoot "skill_lint.ps1"

function Read-Registry {
    if (-not (Test-Path -LiteralPath $REGISTRY_PATH)) { throw "skills_registry.json not found" }
    Get-Content -LiteralPath $REGISTRY_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-Registry {
    param($Registry)
    $Registry.skills_count = @($Registry.skills).Count
    $Registry.generated_at = (Get-Date).ToString("o")
    $Registry | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $REGISTRY_PATH -Encoding UTF8
}

function Read-JsonLines {
    param([string]$Path)
    $items = @()
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $items += ($line | ConvertFrom-Json) } catch {}
    }
    return $items
}

function Read-AllEvents {
    $events = @()
    if (-not (Test-Path -LiteralPath $EVENTS_ROOT)) { return @() }
    foreach ($file in Get-ChildItem -LiteralPath $EVENTS_ROOT -Filter "events-*.jsonl" -File -ErrorAction SilentlyContinue) {
        $events += Read-JsonLines -Path $file.FullName
    }
    return $events
}

$registry = Read-Registry
$entry = @($registry.skills) | Where-Object { $_.name -eq $Name -or $_.id -eq $Name } | Select-Object -First 1
if (-not $entry) { throw "Skill not found: $Name" }

$lint = if (Test-Path -LiteralPath $SKILL_LINT) {
    & $SKILL_LINT -Name $entry.name -Json | Out-String | ConvertFrom-Json
} else {
    [pscustomObject]@{ status = "WARN"; errors = @("skill_lint.ps1 unavailable") }
}

$events = Read-AllEvents
$matches = @()
if ($entry.PSObject.Properties["trigger_event_type"] -and $entry.PSObject.Properties["trigger_source"]) {
    $matches = @($events | Where-Object { $_.event_type -eq $entry.trigger_event_type -and $_.source -eq $entry.trigger_source })
}

$lintPass = $lint.status -ne "FAIL"
$evidenceCount = @($matches).Count
$successRate = if ($lintPass -and $evidenceCount -gt 0) {
    [math]::Round([math]::Min(1.0, $evidenceCount / [math]::Max(1.0, [double]$entry.evidence_count)), 2)
} else {
    0.0
}
$status = if ($lintPass -and $successRate -ge 0.75) { "verified" } elseif ($lintPass) { "reviewed" } else { "rejected" }

$entry.status = $status
$entry.success_rate = $successRate
$evaluatedAt = (Get-Date).ToString("o")
$entry | Add-Member -NotePropertyName "evaluated_at" -NotePropertyValue $evaluatedAt -Force
foreach ($skill in @($registry.skills)) {
    if ($skill.name -eq $entry.name -or $skill.id -eq $entry.id) {
        $skill.status = $entry.status
        $skill.success_rate = $entry.success_rate
        $skill | Add-Member -NotePropertyName "evaluated_at" -NotePropertyValue $evaluatedAt -Force
    }
}
Write-Registry -Registry $registry

$result = [pscustomobject][ordered]@{
    schema_version = 1
    name = $entry.name
    status = $status
    success_rate = $successRate
    evidence_count = $evidenceCount
    lint_status = $lint.status
    registry_path = $REGISTRY_PATH
}

if ($Json) { $result | ConvertTo-Json -Depth 10 }
else { Write-Host "[SKILL_EVAL] $status -- $($entry.name) success_rate=$successRate" }
if ($status -eq "rejected") { exit 1 } else { exit 0 }
