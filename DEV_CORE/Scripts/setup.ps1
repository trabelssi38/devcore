# setup.ps1 -- DEV_CORE v6 -- Installation initiale (lancer UNE fois en admin)
# Usage : powershell -ExecutionPolicy Bypass -File C:\devcore\DEV_CORE\Scripts\setup.ps1

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }

Write-Host ""
Write-Host "  DEV_CORE v6 -- Setup initial" -ForegroundColor Cyan
Write-Host "  -------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# 1. Alias dc dans le profil PowerShell
Write-Host "  1/5 Alias dc..." -ForegroundColor Cyan
$aliasLine = "Set-Alias dc '$DEV_CORE\Scripts\dc.ps1'"
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}
$profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($profileContent -notmatch "dc\.ps1") {
    Add-Content $PROFILE "`n$aliasLine"
    Write-Host "  [OK] Alias dc ajoute dans $PROFILE" -ForegroundColor Green
} else {
    Write-Host "  Alias dc deja present" -ForegroundColor Gray
}

# 2. Variables d'environnement utilisateur persistantes
Write-Host "  2/5 Variables d environnement..." -ForegroundColor Cyan
[System.Environment]::SetEnvironmentVariable("DEVCORE_PLATFORM_ROOT", $DEV_CORE,      "User")
[System.Environment]::SetEnvironmentVariable("DEVCORE_DATA_ROOT",     $DEV_CORE_DATA, "User")
$env:DEVCORE_PLATFORM_ROOT = $DEV_CORE
$env:DEVCORE_DATA_ROOT     = $DEV_CORE_DATA
Write-Host "  [OK] DEVCORE_PLATFORM_ROOT = $DEV_CORE" -ForegroundColor Green
Write-Host "  [OK] DEVCORE_DATA_ROOT     = $DEV_CORE_DATA" -ForegroundColor Green

# 3. Tache planifiee weekly_maintenance (dimanche 23h)
Write-Host "  3/5 Tache planifiee weekly..." -ForegroundColor Cyan
try {
    $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
               -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$DEV_CORE\Scripts\Auto\weekly_maintenance.ps1`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "23:00"
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
    Register-ScheduledTask -TaskName "DEV_CORE Weekly Maintenance" `
        -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "  [OK] Tache planifiee : dimanche 23h" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Tache planifiee echouee (relancer en admin) : $_" -ForegroundColor Yellow
}

# 4. Python packages
Write-Host "  4/5 Python packages..." -ForegroundColor Cyan
$packages = @("qdrant-client", "jsonschema")
foreach ($pkg in $packages) {
    try {
        pip install $pkg --quiet 2>$null
        Write-Host "  [OK] $pkg" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] pip non disponible pour $pkg" -ForegroundColor Yellow
    }
}

# 5. Dossiers DATA manquants
Write-Host "  5/5 Dossiers DEV_CORE_DATA..." -ForegroundColor Cyan
$dirs = @(
    "$DEV_CORE_DATA\Memory",
    "$DEV_CORE_DATA\Vault\Daily Notes",
    "$DEV_CORE_DATA\Vault\Decisions",
    "$DEV_CORE_DATA\Vault\Lessons\bug",
    "$DEV_CORE_DATA\Vault\Lessons\architecture",
    "$DEV_CORE_DATA\Vault\Lessons\prompt",
    "$DEV_CORE_DATA\Vault\Lessons\workflow",
    "$DEV_CORE_DATA\Vault\Architecture",
    "$DEV_CORE_DATA\Vault\00_Global",
    "$DEV_CORE_DATA\Sessions",
    "$DEV_CORE_DATA\Logs\scripts",
    "$DEV_CORE_DATA\Logs\router",
    "$DEV_CORE_DATA\Logs\token_reports",
    "$DEV_CORE_DATA\Backups\auto",
    "$DEV_CORE_DATA\qdrant_storage",
    "$DEV_CORE_DATA\Vault\docs\graphify"
)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "  [CREATE] $d" -ForegroundColor DarkGray
    }
}
Write-Host "  [OK] Dossiers verifies" -ForegroundColor Green

# 6. Hooks clients IA (Claude, Codex, Gemini, Qwen, Antigravity)
Write-Host "  6/6 Hooks clients IA..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\install_universal_hooks.ps1"

# Recharger le profil
try { . $PROFILE } catch {}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "  DEV_CORE v6.1 -- Setup termine             " -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Prochaine etape : dc launch" -ForegroundColor Cyan
Write-Host "  (ouvrir un nouveau terminal si dc introuvable)" -ForegroundColor DarkGray
Write-Host ""