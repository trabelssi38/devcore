# headroom_start.ps1 -- DEV_CORE v9.0
# Démarre le proxy Headroom si disponible
# Usage : & "headroom_start.ps1"

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$LOG = "$DEV_CORE_DATA\Logs\scripts\headroom_start_$TODAY.log"

function Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Log "Demarrage du Headroom Proxy..." "Cyan"

# 1. Vérifier si headroom-ai est installé via python
$checkPkg = python.exe -c "import headroom" 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "  [WARN] Le module python 'headroom-ai' n'est pas installe. Tentative d'installation rapide..." "Yellow"
    pip install "headroom-ai[proxy]" 2>&1 | Out-Null
    $checkPkg2 = python.exe -c "import headroom" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Log "  [ERREUR] Impossible d'installer ou d'importer headroom. Abandon." "Red"
        exit 1
    }
}

Log "  Module 'headroom-ai' detecte." "Green"

# 2. Lancer le proxy en tache de fond (Start-Process)
$configPath = "$DEV_CORE\Config\headroom_config.yaml"

# Creer le repertoire de cache si absent
$cacheDir = "$DEV_CORE_DATA\Cache\headroom"
if (-not (Test-Path $cacheDir)) {
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
}

$metricsDir = "$DEV_CORE_DATA\Metrics"
if (-not (Test-Path $metricsDir)) {
    New-Item -ItemType Directory -Path $metricsDir -Force | Out-Null
}

Log "  Dossiers de cache et metriques configures." "Gray"

# Trouver l'executable headroom.exe
$headroomPath = "headroom"
$customPaths = @(
    "$env:USERPROFILE\AppData\Roaming\Python\Python313\Scripts\headroom.exe",
    "C:\Users\trb_m\AppData\Roaming\Python\Python313\Scripts\headroom.exe",
    "$env:USERPROFILE\AppData\Roaming\Python\Scripts\headroom.exe"
)
foreach ($p in $customPaths) {
    if (Test-Path $p) {
        $headroomPath = $p
        break
    }
}

# Lancement
try {
    Log "  Lancement du processus Headroom Proxy via $headroomPath..." "Gray"
    
    try {
        $proc = Start-Process -FilePath $headroomPath -ArgumentList "proxy", "--port", "8787", "--openai-api-url", "http://127.0.0.1:20130/v1" -WorkingDirectory "C:\devcore" -WindowStyle Hidden -PassThru -ErrorAction Stop
    } catch {
        $proc = Start-Process -FilePath $headroomPath -ArgumentList "proxy", "--port", "8787", "--openai-api-url", "http://127.0.0.1:20130/v1" -WorkingDirectory "C:\devcore" -PassThru
    }

    # Attendre que le port soit ouvert (timeout 15s)
    $portOpen = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $result = $tcp.BeginConnect("127.0.0.1", 8787, $null, $null)
            $success = $result.AsyncWaitHandle.WaitOne(200, $true)
            if ($success) {
                $tcp.EndConnect($result)
                $portOpen = $true
                $tcp.Close()
                break
            }
            $tcp.Close()
        } catch {}
    }

    if ($portOpen) {
        Log "  Headroom Proxy demarre avec succes sur http://localhost:8787" "Green"
        exit 0
    } else {
        Log "  [ERROR] Le proxy n'a pas repondu sur le port 8787 apres 5 secondes." "Red"
        exit 1
    }
} catch {
    Log "  [ERROR] Echec du lancement de Headroom : $_" "Red"
    exit 1
}
