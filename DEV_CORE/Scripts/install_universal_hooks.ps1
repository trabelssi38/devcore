# install_universal_hooks.ps1 -- DEV_CORE v10
# Installe les hooks Python natifs pour tous les clients IA (Claude, Gemini, Codex, Antigravity)

$defaultDevCore = Split-Path -Parent $PSScriptRoot
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
$PYTHON_EXE = "python"
$CLI_SCRIPT = "$DEV_CORE\devcore_engine\cli.py"
$POST_TOOL  = "$DEV_CORE\devcore_engine\hooks\post_tool.py"

. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo

Write-Host "  $($PLATFORM.title) -- Integration Hooks Universelle Python" -ForegroundColor Cyan
Write-Host "  ========================================================" -ForegroundColor DarkGray

# Mapping des noms d'evenements par client
$hookSchemas = @{
    claude      = @{ start = "UserPromptSubmit"; tool = "PostToolUse"; toolMatcher = "Bash"; end = "Stop" }
    codex       = @{ start = "UserPromptSubmit"; tool = "PostToolUse"; toolMatcher = "Bash"; end = "Stop" }
    gemini      = @{ start = "BeforeAgent";      tool = "AfterTool";  toolMatcher = "";     end = "SessionEnd" }
    qwen        = @{ start = "UserPromptSubmit"; tool = "PostToolUse"; toolMatcher = "Bash"; end = "Stop" }
    antigravity = @{ start = "UserPromptSubmit"; tool = "PostToolUse"; toolMatcher = "Bash"; end = "Stop" }
}

$clients = @(".claude", ".codex", ".gemini", ".qwen", ".antigravity")
foreach ($client in $clients) {
    if ($client -eq ".antigravity") {
        $dir = "$env:USERPROFILE\.gemini\antigravity"
    } else {
        $dir = "$env:USERPROFILE\$client"
    }
    
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $settingsFile = "$dir\settings.json"
    $settings = if (Test-Path $settingsFile) {
        try { Get-Content $settingsFile -Raw | ConvertFrom-Json } catch { [PSCustomObject]@{} }
    } else { [PSCustomObject]@{} }

    $clientKey = $client.TrimStart(".")
    $schema    = if ($hookSchemas.ContainsKey($clientKey)) { $hookSchemas[$clientKey] } else { $hookSchemas["claude"] }

    # Commandes Python directes
    $cmdStart = "`"$PYTHON_EXE`" `"$CLI_SCRIPT`" session start"
    $cmdTool  = "`"$PYTHON_EXE`" `"$POST_TOOL`""
    $cmdEnd   = "`"$PYTHON_EXE`" `"$CLI_SCRIPT`" session end"

    $hookStart = [PSCustomObject]@{
        matcher = ""
        hooks   = @( [PSCustomObject]@{ type = "command"; command = $cmdStart } )
    }
    $hookTool = [PSCustomObject]@{
        matcher = $schema.toolMatcher
        hooks   = @( [PSCustomObject]@{ type = "command"; command = $cmdTool } )
    }
    $hookEnd = [PSCustomObject]@{
        matcher = ""
        hooks   = @( [PSCustomObject]@{ type = "command"; command = $cmdEnd } )
    }

    $hooks = [PSCustomObject]@{}
    $hooks | Add-Member -NotePropertyName $schema.start -NotePropertyValue @($hookStart) -Force
    $hooks | Add-Member -NotePropertyName $schema.tool  -NotePropertyValue @($hookTool)  -Force
    $hooks | Add-Member -NotePropertyName $schema.end   -NotePropertyValue @($hookEnd)   -Force

    $settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooks -Force
    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile -Encoding UTF8
    Write-Host "  [OK] $client  ($($schema.start) / $($schema.tool) / $($schema.end)) -> Python Native" -ForegroundColor Green
}

Write-Host ""
Write-Host "  [OK] Universal Python Hooks Installed!" -ForegroundColor Green
