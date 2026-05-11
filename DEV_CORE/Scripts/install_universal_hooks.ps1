# install_universal_hooks.ps1 -- DEV_CORE v6
# Installe les hooks pour tous les clients IA et tous les IDE (via PowerShell Profile)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$sessionStartScript = "$DEV_CORE\Scripts\session_start.ps1"
$postToolScript = "$DEV_CORE\Scripts\post_tool_hook.ps1"

Write-Host "  DEV_CORE v6 -- Integration Universelle" -ForegroundColor Cyan
Write-Host "  ======================================" -ForegroundColor DarkGray

# 1. Integration Clients IA (Claude, Codex, Gemini, Qwen, Antigravity)
$clients = @(".claude", ".codex", ".gemini", ".qwen", ".antigravity")
foreach ($client in $clients) {
    $dir = "$env:USERPROFILE\$client"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    $settingsFile = "$dir\settings.json"
    $settings = if (Test-Path $settingsFile) {
        try { Get-Content $settingsFile -Raw | ConvertFrom-Json } catch { [PSCustomObject]@{} }
    } else { [PSCustomObject]@{} }
    
    $hooks = [PSCustomObject]@{
        UserPromptSubmit = @(
            [PSCustomObject]@{
                matcher = ""
                hooks   = @( [PSCustomObject]@{ type = "command"; command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$sessionStartScript`"" } )
            }
        )
        PostToolUse = @(
            [PSCustomObject]@{
                matcher = "Bash"
                hooks   = @( [PSCustomObject]@{ type = "command"; command = "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$postToolScript`"" } )
            }
        )
    }
    
    $settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooks -Force
    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile -Encoding UTF8
    Write-Host "  [OK] Hooks installes pour client : $client" -ForegroundColor Green
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
