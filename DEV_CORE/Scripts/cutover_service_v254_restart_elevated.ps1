param(
    [string]$NewRelease = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261016-postgres-v254-restart',
    [string]$PreviousRelease = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v253-lan',
    [string]$ServiceName = 'DevCoreIndividual'
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this cutover with elevated PowerShell 7 (pwsh).' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this cutover with elevated PowerShell 7 (pwsh).'
}
$new = (Resolve-Path -LiteralPath $NewRelease).Path
$old = (Resolve-Path -LiteralPath $PreviousRelease).Path
$newBinary = Join-Path $new 'pythonservice.exe'
$oldBinary = Join-Path $old 'pythonservice.exe'
$service = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'" -ErrorAction Stop
if ($service.State -ne 'Running' -or $service.StartMode -ne 'Auto' -or
    $service.PathName.Trim().Trim('"') -ine $oldBinary) {
    throw 'Expected the running v253 LAN service in Auto mode before v254 cutover.'
}

$python = Join-Path $new 'Scripts/python.exe'
$verifier = Join-Path $new 'controls/Scripts/verify_engine_release.py'
& $python -I $verifier --release $new | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'v254 release attestation failed.' }
$config = Get-Content -Raw -LiteralPath (Join-Path $new 'individual-service.json') | ConvertFrom-Json
if ($config.schema_version -ne 3 -or $config.network.bind -ne '172.16.210.32' -or
    $config.local_relative -ne 'state/local' -or $config.data_relative -ne 'state/data') {
    throw 'Unexpected v254 LAN service profile.'
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
if ($LASTEXITCODE -ne 0) { throw 'v254 candidate preflight failed.' }

$changed = $false
$probeCode = 'import httpx,sys,json; c=httpx.Client(base_url=sys.argv[1],verify=sys.argv[2],trust_env=False,timeout=5); print(json.dumps([c.get(p).status_code for p in ["/project","/api/status","/api/auth/session"]])); c.close()'
try {
    Stop-Service $ServiceName -ErrorAction Stop
    (Get-Service $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(45))
    & sc.exe config $ServiceName binPath= ('"' + $newBinary + '"') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'SCM update to v254 failed.' }
    $changed = $true
    Start-Service $ServiceName -ErrorAction Stop

    $deadline = [datetime]::UtcNow.AddSeconds(180)
    $probe = $null
    while ([datetime]::UtcNow -lt $deadline) {
        $state = (Get-Service $ServiceName).Status
        if ($state -eq 'Stopped') { throw 'v254 service stopped during readiness.' }
        try {
            $candidate = & $python -I -c $probeCode 'https://172.16.210.32:20129' $cert 2>$null |
                ConvertFrom-Json
            if ($LASTEXITCODE -eq 0 -and (@($candidate) -join ',') -eq '200,200,401') {
                $probe = @($candidate)
                break
            }
        }
        catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $probe) { throw 'v254 HTTPS readiness timeout.' }
    $actual = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'" -ErrorAction Stop
    if ($actual.State -ne 'Running' -or $actual.PathName.Trim().Trim('"') -ine $newBinary) {
        throw 'v254 did not remain Running on the selected binary.'
    }
    [pscustomobject]@{ status='v254_restart_candidate_cutover_verified'; service=$ServiceName;
        binary=$newBinary; https_statuses=$probe; firewall_unchanged=$true;
        second_host_recheck_pending=$true; reboot_requalification_pending=$true } | ConvertTo-Json
}
catch {
    $failure = $_.Exception.Message
    $rollback = @()
    if ($changed) {
        try {
            if ((Get-Service $ServiceName).Status -ne 'Stopped') {
                Stop-Service $ServiceName -ErrorAction Stop
                (Get-Service $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(45))
            }
            & sc.exe config $ServiceName binPath= ('"' + $oldBinary + '"') | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'SCM rollback to v253 failed.' }
            Start-Service $ServiceName -ErrorAction Stop
            (Get-Service $ServiceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(45))
            $oldPython = Join-Path $old 'Scripts/python.exe'
            $oldDeadline = [datetime]::UtcNow.AddSeconds(60)
            $oldReady = $false
            while ([datetime]::UtcNow -lt $oldDeadline) {
                try {
                    $oldProbe = & $oldPython -I -c $probeCode 'https://172.16.210.32:20129' $cert 2>$null |
                        ConvertFrom-Json
                    if ($LASTEXITCODE -eq 0 -and (@($oldProbe) -join ',') -eq '200,200,401') {
                        $oldReady = $true
                        break
                    }
                }
                catch { }
                Start-Sleep -Seconds 2
            }
            if (-not $oldReady) {
                throw 'v253 rollback HTTPS probe failed.'
            }
            $rollback += 'v253_service_https_verified'
        }
        catch { $rollback += "service_rollback_failed: $($_.Exception.Message)" }
    }
    elseif ((Get-Service $ServiceName).Status -eq 'Stopped') {
        try { Start-Service $ServiceName -ErrorAction Stop; $rollback += 'v253_service_restarted' }
        catch { $rollback += "service_restart_failed: $($_.Exception.Message)" }
    }
    throw "v254 cutover failed: $failure; rollback: $($rollback -join ', ')"
}
