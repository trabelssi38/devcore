# init_agent_env.ps1 -- DEV_CORE v10.0
# Configure de manière persistante ou de session les variables de routage pour les agents AI.
# Usage : & "init_agent_env.ps1" [-Scope User|Process]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("User", "Process")]
    [string]$Scope = "Process"
)

$DEV_CORE      = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { $PSScriptRoot }
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
