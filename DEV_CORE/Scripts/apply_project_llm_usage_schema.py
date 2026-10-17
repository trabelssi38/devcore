"""Back up PostgreSQL and enable project-attributed Gemini usage storage."""

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
DDL = Path(__file__).resolve().parents[1] / (
    "devcore_engine/persistence/migrations/20261017_project_llm_usage.sql")
DDL_SHA256 = "cc4f824839b7421c3fa2a267c4303b006f97df6c2d7212b4ac44532e99c80661"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def connection_options(config: Path, expected_database: str) -> dict:
    settings = json.loads(config.read_text(encoding="utf-8"))
    parsed = urlparse(settings.get("environment", {}).get("DEVCORE_DATABASE_URL", ""))
    if (parsed.scheme != "postgresql" or parsed.hostname != "127.0.0.1"
            or parsed.path.lstrip("/") != expected_database or not parsed.username):
        raise ValueError("Installed loopback PostgreSQL target differs from expected database")
    return {"user": unquote(parsed.username), "password": unquote(parsed.password or ""),
            "host": "127.0.0.1", "port": parsed.port or 5432,
            "database": expected_database}


def ready(options: dict) -> bool:
    db = pg8000.dbapi.connect(**options)
    try:
        cur = db.cursor()
        cur.execute("""SELECT c.relrowsecurity,c.relforcerowsecurity,
            has_table_privilege(current_user,c.oid,'SELECT'),
            has_table_privilege(current_user,c.oid,'INSERT')
            FROM pg_class c WHERE c.oid=to_regclass('public.project_llm_usage')""")
        row = cur.fetchone()
        if row is None or tuple(row) != (True, True, True, True):
            return False
        cur.execute("SELECT count(*) FROM project_llm_usage")
        return cur.fetchone()[0] == 0
    finally:
        db.rollback()
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if not args.config.is_absolute() or not args.backup_dir.is_absolute():
            raise ValueError("Configuration and backup directory must be absolute")
        if not args.backup_dir.is_dir() or sha256(DDL) != DDL_SHA256:
            raise ValueError("Backup directory missing or usage DDL differs from qualified source")
        options = connection_options(args.config, args.expected_database)
        for name in ("pg_dump.exe", "pg_restore.exe", "psql.exe"):
            if not (PG_BIN / name).is_file():
                raise ValueError("PostgreSQL utility missing: " + name)
        if ready(options):
            print(json.dumps({"status": "project_llm_usage_schema_verified",
                              "database": args.expected_database}))
            return 0
        if not args.apply:
            print(json.dumps({"status": "project_llm_usage_apply_ready",
                              "database": args.expected_database,
                              "ddl_sha256": DDL_SHA256}))
            return 0
        password = getpass.getpass("PostgreSQL administrator password: ")
        try:
            admin = pg8000.dbapi.connect(user="postgres", password=password,
                                        host="127.0.0.1", port=options["port"],
                                        database=args.expected_database)
            try:
                cur = admin.cursor()
                cur.execute("SELECT current_user,current_database()")
                if tuple(cur.fetchone()) != ("postgres", args.expected_database):
                    raise ValueError("Administrator connection identity mismatch")
            finally:
                admin.close()
            backup = args.backup_dir / ("before-project-llm-usage-" +
                datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") +
                "-" + uuid4().hex[:8] + ".dump")
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            common = ["-h", "127.0.0.1", "-p", str(options["port"]), "-U", "postgres"]
            dump = subprocess.run([str(PG_BIN / "pg_dump.exe"), *common, "-w", "-F",
                                   "c", "-f", str(backup), args.expected_database],
                                  env=env, check=False)
            if dump.returncode or not backup.is_file() or backup.stat().st_size == 0:
                raise RuntimeError("Full PostgreSQL backup failed; DDL not applied")
            inventory = subprocess.run([str(PG_BIN / "pg_restore.exe"), "-l", str(backup)],
                                       capture_output=True, text=True, check=False)
            if inventory.returncode or "TABLE public projects " not in inventory.stdout:
                raise RuntimeError("Backup inventory misses projects; DDL not applied")
            backup_info = {"path": str(backup), "bytes": backup.stat().st_size,
                           "sha256": sha256(backup)}
            print(json.dumps({"status": "project_llm_usage_backup_verified",
                              "backup": backup_info}), flush=True)
            if sha256(DDL) != DDL_SHA256:
                raise RuntimeError("Usage DDL changed after backup")
            applied = subprocess.run([str(PG_BIN / "psql.exe"), "-X", "-q", "-w",
                                      "-v", "ON_ERROR_STOP=1", *common, "-d",
                                      args.expected_database, "-f", str(DDL)],
                                     env=env, check=False)
            if applied.returncode or not ready(options):
                raise RuntimeError("Usage DDL failed or application RLS check failed")
            print(json.dumps({"status": "project_llm_usage_schema_applied_verified",
                              "database": args.expected_database, "backup": backup_info}))
            return 0
        finally:
            del password
    except Exception as exc:
        print(json.dumps({"status": "project_llm_usage_refused", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
