"""Rehearse a full PostgreSQL restore before installing project hook evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import unquote, urlparse
from uuid import uuid4

import pg8000.dbapi


PG_BIN = Path("C:/Program Files/PostgreSQL/17/bin")
DDL = Path(__file__).resolve().parents[1] / "devcore_engine/persistence/automation_hook_events.sql"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _options(config: Path, expected_database: str) -> dict:
    if not config.is_absolute() or not config.is_file():
        raise ValueError("Absolute installed configuration required")
    data = json.loads(config.read_text(encoding="utf-8"))
    parsed = urlparse(data.get("environment", {}).get("DEVCORE_DATABASE_URL", ""))
    if (parsed.scheme != "postgresql" or parsed.hostname != "127.0.0.1"
            or parsed.path.lstrip("/") != expected_database
            or parsed.username not in {"devcore_app", "devcore_app_qualification"}):
        raise ValueError("Expected local application database and role required")
    return {"user": unquote(parsed.username), "password": unquote(parsed.password or ""),
            "host": "127.0.0.1", "port": parsed.port or 5432,
            "database": expected_database}


def _ready(options: dict) -> bool:
    connection = pg8000.dbapi.connect(**options)
    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT c.relrowsecurity,c.relforcerowsecurity,
            has_table_privilege(current_user,c.oid,'SELECT,INSERT,UPDATE')
            FROM pg_class c WHERE c.oid=to_regclass('public.automation_hook_events')""")
        if tuple(cursor.fetchone() or ()) != (True, True, True):
            return False
        cursor.execute("""SELECT 1 FROM pg_policies WHERE schemaname='public'
            AND tablename='automation_hook_events'
            AND policyname='rls_automation_hook_events_project_isolation'""")
        return cursor.fetchone() is not None
    finally:
        connection.rollback()
        connection.close()


def _run(tool: str, args: list[str], env: dict, *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([str(PG_BIN / tool), *args], env=env, check=False,
                          capture_output=capture, text=capture, timeout=600)


def _restore_rehearsal(backup: Path, options: dict, admin_user: str, env: dict) -> str:
    temporary = "devcore_hook_restore_" + uuid4().hex[:16]
    common = ["-h", "127.0.0.1", "-p", str(options["port"]), "-U", admin_user, "-w"]
    created = _run("createdb.exe", [*common, temporary], env)
    if created.returncode:
        raise RuntimeError("Temporary restore database creation failed")
    try:
        restored = _run("pg_restore.exe", [*common, "--exit-on-error", "-d", temporary,
                                            str(backup)], env)
        if restored.returncode:
            raise RuntimeError("Full backup restore failed")
        rehearsal = _run("psql.exe", [*common, "-X", "-q", "-v", "ON_ERROR_STOP=1",
                                        "-d", temporary, "-f", str(DDL)], env)
        if rehearsal.returncode or not _ready({**options, "database": temporary}):
            raise RuntimeError("Hook DDL or application-role verification failed on restored database")
        return "restored_and_schema_verified"
    finally:
        dropped = _run("dropdb.exe", [*common, "--if-exists", temporary], env)
        if dropped.returncode:
            raise RuntimeError("Temporary restore database cleanup failed")


def apply(config: Path, backup_dir: Path, expected_database: str,
          *, admin_user: str, password: str) -> dict:
    if not backup_dir.is_absolute() or not backup_dir.is_dir():
        raise ValueError("Existing absolute private backup directory required")
    options = _options(config, expected_database)
    for name in ("pg_dump.exe", "pg_restore.exe", "psql.exe", "createdb.exe", "dropdb.exe"):
        if not (PG_BIN / name).is_file():
            raise ValueError("PostgreSQL utility missing: " + name)
    admin = pg8000.dbapi.connect(user=admin_user, password=password, host="127.0.0.1",
                                port=options["port"], database=expected_database)
    try:
        cursor = admin.cursor()
        cursor.execute("SELECT current_user,current_database(),rolsuper FROM pg_roles WHERE rolname=current_user")
        if tuple(cursor.fetchone()) != (admin_user, expected_database, True):
            raise ValueError("Expected PostgreSQL administrator identity required")
    finally:
        admin.rollback()
        admin.close()
    if _ready(options):
        return {"status": "automation_hook_schema_already_verified",
                "database": expected_database}
    ddl_sha256 = _sha(DDL)
    backup = backup_dir / ("before-automation-hooks-"
        + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-" + uuid4().hex[:8] + ".dump")
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    common = ["-h", "127.0.0.1", "-p", str(options["port"]), "-U", admin_user, "-w"]
    dumped = _run("pg_dump.exe", [*common, "-Fc", "-f", str(backup), expected_database], env)
    if dumped.returncode or not backup.is_file() or backup.stat().st_size == 0:
        raise RuntimeError("Full PostgreSQL backup failed; hook DDL was not applied")
    inventory = _run("pg_restore.exe", ["-l", str(backup)], env, capture=True)
    if inventory.returncode or "TABLE public projects " not in inventory.stdout:
        raise RuntimeError("Backup inventory lacks projects; hook DDL was not applied")
    restore = _restore_rehearsal(backup, options, admin_user, env)
    if _sha(DDL) != ddl_sha256:
        raise RuntimeError("Hook DDL changed after restore rehearsal")
    applied = _run("psql.exe", [*common, "-X", "-q", "-v", "ON_ERROR_STOP=1",
                                "-d", expected_database, "-f", str(DDL)], env)
    if applied.returncode or not _ready(options):
        raise RuntimeError("Hook DDL failed or application role cannot read it")
    return {"status": "automation_hook_schema_verified", "database": expected_database,
            "backup": str(backup), "backup_bytes": backup.stat().st_size,
            "backup_sha256": _sha(backup), "restore_rehearsal": restore,
            "ddl_sha256": ddl_sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    options = _options(args.config, args.expected_database)
    if _ready(options):
        print(json.dumps({"status": "automation_hook_schema_already_verified"}))
        return 0
    if not args.apply:
        print(json.dumps({"status": "automation_hook_schema_apply_ready",
                          "database": args.expected_database, "ddl_sha256": _sha(DDL)}))
        return 0
    password = getpass.getpass("Mot de passe administrateur PostgreSQL : ")
    try:
        print(json.dumps(apply(args.config, args.backup_dir, args.expected_database,
                               admin_user="postgres", password=password)))
    finally:
        del password
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
