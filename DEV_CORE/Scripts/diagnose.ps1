# diagnose.ps1 -- DEV_CORE v9.0 -- Auto-reparation
# Usage : dc check        (diagnostic seul)
#         dc check --fix   (diagnostic + reparation automatique)
param([switch]$Fix)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { "C:\devcore\DEV_CORE_DATA" }
$CLAUDE_DIR    = "$env:USERPROFILE\.claude"
$GEMINI_DIR    = "$env:USERPROFILE\.gemini"

Write-Host ""
Write-Host "  DEV_CORE v9.0 -- Diagnostic autonomie" -ForegroundColor Cyan
if ($Fix) { Write-Host "  MODE AUTO-FIX ACTIVE" -ForegroundColor Yellow }
Write-Host "  =======================================" -ForegroundColor DarkGray
Write-Host ""

$ok = 0; $warn = 0; $fail = 0; $fixed = 0

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

function AutoFix {
    param($label, $action)
    if ($script:Fix) {
        Write-Host "  [FIX]  $label" -ForegroundColor Magenta
        try { & $action; $script:fixed++ }
        catch { Write-Host "  [ERR]  Fix echoue : $_" -ForegroundColor Red }
    }
}

# 1. Variables d'environnement
if ($env:DEVCORE_PLATFORM_ROOT) { Check "DEVCORE_PLATFORM_ROOT defini" "OK" }
else {
    Check "DEVCORE_PLATFORM_ROOT non defini" "WARN" "Relancer setup.ps1"
    AutoFix "Set DEVCORE_PLATFORM_ROOT" {
        [System.Environment]::SetEnvironmentVariable("DEVCORE_PLATFORM_ROOT", $DEV_CORE, "User")
        $env:DEVCORE_PLATFORM_ROOT = $DEV_CORE
    }
}
if ($env:DEVCORE_DATA_ROOT) { Check "DEVCORE_DATA_ROOT defini" "OK" }
else {
    Check "DEVCORE_DATA_ROOT non defini" "WARN" "Relancer setup.ps1"
    AutoFix "Set DEVCORE_DATA_ROOT" {
        [System.Environment]::SetEnvironmentVariable("DEVCORE_DATA_ROOT", $DEV_CORE_DATA, "User")
        $env:DEVCORE_DATA_ROOT = $DEV_CORE_DATA
    }
}

