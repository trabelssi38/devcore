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

Write-Host ""
Write-Host "  $($PLATFORM.title) -- Installation hooks Claude Code" -ForegroundColor Cyan
Write-Host "  ==============================================" -ForegroundColor DarkGray
Write-Host ""

# Creer le dossier si absent
New-Item -ItemType Directory -Path $CLAUDE_DIR -Force | Out-Null

# Lire settings.json existant ou creer vide
$settings = if (Test-Path $SETTINGS) {
    try { Get-Content $SETTINGS -Raw | ConvertFrom-Json }
    catch { [PSCustomObject]@{} }
} else {
    [PSCustomObject]@{}
}

# Script de session start -- declenche au premier message de chaque session
$sessionStartScript = "$DEV_CORE\Scripts\session_start.ps1"

# Construire les hooks
$hooks = [PSCustomObject]@{
    UserPromptSubmit = @(
        [PSCustomObject]@{
            matcher = ""
            hooks   = @(
                [PSCustomObject]@{
                    type    = "command"
                    command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$sessionStartScript`""
                }
            )
        }
    )
    PostToolUse = @(
        [PSCustomObject]@{
            matcher = "Bash"
            hooks   = @(
                [PSCustomObject]@{
                    type    = "command"
                    command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$DEV_CORE\Scripts\post_tool_hook.ps1`""
                }
            )
        }
    )
}

# Injecter dans settings
$settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooks -Force

# Sauvegarder
$settings | ConvertTo-Json -Depth 10 | Set-Content $SETTINGS -Encoding UTF8

Write-Host "  [OK] settings.json mis a jour : $SETTINGS" -ForegroundColor Green
Write-Host "  [OK] Hook UserPromptSubmit --> session_start.ps1" -ForegroundColor Green
Write-Host "  [OK] Hook PostToolUse(Bash) --> post_tool_hook.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "  IMPORTANT : Fermer et rouvrir Claude Code Desktop" -ForegroundColor Yellow
Write-Host "  pour que les hooks soient pris en compte." -ForegroundColor Yellow
Write-Host ""
