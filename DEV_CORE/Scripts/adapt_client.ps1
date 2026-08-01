# adapt_client.ps1 -- DEV_CORE client adapter
# Expose DEV_CORE au client actif : liens skills + injection boot
# Usage : adapt_client.ps1 -Client claude|codex|gemini|antigravity|qwen|auto

param(
    [ValidateSet("claude","codex","gemini","antigravity","qwen","auto")]
    [string]$Client = "auto",
    [switch]$Verbose,
    [switch]$DryRun
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
. "$PSScriptRoot\platform_version.ps1"
. "$PSScriptRoot\routing_profile.ps1"
$PLATFORM = Get-DevCorePlatformInfo
$SKILLS_DIR    = "$DEV_CORE\Skills"
$CONFIG_DIR    = "$DEV_CORE\Config"
$RUNTIME_DIR   = "$DEV_CORE_DATA\Runtime"
$ACTIVE_FILE   = "$RUNTIME_DIR\active_client.txt"
$LEGACY_ACTIVE_FILE = "$CONFIG_DIR\active_client.txt"

# -- Source boot par client
# CLAUDE.md  -> Claude Code
# AGENTS.md  -> Codex Desktop
# GEMINI.md  -> Gemini CLI / Antigravity
# BOOT.md    -> Qwen
$CLIENT_BOOT_SRC = @{
    claude      = "$CONFIG_DIR\CLAUDE.md"
    codex       = "$CONFIG_DIR\AGENTS.md"
    gemini      = "$CONFIG_DIR\CLAUDE.md"   # meme directives, format universel
    antigravity = "$CONFIG_DIR\CLAUDE.md"
    qwen        = "$CONFIG_DIR\CLAUDE.md"
}

# -- Destination boot par client (fichier lu par chaque client au demarrage)
$CLIENT_BOOT_DST = @{
    claude      = "$env:USERPROFILE\.claude\CLAUDE.md"
    codex       = "$env:USERPROFILE\.codex\AGENTS.md"
    gemini      = "$env:USERPROFILE\.gemini\GEMINI.md"
    antigravity = "$env:USERPROFILE\.gemini\antigravity\GEMINI.md"
    qwen        = "$env:USERPROFILE\.qwen\BOOT.md"
}

# -- Dossier skills par client
$CLIENT_SKILLS = @{
    claude      = "$env:USERPROFILE\.claude\skills"
    codex       = "$env:USERPROFILE\.codex\skills"
    gemini      = "$env:USERPROFILE\.gemini\skills"
    antigravity = "$env:USERPROFILE\.gemini\config\skills"
    qwen        = "$env:USERPROFILE\.qwen\skills"
}

# -- Detection auto du client actif
function Detect-Client {
    foreach ($c in @("antigravity","claude","codex","gemini","qwen")) {
        if (Get-Process -Name $c -ErrorAction SilentlyContinue) { return $c }
    }
    if (Test-Path $ACTIVE_FILE) { return (Get-Content $ACTIVE_FILE -Raw).Trim() }
    if (Test-Path $LEGACY_ACTIVE_FILE) { return (Get-Content $LEGACY_ACTIVE_FILE -Raw).Trim() }
    return "claude"
}

# -- Resolution client
$resolved = if ($Client -eq "auto") { Detect-Client } else { $Client }
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $RUNTIME_DIR -Force | Out-Null
    $resolved | Set-Content $ACTIVE_FILE -Encoding UTF8
}

