# test_hermes_integration.ps1 -- DEV_CORE + Hermes Integration Tests

param(
    [switch]$All,
    [switch]$Hermes,
    [switch]$MCP,
    [switch]$Cron,
    [switch]$Paths
)

$ErrorActionPreference = "Continue"
$DEVCORE_ROOT = "C:\devcore\DEV_CORE"
. "$DEVCORE_ROOT\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$HERMES_BIN = "C:\devcore\hermes\.venv\Scripts\hermes.exe"
$passed = 0
$failed = 0

function Test-Section {
    param([string]$Name)
    Write-Host ""
    Write-Host "  [$Name]" -ForegroundColor Cyan
    Write-Host "  ========================================" -ForegroundColor DarkGray
}

function Test-Item {
    param([string]$Name, [bool]$Result, [string]$Details = "")
    $icon = if ($Result) { "[PASS]" } else { "[FAIL]" }
    $color = if ($Result) { "Green" } else { "Red" }
    Write-Host "    $icon $Name" -ForegroundColor $color
    if ($Result) { $script:passed++ } else { $script:failed++ }
    if ($Details -and -not $Result) {
        Write-Host "         $Details" -ForegroundColor DarkGray
    }
}

# ========== HERMES TESTS ==========

function Test-Hermes {
    Test-Section "HERMES AGENT"

    # Hermes binaire
    $hermesOk = Test-Path $HERMES_BIN
    Test-Item "Hermes installe" $hermesOk
    if ($hermesOk) {
        $version = & $HERMES_BIN --version 2>&1 | Select-Object -First 1
        Write-Host "         Version: $version" -ForegroundColor DarkGray
    }

    # Config Hermes
    $configPath = "$env:USERPROFILE\.hermes\config.yaml"
    $configOk = Test-Path $configPath
    Test-Item "Config Hermes" $configOk $configPath

    # .env Hermes
    $envPath = "$env:USERPROFILE\.hermes\.env"
    $envOk = Test-Path $envPath
    Test-Item "Env Hermes" $envOk $envPath

    # Context file
    $ctxPath = "$DEVCORE_ROOT\Config\hermes_context.md"
    $ctxOk = Test-Path $ctxPath
    Test-Item "Context file" $ctxOk $ctxPath
}

# ========== MCP TESTS ==========

function Test-MCP {
    Test-Section "MCP SERVERS"

    # MCP folder
    $mcpPath = "$DEVCORE_ROOT\MCP"
    $mcpOk = Test-Path $mcpPath
    Test-Item "MCP folder" $mcpOk $mcpPath

    # devcore-scripts server
    $devcoreServer = "$mcpPath\devcore-scripts\server.py"
    $devcoreOk = Test-Path $devcoreServer
    Test-Item "devcore-scripts server" $devcoreOk $devcoreServer

    # qdrant server
    $qdrantServer = "$mcpPath\qdrant-storage\server.py"
    $qdrantOk = Test-Path $qdrantServer
    Test-Item "qdrant-storage server" $qdrantOk $qdrantServer

    # obsidian server
    $obsidianServer = "$mcpPath\obsidian-vault\server.py"
    $obsidianOk = Test-Path $obsidianServer
    Test-Item "obsidian-vault server" $obsidianOk $obsidianServer

    # requirements
    $reqOk = Test-Path "$mcpPath\requirements.txt"
    Test-Item "MCP requirements" $reqOk
}

# ========== CRON TESTS ==========

function Test-Cron {
    Test-Section "CRON TASKS"

    # hermes_cron.yaml
    $cronPath = "$DEVCORE_ROOT\Scripts\hermes_cron.yaml"
    $cronOk = Test-Path $cronPath
    Test-Item "hermes_cron.yaml" $cronOk $cronPath

    # hermes-daemon.ps1
    $daemonPath = "$DEVCORE_ROOT\Scripts\hermes-daemon.ps1"
    $daemonOk = Test-Path $daemonPath
    Test-Item "hermes-daemon.ps1" $daemonOk $daemonPath

    # Windows scheduled tasks
    $tasks = @("HERMES_Daemon", "DEV_CORE_Daily_Launch", "DEV_CORE_Daily_Endday", "DEV_CORE_Weekly_Maintenance")
    foreach ($taskName in $tasks) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        $taskOk = ($null -ne $task)
        Test-Item "Scheduled Task: $taskName" $taskOk
        if ($taskOk) {
            Write-Host "         State: $($task.State)" -ForegroundColor DarkGray
        }
    }
}

# ========== PATHS TESTS ==========

