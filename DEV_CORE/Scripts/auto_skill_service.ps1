# auto_skill_service.ps1 -- DEV_CORE v11.2 -- controlled auto-skills pipeline
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("List", "Candidates", "Detect", "Promote", "Reject", "Status")]
    [string]$Action,
    [string]$Name = "",
    [int]$Threshold = 3,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$SKILLS_ROOT = Join-Path $DEV_CORE "Skills"
$REGISTRY_PATH = Join-Path $SKILLS_ROOT "skills_registry.json"
$DATA_SKILLS_ROOT = Join-Path $DEV_CORE_DATA "Skills"
$CANDIDATES_ROOT = Join-Path $DATA_SKILLS_ROOT "Candidates"
$EVENTS_ROOT = Join-Path $DEV_CORE_DATA "Bus\events"
$SKILL_LINT = Join-Path $PSScriptRoot "skill_lint.ps1"
$SKILL_EVAL = Join-Path $PSScriptRoot "skill_eval.ps1"

function Ensure-AutoSkillDirs {
    New-Item -ItemType Directory -Path $SKILLS_ROOT,$DATA_SKILLS_ROOT,$CANDIDATES_ROOT -Force | Out-Null
}

function New-EmptyRegistry {
    [pscustomobject][ordered]@{
        schema_version = 1
        generated_at = (Get-Date).ToString("o")
        source = "auto_skill_service"
        skills_count = 0
        skills = @()
    }
}

function Read-Registry {
    Ensure-AutoSkillDirs
    if (-not (Test-Path -LiteralPath $REGISTRY_PATH)) {
        $registry = New-EmptyRegistry
        $registry | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $REGISTRY_PATH -Encoding UTF8
        return $registry
    }
    try {
        $registry = Get-Content -LiteralPath $REGISTRY_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        $registry = New-EmptyRegistry
    }
    if (-not $registry.PSObject.Properties["skills"] -or $null -eq $registry.skills) {
        $registry | Add-Member -NotePropertyName "skills" -NotePropertyValue @() -Force
    }
    return $registry
}

function Write-Registry {
    param($Registry)
    $skills = @($Registry.skills)
    $Registry.skills_count = $skills.Count
    $Registry.generated_at = (Get-Date).ToString("o")
    $Registry.skills = $skills
    $Registry | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $REGISTRY_PATH -Encoding UTF8
}

function ConvertTo-SkillName {
    param([string]$Value)
    $clean = $Value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
    $clean = $clean.Trim("-")
    if ([string]::IsNullOrWhiteSpace($clean)) { return "auto-skill" }
    if ($clean.Length -gt 72) { $clean = $clean.Substring(0, 72).Trim("-") }
    return $clean
}

