# test_memory_service.ps1 -- smoke tests for DEV_CORE Memory Service
$ErrorActionPreference = "Stop"

$memoryServiceScript = Join-Path $PSScriptRoot "memory_service.ps1"
$memoryRotateScript = Join-Path $PSScriptRoot "Auto\memory_rotate.ps1"
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

if (-not (Test-Path -LiteralPath $memoryServiceScript)) {
    throw "memory_service.ps1 should exist"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore-memory-service-" + [guid]::NewGuid().ToString("N"))
$oldDataRoot = $env:DEVCORE_DATA_ROOT

try {
    $env:DEVCORE_DATA_ROOT = $tempRoot

    $memoryPath = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action Path -Name MEMORY | Select-Object -First 1
    Assert-True ($memoryPath -eq (Join-Path $tempRoot "Memory\MEMORY.md")) "Memory Service should resolve MEMORY.md path"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action EnsureMemory | Out-Null
    Assert-True (Test-Path -LiteralPath $memoryPath) "Memory Service should create MEMORY.md"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name LESSONS -Content "first lesson" | Out-Null
    $lessonsText = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action ReadText -Name LESSONS | Out-String
    Assert-True ($lessonsText.Trim() -eq "first lesson") "Memory Service should read written text"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action AppendText -Name LESSONS -Content "second lesson" | Out-Null
    $lessonsText = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action ReadText -Name LESSONS | Out-String
    Assert-True ($lessonsText -match "first lesson") "Memory Service append should keep existing text"
    Assert-True ($lessonsText -match "second lesson") "Memory Service append should add content"

    1..5 | ForEach-Object { "line $_" } | Set-Content $memoryPath -Encoding UTF8
    $rotateJson = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action RotateMemory -MaxLines 3 -KeepLines 2 -Json | Out-String
    $rotate = $rotateJson | ConvertFrom-Json
    Assert-True ($rotate.rotated -eq $true) "Memory Service should rotate when MEMORY.md exceeds MaxLines"
    Assert-True ((Get-Content $memoryPath).Count -eq 2) "Memory Service should keep configured number of lines"
    Assert-True (Test-Path -LiteralPath $rotate.archive_path) "Memory Service should archive before truncating"

    1..5 | ForEach-Object { "line $_" } | Set-Content $memoryPath -Encoding UTF8
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryRotateScript -MaxLines 3 -KeepLines 2 | Out-Null
    Assert-True ((Get-Content $memoryPath).Count -eq 2) "memory_rotate adapter should delegate rotation to Memory Service"

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name DECISIONS -Content "api decision line" | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name LESSONS -Content "api lesson line" | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name PATTERNS -Content "pattern one`npattern two`npattern three`npattern four`npattern five" | Out-Null
    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action WriteText -Name PERSONA -Content "# Persona" | Out-Null

    powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryHierarchyScript -Action Aggregate | Out-Null
    $scenarioPath = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryServiceScript -Action Path -Name SCENARIO -TaskType api | Select-Object -First 1
    $scenarioText = Get-Content $scenarioPath -Raw -Encoding UTF8
    Assert-True ($scenarioText -match "api decision line") "memory_hierarchy aggregate should write scenario decisions through Memory Service"
    Assert-True ($scenarioText -match "api lesson line") "memory_hierarchy aggregate should write scenario lessons through Memory Service"

    $queryText = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $memoryHierarchyScript -Action Query -Query "api" -TaskType api | Out-String
    Assert-True ($queryText -match "api decision line") "memory_hierarchy query should read scenario through Memory Service"

    Write-Host "[OK] memory service smoke tests passed" -ForegroundColor Green
} finally {
    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
