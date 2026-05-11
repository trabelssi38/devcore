# diagnose.ps1 -- DEV_CORE v6 -- ASCII safe
$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\DEV_CORE_DATA" }
$CLAUDE_DIR    = "$env:USERPROFILE\.claude"

Write-Host ""
Write-Host "  DEV_CORE v6 -- Diagnostic autonomie" -ForegroundColor Cyan
Write-Host "  =====================================" -ForegroundColor DarkGray
Write-Host ""

$ok = 0; $warn = 0; $fail = 0

function Check {
    param($label, $status, $fix="")
    if ($status -eq "OK") {
        Write-Host "  [OK]   $label" -ForegroundColor Green; $script:ok++
    } elseif ($status -eq "WARN") {
        Write-Host "  [WARN] $label" -ForegroundColor Yellow
        if ($fix) { Write-Host "         Fix : $fix" -ForegroundColor DarkGray }
        $script:warn++
    } else {
        Write-Host "  [FAIL] $label" -ForegroundColor Red
        if ($fix) { Write-Host "         Fix : $fix" -ForegroundColor DarkGray }
        $script:fail++
    }
}

# 1. CLAUDE.md global -- nouveau check v6 (cherche "devcore-automation" et "session_context")
$claudeMd = "$CLAUDE_DIR\CLAUDE.md"
if (Test-Path $claudeMd) {
    $content = Get-Content $claudeMd -Raw
    if ($content -match "devcore-automation" -and $content -match "session_context") {
        Check "~\.claude\CLAUDE.md OK -- directives DEV_CORE v6 presentes" "OK"
    } elseif ($content -match "DEV_CORE") {
        Check "~\.claude\CLAUDE.md version incomplete (relancer adapt_client)" "WARN" "powershell -File C:\DEV_CORE\Scripts\adapt_client.ps1 -Client claude"
    } else {
        Check "~\.claude\CLAUDE.md sans directives DEV_CORE" "FAIL" "powershell -File C:\DEV_CORE\Scripts\adapt_client.ps1 -Client claude"
    }
} else {
    Check "~\.claude\CLAUDE.md absent" "FAIL" "powershell -File C:\DEV_CORE\Scripts\adapt_client.ps1 -Client claude"
}

# 2. settings.json -- hook UserPromptSubmit
$settingsFile = "$CLAUDE_DIR\settings.json"
if (Test-Path $settingsFile) {
    try {
        $s = Get-Content $settingsFile -Raw | ConvertFrom-Json
        if ($s.hooks -and $s.hooks.UserPromptSubmit) {
            Check "settings.json -- hook UserPromptSubmit present" "OK"
        } else {
            Check "settings.json sans hook UserPromptSubmit" "FAIL" "powershell -File C:\DEV_CORE\Scripts\install_hooks.ps1"
        }
    } catch {
        Check "settings.json JSON invalide" "FAIL" "powershell -File C:\DEV_CORE\Scripts\install_hooks.ps1"
    }
} else {
    Check "settings.json absent" "FAIL" "powershell -File C:\DEV_CORE\Scripts\install_hooks.ps1"
}

# 3. session_start.ps1
if (Test-Path "$DEV_CORE\Scripts\session_start.ps1") {
    Check "Scripts\session_start.ps1 present" "OK"
} else {
    Check "Scripts\session_start.ps1 absent" "FAIL" "Copier session_start.ps1 dans C:\DEV_CORE\Scripts\"
}

# 4. Skill devcore-automation lie
if (Test-Path "$CLAUDE_DIR\skills\devcore-automation") {
    Check "Skill devcore-automation lie dans ~/.claude/skills/" "OK"
} else {
    Check "Skill devcore-automation absent" "FAIL" "powershell -File C:\DEV_CORE\Scripts\adapt_client.ps1 -Client claude"
}

# 5. CLAUDE.md projet dans CWD
if (Test-Path "$(Get-Location)\CLAUDE.md") {
    Check "CLAUDE.md projet present dans le CWD" "OK"
} else {
    Check "CLAUDE.md projet absent dans $(Get-Location)" "WARN" "dc new project [nom]"
}

# 6. Mission active
$mFile = "$DEV_CORE_DATA\Memory\missions.json"
if (Test-Path $mFile) {
    try {
        $board  = Get-Content $mFile -Raw | ConvertFrom-Json
        $active = $board.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1
        if ($active) { Check "Mission active : $($active.id)" "OK" }
        else { Check "Aucune mission active" "WARN" "dc next mission" }
    } catch { Check "missions.json illisible" "WARN" "Verifier $mFile" }
} else {
    Check "missions.json absent" "WARN" "dc new project [nom]"
}

# 7. devcore-automation SKILL.md
if (Test-Path "$DEV_CORE\Skills\devcore-automation\SKILL.md") {
    Check "Skills\devcore-automation\SKILL.md present" "OK"
} else {
    Check "Skills\devcore-automation\SKILL.md absent" "FAIL" "Copier le skill"
}

# 8. Env vars
if ($env:DEVCORE_PLATFORM_ROOT) { Check "DEVCORE_PLATFORM_ROOT defini" "OK" }
else { Check "DEVCORE_PLATFORM_ROOT non defini" "WARN" "Relancer setup.ps1" }

# 9. Logs dir
if (Test-Path "$DEV_CORE_DATA\Logs\scripts") { Check "Logs\scripts accessible" "OK" }
else { Check "Logs\scripts absent" "WARN" "Relancer setup.ps1" }

Write-Host ""
Write-Host "  =====================================" -ForegroundColor DarkGray
Write-Host "  OK: $ok  |  WARN: $warn  |  FAIL: $fail" -ForegroundColor White
Write-Host ""
if ($fail -gt 0)      { Write-Host "  FAIL a corriger -- suivre les Fix ci-dessus" -ForegroundColor Red }
elseif ($warn -gt 0)  { Write-Host "  Quasi pret -- WARN non bloquants" -ForegroundColor Yellow }
else                  { Write-Host "  Tout est OK -- fermer et rouvrir Claude Code Desktop" -ForegroundColor Green }
Write-Host ""
