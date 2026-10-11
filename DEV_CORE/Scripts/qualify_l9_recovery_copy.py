"""Measure backup and restore of an L9 qualification copy, never active roots."""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time


DATABASES = ("devcore.db", "runs/runs.db")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(path: Path) -> dict:
    with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        if integrity != "ok" or violations:
            raise RuntimeError(f"Invalid SQLite copy: {path}")
        return {"integrity": integrity, "foreign_key_violations": violations,
                "bytes": path.stat().st_size}


def copy_database(source: Path, target: Path) -> float:
    target.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(target)) as copy:
            original.backup(copy)
    inspect(target)
    return round(time.monotonic() - start, 3)


def qualify(qualification_root: Path, source_root: Path, output_root: Path) -> dict:
    overall_start = time.monotonic()
    qualification_root = qualification_root.resolve(strict=True)
    source_root = source_root.resolve(strict=True)
    output_root = output_root.resolve()
    if (not source_root.is_relative_to(qualification_root)
            or output_root.parent != qualification_root or output_root.exists()
            or source_root == output_root):
        raise ValueError("Source and new output must be inside the qualification root")
    source_local = source_root / "local"
    for name in DATABASES + ("Security/identity.db",):
        path = source_local / name
        if not path.is_file() or path.is_symlink() or path.is_junction():
            raise ValueError(f"Missing or linked qualification source: {name}")
    source_hashes = {name: digest(source_local / name) for name in DATABASES}
    source_checks = {name: inspect(source_local / name) for name in DATABASES}

    # Set roots before importing engine security helpers, which inspect them.
    os.environ.update({"DEVCORE_LOCAL_ROOT": str(source_local),
                       "DEVCORE_DATA_ROOT": str(source_root / "data")})
    from devcore_engine.security.identity_backup import (
        backup_identity_store, restore_identity_store,
    )
    from devcore_engine.security.private_store import check_store_protection

    identity_source = source_local / "Security/identity.db"
    check_store_protection(identity_source)
    identity_source_hash = digest(identity_source)
    output_root.mkdir()
    archive = output_root / "archive"
    restored = output_root / "restored"
    (archive / "Security").mkdir(parents=True)
    (restored / "local/Security").mkdir(parents=True)
    (restored / "data").mkdir()
    backups = {}
    for name in DATABASES:
        target = archive / name
        seconds = copy_database(source_local / name, target)
        backups[name] = {"seconds": seconds, "sha256": digest(target), **inspect(target)}
    start = time.monotonic()
    identity_archive = backup_identity_store(identity_source, archive / "Security/identity.db")
    backups["Security/identity.db"] = {
        "seconds": round(time.monotonic() - start, 3),
        "sha256": identity_archive["sha256"],
        **inspect(archive / "Security/identity.db"),
    }
    restores = {}
    for name in DATABASES:
        target = restored / "local" / name
        seconds = copy_database(archive / name, target)
        restores[name] = {"seconds": seconds, **inspect(target)}
        if digest(target) != backups[name]["sha256"]:
            raise RuntimeError(f"Restored database hash differs: {name}")
    start = time.monotonic()
    restored_identity = restored / "local/Security/identity.db"
    restore_identity_store(archive / "Security/identity.db", restored_identity,
                           identity_archive["sha256"])
    restores["Security/identity.db"] = {
        "seconds": round(time.monotonic() - start, 3), **inspect(restored_identity),
    }
    with closing(sqlite3.connect(f"{restored_identity.as_uri()}?mode=ro", uri=True)) as conn:
        revoked = {table: conn.execute(f"SELECT count(*) FROM {table} WHERE revoked=0").fetchone()[0]
                   for table in ("identity_credentials", "identity_admin_credentials",
                                 "identity_browser_sessions")}
        enabled_users = conn.execute("SELECT count(*) FROM identity_users WHERE enabled=1").fetchone()[0]
    if enabled_users or any(revoked.values()):
        raise RuntimeError("Restored identity left active access")
    if {name: digest(source_local / name) for name in DATABASES} != source_hashes:
        raise RuntimeError("Qualification source changed during rehearsal")
    if digest(identity_source) != identity_source_hash:
        raise RuntimeError("Identity source changed during rehearsal")
    total_bytes = sum(row["bytes"] for row in backups.values())
    report = {
        "qualification_source": str(source_root), "output": str(output_root),
        "source_checks": source_checks, "backups": backups, "restores": restores,
        "backup_seconds": round(sum(row["seconds"] for row in backups.values()), 3),
        "restore_seconds": round(sum(row["seconds"] for row in restores.values()), 3),
        "total_seconds": round(time.monotonic() - overall_start, 3),
        "one_backup_bytes": total_bytes, "eleven_backups_bytes": total_bytes * 11,
        "restored_enabled_users": enabled_users, "restored_active_capabilities": revoked,
        "source_hashes_unchanged": True, "operationally_qualified": False,
    }
    (output_root / "qualification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.qualification_root, args.source, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
