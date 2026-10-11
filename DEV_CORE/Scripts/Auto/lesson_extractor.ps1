# lesson_extractor.ps1 -- project-scoped lesson extraction
[CmdletBinding()]
param(
    [string]$Project
)

if ([string]::IsNullOrWhiteSpace($Project)) {
    Write-Warning 'Lesson extraction skipped: pass an explicit -Project to avoid writing shared legacy memory.'
    exit 0
}
if ($Project -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') { throw 'Project must be a simple registered project id.' }
$ErrorActionPreference = 'Stop'
$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT -and (Test-Path -LiteralPath (Join-Path $env:DEVCORE_PLATFORM_ROOT 'Scripts\platform_version.ps1'))) {
    $env:DEVCORE_PLATFORM_ROOT
} else {
    Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
if (-not [IO.Path]::IsPathRooted($env:DEVCORE_DATA_ROOT)) {
    throw 'DEVCORE_DATA_ROOT must be set to an absolute path.'
}
$DEV_CORE_DATA = [IO.Path]::GetFullPath($env:DEVCORE_DATA_ROOT)
$configRoot = if ($env:DEVCORE_CONFIG_ROOT) { $env:DEVCORE_CONFIG_ROOT } else { Join-Path $DEV_CORE 'Config' }
if (-not [IO.Path]::IsPathRooted($configRoot)) { throw 'DEVCORE_CONFIG_ROOT must be absolute.' }
$registryPath = Join-Path ([IO.Path]::GetFullPath($configRoot)) 'projects.json'
if (-not (Test-Path -LiteralPath $registryPath -PathType Leaf)) { throw "Project registry not found: $registryPath" }
$registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
$matches = @($registry.projects | Where-Object { $_.name -ceq $Project })
if ($matches.Count -ne 1 -or -not $matches[0].path -or -not [IO.Path]::IsPathRooted([string]$matches[0].path)) {
    throw "Project '$Project' must resolve to exactly one absolute path in projects.json."
}
$repoPath = [IO.Path]::GetFullPath([string]$matches[0].path)
if (-not (Test-Path -LiteralPath $repoPath -PathType Container)) { throw "Registered project path not found: $repoPath" }
$gitRootLines = & git -C $repoPath rev-parse --show-toplevel 2>$null
$gitRootExitCode = $LASTEXITCODE
$gitRoot = $gitRootLines | Select-Object -First 1
if ($gitRootExitCode -ne 0 -or -not $gitRoot) { throw "Registered project is not a Git repository: $repoPath" }
$gitRoot = [IO.Path]::GetFullPath(([string]$gitRoot).Trim())
if (-not $gitRoot.Equals($repoPath, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Registered path must be the project Git root: $repoPath"
}

. (Join-Path $DEV_CORE 'Scripts\platform_version.ps1')
$pythonExe = Get-DevCorePython
$TODAY = Get-Date -Format 'yyyy-MM-dd'
$projectMemory = Join-Path (Join-Path $DEV_CORE_DATA 'Memory') $Project
$lessonsFile = Join-Path $projectMemory 'LESSONS.md'
$logDir = Join-Path (Join-Path $DEV_CORE_DATA 'Logs\scripts') $Project
$LOG = Join-Path $logDir "lesson_extractor_$TODAY.log"
$lessonDir = Join-Path (Join-Path (Join-Path (Join-Path $DEV_CORE_DATA 'Vault') 'Lessons') $Project) 'workflow'
New-Item -ItemType Directory -Path $projectMemory,$logDir -Force | Out-Null
function Log {
    param([string]$Message, [string]$Color = 'Gray')
    $line = "[$(Get-Date -Format HH:mm:ss)] [$Project] $Message"
    Add-Content -LiteralPath $LOG -Value $line -ErrorAction SilentlyContinue
    Write-Host "    $line" -ForegroundColor $Color
}
function Write-AtomicUtf8 {
    param([string]$Path, [string]$Text)
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temp = Join-Path $parent ('.' + [IO.Path]::GetFileName($Path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    $encoding = New-Object System.Text.UTF8Encoding($false)
    try {
        [IO.File]::WriteAllText($temp, $Text, $encoding)
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            [IO.File]::Move($temp, $Path, $true)
        } else {
            [IO.File]::Move($temp, $Path)
        }
    } finally {
        if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
    }
}

$PLATFORM = Get-DevCorePlatformInfo
Log "$($PLATFORM.title) lesson_extractor -- projet $Project" 'Cyan'

# Read the transactional board through the explicit-project service API; never inspect legacy tasks.json.
$oldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($oldPythonPath) { "$DEV_CORE;$oldPythonPath" } else { $DEV_CORE }
$boardJson = $null
try {
    Push-Location $DEV_CORE
    $boardJson = (& $pythonExe -m devcore_engine.cli task board --project $Project --json 2>&1 | Out-String).Trim()
    $cliExitCode = $LASTEXITCODE
} finally {
    Pop-Location
    $env:PYTHONPATH = $oldPythonPath
}
if ($cliExitCode -ne 0) { throw "Task board query failed for project '$Project' (exit $cliExitCode): $boardJson" }
try { $board = $boardJson | ConvertFrom-Json } catch { throw "Task board returned invalid JSON for '$Project'." }
if ($board.project -cne $Project -or $null -eq $board.tasks) { throw "Task board project mismatch for '$Project'." }
$doneTasks = @($board.tasks | Where-Object { $_.status -eq 'done' })

if (Test-Path -LiteralPath $lessonsFile -PathType Leaf) {
    $content = Get-Content -LiteralPath $lessonsFile -Raw
} else {
    $content = @"
# LESSONS.md -- $($PLATFORM.title) / $Project
<!-- Auto-genere par lesson_extractor.ps1 -->
<!-- Score min inclusion : 0.5 | Derniere maj : $TODAY -->

## Architecture

## Chemins & Configuration

## Debugging

## Workflow
"@
}

foreach ($task in $doneTasks) {
    $tag = "lesson:$($task.id)"
    if ($content -notmatch [regex]::Escape($tag)) {
        $stepTitles = @($task.steps | ForEach-Object { $_.title } | Where-Object { $_ })
        $stepsInfo = if ($stepTitles.Count) { $stepTitles -join ' -> ' } else { "$($task.steps_done)/$($task.steps_total) steps" }
        $content += "`n- [score: 0.7] [created: $TODAY] [$tag] $($task.title) ($($task.mode)) : $stepsInfo"
        Log "Lecon ajoutee depuis $($task.id)" 'Green'
    }
}

try {
    $recentCommits = @(& git -C $repoPath log --since='7 days ago' --format='%s' 2>&1)
    $gitLogExitCode = $LASTEXITCODE
    if ($gitLogExitCode -ne 0) { throw ($recentCommits -join "`n") }
    if ($recentCommits.Count) {
        $fixCount = @($recentCommits | Where-Object { $_ -match '^fix:' }).Count
        $featCount = @($recentCommits | Where-Object { $_ -match '^feat:' }).Count
        $tag = "lesson:git-stats-$TODAY"
        if ($content -notmatch [regex]::Escape($tag)) {
            $content += "`n- [score: 0.6] [created: $TODAY] [$tag] Semaine : $($recentCommits.Count) commits ($featCount feat, $fixCount fix)"
            Log 'Stats Git ajoutees' 'Green'
        }
    }
} catch { Log "Git log extraction echouee: $_" 'Yellow' }

$now = Get-Date
$updatedLines = foreach ($line in ($content -split "\r?\n")) {
    if ($line -match '^\-\s*\[score:\s*([\d\.]+)\](.*)') {
        $score = [double]$Matches[1]
        $rest = $Matches[2]
        $entryDate = $now
        if ($rest -match '\[created:\s*(\d{4}-\d{2}-\d{2})\]') {
            try { $entryDate = [datetime]::Parse($Matches[1]) } catch {}
        } else { $rest = " [created: $TODAY]$rest" }
        $ageDays = ($now - $entryDate).TotalDays
        $multiplier = if ($ageDays -gt 180) { 0.5 } elseif ($ageDays -gt 90) { 0.7 } elseif ($ageDays -gt 30) { 0.9 } else { 1.0 }
        $newScore = [math]::Round($score * $multiplier, 2)
        if ($newScore -ge 0.3) { "- [score: $newScore]$rest" } else { Log "Entree expiree (score $newScore)" 'Yellow' }
    } else { $line }
}
$content = ($updatedLines -join "`n") -replace 'Derniere maj : \d{4}-\d{2}-\d{2}', "Derniere maj : $TODAY"
Write-AtomicUtf8 -Path $lessonsFile -Text ($content.TrimEnd() + "`n")

New-Item -ItemType Directory -Path $lessonDir -Force | Out-Null
$noteFile = Join-Path $lessonDir "session_$TODAY.md"
if (-not (Test-Path -LiteralPath $noteFile -PathType Leaf)) {
    $doneSummary = if ($doneTasks.Count) { ($doneTasks | ForEach-Object { "- [x] $($_.id): $($_.title) ($($_.mode))" }) -join "`n" } else { 'Aucune' }
    $note = @"
---
title: Session $Project $TODAY
date: $TODAY
project: $Project
tags: [lesson, workflow, auto]
score: 0.5
---

# Session $Project $TODAY

## Taches completees
$doneSummary

## Lecons
Voir `Memory/$Project/LESSONS.md` pour les lecons consolidees.

## Next actions
- [ ] Continuer les taches en attente
"@
    Write-AtomicUtf8 -Path $noteFile -Text $note
    Log "Note creee : $noteFile" 'Green'
}
Log 'lesson_extractor termine' 'Green'
