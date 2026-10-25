"""Provision one real pilot user after a full PostgreSQL backup.

Run interactively from the pinned v251 Python. Passwords are read from the
console and are never accepted as arguments or written to a file.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pg8000.dbapi
from argon2 import PasswordHasher


DB_NAME = "devcore_qualification_team_20261013"
PG_BIN = Path("C:/Program Files/PostgreSQL/17/bin")
BACKUP_DIR = Path("E:/DevCoreRuntime/migration")
HOST = "127.0.0.1"
PORT = 5432


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True)
    parser.add_argument("--project", default="devcore")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", args.user):
        parser.error("user must be a simple lowercase identifier")
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", args.project):
        parser.error("project must be a simple lowercase identifier")
    if not BACKUP_DIR.is_dir():
        raise SystemExit("Private backup directory does not exist")
    for name in ("pg_dump.exe", "pg_restore.exe"):
        if not (PG_BIN / name).is_file():
            raise SystemExit(f"PostgreSQL tool missing: {name}")

    password = getpass.getpass(f"New password for {args.user} (12-256 characters): ")
    confirmation = getpass.getpass("Repeat new user password: ")
    if password != confirmation:
        raise SystemExit("Passwords differ; no backup or account change was made")
    if not 12 <= len(password) <= 256:
        raise SystemExit("Password must contain 12-256 characters; no backup or account change was made")
    password_hash = PasswordHasher().hash(password)
    del password, confirmation

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"before-pilot-user-{args.user}-{stamp}.dump"
    if backup.exists():
        raise SystemExit("Backup filename already exists")
    print("PostgreSQL administrator password for the full backup:", flush=True)
    dump = subprocess.run(
        [str(PG_BIN / "pg_dump.exe"), "-h", HOST, "-p", str(PORT),
         "-U", "postgres", "-W", "-F", "c", "-f", str(backup), DB_NAME],
        check=False,
    )
    if dump.returncode or not backup.is_file() or backup.stat().st_size == 0:
        raise SystemExit(f"Backup failed (exit {dump.returncode}); no account was changed")
    inventory = subprocess.run(
        [str(PG_BIN / "pg_restore.exe"), "-l", str(backup)],
        stdout=subprocess.DEVNULL, check=False,
    )
    if inventory.returncode:
        raise SystemExit("Backup inventory check failed; no account was changed")
    digest = hashlib.sha256()
    with backup.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    print(f"Backup verified: {backup} ({backup.stat().st_size} bytes, SHA-256 {digest.hexdigest()})")

    admin_password = getpass.getpass("PostgreSQL administrator password for provisioning: ")

    conn = pg8000.dbapi.connect(
        user="postgres", password=admin_password, host=HOST, port=PORT, database=DB_NAME,
    )
    del admin_password
    try:
        cur = conn.cursor()
        cur.execute("select id from projects where id=%s", (args.project,))
        if cur.fetchone() is None:
            raise RuntimeError("Project does not exist")
        cur.execute("select id from users where id=%s", (args.user,))
        if cur.fetchone() is not None:
            raise RuntimeError("User already exists; refusing to replace credentials or memberships")
        email = f"pilot-{args.user}@devcore.local"
        cur.execute("select id from users where email=%s", (email,))
        if cur.fetchone() is not None:
            raise RuntimeError("Provisioning email is already used")
        metadata = json.dumps({"source": "local_pilot_provisioning", "pilot": True})
        cur.execute(
            """insert into users (id,email,display_name,password_hash,status,metadata)
               values (%s,%s,%s,%s,'active',%s::jsonb)""",
            (args.user, email, args.user, password_hash, metadata),
        )
        cur.execute(
            """insert into project_memberships (id,project_id,user_id,role,metadata)
               values (%s,%s,%s,'contributor',%s::jsonb)""",
            (f"pilot-{uuid4()}", args.project, args.user, metadata),
        )
        conn.commit()
        cur.execute(
            """select u.status, u.password_hash is not null, m.role
               from users u join project_memberships m on m.user_id=u.id
               where u.id=%s and m.project_id=%s""",
            (args.user, args.project),
        )
        result = cur.fetchone()
        if result is None or tuple(result) != ("active", True, "contributor"):
            raise RuntimeError(f"Post-commit verification failed: {result!r}")
        print(json.dumps({"status": "pilot_user_provisioned", "user": args.user,
                          "project": args.project, "role": "contributor",
                          "backup": str(backup), "backup_sha256": digest.hexdigest()}))
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
