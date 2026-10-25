"""Reset a PostgreSQL pilot password without changing project roles.

Run interactively with the pinned release Python. Secrets are entered locally.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pg8000.dbapi
from argon2 import PasswordHasher


DB_NAME = "devcore_qualification_team_20261013"
PG_BIN = Path("C:/Program Files/PostgreSQL/17/bin")
BACKUP_DIR = Path("E:/DevCoreRuntime/migration")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", choices=("majdi", "mohd"), default="majdi")
    user = parser.parse_args().user
    if not BACKUP_DIR.is_dir():
        raise SystemExit("Private backup directory does not exist")
    if not all((PG_BIN / name).is_file() for name in ("pg_dump.exe", "pg_restore.exe")):
        raise SystemExit("PostgreSQL backup tools are missing")

    password = getpass.getpass(f"New password for {user} (12-256 characters): ")
    confirmation = getpass.getpass("Repeat new password: ")
    if password != confirmation:
        raise SystemExit("Passwords differ; no backup or account change was made")
    if not 12 <= len(password) <= 256:
        raise SystemExit("Password must contain 12-256 characters; no backup or account change was made")
    hasher = PasswordHasher()
    password_hash = hasher.hash(password)
    if not hasher.verify(password_hash, password):
        raise SystemExit("Password hash verification failed; no account change was made")
    del password, confirmation

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"before-password-reset-{user}-{stamp}.dump"
    if backup.exists():
        raise SystemExit("Backup filename already exists")
    print("PostgreSQL administrator password for the full backup:", flush=True)
    dump = subprocess.run(
        [str(PG_BIN / "pg_dump.exe"), "-h", "127.0.0.1", "-p", "5432",
         "-U", "postgres", "-W", "-F", "c", "-f", str(backup), DB_NAME],
        check=False,
    )
    if dump.returncode or not backup.is_file() or backup.stat().st_size == 0:
        raise SystemExit(f"Backup failed (exit {dump.returncode}); password was not changed")
    inventory = subprocess.run(
        [str(PG_BIN / "pg_restore.exe"), "-l", str(backup)],
        stdout=subprocess.DEVNULL, check=False,
    )
    if inventory.returncode:
        raise SystemExit("Backup inventory check failed; password was not changed")
    digest = hashlib.sha256()
    with backup.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    print(f"Backup verified: {backup} ({backup.stat().st_size} bytes, SHA-256 {digest.hexdigest()})")

    admin_password = getpass.getpass("PostgreSQL administrator password for reset: ")
    conn = pg8000.dbapi.connect(
        user="postgres", password=admin_password, host="127.0.0.1", port=5432,
        database=DB_NAME,
    )
    del admin_password
    try:
        cur = conn.cursor()
        cur.execute("select status from users where id=%s for update", (user,))
        row = cur.fetchone()
        if row is None or row[0] != "active":
            raise RuntimeError(f"Active {user} account not found; no password was changed")
        cur.execute("select count(*) from project_memberships where user_id=%s", (user,))
        memberships_before = cur.fetchone()[0]
        cur.execute(
            "update users set password_hash=%s, updated_at=now() where id=%s",
            (password_hash, user),
        )
        cur.execute(
            "update sessions set revoked_at=now() where user_id=%s and revoked_at is null",
            (user,),
        )
        revoked = cur.rowcount
        conn.commit()

        cur.execute("select status,password_hash from users where id=%s", (user,))
        after = cur.fetchone()
        cur.execute("select count(*) from project_memberships where user_id=%s", (user,))
        memberships_after = cur.fetchone()[0]
        cur.execute(
            "select count(*) from sessions where user_id=%s and revoked_at is null and expires_at>now()",
            (user,),
        )
        valid_sessions = cur.fetchone()[0]
        if (after is None or after[0] != "active" or after[1] != password_hash
                or memberships_after != memberships_before or valid_sessions != 0):
            raise RuntimeError("Post-commit verification failed; inspect database before retrying")
        print(json.dumps({"status": "password_reset_verified", "user": user,
                          "memberships_preserved": memberships_after,
                          "sessions_revoked": revoked,
                          "valid_sessions_after": valid_sessions,
                          "backup": str(backup), "backup_sha256": digest.hexdigest()}))
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
