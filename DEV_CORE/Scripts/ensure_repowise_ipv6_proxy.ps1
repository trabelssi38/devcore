# ensure_repowise_ipv6_proxy.ps1 -- make http://localhost:7337 work on Windows
param(
    [string]$Python = "python",
    [string]$ScriptPath = "$PSScriptRoot\repowise_ipv6_proxy.py"
)

$ErrorActionPreference = "Stop"

function Test-Tcp {
    param([string]$HostName, [int]$Port)
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(500)
        if ($ok) { $client.EndConnect($iar) }
        $client.Close()
        return $ok
    } catch {
        return $false
    }
}

if (Test-Tcp -HostName "::1" -Port 7337) {
    Write-Host "[DEV_CORE] Repowise IPv6 proxy OK -- ::1:7337 reachable"
    exit 0
}

if (-not (Test-Path -LiteralPath $ScriptPath)) {
    Write-Host "[DEV_CORE] Repowise IPv6 proxy WARN -- script missing: $ScriptPath"
    exit 0
}

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match [regex]::Escape("repowise_ipv6_proxy.py") } |
    Select-Object -First 1
if ($existing) {
    Write-Host "[DEV_CORE] Repowise IPv6 proxy WAIT -- process exists pid=$($existing.ProcessId)"
    exit 0
}

$logDir = Join-Path (Split-Path -Parent $PSScriptRoot) "DEV_CORE_DATA\Logs\scripts"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$out = Join-Path $logDir "repowise_ipv6_proxy.log"
$err = Join-Path $logDir "repowise_ipv6_proxy_err.log"

Start-Process -FilePath $Python -ArgumentList @($ScriptPath) -WorkingDirectory $(Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -ErrorAction SilentlyContinue | Out-Null
Start-Sleep -Milliseconds 800

if (Test-Tcp -HostName "::1" -Port 7337) {
    Write-Host "[DEV_CORE] Repowise IPv6 proxy OK -- started"
} else {
    Write-Host "[DEV_CORE] Repowise IPv6 proxy WARN -- not reachable after start"
}
