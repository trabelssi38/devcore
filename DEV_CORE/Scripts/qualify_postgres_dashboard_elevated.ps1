$ErrorActionPreference = 'Stop'
$hba = 'C:/Program Files/PostgreSQL/17/data/pg_hba.conf'
$backup = "$hba.codex-backup"
$psql = 'C:/Program Files/PostgreSQL/17/bin/psql.exe'
$adminSecret = [Convert]::ToBase64String((1..32 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 256) }))
$smokeToken = [Convert]::ToBase64String((1..32 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 256) }))
$sha = [Security.Cryptography.SHA256]::Create()
$tokenHash = ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($smokeToken)) | ForEach-Object { $_.ToString('x2') }) -join ''
$sha.Dispose()
$smokeUser = 'codex-smoke-' + ([guid]::NewGuid().ToString('N').Substring(0, 12))
$smokeMembership = 'pm-' + $smokeUser
$smokeSession = 'smoke-' + ([guid]::NewGuid().ToString('N'))
$db = 'devcore_qualification_team_20261013'
$now = [DateTime]::UtcNow.ToString('yyyy-MM-dd HH:mm:ss+00')
$expiry = [DateTime]::UtcNow.AddMinutes(10).ToString('yyyy-MM-dd HH:mm:ss+00')
Copy-Item -LiteralPath $hba -Destination $backup -Force
try {
  (Get-Content -LiteralPath $hba) | ForEach-Object { if ($_ -match '^\s*(local|host)\s+') { $_ -replace 'scram-sha-256','trust' } else { $_ } } | Set-Content -LiteralPath $hba -Encoding ASCII
  Restart-Service postgresql-x64-17 -Force
  Start-Sleep -Seconds 2
  & $psql -w -h 127.0.0.1 -U postgres -d postgres -c "ALTER ROLE postgres PASSWORD '$adminSecret';" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Unable to initialize local PostgreSQL administrator credential.' }
} finally {
  Copy-Item -LiteralPath $backup -Destination $hba -Force
  Restart-Service postgresql-x64-17 -Force
  Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
}
$env:PGPASSWORD = $adminSecret
$sql = "GRANT USAGE ON SCHEMA public TO devcore_app_qualification; GRANT SELECT ON projects,project_memberships,tasks TO devcore_app_qualification; GRANT UPDATE ON tasks TO devcore_app_qualification; GRANT SELECT,INSERT,UPDATE ON events,audit_log,sessions TO devcore_app_qualification; INSERT INTO users(id,email,display_name,status,metadata) VALUES ('$smokeUser','$smokeUser@local','Codex smoke','active','{}'::jsonb) ON CONFLICT DO NOTHING; INSERT INTO project_memberships(id,project_id,user_id,role) VALUES ('$smokeMembership','devcore','$smokeUser','owner') ON CONFLICT DO NOTHING; INSERT INTO sessions(id,user_id,token_hash,expires_at,metadata,created_at) VALUES ('$smokeSession','$smokeUser','$tokenHash','$expiry',json_build_object('projects',json_build_array('devcore'),'actions',json_build_array('task.read','task.mutate','context.read','task.audit.read'),'browser',false,'source','codex-smoke'),'$now') ON CONFLICT DO NOTHING;"
& $psql -w -h 127.0.0.1 -U postgres -d $db -v ON_ERROR_STOP=1 -c $sql | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL grants or smoke identity creation failed.' }
[pscustomobject]@{smoke_user=$smokeUser;token=$smokeToken} | ConvertTo-Json -Compress
