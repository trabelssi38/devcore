param(
    [switch]$RecordBaseline,
    [string]$BaselinePath = 'E:/src_python/devcore/docs/audit-2026-09-30/v253-restart-baseline-2026-10-16.json'
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this check with PowerShell 7 (pwsh).' }
$boot = (Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).LastBootUpTime.ToUniversalTime()
if ($RecordBaseline) {
    if (Test-Path -LiteralPath $BaselinePath) { throw 'A restart baseline already exists; refusing to replace it.' }
    $baseline = [ordered]@{
        host = $env:COMPUTERNAME
        boot_utc = $boot.ToString('o')
        recorded_utc = [datetime]::UtcNow.ToString('o')
    }
    [pscustomobject]$baseline | ConvertTo-Json | Set-Content -LiteralPath $BaselinePath -Encoding utf8 -NoNewline
    [pscustomobject]@{ status='v253_restart_baseline_recorded'; path=$BaselinePath;
        boot_utc=$baseline.boot_utc } | ConvertTo-Json
    return
}

if (-not (Test-Path -LiteralPath $BaselinePath -PathType Leaf)) { throw 'Restart baseline is missing.' }
$baseline = Get-Content -Raw -LiteralPath $BaselinePath | ConvertFrom-Json
if ($baseline.host -ne $env:COMPUTERNAME) { throw 'Restart baseline belongs to another host.' }
$previousBoot = if ($baseline.boot_utc -is [datetime]) {
    $baseline.boot_utc.ToUniversalTime()
} else {
    [datetime]::Parse([string]$baseline.boot_utc, [cultureinfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}
if ($boot -le $previousBoot) { throw 'Windows has not restarted since the v253 baseline was recorded.' }
$failures = @(Get-WinEvent -FilterHashtable @{
    LogName='System'; ProviderName='Service Control Manager';
    StartTime=$boot.ToLocalTime(); Id=@(7024,7031,7034)
} -ErrorAction SilentlyContinue | Where-Object { $_.Message -match 'DevCore Individual Dashboard' })
if ($failures.Count -gt 0) {
    throw 'DevCore service failed after boot; a later manual start cannot qualify automatic recovery.'
}

$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run the post-restart check with elevated PowerShell 7 (pwsh).'
}

$release = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v253-lan'
$expectedBinary = (Resolve-Path -LiteralPath (Join-Path $release 'pythonservice.exe')).Path
$service = Get-CimInstance Win32_Service -Filter "Name='DevCoreIndividual'" -ErrorAction Stop
if ($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or
    $service.PathName.Trim().Trim('"') -ine $expectedBinary) {
    throw 'DevCoreIndividual did not resume on the expected v253 binary in Auto mode.'
}
$postgres = Get-CimInstance Win32_Service -Filter "Name='postgresql-x64-17'" -ErrorAction Stop
if ($postgres.State -ne 'Running' -or $postgres.StartMode -ne 'Auto') {
    throw 'PostgreSQL did not resume in Auto mode.'
}
$devcoreListeners = @(Get-NetTCPConnection -State Listen -LocalPort 20129 -ErrorAction Stop)
if ($devcoreListeners.Count -ne 1 -or $devcoreListeners[0].LocalAddress -ne '172.16.210.32') {
    throw 'DevCore listener is not limited to the expected LAN address.'
}
$postgresListeners = @(Get-NetTCPConnection -State Listen -LocalPort 5432 -ErrorAction Stop)
if ($postgresListeners.Count -lt 1 -or
    @($postgresListeners | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }).Count -ne 0) {
    throw 'PostgreSQL is not limited to loopback after restart.'
}
$private = Get-NetFirewallProfile -Name Private -PolicyStore ActiveStore -ErrorAction Stop
if ([string]$private.Enabled -ne 'True' -or [string]$private.AllowInboundRules -ne 'True' -or
    [string]$private.AllowLocalFirewallRules -ne 'True') {
    throw 'The Private firewall profile is not enforcing local inbound rules.'
}

function Assert-PilotRule([string]$displayName, [string[]]$remoteForms) {
    $rules = @(Get-NetFirewallRule -PolicyStore ActiveStore -DisplayName $displayName -ErrorAction Stop)
    if ($rules.Count -ne 1) { throw "Expected one active firewall rule: $displayName" }
    $rule = $rules[0]
    $port = $rule | Get-NetFirewallPortFilter -ErrorAction Stop
    $addresses = $rule | Get-NetFirewallAddressFilter -ErrorAction Stop
    $remote = @($addresses.RemoteAddress | ForEach-Object { [string]$_ })
    $localForms = @('172.16.210.32', '172.16.210.32/32',
        '172.16.210.32/255.255.255.255')
    if ([string]$rule.Enabled -ne 'True' -or [string]$rule.Direction -ne 'Inbound' -or
        [string]$rule.Action -ne 'Allow' -or [string]$rule.Profile -ne 'Private' -or
        [string]$port.Protocol -notin @('TCP', '6') -or [string]$port.LocalPort -ne '20129' -or
        [string]$addresses.LocalAddress -notin $localForms -or
        $remote.Count -ne 1 -or $remote[0] -notin $remoteForms) {
        throw "Firewall rule is outside the expected scope: $displayName"
    }
    return $remote[0]
}

$lanRemote = Assert-PilotRule 'DevCore Individual TLS pilot' @(
    '172.16.210.0/24', '172.16.210.0/255.255.255.0')
$clientRemote = Assert-PilotRule 'DevCore Individual TLS pilot second host' @(
    '10.40.100.2', '10.40.100.2/32', '10.40.100.2/255.255.255.255')

$python = Join-Path $release 'Scripts/python.exe'
$cert = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/state/local/Security/lan-tls/cert.pem'
$probeCode = 'import httpx,sys,json; c=httpx.Client(base_url="https://172.16.210.32:20129",verify=sys.argv[1],trust_env=False,timeout=5); print(json.dumps([c.get(p).status_code for p in ["/project","/api/status","/api/auth/session"]])); c.close()'
$probe = & $python -I -c $probeCode $cert | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or (@($probe) -join ',') -ne '200,200,401') {
    throw 'v253 HTTPS service probes failed after restart.'
}

[pscustomobject]@{
    status = 'v253_post_restart_local_verified'
    boot_utc = $boot.ToString('o')
    service = 'Running/Auto'
    postgres = 'Running/Auto/loopback'
    lan_listener = '172.16.210.32:20129'
    firewall_remote_ranges = @($lanRemote, $clientRemote)
    https_statuses = @($probe)
    second_host_recheck_pending = $true
} | ConvertTo-Json