# 2. Dossiers critiques
$critDirs = @(
    "$DEV_CORE_DATA\Memory",
    "$DEV_CORE_DATA\Logs\scripts",
    "$DEV_CORE_DATA\Backups\auto",
    "$DEV_CORE_DATA\Sessions"
)
foreach ($d in $critDirs) {
    if (Test-Path $d) { Check "Dossier $(Split-Path $d -Leaf) present" "OK" }
    else {
        Check "Dossier $d absent" "WARN" "mkdir $d"
        AutoFix "Creer $d" { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    }
}

# 3. Hooks clients IA
$hookChecks = @{
    ".claude" = @{ file = "$CLAUDE_DIR\settings.json"; event = "UserPromptSubmit" }
    ".gemini" = @{ file = "$GEMINI_DIR\settings.json"; event = "BeforeAgent" }
}
foreach ($client in $hookChecks.Keys) {
    $hc = $hookChecks[$client]
    if (Test-Path $hc.file) {
        try {
            $s = Get-Content $hc.file -Raw | ConvertFrom-Json
            if ($s.hooks -and ($s.hooks.PSObject.Properties.Name -contains $hc.event)) {
                Check "$client hooks ($($hc.event)) OK" "OK"
            } else {
                Check "$client hooks manquants" "FAIL" "install_universal_hooks.ps1"
                AutoFix "Reinstaller hooks $client" { & "$DEV_CORE\Scripts\install_universal_hooks.ps1" }
            }
        } catch {
            Check "$client settings.json invalide" "FAIL" "install_universal_hooks.ps1"
            AutoFix "Reinstaller hooks $client" { & "$DEV_CORE\Scripts\install_universal_hooks.ps1" }
        }
    } else {
        Check "$client settings.json absent" "FAIL" "install_universal_hooks.ps1"
        AutoFix "Creer hooks $client" { & "$DEV_CORE\Scripts\install_universal_hooks.ps1" }
    }
}

# 4. Scripts critiques
$scripts = @("session_start.ps1","session_end.ps1","post_tool_hook.ps1","task_next.ps1","task_done.ps1","task_step_done.ps1","launch.ps1")
foreach ($s in $scripts) {
    if (Test-Path "$DEV_CORE\Scripts\$s") { Check "Script $s present" "OK" }
    else { Check "Script $s MANQUANT" "FAIL" "Reinstaller DEV_CORE" }
}

# 4.5 Secrets dans fichiers suivis
$secretScan = "$DEV_CORE\Scripts\secret_scan.ps1"
if (Test-Path $secretScan) {
    & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $secretScan -Path (Get-Location).Path -Quiet
    if ($LASTEXITCODE -eq 0) {
        Check "Secrets hardcodes absents des fichiers suivis" "OK"
    } else {
        Check "Secrets hardcodes detectes dans les fichiers suivis" "FAIL" "powershell -File `"$secretScan`" -Path `"$((Get-Location).Path)`""
    }
} else {
    Check "Secret scan indisponible" "FAIL" "Restaurer secret_scan.ps1"
}

# 5. Task active + integrite
$tFile = "$DEV_CORE_DATA\Memory\$(& "$PSScriptRoot\Get-ActiveProject.ps1")\tasks.json"
if (Test-Path $tFile) {
    try {
        $board  = Get-Content $tFile -Raw | ConvertFrom-Json
        $active = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1
        if ($active) {
            Check "Task active : $($active.id) ($($active.steps_done)/$($active.steps_total))" "OK"

            # Integrity check : steps_done vs steps reellement done
            if ($active.steps -and $active.steps.Count -gt 0) {
                $realDone = @($active.steps | Where-Object { $_.done }).Count
                if ($active.steps_done -ne $realDone) {
                    Check "Integrite steps $($active.id) : steps_done=$($active.steps_done) vs reel=$realDone" "WARN" "Corriger steps_done"
                    AutoFix "Corriger steps_done $($active.id)" {
                        $active.steps_done = $realDone
                        $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
                    }
                } else {
                    Check "Integrite steps $($active.id) coherente" "OK"
                }
            }

            # Check tasks 'done' avec steps incompletes
            $corruptDone = $board.tasks | Where-Object {
                $_.status -eq "done" -and $_.steps_done -lt $_.steps_total
            }
            if ($corruptDone) {
                foreach ($cd in $corruptDone) {
                    Check "Corruption : $($cd.id) done mais $($cd.steps_done)/$($cd.steps_total)" "WARN"
                    AutoFix "Corriger $($cd.id) steps_done" {
                        $cd.steps_done = $cd.steps_total
                        if ($cd.steps) { $cd.steps | ForEach-Object { $_.done = $true } }
                        $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
                    }
                }
            }
        } else {
            Check "Aucune task active" "WARN" "dc next task"
        }
    } catch { Check "tasks.json illisible" "FAIL" "Verifier $tFile" }
} else {
    Check "tasks.json absent" "WARN" "dc new task [nom]"
}

# 6. CLAUDE.md projet CWD
if (Test-Path "$(Get-Location)\CLAUDE.md") { Check "CLAUDE.md projet present" "OK" }
else { Check "CLAUDE.md projet absent" "WARN" "dc new project [nom]" }

# 7. Qdrant
try {
    $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3
    Check "Qdrant OK ($($q.result.collections.Count) collections)" "OK"
} catch {
    Check "Qdrant non disponible" "WARN" "docker start qdrant"
    AutoFix "Demarrer Qdrant" {
        Start-Process "docker" -ArgumentList "start qdrant" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Start-Sleep 3
    }
}

# 7.2 Gemini Router (Port 20130) - Primary
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $result = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 20130, $null, $null)
    $success = $result.AsyncWaitHandle.WaitOne(1000, $true)
    if ($success) {
        $tcp.EndConnect($result)
        Check "Gemini Router OK (Port 20130)" "OK"
    } else {
        throw "Timeout"
    }
    $tcp.Close()
} catch {
    Check "Gemini Router non disponible" "WARN" "dc launch"
    AutoFix "Demarrer Gemini Router" {
        $logOut = "$DEV_CORE_DATA\Logs\scripts\gemini_router.log"
        $logErr = "$DEV_CORE_DATA\Logs\scripts\gemini_router_err.log"
        Start-Process -FilePath "python" -ArgumentList "$DEV_CORE\Scripts\gemini_router.py" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -ErrorAction SilentlyContinue
        
        # Attendre que le port s'ouvre (timeout 10s)
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $tcp = New-Object System.Net.Sockets.TcpClient
                $res = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 20130, $null, $null)
                $suc = $res.AsyncWaitHandle.WaitOne(100, $true)
                if ($suc) {
                    $tcp.EndConnect($res)
                    $tcp.Close()
                    break
                }
                $tcp.Close()
            } catch {}
        }
    }
}

