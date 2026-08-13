# install_hooks.ps1 -- DEV_CORE
# Installe les hooks Claude Code dans settings.json
# C'est CE fichier qui rend les actions autonomes -- CLAUDE.md seul ne suffit pas
# Usage : powershell -ExecutionPolicy Bypass -File C:\devcore\DEV_CORE\Scripts\install_hooks.ps1

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
. "$DEV_CORE\Scripts\platform_version.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$SETTINGS_PATH = "$CLAUDE_DIR\settings.json"

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Installation hooks Claude Code" -ForegroundColor Cyan
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

$PYTHON_EXE = Get-DevCorePython
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
