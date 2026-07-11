# test_skills_runtime.ps1 -- skills registry stays static, runtime state goes to DEV_CORE_DATA
$ErrorActionPreference = "Stop"

$autoSkillsScript = Join-Path $PSScriptRoot "Auto\auto_skills_detector.ps1"
$weeklyScript = Join-Path $PSScriptRoot "Auto\weekly_maintenance.ps1"
$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_skills_runtime_test_" + [guid]::NewGuid().ToString("n"))
$platformRoot = Join-Path $tmpRoot "DEV_CORE"
$dataRoot = Join-Path $tmpRoot "DEV_CORE_DATA"
$oldPlatformRoot = $env:DEVCORE_PLATFORM_ROOT
$oldDataRoot = $env:DEVCORE_DATA_ROOT

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path (Join-Path $platformRoot "Skills"),(Join-Path $dataRoot "Logs\scripts"),(Join-Path $dataRoot "Memory"),(Join-Path $dataRoot "Backups\auto") -Force | Out-Null
    "memory" | Set-Content -LiteralPath (Join-Path $dataRoot "Memory\MEMORY.md") -Encoding UTF8

    $registryPath = Join-Path $platformRoot "Skills\skills_registry.json"
    $registry = [pscustomobject][ordered]@{
        schema_version = 1
        generated_at = "2026-07-11T00:00:00+01:00"
        source = "test"
        skills_count = 2
        skills = @(
            [pscustomobject][ordered]@{
                id = "dev-methodology"
                name = "dev-methodology"
                enabled = $true
                skill_path = "C:\devcore\DEV_CORE\Skills\dev-methodology\SKILL.md"
            },
            [pscustomobject][ordered]@{
                id = "qdrant"
                name = "qdrant"
                enabled = $true
                skill_path = "C:\devcore\DEV_CORE\Skills\qdrant\SKILL.md"
            }
        )
    }
    $registry | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $registryPath -Encoding UTF8
    $before = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8

    $env:DEVCORE_PLATFORM_ROOT = $platformRoot
    $env:DEVCORE_DATA_ROOT = $dataRoot

    & $autoSkillsScript | Out-Null

    $after = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8
    Assert-True ($before -eq $after) "auto_skills_detector must not mutate skills_registry.json"

    $runtimePath = Join-Path $dataRoot "Skills\skills_runtime.json"
    Assert-True (Test-Path -LiteralPath $runtimePath) "auto_skills_detector should create skills_runtime.json"
    $runtime = Get-Content -LiteralPath $runtimePath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($runtime.skills_count -eq 2) "runtime should track all registry skills"
    $qdrantRuntime = $runtime.skills | Where-Object { $_.id -eq "qdrant" } | Select-Object -First 1
    Assert-True (-not [string]::IsNullOrWhiteSpace([string]$qdrantRuntime.last_checked)) "runtime should track last_checked per skill"
    Assert-True (($runtime.skills | Where-Object { $_.id -eq "qdrant" }).usage_count -eq 0) "runtime should default usage_count to 0"
    Assert-True ($null -eq (($after | ConvertFrom-Json).skills[0].PSObject.Properties["last_checked"])) "registry skill should not contain last_checked"
    Assert-True ($null -eq (($after | ConvertFrom-Json).skills[0].PSObject.Properties["last_used"])) "registry skill should not contain last_used"
    Assert-True ($null -eq (($after | ConvertFrom-Json).skills[0].PSObject.Properties["usage_count"])) "registry skill should not contain usage_count"

    & $weeklyScript | Out-Null
    $afterWeekly = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8
    Assert-True ($before -eq $afterWeekly) "weekly_maintenance must not mutate skills_registry.json"

    Write-Host "[OK] skills runtime smoke tests passed"
} finally {
    if ($null -eq $oldPlatformRoot) {
        Remove-Item Env:\DEVCORE_PLATFORM_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_PLATFORM_ROOT = $oldPlatformRoot
    }

    if ($null -eq $oldDataRoot) {
        Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue
    } else {
        $env:DEVCORE_DATA_ROOT = $oldDataRoot
    }

    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
