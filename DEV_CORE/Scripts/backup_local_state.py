"""Create and verify a local, read-only migration snapshot.

The SQLite online backup is consistent. Dropbox JSON files are copied with
per-file hashes; callers must stop other writers before using them for a final
migration. No secrets or JSON contents are printed in the summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.db import get_data_root, get_db_path  # noqa: E402


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def snapshot(destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"Snapshot destination exists: {destination}")
    db_path = get_db_path()
    memory_root = get_data_root() / "Memory"
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    if not memory_root.is_dir():
        raise FileNotFoundError(memory_root)

    destination.mkdir(parents=True)
    db_copy = destination / "devcore.db"
    source = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    backup = sqlite3.connect(db_copy)
    try:
        source.backup(backup)
        source_counts = {
            table: source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("projects", "tasks", "runs", "bus_events", "memory_entries")
        }
        integrity = backup.execute("PRAGMA integrity_check").fetchone()[0]
        restored_counts = {
            table: backup.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in source_counts
        }
        if integrity != "ok" or restored_counts != source_counts:
            raise RuntimeError("SQLite backup did not pass integrity and row-count checks")
    finally:
        source.close()
        backup.close()

    files = []
    memory_copy = destination / "Memory"
    for source_file in sorted(memory_root.rglob("*.json")):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(memory_root)
        target_file = memory_copy / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        original_hash = digest(source_file)
        copied_hash = digest(target_file)
        files.append({
            "path": relative.as_posix(),
            "bytes": target_file.stat().st_size,
            "sha256": copied_hash,
            "source_stable_during_copy": original_hash == copied_hash,
        })

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "sqlite": {"bytes": db_copy.stat().st_size, "sha256": digest(db_copy),
                   "integrity": integrity, "counts": restored_counts},
        "memory_json": files,
        "memory_json_count": len(files),
        "memory_json_bytes": sum(item["bytes"] for item in files),
        "memory_source_stable": all(item["source_stable_during_copy"] for item in files),
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"destination": str(destination), "sqlite": manifest["sqlite"],
            "memory_json_count": manifest["memory_json_count"],
            "memory_json_bytes": manifest["memory_json_bytes"],
            "memory_source_stable": manifest["memory_source_stable"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    print(json.dumps(snapshot(parser.parse_args().destination), indent=2))
