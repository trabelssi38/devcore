"""Back up and scope the verified historical PostgreSQL graph.

Default mode is read only. --apply prompts locally for the PostgreSQL
administrator password, verifies a complete dump, then applies the DDL.
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
from urllib.parse import unquote, urlparse
from uuid import uuid4

import pg8000.dbapi

from audit_postgres_graph_scope import audit


PG_BIN = Path("C:/Program Files/PostgreSQL/17/bin")
DDL = Path(__file__).resolve().parents[1] / (
    "devcore_engine/persistence/migrations/20261017_legacy_graph_scope.sql")
DDL_SHA256 = "397fa0cc0a25fbf46bbedd12e7b5a8fe47586ab39b7619be28977e2594b5989c"
EXPECTED = {"kg_nodes": 2272, "kg_edges": 696267,
            "same_project_edges": 681642, "cross_project_edges_for_quarantine": 14625}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def app_counts(config: Path) -> dict[str, tuple[int, int, int]]:
    data = json.loads(config.read_text(encoding="utf-8"))
    parsed = urlparse(data.get("environment", {}).get("DEVCORE_DATABASE_URL", ""))
    db = pg8000.dbapi.connect(user=unquote(parsed.username or ""),
                              password=unquote(parsed.password or ""),
                              host="127.0.0.1", port=parsed.port or 5432,
                              database=parsed.path.lstrip("/"))
    try:
        counts = {}
        for project in (None, "devcore", "scripts"):
            cur = db.cursor()
            if project:
                cur.execute("SELECT set_config('app.current_project_id', %s, true)", (project,))
            values = []
            for table in ("legacy_kg_nodes", "legacy_kg_edges", "project_graph_stats"):
                cur.execute(f"SELECT count(*) FROM {table}")
                values.append(cur.fetchone()[0])
            counts[project or "no_project"] = tuple(values)
            db.rollback()
        return counts
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if not all(path.is_absolute() for path in
                   (args.candidate, args.config, args.backup_dir)):
            raise ValueError("All paths must be absolute")
        if not args.backup_dir.is_dir():
            raise ValueError("Backup directory missing")
        if sha256(DDL) != DDL_SHA256:
            raise ValueError("Graph DDL hash differs from qualified source")
        source = audit(args.candidate, args.config)
        if source["database"] != args.expected_database:
            raise ValueError("PostgreSQL database identity differs from expected")
        for key, expected in EXPECTED.items():
            actual = source[key]["rows"] if key.startswith("kg_") else source[key]
            if actual != expected:
                raise ValueError(f"Graph {key} count differs from qualified source")
        for name in ("pg_dump.exe", "pg_restore.exe", "psql.exe"):
            if not (PG_BIN / name).is_file():
                raise ValueError("PostgreSQL utility missing: " + name)
        summary = {"database": source["database"], "ddl_sha256": DDL_SHA256,
                   "nodes": EXPECTED["kg_nodes"], "edges": EXPECTED["kg_edges"],
                   "readable_edges": EXPECTED["same_project_edges"],
                   "quarantined_edges": EXPECTED["cross_project_edges_for_quarantine"]}
        try:
            current = app_counts(args.config)
        except pg8000.dbapi.DatabaseError:
            current = None
        if current is not None:
            if current != {"no_project": (0, 0, 0), "devcore": (2268, 681642, 1),
                           "scripts": (1, 0, 1)}:
                raise ValueError("Existing graph scope differs from qualified counts")
            print(json.dumps({"status": "graph_scope_already_verified", **summary}))
            return 0
        if not args.apply:
            print(json.dumps({"status": "graph_scope_apply_ready", **summary}))
            return 0
        password = getpass.getpass("PostgreSQL administrator password: ")
        try:
            parsed = urlparse(json.loads(args.config.read_text(encoding="utf-8"))
                              ["environment"]["DEVCORE_DATABASE_URL"])
            port = parsed.port or 5432
            admin = pg8000.dbapi.connect(user="postgres", password=password,
                                        host="127.0.0.1", port=port,
                                        database=args.expected_database)
            try:
                cur = admin.cursor()
                cur.execute("SELECT current_user,current_database()")
                if tuple(cur.fetchone()) != ("postgres", args.expected_database):
                    raise ValueError("Administrator connection identity mismatch")
            finally:
                admin.close()
            backup = args.backup_dir / ("before-graph-scope-" +
                datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") +
                "-" + uuid4().hex[:8] + ".dump")
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            common = ["-h", "127.0.0.1", "-p", str(port), "-U", "postgres"]
            dump = subprocess.run([str(PG_BIN / "pg_dump.exe"), *common,
                                   "-w", "-F", "c", "-f", str(backup),
                                   args.expected_database], env=env, check=False)
            if dump.returncode or not backup.is_file() or backup.stat().st_size == 0:
                raise RuntimeError("Full PostgreSQL backup failed; DDL not applied")
            inventory = subprocess.run([str(PG_BIN / "pg_restore.exe"), "-l", str(backup)],
                                       capture_output=True, text=True, check=False)
            if inventory.returncode or not all(
                    f"TABLE public {name} " in inventory.stdout
                    for name in ("legacy_kg_nodes", "legacy_kg_edges", "projects")):
                raise RuntimeError("Backup inventory misses graph tables; DDL not applied")
            backup_info = {"path": str(backup), "bytes": backup.stat().st_size,
                           "sha256": sha256(backup)}
            print(json.dumps({"status": "graph_scope_backup_verified",
                              "backup": backup_info}), flush=True)
            if sha256(DDL) != DDL_SHA256:
                raise RuntimeError("Graph DDL changed after backup")
            applied = subprocess.run([str(PG_BIN / "psql.exe"), "-X", "-q", "-w",
                                      "-v", "ON_ERROR_STOP=1", *common, "-d",
                                      args.expected_database, "-f", str(DDL)],
                                     env=env, check=False)
            if applied.returncode:
                raise RuntimeError(f"Graph DDL failed (exit {applied.returncode})")
            counts = app_counts(args.config)
            if counts != {"no_project": (0, 0, 0),
                          "devcore": (2268, 681642, 1), "scripts": (1, 0, 1)}:
                raise RuntimeError("Graph DDL committed but project RLS verification failed")
            print(json.dumps({"status": "graph_scope_applied_verified", **summary,
                              "backup": backup_info, "rls_counts": counts}))
            return 0
        finally:
            del password
    except Exception as exc:
        print(json.dumps({"status": "graph_scope_refused", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