function Get-FileHashHex {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
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

function Get-RegistryEntry {
    param($Registry, [string]$SkillName)
    @($Registry.skills) | Where-Object { $_.name -eq $SkillName -or $_.id -eq $SkillName } | Select-Object -First 1
}

function Set-RegistryEntry {
    param($Registry, $Entry)
    $items = @()
    $found = $false
    foreach ($skill in @($Registry.skills)) {
        if ($skill.name -eq $Entry.name -or $skill.id -eq $Entry.id) {
            $items += $Entry
            $found = $true
        } else {
            $items += $skill
        }
    }
    if (-not $found) { $items += $Entry }
    $Registry.skills = $items
}

function New-CandidateSkill {
    param(
        [string]$SkillName,
        [string]$EventType,
        [string]$Source,
        [int]$Count
    )

    $candidateDir = Join-Path $CANDIDATES_ROOT $SkillName
    New-Item -ItemType Directory -Path $candidateDir -Force | Out-Null
    $skillPath = Join-Path $candidateDir "SKILL.md"
    $description = "Auto-skill candidate generated from repeated $EventType events emitted by $Source."
    $content = @"
---
name: $SkillName
description: $description
status: candidate
source: repeated_event
trust_level: low
---

# Skill -- $SkillName

## Trigger
- Use when DEV_CORE observes repeated `$EventType` events from `$Source`.

## Workflow
1. Read the latest event payloads for `$EventType`.
2. Identify the common failure or repeated action.
3. Propose the smallest diagnostic or automation step.
4. Do not mutate files, secrets, git state, or configuration unless a human explicitly approves.

## Evidence
- event_type: `$EventType`
- source: `$Source`
- occurrences: $Count

## Safety
- Candidate skills are advisory until promoted.
- Do not run destructive commands.
- Do not expose prompt content, credentials, tokens, or raw logs.
"@
    $content | Set-Content -LiteralPath $skillPath -Encoding UTF8
    return [pscustomobject][ordered]@{
        name = $SkillName
        skill_path = $skillPath
        event_type = $EventType
        source = $Source
        occurrences = $Count
        hash = Get-FileHashHex -Path $skillPath
    }
}

function Invoke-Detect {
    $registry = Read-Registry
    $events = Read-AllEvents
    $groups = @{}
    foreach ($event in @($events)) {
        $eventType = if ($event.event_type) { [string]$event.event_type } else { "unknown" }
        $source = if ($event.source) { [string]$event.source } else { "unknown" }
        $key = "$eventType|$source"
        if (-not $groups.ContainsKey($key)) {
            $groups[$key] = [ordered]@{ event_type = $eventType; source = $source; count = 0 }
        }
        $groups[$key].count++
    }

    $created = @()
    foreach ($key in @($groups.Keys | Sort-Object)) {
        $group = $groups[$key]
        if ([int]$group.count -lt $Threshold) { continue }
        $skillName = ConvertTo-SkillName -Value "auto-$($group.event_type)-$($group.source)"
        if (Get-RegistryEntry -Registry $registry -SkillName $skillName) { continue }

        $candidate = New-CandidateSkill -SkillName $skillName -EventType $group.event_type -Source $group.source -Count $group.count
        $entry = [pscustomobject][ordered]@{
            id = $candidate.name
            name = $candidate.name
            description = "Auto-skill candidate generated from repeated $($candidate.event_type) events."
            scope = "global"
            status = "candidate"
            source = "repeated_event"
            created_from_task = $null
            trust_level = "low"
            version = "0.1.0"
            hash = $candidate.hash
            last_used = $null
            success_rate = 0
            enabled = $false
            auto_generated = $true
            skill_path = $candidate.skill_path
            trigger_event_type = $candidate.event_type
            trigger_source = $candidate.source
            evidence_count = $candidate.occurrences
        }
        Set-RegistryEntry -Registry $registry -Entry $entry
        $created += $candidate
    }

    Write-Registry -Registry $registry
    [pscustomobject][ordered]@{
        schema_version = 1
        threshold = $Threshold
        patterns_found = @($groups.Keys).Count
        candidates_created = @($created).Count
        candidates = @($created)
        registry_path = $REGISTRY_PATH
    }
}

function Invoke-Promote {
    if ([string]::IsNullOrWhiteSpace($Name)) { throw "Name is required for Promote." }
    $registry = Read-Registry
    $entry = Get-RegistryEntry -Registry $registry -SkillName $Name
    if (-not $entry) { throw "Skill not found: $Name" }

    if (Test-Path -LiteralPath $SKILL_LINT) {
        $lint = & $SKILL_LINT -Name $entry.name -Json | Out-String | ConvertFrom-Json
        if ($lint.status -eq "FAIL") { throw "Skill lint failed: $($lint.errors -join '; ')" }
    }
    if ($entry.status -ne "verified" -and (Test-Path -LiteralPath $SKILL_EVAL)) {
        $eval = & $SKILL_EVAL -Name $entry.name -Json | Out-String | ConvertFrom-Json
        $entry = Get-RegistryEntry -Registry (Read-Registry) -SkillName $Name
        if ($eval.status -ne "verified") { throw "Skill eval did not verify: $Name" }
    }

    $activeDir = Join-Path $SKILLS_ROOT $entry.name
    New-Item -ItemType Directory -Path $activeDir -Force | Out-Null
    $activePath = Join-Path $activeDir "SKILL.md"
    Copy-Item -LiteralPath $entry.skill_path -Destination $activePath -Force
    $entry.skill_path = $activePath
    $entry.hash = Get-FileHashHex -Path $activePath
    $entry.status = "active"
    $entry.enabled = $true
    $entry.trust_level = "medium"
    Set-RegistryEntry -Registry $registry -Entry $entry
    Write-Registry -Registry $registry

    [pscustomobject][ordered]@{
        schema_version = 1
        name = $entry.name
        status = $entry.status
        skill_path = $entry.skill_path
        registry_path = $REGISTRY_PATH
    }
}

function Invoke-Reject {
    if ([string]::IsNullOrWhiteSpace($Name)) { throw "Name is required for Reject." }
    $registry = Read-Registry
    $entry = Get-RegistryEntry -Registry $registry -SkillName $Name
    if (-not $entry) { throw "Skill not found: $Name" }
    $entry.status = "rejected"
    $entry.enabled = $false
    Set-RegistryEntry -Registry $registry -Entry $entry
    Write-Registry -Registry $registry
    [pscustomobject][ordered]@{
        schema_version = 1
        name = $entry.name
        status = $entry.status
        registry_path = $REGISTRY_PATH
    }
}

function Invoke-List {
    $registry = Read-Registry
    [pscustomobject][ordered]@{
        schema_version = 1
        registry_path = $REGISTRY_PATH
        skills_count = @($registry.skills).Count
        skills = @($registry.skills)
    }
}

function Invoke-Candidates {
    $registry = Read-Registry
    $candidates = @($registry.skills | Where-Object { $_.status -eq "candidate" -or $_.status -eq "reviewed" -or $_.status -eq "verified" })
    [pscustomobject][ordered]@{
        schema_version = 1
        candidates_root = $CANDIDATES_ROOT
        candidates_count = @($candidates).Count
        candidates = $candidates
    }
}

function Invoke-Status {
    $registry = Read-Registry
    $skills = @($registry.skills)
    [pscustomobject][ordered]@{
        schema_version = 1
        registry_path = $REGISTRY_PATH
        candidates_root = $CANDIDATES_ROOT
        total = $skills.Count
        candidate = @($skills | Where-Object status -eq "candidate").Count
        reviewed = @($skills | Where-Object status -eq "reviewed").Count
        verified = @($skills | Where-Object status -eq "verified").Count
        active = @($skills | Where-Object { $_.status -eq "active" -or ($_.enabled -eq $true -and -not $_.status) }).Count
        rejected = @($skills | Where-Object status -eq "rejected").Count
    }
}

$result = switch ($Action) {
    "List" { Invoke-List }
    "Candidates" { Invoke-Candidates }
    "Detect" { Invoke-Detect }
    "Promote" { Invoke-Promote }
    "Reject" { Invoke-Reject }
    "Status" { Invoke-Status }
}

if ($Json) {
    $result | ConvertTo-Json -Depth 30
} else {
    switch ($Action) {
        "List" { Write-Host "[AUTO_SKILLS] list OK -- $($result.skills_count) skills" }
        "Candidates" { Write-Host "[AUTO_SKILLS] candidates OK -- $($result.candidates_count) candidate(s)" }
        "Detect" { Write-Host "[AUTO_SKILLS] detect OK -- $($result.candidates_created) candidate(s) created" }
        "Promote" { Write-Host "[AUTO_SKILLS] promote OK -- $($result.name) active" }
        "Reject" { Write-Host "[AUTO_SKILLS] reject OK -- $($result.name) rejected" }
        "Status" { Write-Host "[AUTO_SKILLS] status OK -- total=$($result.total) candidates=$($result.candidate) active=$($result.active)" }
    }
}
