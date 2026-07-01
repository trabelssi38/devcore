# install_universal_hooks.ps1 -- DEV_CORE v9.0
# Installe les hooks pour tous les clients IA et tous les IDE (via PowerShell Profile)
# Chaque client IA a ses propres noms d'evenements -- ce script les gere correctement.

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$sessionStartScript = "$DEV_CORE\Scripts\session_start.ps1"
$postToolScript     = "$DEV_CORE\Scripts\post_tool_hook.ps1"
$sessionEndScript   = "$DEV_CORE\Scripts\session_end.ps1"

Write-Host "  DEV_CORE v9.0 -- Integration Universelle" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray

# Mapping des noms d'evenements par client
# Claude Code / Codex / Qwen / Antigravity : noms Claude
# Gemini CLI : noms propres (BeforeAgent, AfterTool, SessionEnd)
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

    # Choisir le bon schema d'evenements pour ce client
    $clientKey = $client.TrimStart(".")
    $schema    = if ($hookSchemas.ContainsKey($clientKey)) { $hookSchemas[$clientKey] } else { $hookSchemas["claude"] }

    # Construire les hooks avec les bons noms d'evenements
    $hookStart = [PSCustomObject]@{
        matcher = ""
        hooks   = @( [PSCustomObject]@{ type = "command"; command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$sessionStartScript`"" } )
    }
    $hookTool = [PSCustomObject]@{
        matcher = $schema.toolMatcher
        hooks   = @( [PSCustomObject]@{ type = "command"; command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$postToolScript`"" } )
    }
    $hookEnd = [PSCustomObject]@{
        matcher = ""
        hooks   = @( [PSCustomObject]@{ type = "command"; command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$sessionEndScript`"" } )
    }

    $hooks = [PSCustomObject]@{}
    $hooks | Add-Member -NotePropertyName $schema.start -NotePropertyValue @($hookStart) -Force
    $hooks | Add-Member -NotePropertyName $schema.tool  -NotePropertyValue @($hookTool)  -Force
    $hooks | Add-Member -NotePropertyName $schema.end   -NotePropertyValue @($hookEnd)   -Force

    $settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooks -Force
    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile -Encoding UTF8
    Write-Host "  [OK] $client  ($($schema.start) / $($schema.tool) / $($schema.end))" -ForegroundColor Green
}


# 2. Integration IDE Universelle (via PowerShell Profile)
$profilePath = $PROFILE
if (-not (Test-Path (Split-Path $profilePath -Parent))) {
    New-Item -ItemType Directory -Path (Split-Path $profilePath -Parent) -Force | Out-Null
}
if (-not (Test-Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}

$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
$hookBlock = @"

# --- DEV_CORE AUTO-INIT HOOK ---
# S'execute au demarrage d'un terminal (VS Code, Cursor, etc.)
if (Test-Path "`.git") {
    `$devcore_session = "$sessionStartScript"
    if (Test-Path `$devcore_session) {
        powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `$devcore_session
    }
}
# -------------------------------
"@

if ($profileContent -notmatch "DEV_CORE AUTO-INIT HOOK") {
    Add-Content -Path $profilePath -Value $hookBlock -Encoding UTF8
    Write-Host "  [OK] Hook d'IDE installe dans le profil PowerShell ($profilePath)" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] Hook d'IDE deja present dans le profil PowerShell" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  L'integration est terminee ! N'importe quel projet ouvert dans un IDE" -ForegroundColor Yellow
Write-Host "  ou un client IA sera automatiquement initialise par DEV_CORE." -ForegroundColor Yellow
