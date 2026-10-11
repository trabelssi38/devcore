param(
    [string]$Python = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe',
    [string]$Release = 'E:/DevCoreRuntime/qualification/service-profile-v249/runtime/releases/devcore-py31316-20261011-l9-autostart-clean-v249'
)

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run PowerShell as Administrator before launching this script.'
    exit 740
}
if (-not (Test-Path -LiteralPath $Python)) { Write-Error "Python missing: $Python"; exit 2 }
if (-not (Test-Path -LiteralPath $Release)) { Write-Error "Release missing: $Release"; exit 2 }

$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $repo
$env:PYTHONPATH = Join-Path $repo 'DEV_CORE'

# The source installer contains the ERROR_SERVICE_EXISTS -> ChangeServiceConfig
# fallback. The release itself remains immutable and is attested before SCM use.
$service = Get-Service -Name 'DevCoreIndividual' -ErrorAction Stop
$wasRunning = $service.Status -eq 'Running'
if ($wasRunning) {
    & sc.exe stop DevCoreIndividual | Out-Host
    $deadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $service.Refresh()
    } while ($service.Status -ne 'Stopped' -and (Get-Date) -lt $deadline)
    if ($service.Status -ne 'Stopped') {
        Write-Error 'DevCoreIndividual did not reach STOPPED before installation.'
        exit 1
    }
}
try {
    & $Python 'DEV_CORE/Scripts/install_individual_service.py' `
        --release $Release install --account '.\Administrateur' --start
    $code = $LASTEXITCODE
}
catch {
    $code = 1
    Write-Error $_
}
if ($code -ne 0 -and $wasRunning) {
    Write-Warning 'Installation failed; starting the previous SCM registration.'
    & sc.exe start DevCoreIndividual | Out-Host
}
exit $code
