"""Import the local identity database into the PostgreSQL qualification target.

The import is deliberately qualification-only: imported sessions are revoked,
and every row carries source provenance. The active service is never changed.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import psycopg


def utc_epoch(value: float | None) -> datetime | None:
    return None if value is None else datetime.fromtimestamp(float(value), tz=timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = sqlite3.connect(f"file:{args.source}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    target = psycopg.connect(args.dsn)
    counts = {"users": 0, "memberships": 0, "sessions": 0, "passwords": 0}
    unmapped_projects: list[str] = []
    now = datetime.now(timezone.utc)
    try:
        with target.cursor() as cur:
            users = source.execute("select id, enabled from identity_users").fetchall()
            for row in users:
                uid = str(row["id"])
                password = source.execute(
                    "select password_hash from identity_passwords where user_id = ?", (uid,)
                ).fetchone()
                metadata = {
                    "source": "identity.db",
                    "source_user_id": uid,
                    "migration": "qualification",
                    "enabled_in_source": bool(row["enabled"]),
                }
                cur.execute(
                    """insert into users (id,email,display_name,password_hash,status,metadata,created_at,updated_at)
                       values (%s,%s,%s,%s,%s,%s,%s,%s)
                       on conflict (id) do update set email=excluded.email,
                         display_name=excluded.display_name,password_hash=excluded.password_hash,
                         status=excluded.status,metadata=excluded.metadata,updated_at=excluded.updated_at""",
                    (
                        uid,
                        f"identity-{uid}@devcore.local",
                        uid,
                        password["password_hash"] if password else None,
                        "active" if row["enabled"] else "disabled",
                        json.dumps(metadata),
                        now,
                        now,
                    ),
                )
                counts["users"] += 1
                if password:
                    counts["passwords"] += 1

            projects = {
                r[0] for r in cur.execute("select id from projects").fetchall()
            }
            for row in source.execute("select user_id,project_id,role from identity_memberships"):
                pid = str(row["project_id"])
                if pid not in projects:
                    unmapped_projects.append(pid)
                    continue
                membership_id = f"identity-{row['user_id']}-{pid}"
                cur.execute(
                    """insert into project_memberships
                       (id,project_id,user_id,role,metadata,created_at,updated_at)
                       values (%s,%s,%s,%s,%s,%s,%s)
                       on conflict (id) do update set role=excluded.role,
                         metadata=excluded.metadata,updated_at=excluded.updated_at""",
                    (
                        membership_id,
                        pid,
                        str(row["user_id"]),
                        str(row["role"]),
                        json.dumps({"source": "identity.db", "migration": "qualification"}),
                        now,
                        now,
                    ),
                )
                counts["memberships"] += 1

            for row in source.execute(
                "select id,user_id,token_hash,expires_at,revoked,projects,actions from identity_credentials"
            ):
                # Credentials are retained for audit, but cannot authenticate in qualification.
                sid = f"identity-credential-{row['id']}"
                cur.execute(
                    """insert into sessions
                       (id,user_id,token_hash,csrf_token_hash,expires_at,revoked_at,metadata,created_at)
                       values (%s,%s,%s,%s,%s,%s,%s,%s)
                       on conflict (id) do update set revoked_at=excluded.revoked_at,
                         metadata=excluded.metadata""",
                    (
                        sid,
                        str(row["user_id"]),
                        str(row["token_hash"]),
                        None,
                        utc_epoch(row["expires_at"]) or now,
                        now,
                        json.dumps(
                            {
                                "source": "identity.db",
                                "source_credential_id": row["id"],
                                "source_revoked": bool(row["revoked"]),
                                "projects": json.loads(row["projects"]),
                                "actions": json.loads(row["actions"]),
                                "migration": "qualification",
                                "forced_revoked": True,
                            }
                        ),
                        utc_epoch(row["expires_at"]) or now,
                    ),
                )
                counts["sessions"] += 1
            target.commit()
    finally:
        source.close()
        target.close()

    report = {
        "status": "identity_imported_sessions_revoked",
        "source": str(args.source),
        "target": "postgresql qualification database",
        "counts": counts,
        "unmapped_projects": sorted(set(unmapped_projects)),
        "active_service_modified": False,
        "blockers": [
            "active_service_identity_still_uses_sqlite",
            "operational_cutover_deferred",
        ],
        "limitations": [
            "browser sessions and admin credentials remain in the source-only audit scope",
            "imported PostgreSQL sessions are forced revoked until an approved cutover",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
