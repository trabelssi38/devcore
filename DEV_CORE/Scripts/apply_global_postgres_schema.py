"""Back up a PostgreSQL database, then apply the attested global-stack DDL.

The administrator password is read from the local console, never from argv.
Without --apply this command performs only local file and target checks.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from uuid import uuid4

import pg8000.dbapi

from check_global_postgres_schema import check
from prepare_global_postgres_migration import assemble


PG_BIN = Path("C:/Program Files/PostgreSQL/17/bin")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _preflight(config_path: Path, ddl_path: Path, expected_database: str) -> tuple[str, int]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    parsed = urlparse(config.get("environment", {}).get("DEVCORE_DATABASE_URL", ""))
    if (parsed.scheme != "postgresql" or parsed.hostname != "127.0.0.1"
            or parsed.path.lstrip("/") != expected_database or not parsed.username):
        raise ValueError("Service database target differs from the expected loopback database")
    port = parsed.port or 5432
    if port < 1 or port > 65535:
        raise ValueError("Invalid PostgreSQL port")
    assembled, _ = assemble()
    if ddl_path.read_bytes() != assembled.encode("utf-8"):
        raise ValueError("DDL artifact differs from current migration sources")
    for name in ("pg_dump.exe", "pg_restore.exe", "psql.exe"):
        if not (PG_BIN / name).is_file():
            raise ValueError("PostgreSQL tool missing: " + name)
    return expected_database, port


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--ddl", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for path in (args.config, args.ddl, args.backup_dir):
        if not path.is_absolute():
            parser.error("All paths must be absolute")
    if not args.backup_dir.is_dir():
        parser.error("Backup directory does not exist")
    try:
        database, port = _preflight(args.config, args.ddl, args.expected_database)
        before = check(args.config)
    except Exception as exc:
        print(json.dumps({"status": "global_ddl_preflight_refused", "reason": str(exc)}))
        return 1
    summary = {"database": database, "port": port, "ddl_sha256": _sha256(args.ddl),
               "schema_before": before["status"]}
    if not args.apply:
        print(json.dumps({"status": "global_ddl_files_ready", **summary}))
        return 0
    if before["status"] == "global_schema_ready":
        print(json.dumps({"status": "global_schema_already_ready", **summary}))
        return 0

    password = getpass.getpass("PostgreSQL administrator password: ")
    try:
        connection = pg8000.dbapi.connect(user="postgres", password=password,
                                         host="127.0.0.1", port=port, database=database)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT current_user, current_database()")
            if tuple(cursor.fetchone()) != ("postgres", database):
                raise ValueError("Administrator connection identity mismatch")
        finally:
            connection.close()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup = args.backup_dir / f"before-global-stack-{stamp}-{uuid4().hex[:8]}.dump"
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        common = ["-h", "127.0.0.1", "-p", str(port), "-U", "postgres"]
        dump = subprocess.run([str(PG_BIN / "pg_dump.exe"), *common, "-w", "-F", "c",
                               "-f", str(backup), database], env=env, check=False)
        if dump.returncode or not backup.is_file() or backup.stat().st_size == 0:
            raise RuntimeError(f"Full backup failed (exit {dump.returncode}); DDL not applied")
        inventory = subprocess.run([str(PG_BIN / "pg_restore.exe"), "-l", str(backup)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, check=False)
        if inventory.returncode or not all(
                f"TABLE public {name} " in inventory.stdout
                for name in ("runs", "schedules", "schedule_history")):
            raise RuntimeError("Backup inventory check failed; DDL not applied")
        backup_info = {"path": str(backup), "bytes": backup.stat().st_size,
                       "sha256": _sha256(backup)}
        print(json.dumps({"status": "global_ddl_backup_verified", "backup": backup_info}), flush=True)
        applied = subprocess.run([str(PG_BIN / "psql.exe"), "-X", "-q", "-w", "-v",
                                  "ON_ERROR_STOP=1", *common, "-d", database,
                                  "-f", str(args.ddl)], env=env, check=False)
        if applied.returncode:
            raise RuntimeError(f"DDL failed (exit {applied.returncode}); inspect PostgreSQL state")
        after = check(args.config)
        if after["status"] != "global_schema_ready":
            raise RuntimeError("DDL committed but application schema gate failed: "
                               + ", ".join(after["missing"]))
        print(json.dumps({"status": "global_schema_applied_verified", **summary,
                          "backup": backup_info, "schema_after": after["status"]}))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "global_ddl_apply_failed", "reason": str(exc)}))
        return 1
    finally:
        del password


if __name__ == "__main__":
    raise SystemExit(main())