# 7.2.5 Dashboard API Server (Port 20129)
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $result = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 20129, $null, $null)
    $success = $result.AsyncWaitHandle.WaitOne(1000, $true)
    if ($success) {
        $tcp.EndConnect($result)
        Check "Dashboard API Server OK (Port 20129)" "OK"
    } else {
        throw "Timeout"
    }
    $tcp.Close()
} catch {
    Check "Dashboard API Server non disponible" "WARN" "dc launch"
    AutoFix "Demarrer Dashboard API Server" {
        $logOut = "$DEV_CORE_DATA\Logs\scripts\dashboard_api.log"
        $logErr = "$DEV_CORE_DATA\Logs\scripts\dashboard_api_err.log"
        Start-Process -FilePath "python" -ArgumentList "$DEV_CORE\Scripts\dashboard_api.py" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -ErrorAction SilentlyContinue
        
        # Attendre que le port s'ouvre (timeout 10s)
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $tcp = New-Object System.Net.Sockets.TcpClient
                $res = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 20129, $null, $null)
                $suc = $res.AsyncWaitHandle.WaitOne(100, $true)
                if ($suc) {
                    $tcp.EndConnect($res)
                    $tcp.Close()
                    break
                }
                $tcp.Close()
            } catch {}
        }
    }
}


# 7.5 Headroom Proxy
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $result = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 8787, $null, $null)
    $success = $result.AsyncWaitHandle.WaitOne(1000, $true)
    if ($success) {
        $tcp.EndConnect($result)
        Check "Headroom Proxy OK (Port 8787)" "OK"
    } else {
        throw "Timeout"
    }
    $tcp.Close()
} catch {
    Check "Headroom Proxy non disponible" "WARN" "headroom proxy --port 8787"
    AutoFix "Demarrer Headroom Proxy" {
        & "$DEV_CORE\Scripts\headroom_start.ps1"
    }
}

# 7.6 Repowise Server
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $result = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 7337, $null, $null)
    $success = $result.AsyncWaitHandle.WaitOne(1000, $true)
    if ($success) {
        $tcp.EndConnect($result)
        Check "Repowise Server OK (Port 7337)" "OK"
    } else {
        throw "Timeout"
    }
    $tcp.Close()
} catch {
    Check "Repowise Server non disponible" "WARN" "repowise serve"
    AutoFix "Demarrer Repowise Server" {
        $repowisePath = "C:\Users\trb_m\AppData\Roaming\Python\Python313\Scripts\repowise.exe"
        if (-not (Test-Path $repowisePath)) { $repowisePath = "repowise" }
        $logOut = "$DEV_CORE_DATA\Logs\scripts\repowise.log"
        $logErr = "$DEV_CORE_DATA\Logs\scripts\repowise_err.log"
        $env:REPOWISE_EMBEDDER = "mock"
        Start-Process -FilePath $repowisePath -ArgumentList "serve --ui-port 3100 --host localhost" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -ErrorAction SilentlyContinue
        
        # Attendre que le port s'ouvre (timeout 10s)
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $tcp = New-Object System.Net.Sockets.TcpClient
                $res = $tcp.BeginConnect([System.Net.IPAddress]::Loopback, 7337, $null, $null)
                $suc = $res.AsyncWaitHandle.WaitOne(100, $true)
                if ($suc) {
                    $tcp.EndConnect($res)
                    $tcp.Close()
                    break
                }
                $tcp.Close()
            } catch {}
        }
    }
}


# 8. Post-commit hook
$gitHooksDir = "$(Get-Location)\.git\hooks"
if (Test-Path "$gitHooksDir\post-commit") { Check "Git post-commit hook installe" "OK" }
elseif (Test-Path $gitHooksDir) {
    Check "Git post-commit hook absent" "WARN" "Copier post-commit.hook"
    AutoFix "Installer post-commit hook" {
        Copy-Item "$DEV_CORE\Scripts\post-commit.hook" "$gitHooksDir\post-commit" -Force
    }
}

# Resultat
Write-Host ""
Write-Host "  =======================================" -ForegroundColor DarkGray
Write-Host "  OK: $ok  |  WARN: $warn  |  FAIL: $fail" -NoNewline -ForegroundColor White
if ($Fix -and $fixed -gt 0) { Write-Host "  |  FIXED: $fixed" -ForegroundColor Magenta }
else { Write-Host "" }
Write-Host ""
if ($fail -gt 0)      { Write-Host "  FAIL a corriger -- dc check --fix pour auto-reparer" -ForegroundColor Red }
elseif ($warn -gt 0)  { Write-Host "  Quasi pret -- dc check --fix pour corriger les WARN" -ForegroundColor Yellow }
else                  { Write-Host "  100% operationnel -- autonomie complete" -ForegroundColor Green }
Write-Host ""

