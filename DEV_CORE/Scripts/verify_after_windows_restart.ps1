param(
    [string]$ExpectedHost = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261013-postgres-v250/pythonservice.exe'
)

$service = Get-Service -Name 'DevCoreIndividual' -ErrorAction Stop
if ($service.Status -ne 'Running') {
    Write-Error "DevCoreIndividual is $($service.Status), expected Running."
    exit 1
}
$config = sc.exe qc DevCoreIndividual | Out-String
if ($config -notmatch 'START_TYPE\s*:\s*2\s+AUTO_START') {
    Write-Error 'DevCoreIndividual is not configured for AUTO_START.'
    exit 1
}
$hostLine = ($config -split "`r?`n" | Where-Object { $_ -match 'BINARY_PATH_NAME\s*:' } | Select-Object -First 1)
$actualHost = if ($hostLine) { ($hostLine -replace '^.*BINARY_PATH_NAME\s*:\s*', '').Trim().Trim('"') } else { '' }
$expectedNormalized = [IO.Path]::GetFullPath($ExpectedHost)
if (-not $actualHost -or [IO.Path]::GetFullPath($actualHost) -ine $expectedNormalized) {
    Write-Error "Unexpected service host. Expected: $ExpectedHost"
    exit 1
}
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:20129/project' -TimeoutSec 15
} catch {
    Write-Error "Cockpit unavailable: $($_.Exception.Message)"
    exit 1
}
if ($response.StatusCode -ne 200) {
    Write-Error "Cockpit returned HTTP $($response.StatusCode), expected 200."
    exit 1
}
Write-Output ('restart_check=passed service=Running startup=Auto cockpit_http=' + $response.StatusCode)
