# test_auto_skills_pipeline.ps1 -- smoke tests for DEV_CORE Auto-Skills Pipeline
$ErrorActionPreference = "Stop"

$autoSkillService = Join-Path $PSScriptRoot "auto_skill_service.ps1"
$skillLint = Join-Path $PSScriptRoot "skill_lint.ps1"
$skillEval = Join-Path $PSScriptRoot "skill_eval.ps1"
$dcScript = Join-Path $PSScriptRoot "dc.ps1"

$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("devcore_auto_skills_test_" + [guid]::NewGuid().ToString("n"))
$platformRoot = Join-Path $tmpRoot "DEV_CORE"
$dataRoot = Join-Path $tmpRoot "DEV_CORE_DATA"
$oldPlatformRoot = $env:DEVCORE_PLATFORM_ROOT
$oldDataRoot = $env:DEVCORE_DATA_ROOT
$oldProject = $env:DEVCORE_ACTIVE_PROJECT_NAME
$oldPwd = $env:DEVCORE_ACTIVE_PROJECT_PWD

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Write-JsonLine {
    param([string]$Path, $Value)
    ($Value | ConvertTo-Json -Depth 20 -Compress) | Add-Content -LiteralPath $Path -Encoding UTF8
}

try {
    New-Item -ItemType Directory -Path `
        (Join-Path $platformRoot "Skills"),`
        (Join-Path $platformRoot "Scripts"),`
        (Join-Path $dataRoot "Bus\events"),`
        (Join-Path $dataRoot "Logs\metrics"),`
        (Join-Path $dataRoot "Memory\devcore") -Force | Out-Null

    $env:DEVCORE_PLATFORM_ROOT = $platformRoot
    $env:DEVCORE_DATA_ROOT = $dataRoot
    $env:DEVCORE_ACTIVE_PROJECT_NAME = "devcore"
    $env:DEVCORE_ACTIVE_PROJECT_PWD = (Get-Location).Path

    [pscustomobject][ordered]@{
        schema_version = 1
        generated_at = "2026-07-11T00:00:00+01:00"
        source = "test"
        skills_count = 0
        skills = @()
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $platformRoot "Skills\skills_registry.json") -Encoding UTF8

    [pscustomobject][ordered]@{
        project = "devcore"
        current_task = "T-128"
        tasks = @(
            [pscustomobject][ordered]@{
                id = "T-128"
                title = "feat: implement auto skills pipeline"
                mode = "coding"
                status = "active"
                steps_total = 1
                steps_done = 0
            }
        )
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $dataRoot "Memory\devcore\tasks.json") -Encoding UTF8

    $today = Get-Date -Format "yyyy-MM-dd"
    $eventsFile = Join-Path $dataRoot "Bus\events\events-$today.jsonl"
    for ($i = 1; $i -le 3; $i++) {
        Write-JsonLine $eventsFile @{
            schema_version = 1
            id = "health-$i"
            timestamp = "2026-07-11T10:0$i`:00+01:00"
            source = "dashboard_api"
            event_type = "HealthCheckFailed"
            project = "devcore"
            task_id = "T-128"
            correlation_id = "health-$i"
            payload = @{ status = "fail" }
        }
    }

    Assert-True (Test-Path -LiteralPath $autoSkillService) "auto_skill_service.ps1 should exist"
    Assert-True (Test-Path -LiteralPath $skillLint) "skill_lint.ps1 should exist"
    Assert-True (Test-Path -LiteralPath $skillEval) "skill_eval.ps1 should exist"
    Copy-Item -LiteralPath $autoSkillService -Destination (Join-Path $platformRoot "Scripts\auto_skill_service.ps1") -Force
    Copy-Item -LiteralPath $skillLint -Destination (Join-Path $platformRoot "Scripts\skill_lint.ps1") -Force
    Copy-Item -LiteralPath $skillEval -Destination (Join-Path $platformRoot "Scripts\skill_eval.ps1") -Force

    $detectJson = & $autoSkillService -Action Detect -Threshold 3 -Json | Out-String
    $detect = $detectJson | ConvertFrom-Json
    Assert-True ($detect.candidates_created -eq 1) "Detect should create one candidate from repeated events"
    Assert-True (Test-Path -LiteralPath $detect.candidates[0].skill_path) "Detect should write candidate SKILL.md"

    $candidateName = [string]$detect.candidates[0].name
    $registry = Get-Content -LiteralPath (Join-Path $platformRoot "Skills\skills_registry.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $candidateEntry = $registry.skills | Where-Object { $_.name -eq $candidateName } | Select-Object -First 1
    Assert-True ($null -ne $candidateEntry) "Detect should register candidate"
    Assert-True ($candidateEntry.status -eq "candidate") "Candidate should start with candidate status"

    $lintJson = & $skillLint -Name $candidateName -Json | Out-String
    $lint = $lintJson | ConvertFrom-Json
    Assert-True ($lint.status -eq "PASS") "Generated candidate should pass skill lint"

    $evalJson = & $skillEval -Name $candidateName -Json | Out-String
    $eval = $evalJson | ConvertFrom-Json
    Assert-True ($eval.status -eq "verified") "Generated candidate should verify against available evidence"
    Assert-True ($eval.success_rate -gt 0) "Skill eval should compute success_rate"

    $promoteJson = & $autoSkillService -Action Promote -Name $candidateName -Json | Out-String
    $promote = $promoteJson | ConvertFrom-Json
    Assert-True ($promote.status -eq "active") "Promote should activate a verified candidate"
    Assert-True (Test-Path -LiteralPath (Join-Path $platformRoot "Skills\$candidateName\SKILL.md")) "Promote should copy candidate into active skills"

    $rejectJson = & $autoSkillService -Action Reject -Name $candidateName -Json | Out-String
    $reject = $rejectJson | ConvertFrom-Json
    Assert-True ($reject.status -eq "rejected") "Reject should mark a skill rejected"

    $dcList = & $dcScript skills list *>&1 | Out-String
    Assert-True ($dcList -match "skills") "dc skills list should route to auto_skill_service"

    $dcStatus = & $dcScript skills status *>&1 | Out-String
    Assert-True ($dcStatus -match "AUTO_SKILLS") "dc skills status should route to auto_skill_service"

    Write-Host "[OK] auto skills pipeline smoke tests passed"
} finally {
    if ($null -eq $oldPlatformRoot) { Remove-Item Env:\DEVCORE_PLATFORM_ROOT -ErrorAction SilentlyContinue } else { $env:DEVCORE_PLATFORM_ROOT = $oldPlatformRoot }
    if ($null -eq $oldDataRoot) { Remove-Item Env:\DEVCORE_DATA_ROOT -ErrorAction SilentlyContinue } else { $env:DEVCORE_DATA_ROOT = $oldDataRoot }
    if ($null -eq $oldProject) { Remove-Item Env:\DEVCORE_ACTIVE_PROJECT_NAME -ErrorAction SilentlyContinue } else { $env:DEVCORE_ACTIVE_PROJECT_NAME = $oldProject }
    if ($null -eq $oldPwd) { Remove-Item Env:\DEVCORE_ACTIVE_PROJECT_PWD -ErrorAction SilentlyContinue } else { $env:DEVCORE_ACTIVE_PROJECT_PWD = $oldPwd }
    Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
}
