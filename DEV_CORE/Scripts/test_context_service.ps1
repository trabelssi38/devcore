# test_context_service.ps1 -- smoke tests for DEV_CORE Context Service
$ErrorActionPreference = "Stop"

$contextServiceScript = Join-Path $PSScriptRoot "context_service.ps1"
$memoryServiceScript = Join-Path $PSScriptRoot "memory_service.ps1"
$memoryHierarchyScript = Join-Path $PSScriptRoot "memory_hierarchy.ps1"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

if (-not (Test-Path -LiteralPath $contextServiceScript)) {
    throw "context_service.ps1 should exist"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-context-service-" + [guid]::NewGuid().ToString("N"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT

try {
    $env:DEVCORE_DATA_ROOT = $tempRoot

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name PERSONA -Content "api persona preference" | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name SCENARIO -TaskType api -Content "api scenario contract" | Out-Null

    $scoreJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $contextServiceScript -Action ScoreSources -Query "api contract" -TaskType api -Json | Out-String
    $score = $scoreJson | ConvertFrom-Json
    Assert-True ($score.schema_version -eq 1) "Context Service should return schema_version 1"
    Assert-True (($score.sources | Measure-Object).Count -ge 2) "Context Service should return scored sources"

    $scenario = $score.sources | Where-Object { $_.id -eq "L2:scenario:api" } | Select-Object -First 1
    $persona = $score.sources | Where-Object { $_.id -eq "L3:persona" } | Select-Object -First 1
    Assert-True ($null -ne $scenario) "Context Service should score the task scenario"
    Assert-True ($null -ne $persona) "Context Service should score persona"
    Assert-True ($scenario.score -gt $persona.score) "Task-specific scenario should outrank persona for matching task query"
    Assert-True ($scenario.included -eq $true) "Relevant scenario should be included"

    $queryText = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryHierarchyScript -Action Query -Query "api contract" -TaskType api | Out-String
    Assert-True ($queryText -match "CONTEXT SOURCE SCORES") "memory_hierarchy query should display context source scores"
    Assert-True ($queryText -match "L2:scenario:api") "memory_hierarchy query should include scored scenario id"

    Write-Host "[OK] context service smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
