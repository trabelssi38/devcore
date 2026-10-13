param(
    [string]$Release = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261013-postgres-v250',
    [string]$ServiceName = 'DevCoreIndividual',
    [string]$ProbeUrl = 'http://127.0.0.1:20129/project',
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell session.'
}

$releasePath = (Resolve-Path -LiteralPath $Release).Path
$python = Join-Path $releasePath 'Scripts/python.exe'
$verifier = Join-Path $releasePath 'controls/Scripts/verify_engine_release.py'
$newBinary = Join-Path $releasePath 'pythonservice.exe'
if (-not (Test-Path -LiteralPath $newBinary)) { throw "Missing staged service host: $newBinary" }
if ((Test-Path -LiteralPath (Join-Path $releasePath 'individual-platform-v2/Scripts/dashboard_api.py')) -and
    -not (Test-Path -LiteralPath (Join-Path $releasePath 'postgres-dashboard-qualified.json'))) {
    throw 'The staged SCM host still runs the SQLite Dashboard; PostgreSQL Dashboard qualification is missing.'
}
& $python -I $verifier --release $releasePath
if ($LASTEXITCODE -ne 0) { throw 'v250 release attestation failed.' }

$service = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'"
if (-not $service) { throw "Service not found: $ServiceName" }
$oldBinary = $service.PathName.Trim().Trim('"')
$initialStatus = (Get-Service $ServiceName).Status
$wasRunning = $initialStatus -eq 'Running'
$newQuoted = '"' + $newBinary + '"'

function Wait-ServiceState([string]$Name, [string]$Expected, [datetime]$Deadline) {
    do {
        $state = (Get-Service $Name).Status.ToString()
        if ($state -eq $Expected) { return $true }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $Deadline)
    return ((Get-Service $Name).Status.ToString() -eq $Expected)
}

function Force-StopServiceProcess([string]$Name, [string]$ExpectedBinary) {
    $svc = Get-CimInstance Win32_Service -Filter "Name='$Name'"
    $servicePid = [int]$svc.ProcessId
    if ($servicePid -le 0) { throw "Service $Name did not stop and has no process id." }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$servicePid"
    $path = [string]$proc.ExecutablePath
    if (-not $path -or -not ($path -ieq $ExpectedBinary)) {
        throw "Refusing to force-stop unexpected service process $servicePid ($path)."
    }
    Stop-Process -Id $servicePid -Force
    if (-not (Wait-ServiceState $Name 'Stopped' ((Get-Date).AddSeconds(10)))) {
        throw "Service $Name remained non-stopped after terminating process $servicePid."
    }
}

function Clear-StaleServiceListener([string]$Url, [string]$ReleaseRoot) {
    $uri = [Uri]$Url
    $allowedInterpreter = 'E:\DevCoreRuntime\interpreters\cpython-3.13.16-windows-x86_64-none\python.exe'
    $listeners = @(Get-NetTCPConnection -LocalPort $uri.Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $listenerPid = [int]$listener.OwningProcess
        if ($listenerPid -le 0) { continue }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$listenerPid"
        $path = [string]$proc.ExecutablePath
        $expectedPath = $path.StartsWith($ReleaseRoot, [StringComparison]::OrdinalIgnoreCase) -or
            ($path -ieq $allowedInterpreter)
        if (-not $path -or -not $expectedPath) {
            throw "Refusing to terminate unexpected listener process $listenerPid ($path) on port $($uri.Port)."
        }
        Stop-Process -Id $listenerPid -Force
    }
    if (Get-NetTCPConnection -LocalPort $uri.Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $($uri.Port) remains occupied after stale listener cleanup."
    }
}

try {
    if ($initialStatus -ne 'Stopped') {
        sc.exe stop $ServiceName | Out-Host
        if (-not (Wait-ServiceState $ServiceName 'Stopped' ((Get-Date).AddSeconds($TimeoutSeconds)))) {
            Force-StopServiceProcess $ServiceName $oldBinary
        }
    }
    Clear-StaleServiceListener $ProbeUrl $releasePath
    sc.exe config $ServiceName binPath= $newQuoted | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'SCM registration update failed.' }
    sc.exe start $ServiceName | Out-Host
    if (-not (Wait-ServiceState $ServiceName 'Running' ((Get-Date).AddSeconds($TimeoutSeconds)))) { throw 'v250 service did not reach Running.' }
    Start-Sleep -Seconds 3
    if ((Get-Service $ServiceName).Status -ne 'Running') { throw 'v250 service exited after reaching Running.' }
    $probe = Invoke-WebRequest -UseBasicParsing $ProbeUrl -TimeoutSec $TimeoutSeconds
    if ($probe.StatusCode -ne 200) { throw "Probe returned HTTP $($probe.StatusCode)." }
    [pscustomobject]@{ status='cutover_verified'; service=$ServiceName; binary=$newBinary; probe_status=$probe.StatusCode } | ConvertTo-Json
}
catch {
    Write-Warning $_.Exception.Message
    if (Test-Path -LiteralPath $oldBinary) {
        sc.exe stop $ServiceName | Out-Host
        Start-Sleep -Seconds 2
        sc.exe config $ServiceName binPath= ('"' + $oldBinary + '"') | Out-Host
        sc.exe start $ServiceName | Out-Host
    }
    throw
}
