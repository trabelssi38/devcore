param(
    [string]$Release = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v251',
    [string]$PreviousRelease = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261013-postgres-v250',
    [string]$ServiceName = 'DevCoreIndividual'
)

$ErrorActionPreference = 'Stop'
$cutover = Join-Path $PSScriptRoot 'cutover_service_v250_elevated.ps1'
$oldBinary = (Resolve-Path -LiteralPath (Join-Path $PreviousRelease 'pythonservice.exe')).Path
$newBinary = (Resolve-Path -LiteralPath (Join-Path $Release 'pythonservice.exe')).Path
$wheel = Join-Path $Release 'artifacts/wheels/devcore_engine-10.2.0-py3-none-any.whl'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $wheel).Hash -ine '18ddf3e1ac443577e3f8eabd41acb35cad90a77d6d892e62a975b158760fb979') {
    throw 'v251 corrective wheel differs from the qualified candidate'
}
$current = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").PathName.Trim().Trim('"')
if ($current -ine $oldBinary) {
    throw "Expected $ServiceName on v250 before cutover; found $current"
}

$releasePath = (Resolve-Path -LiteralPath $Release).Path
$runtimeRoot = Split-Path -Parent (Split-Path -Parent $releasePath)
$config = Get-Content -Raw -LiteralPath (Join-Path $releasePath 'individual-service.json') | ConvertFrom-Json
$localRoot = Join-Path $runtimeRoot $config.local_relative
$dataRoot = Join-Path $runtimeRoot $config.data_relative
$launcher = Join-Path $releasePath 'controls/Scripts/launch_individual_candidate.py'
& (Join-Path $releasePath 'Scripts/python.exe') -I $launcher `
    --bundle (Join-Path $releasePath 'individual-platform-v2') `
    --manifest-sha256 $config.bundle_manifest_sha256 `
    --local-root $localRoot --data-root $dataRoot `
    --identity-store (Join-Path $localRoot 'Security/identity.db') `
    --port 20129 --check
if ($LASTEXITCODE -ne 0) { throw 'v251 candidate preflight failed before service cutover' }

& $cutover -Release $Release -ServiceName $ServiceName

function Get-HttpStatus([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        return [int]$response.StatusCode
    }
    catch {
        if ($null -eq $_.Exception.Response) { throw }
        return [int]$_.Exception.Response.StatusCode
    }
}

try {
    $expectations = @(
        @{ Url = 'http://127.0.0.1:20129/api/status'; Code = 200 },
        @{ Url = 'http://127.0.0.1:20129/project'; Code = 200 },
        @{ Url = 'http://127.0.0.1:20129/api/auth/session'; Code = 401 },
        @{ Url = 'http://127.0.0.1:20129/api/dashboard/tasks?project=devcore'; Code = 401 }
    )
    foreach ($check in $expectations) {
        $status = Get-HttpStatus $check.Url
        if ($status -ne $check.Code) {
            throw "Unexpected HTTP $status for $($check.Url); expected $($check.Code)"
        }
    }
    $actual = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").PathName.Trim().Trim('"')
    if ($actual -ine $newBinary -or (Get-Service $ServiceName).Status -ne 'Running') {
        throw 'Service did not remain on the v251 release in Running state'
    }
    [pscustomobject]@{
        status = 'v251_authfix_cutover_verified'
        service = $ServiceName
        binary = $newBinary
        anonymous_session_http = 401
        anonymous_tasks_http = 401
    } | ConvertTo-Json
}
catch {
    $failure = $_.Exception.Message
    Write-Warning "v251 post-cutover verification failed: $failure"
    & $cutover -Release $PreviousRelease -ServiceName $ServiceName
    throw "v251 verification failed; v250 rollback attempted: $failure"
}