Write-Host "  [adapt_client] Client : $resolved" -ForegroundColor Cyan

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. LIENS SYMBOLIQUES SKILLS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$skillsTarget = $CLIENT_SKILLS[$resolved]
if ($skillsTarget) {
    if (-not (Test-Path $skillsTarget) -and -not $DryRun) {
        New-Item -ItemType Directory -Path $skillsTarget -Force | Out-Null
    }
    $skills = @("devcore-automation","obsidian","qdrant","dev-methodology","ui-ux","fabric-patterns","android_release","python_api","web_ui")
    foreach ($skill in $skills) {
        $src  = "$SKILLS_DIR\$skill"
        $link = "$skillsTarget\$skill"
        if ((Test-Path $src) -and -not (Test-Path $link) -and -not $DryRun) {
            try {
                New-Item -ItemType Junction -Path $link -Target $src -ErrorAction Stop | Out-Null
                if ($Verbose) { Write-Host "    [LINK] $skill" -ForegroundColor Green }
            } catch {
                if ($Verbose) { Write-Host "    [SKIP] $skill (deja lie ou erreur)" -ForegroundColor DarkGray }
            }
        }
    }
    Write-Host "  [adapt_client] Skills lies dans $skillsTarget" -ForegroundColor Green

    if ($resolved -eq "antigravity" -and -not $DryRun) {
        $manifestPath = "$env:USERPROFILE\.gemini\config\skills\.antigravity-install-manifest.json"
        if (Test-Path $manifestPath) {
            try {
                $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
                $modified = $false
                foreach ($skill in $skills) {
                    if ($manifest.entries -notcontains $skill) {
                        $manifest.entries += $skill
                        $modified = $true
                    }
                }
                if ($modified) {
                    $manifest | ConvertTo-Json -Depth 100 | Set-Content $manifestPath -Encoding UTF8
                    Write-Host "  [adapt_client] Skills enregistres dans le manifeste Antigravity" -ForegroundColor Green
                }
            } catch {
                Write-Host "  [adapt_client] WARN : Impossible de mettre a jour le manifeste Antigravity : $_" -ForegroundColor Yellow
            }
        }
    }
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. INJECTION DU FICHIER BOOT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
$bootSrc = $CLIENT_BOOT_SRC[$resolved]
$bootDst = $CLIENT_BOOT_DST[$resolved]

if (-not $bootSrc -or -not (Test-Path $bootSrc)) {
    Write-Host "  [adapt_client] WARN : source boot introuvable $bootSrc" -ForegroundColor Yellow
    exit 0
}

# Creer le dossier destination si necessaire
$dstDir = Split-Path $bootDst -Parent
if (-not (Test-Path $dstDir) -and -not $DryRun) {
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
}

# Lire le fichier boot source
$bootContent = Get-Content $bootSrc -Raw -ErrorAction SilentlyContinue

# Injecter la task courante en haut si disponible
$missionBlock = ""
$tasksFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (Test-Path $tasksFile) {
    try {
        $board   = Get-Content $tasksFile -Raw | ConvertFrom-Json
        $current = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
        if ($current) {
            $routingProfile = Resolve-DevCoreRoutingProfile -Mode $current.mode
            $missionBlock = @"
## TASK ACTIVE INJECTEE -- $($current.id)
Titre  : $($current.title)
Mode   : $($current.mode)
Profil : $($routingProfile.profile)
Budget : $($routingProfile.budget)
Mode resolu : $($routingProfile.mode)
Modele DEV_CORE : $($routingProfile.model)
Modele Gemini   : $($routingProfile.gemini_model)
Codex : $($routingProfile.codex_behavior)
Steps  : $($current.steps_done)/$($current.steps_total)
Tag git: [$($current.id)]
Action : dc task done quand steps_done = steps_total

"@
        }
    } catch { }
}

# Header + mission + boot content
$header = "<!-- $($PLATFORM.title) -- genere par adapt_client.ps1 le $(Get-Date -f 'yyyy-MM-dd HH:mm') -->`n"
$final  = $header + $missionBlock + $bootContent

if (-not $DryRun) {
    $final | Set-Content $bootDst -Encoding UTF8
}

Write-Host "  [adapt_client] Boot injecte : $bootDst" -ForegroundColor Green
Write-Host "  [adapt_client] Source       : $bootSrc" -ForegroundColor DarkGray
