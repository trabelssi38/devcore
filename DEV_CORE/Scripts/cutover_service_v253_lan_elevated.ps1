param(
    [string]$Release = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v253-lan',
    [string]$PreviousRelease = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v252-clean',
    [string]$ServiceName = 'DevCoreIndividual'
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this cutover with elevated PowerShell 7 (pwsh).' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this cutover with elevated PowerShell 7 (pwsh).'
}

$new = (Resolve-Path -LiteralPath $Release).Path
$old = (Resolve-Path -LiteralPath $PreviousRelease).Path
$newBinary = Join-Path $new 'pythonservice.exe'
$oldBinary = Join-Path $old 'pythonservice.exe'
$current = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").PathName.Trim().Trim('"')
if ($current -ine $oldBinary -or (Get-Service $ServiceName).Status -ne 'Running') {
    throw 'Expected the running v252 service before the LAN cutover.'
}
$python = Join-Path $new 'Scripts/python.exe'
$verifier = Join-Path $new 'controls/Scripts/verify_engine_release.py'
& $python -I $verifier --release $new | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'v253 release attestation failed.' }
$config = Get-Content -Raw -LiteralPath (Join-Path $new 'individual-service.json') | ConvertFrom-Json
if ($config.schema_version -ne 3 -or $config.network.bind -ne '172.16.210.32') {
    throw 'Unexpected LAN service profile.'
}
$runtimeRoot = Split-Path -Parent (Split-Path -Parent $new)
$localRoot = Join-Path $runtimeRoot $config.local_relative
$dataRoot = Join-Path $runtimeRoot $config.data_relative
$cert = Join-Path $runtimeRoot $config.network.cert_relative
$key = Join-Path $runtimeRoot $config.network.key_relative
$launcher = Join-Path $new 'controls/Scripts/launch_individual_candidate.py'
& $python -I $launcher --bundle (Join-Path $new 'individual-platform-v2') `
    --manifest-sha256 $config.bundle_manifest_sha256 --local-root $localRoot --data-root $dataRoot `
    --identity-store (Join-Path $localRoot 'Security/identity.db') --port 20129 --managed `
    --lan-bind $config.network.bind --tls-certfile $cert --tls-keyfile $key --check | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'v253 LAN candidate preflight failed.' }

$firewallScript = Join-Path $PSScriptRoot 'configure_devcore_lan_firewall_elevated.ps1'
$privateWasEnabled = (Get-NetFirewallProfile -Name Private).Enabled
$firewallApplied = $false
$serviceChanged = $false
$ruleName = 'DevCore Individual TLS pilot'
try {
    $firewall = & $firewallScript -Apply | ConvertFrom-Json
    if ($firewall.action -ne 'private_firewall_and_scoped_rule_verified') {
        throw 'Scoped firewall rule was not verified.'
    }
    $firewallApplied = $true
    Stop-Service $ServiceName -ErrorAction Stop
    (Get-Service $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(45))
    & sc.exe config $ServiceName binPath= ('"' + $newBinary + '"') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'SCM update to v253 failed.' }
    $serviceChanged = $true
    Start-Service $ServiceName -ErrorAction Stop
    (Get-Service $ServiceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(45))

    $probeCode = 'import httpx,sys,json; c=httpx.Client(base_url=sys.argv[1],verify=sys.argv[2],trust_env=False,timeout=5); paths=["/project","/api/status","/api/auth/session","/api/dashboard/tasks?project=devcore"]; print(json.dumps([c.get(p).status_code for p in paths])); c.close()'
    $probe = & $python -I -c $probeCode 'https://172.16.210.32:20129' $cert | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or (@($probe) -join ',') -ne '200,200,401,401') {
        throw 'v253 HTTPS service probes failed.'
    }
    $actual = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").PathName.Trim().Trim('"')
    if ($actual -ine $newBinary -or (Get-Service $ServiceName).Status -ne 'Running') {
        throw 'v253 service did not remain Running.'
    }
    [pscustomobject]@{ status='v253_lan_local_cutover_verified'; service=$ServiceName;
        binary=$newBinary; tls_origin='https://172.16.210.32:20129';
        http_statuses=@($probe); second_host_pending=$true } | ConvertTo-Json
}
catch {
    $failure = $_.Exception.Message
    $rollback = @()
    if ($serviceChanged) {
        try {
            Stop-Service $ServiceName -ErrorAction SilentlyContinue
            (Get-Service $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(45))
            & sc.exe config $ServiceName binPath= ('"' + $oldBinary + '"') | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'SCM rollback failed.' }
            Start-Service $ServiceName -ErrorAction Stop
            (Get-Service $ServiceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(45))
            $rollback += 'service_restored'
        }
        catch { $rollback += "service_rollback_failed: $($_.Exception.Message)" }
    }
    elseif ((Get-Service $ServiceName).Status -ne 'Running') {
        try { Start-Service $ServiceName -ErrorAction Stop; $rollback += 'original_service_restarted' }
        catch { $rollback += "original_service_restart_failed: $($_.Exception.Message)" }
    }
    if ($firewallApplied) {
        try {
            Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction Stop
            Set-NetFirewallProfile -Name Private -Enabled $privateWasEnabled -ErrorAction Stop
            $rollback += 'firewall_restored'
        }
        catch { $rollback += "firewall_rollback_failed: $($_.Exception.Message)" }
    }
    throw "v253 LAN cutover failed: $failure; rollback: $($rollback -join ', ')"
}
