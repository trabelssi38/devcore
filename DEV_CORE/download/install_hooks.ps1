# install_hooks.ps1 -- DEV_CORE v6
# Installe les hooks Claude Code dans settings.json
# C'est CE fichier qui rend les actions autonomes -- CLAUDE.md seul ne suffit pas
# Usage : powershell -ExecutionPolicy Bypass -File C:\DEV_CORE\Scripts\install_hooks.ps1

$DEV_CORE   = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$SETTINGS_PATH = "$CLAUDE_DIR\settings.json"

Write-Host ""
Write-Host "  DEV_CORE v6 -- Installation hooks Claude Code" -ForegroundColor Cyan
Write-Host "  ==============================================" -ForegroundColor DarkGray
Write-Host ""

# Creer le dossier si absent
New-Item -ItemType Directory -Path $CLAUDE_DIR -Force | Out-Null

# Lire settings.json existant ou creer vide
$settings = if (Test-Path $SETTINGS_PATH) {
    try { Get-Content $SETTINGS_PATH -Raw | ConvertFrom-Json }
    catch { [PSCustomObject]@{} }
} else {
    [PSCustomObject]@{}
}

$PYTHON_EXE = "python"
$CLI_SCRIPT = "$DEV_CORE\devcore_engine\cli.py"
$POST_TOOL  = "$DEV_CORE\devcore_engine\hooks\post_tool.py"

# Commandes Python directes
$cmdStart = "`"$PYTHON_EXE`" `"$CLI_SCRIPT`" session start"
$cmdTool  = "`"$PYTHON_EXE`" `"$POST_TOOL`""
$cmdEnd   = "`"$PYTHON_EXE`" `"$CLI_SCRIPT`" session end"

# Construire les hooks
$hooks = [PSCustomObject]@{
    UserPromptSubmit = @(
        [PSCustomObject]@{
            matcher = ""
            hooks   = @( [PSCustomObject]@{ type = "command"; command = $cmdStart } )
        }
    )
    PostToolUse = @(
        [PSCustomObject]@{
            matcher = "Bash"
            hooks   = @( [PSCustomObject]@{ type = "command"; command = $cmdTool } )
        }
    )
    Stop = @(
        [PSCustomObject]@{
            matcher = ""
            hooks   = @( [PSCustomObject]@{ type = "command"; command = $cmdEnd } )
        }
    )
}

# Injecter dans settings
$settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooks -Force

# Sauvegarder
$settings | ConvertTo-Json -Depth 10 | Set-Content $SETTINGS_PATH -Encoding UTF8

Write-Host "  [OK] settings.json mis a jour : $SETTINGS_PATH" -ForegroundColor Green
Write-Host "  [OK] Hook UserPromptSubmit --> Python Native (session start)" -ForegroundColor Green
Write-Host "  [OK] Hook PostToolUse(Bash) --> Python Native (post_tool)" -ForegroundColor Green
Write-Host "  [OK] Hook Stop --> Python Native (session end)" -ForegroundColor Green
Write-Host ""
Write-Host "  IMPORTANT : Fermer et rouvrir Claude Code Desktop" -ForegroundColor Yellow
Write-Host "  pour que les hooks soient pris en compte." -ForegroundColor Yellow
Write-Host ""
