$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 required.' }
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator token required.'
}

$python = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261016-postgres-v254-restart/Scripts/python.exe'
$script = 'E:/src_python/devcore/DEV_CORE/Scripts/apply_automation_hook_events_schema.py'
$config = 'E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261016-postgres-v254-restart/individual-service.json'
$backupDir = 'E:/DevCoreRuntime/migration'
$report = 'E:/DevCoreRuntime/qualification/automation-hook-schema-cutover.json'

if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $script -PathType Leaf) -or
    -not (Test-Path -LiteralPath $config -PathType Leaf) -or
    -not (Test-Path -LiteralPath $backupDir -PathType Container)) {
    throw 'Pinned runtime, migration script, configuration or private backup directory missing.'
}
$resultLines = @(& $python $script --config $config --backup-dir $backupDir `
    --expected-database 'devcore_qualification_team_20261013' --apply)
if ($LASTEXITCODE -ne 0 -or $resultLines.Count -eq 0) {
    throw 'Automation hook schema migration failed.'
}
$result = $resultLines[-1] | ConvertFrom-Json
if ($result.status -notin @('automation_hook_schema_verified',
                           'automation_hook_schema_already_verified')) {
    throw 'Automation hook schema migration did not report a verified state.'
}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding utf8
$result | ConvertTo-Json -Depth 5
