"""Inspect the actual SCM host and PostgreSQL evidence before cutover."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psycopg


def verify(database: str, password: str, api_source: Path, service_data: Path,
           output: Path, identity_report: Path | None = None,
           identity_api_source: Path | None = None,
           service_release: Path | None = None) -> dict:
    with psycopg.connect(host="127.0.0.1", port=5432, user="postgres",
                         password=password, dbname=database) as db:
        with db.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_policies WHERE schemaname='public'")
            policies = cur.fetchone()[0]
            cur.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname='devcore_app_qualification'")
            role = cur.fetchone()
            bypass = None if role is None else role[0]
            counts = {}
            for table in ("projects", "tasks", "events", "runs", "users", "sessions"):
                cur.execute(f'SELECT count(*) FROM "{table}"')
                counts[table] = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM sessions WHERE revoked_at IS NULL AND expires_at > now()")
            usable_sessions = cur.fetchone()[0]

    blockers = []
    if policies < 7 or bypass is not False:
        blockers.append("rls_role_or_policies_invalid")
    api_text = api_source.read_text(encoding="utf-8")
    api_read_adapter = "PostgresTaskRepository" in api_text
    if not api_read_adapter:
        blockers.append("api_postgres_read_adapter_missing")
    identity_api_configured = bool(identity_api_source and identity_api_source.exists()
                                   and "PostgresIdentityProvider" in identity_api_source.read_text(encoding="utf-8"))
    if not identity_api_configured:
        blockers.append("api_identity_adapter_missing")

    identity_status = None
    if identity_report and identity_report.exists():
        identity_status = json.loads(identity_report.read_text(encoding="utf-8")).get("status")
    if identity_status != "identity_imported_sessions_revoked":
        blockers.append("identity_qualification_evidence_missing")

    dashboard_source = (service_release / "individual-platform-v2" / "Scripts" / "dashboard_api.py"
                        if service_release else None)
    dashboard_text = dashboard_source.read_text(encoding="utf-8") if dashboard_source and dashboard_source.is_file() else ""
    dashboard_postgres_routes = all(marker in dashboard_text for marker in (
        "POSTGRES_DASHBOARD", "_postgres_task_mutation", "_postgres_task_audit",
        "load_project_context", "postgres_browser_sessions"))
    dashboard_sqlite = bool(dashboard_text and not dashboard_postgres_routes and
                            "SqliteIdentityProvider" in dashboard_text and
                            'get_local_path("devcore.db")' in dashboard_text)
    if dashboard_source is None or not dashboard_source.is_file():
        blockers.append("staged_scm_host_not_inspected")
    elif dashboard_sqlite:
        blockers.append("staged_scm_host_still_uses_sqlite_dashboard")
    elif not dashboard_postgres_routes:
        blockers.append("staged_dashboard_postgres_routes_missing")
    else:
        smoke_marker = service_release / "postgres-dashboard-qualified.json"
        if not smoke_marker.is_file():
            blockers.append("staged_dashboard_authenticated_smoke_missing")

    active_binary = None
    try:
        scm = subprocess.run(["sc.exe", "qc", "DevCoreIndividual"], capture_output=True,
                             text=True, errors="replace", timeout=10, check=True)
        for line in scm.stdout.splitlines():
            if "BINARY_PATH_NAME" in line:
                active_binary = line.partition(":")[2].strip().strip('"')
                break
    except (OSError, subprocess.SubprocessError):
        pass
    if active_binary is None:
        blockers.append("active_service_registration_unavailable")
    elif service_release is None or Path(active_binary).resolve() != (service_release / "pythonservice.exe").resolve():
        blockers.append("active_service_not_switched_to_staged_release")

    # Archived SQLite files can remain after a valid migration; their mere
    # existence is not evidence that they are still the active source. The
    # operational gate is therefore derived from the active SCM registration
    # and the staged Dashboard qualification above, rather than asserted here.
    result = {
        "report_version": 5,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pre_cutover_blocked" if blockers else "ready_for_cutover",
        "ready_for_cutover": not blockers,
        "database": database,
        "postgresql": {"policies": policies, "app_role_bypassrls": bypass,
                        **counts, "usable_sessions": usable_sessions},
        "identity": {"status": identity_status, "api_adapter_configured": identity_api_configured},
        "service": {"active_binary": active_binary,
                    "staged_release": str(service_release.resolve()) if service_release else None,
                    "dashboard_sqlite": dashboard_sqlite},
        "blockers": blockers,
        "evidence": {"api_source": str(api_source.resolve()),
                     "identity_api_source": str(identity_api_source.resolve()) if identity_api_source else None,
                     "active_sqlite_archive": str(service_data.resolve()) if service_data.exists() else None,
                     "identity_report": str(identity_report.resolve()) if identity_report else None,
                     "dashboard_source": str(dashboard_source.resolve()) if dashboard_source else None},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--api-source", type=Path, required=True)
    parser.add_argument("--service-data", type=Path, required=True)
    parser.add_argument("--identity-report", type=Path)
    parser.add_argument("--identity-api-source", type=Path)
    parser.add_argument("--service-release", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.database, args.password, args.api_source, args.service_data,
           args.output, args.identity_report, args.identity_api_source,
           args.service_release)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
