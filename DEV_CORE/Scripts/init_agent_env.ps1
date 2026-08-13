# init_agent_env.ps1 -- DEV_CORE v10.0
# Configure de manière persistante ou de session les variables de routage pour les agents AI.
# Usage : & "init_agent_env.ps1" [-Scope User|Process]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("User", "Process")]
    [string]$Scope = "Process"
)

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
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT)     { $env:DEVCORE_DATA_ROOT }     else { (Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA") }
$TODAY         = Get-Date -Format "yyyy-MM-dd"
$LOG           = "$DEV_CORE_DATA\Logs\scripts\init_agent_env_$TODAY.log"

function Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] [init_env] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Log "Configuration des variables d'environnement des agents (Scope: $Scope)..." "Cyan"

$vars = @{
    "OPENAI_BASE_URL"           = "http://localhost:8787/v1"
    "OPENAI_API_BASE"           = "http://localhost:8787/v1"
    "ANTHROPIC_BASE_URL"        = "http://localhost:8788"
    "DEVCORE_HEADROOM_ENFORCED" = "1"
}

foreach ($key in $vars.Keys) {
    $val = $vars[$key]
    if ($Scope -eq "User") {
        [System.Environment]::SetEnvironmentVariable($key, $val, "User")
        # Also set in current process so it's active immediately
        [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
    } else {
        [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
    Log "  $key = $val" "Gray"
}

Log "Variables d'environnement configurees avec succes." "Green"