function Test-Paths {
    Test-Section "DEV_CORE PATHS"

    $paths = @{
        "Scripts" = "$DEVCORE_ROOT\Scripts"
        "Skills" = "$DEVCORE_ROOT\Skills"
        "Config" = "$DEVCORE_ROOT\Config"
        "Dashboard" = "$DEVCORE_ROOT\Dashboard"
        "MCP" = "$DEVCORE_ROOT\MCP"
        "Memory" = "$DEVCORE_ROOT\..\DEV_CORE_DATA\Memory"
        "Vault" = "$DEVCORE_ROOT\..\DEV_CORE_DATA\Vault"
        "Logs" = "$DEVCORE_ROOT\..\DEV_CORE_DATA\Logs"
    }

    foreach ($name in $paths.Keys) {
        $path = $paths[$name]
        $exists = Test-Path $path
        Test-Item "$name" $exists $path
    }
}

# ========== SERVICES TESTS ==========

function Test-Services {
    Test-Section "SERVICES"

    # Qdrant
    try {
        $q = Invoke-RestMethod "http://localhost:6333/" -TimeoutSec 3
        Test-Item "Qdrant (6333)" $true
        $cols = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3
        $colCount = $cols.result.collections.Count
        Write-Host "         Collections: $colCount" -ForegroundColor DarkGray
    } catch {
        Test-Item "Qdrant (6333)" $false "Non accessible"
    }

}

# ========== SKILLS TESTS ==========

function Test-Skills {
    Test-Section "DEV_CORE SKILLS"

    $skills = @("devcore", "qdrant", "obsidian", "fabric-patterns", "dev-methodology")
    foreach ($skill in $skills) {
        $skillPath = "$DEVCORE_ROOT\Skills\$skill\SKILL.md"
        $skillOk = Test-Path $skillPath
        Test-Item "Skill: $skill" $skillOk $skillPath
    }

    $removedSkill = "grap" + "hify"
    $removedSkillPath = "$DEVCORE_ROOT\Skills\$removedSkill"
    Test-Item "Removed optional graph tool absent" (-not (Test-Path $removedSkillPath)) $removedSkillPath

    # skills_registry.json
    $regPath = "$DEVCORE_ROOT\Skills\skills_registry.json"
    $regOk = Test-Path $regPath
    Test-Item "skills_registry.json" $regOk
    if ($regOk) {
        try {
            $reg = Get-Content $regPath -Raw | ConvertFrom-Json
            Write-Host "         Skills count: $($reg.skills.Count)" -ForegroundColor DarkGray
        } catch {}
    }
}

# ========== TESTS SCRIPTS ==========

function Test-Scripts {
    Test-Section "DEV_CORE SCRIPTS"

    $scripts = @(
        "dc.ps1",
        "launch.ps1",
        "endday.ps1",
        "task_add.ps1",
        "task_done.ps1",
        "task_next.ps1",
        "task_scan.ps1",
        "task_sync.ps1",
        "task_status.ps1",
        "diagnose.ps1",
        "setup.ps1"
    )

    foreach ($script in $scripts) {
        $scriptPath = "$DEVCORE_ROOT\Scripts\$script"
        $scriptOk = Test-Path $scriptPath
        Test-Item "Scripts/$script" $scriptOk
    }

    # Auto scripts
    $autoScripts = @(
        "task_git_scanner.ps1",
        "task_spec_parser.ps1",
        "task_prompt_analyzer.ps1",
        "qdrant_sync.ps1",
        "obsidian_sync.ps1",
        "lesson_extractor.ps1",
        "memory_rotate.ps1",
        "weekly_maintenance.ps1"
    )

    foreach ($script in $autoScripts) {
        $scriptPath = "$DEVCORE_ROOT\Scripts\Auto\$script"
        $scriptOk = Test-Path $scriptPath
        Test-Item "Auto/$script" $scriptOk
    }
}

# ========== MAIN ==========

Write-Host ""
Write-Host "  $($PLATFORM.title) + HERMES INTEGRATION TEST" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host "  Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

if ($All -or (-not ($Hermes -or $MCP -or $Cron -or $Paths))) {
    Test-Hermes
    Test-MCP
    Test-Cron
    Test-Paths
    Test-Services
    Test-Skills
    Test-Scripts
} else {
    if ($Hermes) { Test-Hermes }
    if ($MCP) { Test-MCP }
    if ($Cron) { Test-Cron }
    if ($Paths) { Test-Paths }
    if ($Services) { Test-Services }
    if ($Skills) { Test-Skills }
    if ($Scripts) { Test-Scripts }
}

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Tests termines" -ForegroundColor Green
Write-Host ""

Write-Host "  PASS: $passed  |  FAIL: $failed" -ForegroundColor White
Write-Host ""

if ($failed -gt 0) { exit 1 }
exit 0
