# test_qdrant_vector_contract.ps1 -- SQLite vec / vector contract test
$ErrorActionPreference = "Stop"

$dbPath = "C:\devcore\DEV_CORE_DATA\devcore.db"
if (-not (Test-Path $dbPath)) {
    throw "Unified devcore.db does not exist at $dbPath"
}

# Run quick check for vector module in SQLite with double quote escaping handled properly
$output = & "C:\Program Files\Python313\python.exe" -c "
import sqlite3
conn = sqlite3.connect(r'$dbPath')
cursor = conn.cursor()
tables = [r[0] for r in cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\'').fetchall()]
vec_ok = any(t.startswith('vec_') or 'vec' in t for t in tables)
print('OK' if vec_ok else 'FAIL')
conn.close()
"

if ($null -eq $output -or $output.Trim() -ne "OK") {
    throw "SQLite Vector DB unifiée has no vec0 / vec_ sémantique tables initialized. Output: $output"
}

Write-Host "[OK] SQLite Vector DB contract passed" -ForegroundColor Green
