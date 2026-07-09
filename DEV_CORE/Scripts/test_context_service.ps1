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
    Assert-True (-not [string]::IsNullOrWhiteSpace($scenario.justification)) "Included scenario should explain why it was selected"
    Assert-True ($scenario.justification -match "api|contract") "Scenario justification should mention matched query evidence"
    Assert-True (-not [string]::IsNullOrWhiteSpace($persona.justification)) "Persona should expose a source justification"

    $queryText = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryHierarchyScript -Action Query -Query "api contract" -TaskType api | Out-String
    Assert-True ($queryText -match "CONTEXT SOURCE SCORES") "memory_hierarchy query should display context source scores"
    Assert-True ($queryText -match "L2:scenario:api") "memory_hierarchy query should include scored scenario id"
    Assert-True ($queryText -match "reason=") "memory_hierarchy query should display source justifications"

    $smallBlockJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $contextServiceScript -Action OffloadBlock -Content "short context" -TaskId T-116 -Type context -MaxChars 100 -Json | Out-String
    $smallBlock = $smallBlockJson | ConvertFrom-Json
    Assert-True ($smallBlock.offloaded -eq $false) "Small context blocks should stay inline"
    Assert-True ($smallBlock.content -eq "short context") "Small context block content should be preserved"

    $largeContent = "api contract " * 20
    $largeBlockJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $contextServiceScript -Action OffloadBlock -Content $largeContent -TaskId T-116 -Type context -MaxChars 80 -Json | Out-String
    $largeBlock = $largeBlockJson | ConvertFrom-Json
    Assert-True ($largeBlock.offloaded -eq $true) "Large context blocks should be offloaded"
    Assert-True ($largeBlock.node_id -match "^T116_context_") "Large context offload should return a Canvas node id"
    Assert-True ($largeBlock.content -match "OFFLOADED context block") "Large context output should be replaced by a compact marker"

    $fetched = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "canvas_manager.ps1") -Action Fetch -NodeId $largeBlock.node_id | Out-String
    Assert-True ($fetched -match "api contract") "Offloaded context should be fetchable from Canvas refs"

    Write-Host "[OK] context service smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
