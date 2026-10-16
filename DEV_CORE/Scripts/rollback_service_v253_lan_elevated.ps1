param(
    [string]$ServiceName = 'DevCoreIndividual',
    [string]$LanRelease = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v253-lan',
    [string]$PreviousRelease = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v252-clean'
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this rollback with elevated PowerShell 7 (pwsh).' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this rollback with elevated PowerShell 7 (pwsh).'
}
$lanBinary = (Resolve-Path -LiteralPath (Join-Path $LanRelease 'pythonservice.exe')).Path
$localBinary = (Resolve-Path -LiteralPath (Join-Path $PreviousRelease 'pythonservice.exe')).Path
$current = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").PathName.Trim().Trim('"')
if ($current -ine $lanBinary) { throw 'The service is not on v253 LAN; refusing rollback.' }

# Close the sole DevCore LAN firewall rule before touching the service. Keep
# the Private profile enabled after a successful rollback for fail-closed state.
$ruleName = 'DevCore Individual TLS pilot'
$secondHostRuleName = 'DevCore Individual TLS pilot second host'
$secondHostRule = Get-NetFirewallRule -DisplayName $secondHostRuleName -ErrorAction SilentlyContinue
if ($secondHostRule) { Remove-NetFirewallRule -DisplayName $secondHostRuleName -ErrorAction Stop }
$rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($rule) { Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction Stop }
Stop-Service $ServiceName -ErrorAction Stop
(Get-Service $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(45))
& sc.exe config $ServiceName binPath= ('"' + $localBinary + '"') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'SCM rollback to v252 failed; LAN rule remains closed.' }
Start-Service $ServiceName -ErrorAction Stop
(Get-Service $ServiceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(45))
$probe = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 'http://127.0.0.1:20129/project'
if ($probe.StatusCode -ne 200) { throw 'v252 local probe failed after rollback.' }
[pscustomobject]@{ status='v252_local_rollback_verified'; service=$ServiceName;
    binary=$localBinary; project_http=200; private_firewall_enabled=[bool](Get-NetFirewallProfile -Name Private).Enabled } | ConvertTo-Json
