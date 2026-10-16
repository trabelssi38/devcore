param(
    [string]$ConfigPath = 'C:/Program Files/PostgreSQL/17/data/postgresql.conf',
    [string]$PostgresService = 'postgresql-x64-17',
    [string]$DevCoreService = 'DevCoreIndividual'
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Run this hardening with elevated PowerShell 7 (pwsh).'
}
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this hardening with elevated PowerShell 7 (pwsh).'
}

$config = (Resolve-Path -LiteralPath $ConfigPath).Path
$expectedHash = 'FFF874182DD5FB4A1C5D133F0D2657D732C0CF87EDAE2FB0F10653E1EFB4649C'
if ((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash -ine $expectedHash) {
    throw 'PostgreSQL configuration changed since preflight; inspect before retrying.'
}
if ((Get-Service -Name $PostgresService).Status -ne 'Running' -or
    (Get-Service -Name $DevCoreService).Status -ne 'Running') {
    throw 'Both PostgreSQL and DevCore must be running before this maintenance.'
}

$raw = [System.IO.File]::ReadAllText($config)
$needle = "listen_addresses = '*'"
if ([regex]::Matches($raw, [regex]::Escape($needle)).Count -ne 1) {
    throw 'Expected exactly one wildcard listen_addresses setting.'
}
$updated = $raw.Replace($needle, "listen_addresses = 'localhost'")
$pgReady = 'C:/Program Files/PostgreSQL/17/bin/pg_isready.exe'
if (-not (Test-Path -LiteralPath $pgReady)) { throw 'pg_isready.exe is missing.' }
$backup = "$config.before-loopback-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
Copy-Item -LiteralPath $config -Destination $backup -ErrorAction Stop
if ((Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash -ine $expectedHash) {
    throw 'Backup hash mismatch; no service was changed.'
}

$changed = $false
try {
    Stop-Service -Name $DevCoreService -ErrorAction Stop
    (Get-Service -Name $DevCoreService).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(60))
    $changed = $true
    [System.IO.File]::WriteAllText($config, $updated, [System.Text.UTF8Encoding]::new($false))
    Restart-Service -Name $PostgresService -ErrorAction Stop
    (Get-Service -Name $PostgresService).WaitForStatus('Running', [TimeSpan]::FromSeconds(60))

    & $pgReady -h 127.0.0.1 -p 5432 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not answer on localhost.' }
    $listeners = @(Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction Stop)
    if ($listeners.Count -eq 0 -or
        @($listeners | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }).Count -gt 0) {
        throw 'PostgreSQL still has a non-loopback listener.'
    }

    Start-Service -Name $DevCoreService -ErrorAction Stop
    (Get-Service -Name $DevCoreService).WaitForStatus('Running', [TimeSpan]::FromSeconds(60))
    $probeOk = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $status = (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:20129/api/status' -TimeoutSec 3).StatusCode
            $project = (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:20129/project' -TimeoutSec 3).StatusCode
            if ($status -eq 200 -and $project -eq 200) { $probeOk = $true; break }
        }
        catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $probeOk) { throw 'DevCore HTTP probes did not recover.' }

    [pscustomobject]@{
        status = 'postgresql_loopback_verified'
        config = $config
        backup = $backup
        config_sha256 = (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash
        postgres_listeners = @($listeners | Select-Object -ExpandProperty LocalAddress)
        devcore_status_http = $status
        devcore_project_http = $project
    } | ConvertTo-Json -Depth 4
}
catch {
    $failure = $_.Exception.Message
    $rollbackErrors = @()
    if ($changed) {
        try {
            Copy-Item -LiteralPath $backup -Destination $config -Force -ErrorAction Stop
            Restart-Service -Name $PostgresService -ErrorAction Stop
            (Get-Service -Name $PostgresService).WaitForStatus('Running', [TimeSpan]::FromSeconds(60))
        }
        catch { $rollbackErrors += "PostgreSQL: $($_.Exception.Message)" }
    }
    try {
        if ((Get-Service -Name $DevCoreService).Status -ne 'Running') {
            Start-Service -Name $DevCoreService -ErrorAction Stop
            (Get-Service -Name $DevCoreService).WaitForStatus('Running', [TimeSpan]::FromSeconds(60))
        }
    }
    catch { $rollbackErrors += "DevCore: $($_.Exception.Message)" }
    $rollbackDetail = if ($rollbackErrors.Count) { $rollbackErrors -join '; ' } else { 'no rollback error' }
    throw "Loopback hardening failed; rollback attempted ($rollbackDetail): $failure"
}
