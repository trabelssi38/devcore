# context_service.ps1 -- DEV_CORE v10 -- Context Service adapter
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("ScoreSources")]
    [string]$Action,
    [string]$Query = "",
    [string]$TaskType = "devcore",
    [double]$IncludeThreshold = 0.5,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$MEMORY_SERVICE = Join-Path $DEV_CORE "Scripts\memory_service.ps1"

function Get-FreshnessScore {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return 0.0 }
    $ageDays = ((Get-Date) - (Get-Item -LiteralPath $Path).LastWriteTime).TotalDays
    if ($ageDays -le 7) { return 1.0 }
    if ($ageDays -le 30) { return 0.8 }
    if ($ageDays -le 90) { return 0.6 }
    return 0.4
}

function Get-RelevanceScore {
    param(
        [string]$Content,
        [string]$Needle,
        [string]$ScenarioType,
        [double]$Base = 0.45
    )

    $score = $Base
    $lowerContent = if ($Content) { $Content.ToLowerInvariant() } else { "" }
    $terms = @($Needle.ToLowerInvariant() -split "\s+" | Where-Object { $_.Length -gt 2 })
    $hits = 0
    foreach ($term in $terms) {
        if ($lowerContent.Contains($term)) { $hits++ }
    }
    if ($terms.Count -gt 0) {
        $score += [Math]::Min(0.35, 0.35 * ($hits / $terms.Count))
    }
    if ($ScenarioType -and $lowerContent.Contains($ScenarioType.ToLowerInvariant())) {
        $score += 0.15
    }
    return [Math]::Min(1.0, [Math]::Round($score, 4))
}

function Get-MatchedTerms {
    param(
        [string]$Content,
        [string]$Needle
    )

    $lowerContent = if ($Content) { $Content.ToLowerInvariant() } else { "" }
    $terms = @($Needle.ToLowerInvariant() -split "\s+" | Where-Object { $_.Length -gt 2 })
    $matches = @()
    foreach ($term in $terms) {
        if ($lowerContent.Contains($term)) { $matches += $term }
    }
    return @($matches | Select-Object -Unique)
}

function New-SourceJustification {
    param(
        [string]$Type,
        [string[]]$MatchedTerms,
        [double]$Score,
        [double]$Freshness,
        [double]$Authority,
        [bool]$Included
    )

    $reasons = @()
    if ($MatchedTerms.Count -gt 0) {
        $reasons += ("matched query terms: " + (($MatchedTerms | Select-Object -First 5) -join ", "))
    } else {
        $reasons += "no direct query term match"
    }
    if ($Freshness -ge 0.8) { $reasons += "fresh source" } else { $reasons += "older source" }
    if ($Authority -ge 0.85) { $reasons += "high authority $Type" } else { $reasons += "supporting $Type" }
    $decision = if ($Included) { "included" } else { "excluded" }
    return "${decision}: score=$Score; " + ($reasons -join "; ")
}

function New-SourceScore {
    param(
        [string]$Id,
        [string]$Tier,
        [string]$Type,
        [string]$Path,
        [double]$Authority,
        [double]$RelevanceBase
    )

    $content = ""
    if (Test-Path -LiteralPath $Path) {
        $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    }
    $relevance = Get-RelevanceScore -Content $content -Needle $Query -ScenarioType $TaskType -Base $RelevanceBase
    $freshness = Get-FreshnessScore -Path $Path
    $score = [Math]::Round(($relevance * 0.5) + ($freshness * 0.2) + ($Authority * 0.3), 4)
    $included = ($score -ge $IncludeThreshold)
    $matchedTerms = @(Get-MatchedTerms -Content $content -Needle $Query)
    [pscustomobject]@{
        id = $Id
        tier = $Tier
        type = $Type
        path = $Path
        score = $score
        relevance = $relevance
        freshness = $freshness
        authority = $Authority
        included = $included
        matched_terms = $matchedTerms
        justification = New-SourceJustification -Type $Type -MatchedTerms $matchedTerms -Score $score -Freshness $freshness -Authority $Authority -Included $included
    }
}

switch ($Action) {
    "ScoreSources" {
        $personaPath = & $MEMORY_SERVICE -Action Path -Name PERSONA
        $scenarioPath = & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType $TaskType
        $fallbackScenarioPath = & $MEMORY_SERVICE -Action Path -Name SCENARIO -TaskType "devcore"
        $dbRoot = Split-Path -Parent (& $MEMORY_SERVICE -Action Path -Name MEMORY)
        $dbPath = Join-Path $dbRoot "conversations.db"

        $sources = @()
        $sources += New-SourceScore -Id "L3:persona" -Tier "L3" -Type "persona" -Path $personaPath -Authority 0.95 -RelevanceBase 0.35
        if (Test-Path -LiteralPath $scenarioPath) {
            $sources += New-SourceScore -Id "L2:scenario:$TaskType" -Tier "L2" -Type "scenario" -Path $scenarioPath -Authority 0.90 -RelevanceBase 0.50
        } elseif (Test-Path -LiteralPath $fallbackScenarioPath) {
            $sources += New-SourceScore -Id "L2:scenario:devcore" -Tier "L2" -Type "scenario_fallback" -Path $fallbackScenarioPath -Authority 0.75 -RelevanceBase 0.35
        }
        $sources += [pscustomobject]@{
            id = "L1:qdrant"
            tier = "L1"
            type = "vector"
            path = "http://localhost:6333"
            score = 0.0
            relevance = 0.0
            freshness = 1.0
            authority = 0.85
            included = $false
            matched_terms = @()
            justification = "excluded: vector search is scored by memory_hierarchy query results, not static source scoring"
        }
        $sqliteExists = Test-Path -LiteralPath $dbPath
        $sources += [pscustomobject]@{
            id = "L0:sqlite"
            tier = "L0"
            type = "conversation_fts"
            path = $dbPath
            score = if ($sqliteExists) { 0.46 } else { 0.0 }
            relevance = 0.30
            freshness = Get-FreshnessScore -Path $dbPath
            authority = 0.65
            included = $false
            matched_terms = @()
            justification = if ($sqliteExists) { "excluded: fallback FTS source kept below include threshold until higher tiers are insufficient" } else { "excluded: SQLite fallback database not found" }
        }

        $orderedSources = @($sources | Sort-Object score -Descending)
        $payload = [pscustomobject]@{
            schema_version = 1
            query = $Query
            task_type = $TaskType
            include_threshold = $IncludeThreshold
            sources = $orderedSources
        }

        if ($Json) {
            $payload | ConvertTo-Json -Depth 8
        } else {
            $orderedSources | ForEach-Object {
                "{0} score={1} relevance={2} freshness={3} authority={4} included={5}" -f $_.id, $_.score, $_.relevance, $_.freshness, $_.authority, $_.included
            }
        }
        exit 0
    }
}
