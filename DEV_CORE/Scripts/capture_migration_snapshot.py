"""Capture an immutable migration snapshot with pre/post mutation detection."""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def files_under(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink() and not path.is_junction()
            and ".guard" not in path.name and path.parent.name != "Runtime"
            and not path.name.endswith(("-wal", "-shm"))]


def copy_sqlite(source: Path, target: Path, *, allow_foreign_keys: bool = False) -> dict:
    if (sidecar := source.with_name(source.name + "-wal")).is_file() and sidecar.stat().st_size:
        raise RuntimeError(f"SQLite sidecar present; capture requires a stable source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(target)) as copy:
            origin.backup(copy)
            integrity = copy.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = len(copy.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or (foreign_keys and not allow_foreign_keys):
        raise RuntimeError(f"SQLite integrity failure: {source}")
    return {"bytes": target.stat().st_size, "sha256": digest(target),
            "integrity": integrity, "foreign_key_violations": foreign_keys,
            "foreign_key_violations_allowed": allow_foreign_keys}


def capture(source_local: Path, source_data: Path, output: Path,
            exclude_sqlite: set[str] | None = None,
            allow_foreign_keys: bool = False) -> dict:
    source_local = source_local.resolve(strict=True)
    source_data = source_data.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if source_local == output or output.is_relative_to(source_local) or output.is_relative_to(source_data):
        raise ValueError("output must be outside source roots")
    local_files_before = {p.relative_to(source_local).as_posix(): digest(p) for p in files_under(source_local)}
    data_files_before = {p.relative_to(source_data).as_posix(): digest(p) for p in files_under(source_data)}
    output.mkdir(parents=True)
    exclude_sqlite = exclude_sqlite or set()
    sqlite_manifest = {}
    excluded_sqlite = []
    for source in sorted(source_local.rglob("*.db")):
        relative = source.relative_to(source_local)
        if relative.as_posix() in exclude_sqlite:
            excluded_sqlite.append(relative.as_posix())
            continue
        sqlite_manifest[relative.as_posix()] = copy_sqlite(
            source, output / "local" / relative, allow_foreign_keys=allow_foreign_keys)
    local_files = []
    for source in files_under(source_local):
        if source.suffix == ".db":
            continue
        relative = source.relative_to(source_local)
        target = output / "local" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_hash = digest(target)
        if copied_hash != local_files_before[relative.as_posix()]:
            raise RuntimeError(f"Local file copy mismatch: {relative}")
        local_files.append({"path": relative.as_posix(), "bytes": target.stat().st_size,
                            "sha256": copied_hash})
    copied_files = []
    for source in files_under(source_data):
        relative = source.relative_to(source_data)
        target = output / "data" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_hash = digest(target)
        if copied_hash != data_files_before[relative.as_posix()]:
            raise RuntimeError(f"Data file copy mismatch: {relative}")
        copied_files.append({"path": relative.as_posix(), "bytes": target.stat().st_size,
                             "sha256": copied_hash})
    local_files_after = {p.relative_to(source_local).as_posix(): digest(p) for p in files_under(source_local)}
    data_files_after = {p.relative_to(source_data).as_posix(): digest(p) for p in files_under(source_data)}
    if local_files_before != local_files_after or data_files_before != data_files_after:
        raise RuntimeError("source mutated during capture; snapshot is invalid")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_local": str(source_local), "source_data": str(source_data),
        "output": str(output), "source_stable": True,
        "sqlite": sqlite_manifest, "local_files": local_files, "data_files": copied_files,
        "excluded_sqlite": excluded_sqlite,
        "foreign_key_violations_allowed": allow_foreign_keys,
        "source_file_count": len(local_files_before) + len(data_files_before),
        "output_file_count": sum(1 for _ in files_under(output)),
        "ready_for_cutover": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-local", type=Path, required=True)
    parser.add_argument("--source-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude-sqlite", action="append", default=[],
                        help="relative SQLite path to record but exclude from the capture")
    parser.add_argument("--allow-foreign-key-violations", action="store_true",
                        help="capture historical databases while recording FK violations")
    args = parser.parse_args()
    print(json.dumps(capture(args.source_local, args.source_data, args.output,
                             set(args.exclude_sqlite), args.allow_foreign_key_violations), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
