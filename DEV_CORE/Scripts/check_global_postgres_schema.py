"""Read-only catalog gate for the operational PostgreSQL global stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.dbapi


RUN_COLUMNS = frozenset({
    "task_id", "title", "command", "timeout_seconds", "attempt_number",
    "max_attempts", "worker_token", "heartbeat_at", "cancellation_requested",
    "output", "error", "exit_code", "idempotency_key", "actor", "env",
    "execution_ready",
})
EXPECTED_POLICIES = {
    "runs": "rls_runs_project_isolation",
    "external_effects": "rls_external_effects_project_isolation",
    "schedules": "rls_schedules_project_isolation",
    "schedule_history": "rls_schedule_history_project_isolation",
}
EXPECTED_INDEXES = {"uq_runs_project_idempotency", "idx_runs_ready_project_status_created"}
PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")


def check(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_url = config.get("environment", {}).get("DEVCORE_DATABASE_URL", "")
    parsed = urlparse(raw_url)
    if parsed.scheme != "postgresql" or not parsed.username or not parsed.hostname:
        raise ValueError("PostgreSQL service URL missing or invalid")
    connection = pg8000.dbapi.connect(
        user=unquote(parsed.username), password=unquote(parsed.password or ""),
        host=parsed.hostname, port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
    )
    try:
        cur = connection.cursor()
        cur.execute("BEGIN READ ONLY")
        cur.execute("SELECT current_user,current_database(),r.rolsuper,r.rolbypassrls "
                    "FROM pg_roles r WHERE r.rolname=current_user")
        role, database, superuser, bypassrls = cur.fetchone()
        cur.execute("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname IN
            ('runs','external_effects','schedules','schedule_history')""")
        tables = {name: {"rls": rls, "force_rls": force} for name, rls, force in cur.fetchall()}
        cur.execute("""SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='runs'""")
        run_columns = {row[0] for row in cur.fetchall()}
        cur.execute("""SELECT tablename,policyname FROM pg_policies
            WHERE schemaname='public' AND tablename IN
            ('runs','external_effects','schedules','schedule_history')""")
        policies = {tuple(row) for row in cur.fetchall()}
        cur.execute("""SELECT indexname FROM pg_indexes WHERE schemaname='public'
            AND tablename='runs'""")
        indexes = {row[0] for row in cur.fetchall()}
        grants = {}
        for table in EXPECTED_POLICIES:
            if table not in tables:
                grants[table] = []
                continue
            grants[table] = []
            for privilege in PRIVILEGES:
                cur.execute("SELECT has_table_privilege(current_user,%s,%s)",
                            ("public." + table, privilege))
                if cur.fetchone()[0]:
                    grants[table].append(privilege)
        missing = []
        if superuser or bypassrls:
            missing.append("application_role_bypasses_rls")
        for table, policy in EXPECTED_POLICIES.items():
            flags = tables.get(table)
            if flags is None:
                missing.append(table + ":missing")
                continue
            if not flags["rls"] or not flags["force_rls"]:
                missing.append(table + ":force_rls_missing")
            if (table, policy) not in policies:
                missing.append(table + ":policy_missing")
            for privilege in PRIVILEGES:
                if privilege not in grants[table]:
                    missing.append(table + ":" + privilege.lower() + "_grant_missing")
        missing.extend("runs:" + name + "_column_missing" for name in sorted(RUN_COLUMNS - run_columns))
        missing.extend("runs:" + name + "_index_missing" for name in sorted(EXPECTED_INDEXES - indexes))
        return {"status": "global_schema_ready" if not missing else "global_schema_missing",
                "database": database, "application_role": role, "missing": missing,
                "privileges": grants}
    finally:
        connection.rollback()
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True,
                        help="Installed individual-service.json or isolated fixture config")
    args = parser.parse_args()
    try:
        result = check(args.config)
    except Exception:
        print(json.dumps({"status": "global_schema_check_failed"}))
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["status"] == "global_schema_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
