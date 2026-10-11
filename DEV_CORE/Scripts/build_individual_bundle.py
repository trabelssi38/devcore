"""Create/verify a source snapshot for the individual profile; never deploy it.

Only explicitly listed files are copied. Identity stores, project context,
configuration, legacy handlers and live data are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

FILES = (
    "Scripts/dashboard_api.py", "Dashboard/project.html", "Dashboard/project_tasks.js",
    "Scripts/dashboard/__init__.py", "Scripts/dashboard/snapshots.py",
    "Scripts/dashboard/publication.py", "Scripts/dashboard/generation_lock.py",
    "Scripts/dashboard/refresh_coordinator.py", "Scripts/dashboard/input_watcher.py",
    "Scripts/dashboard/error_reporter.py", "Scripts/dashboard/stream_admission.py",
    "Scripts/dashboard/sse_cursor.py",
    "MCP/devcore-scripts/server.py", "MCP/devcore-scripts/services/individual_context.py",
    "MCP/devcore-scripts/services/individual_tasks.py", "Scripts/check_sqlite_runtime.py",
)
MAX_FILE_BYTES = 2 * 1024 * 1024


def ordinary(path: Path, root: Path) -> None:
    relative = path.relative_to(root)
    for item in [root, *(root.joinpath(*relative.parts[:i]) for i in range(1, len(relative.parts) + 1))]:
        if item.is_symlink() or item.is_junction():
            raise ValueError("Links and junctions are not allowed in bundle paths")
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Missing or oversized source file")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory: Path) -> dict:
    directory = Path(directory).absolute()
    ordinary(directory / "manifest.json", directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("profile") != "individual-candidate":
        raise ValueError("Unsupported bundle manifest")
    records = manifest.get("files")
    if not isinstance(records, dict) or set(records) != set(FILES):
        raise ValueError("Bundle file allowlist differs")
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if actual != {*FILES, "manifest.json"}:
        raise ValueError("Undeclared or missing bundle files")
    for name in FILES:
        path = directory / name
        ordinary(path, directory)
        if records[name] != digest(path):
            raise ValueError("Bundle file hash differs")
    return manifest


def build(platform: Path, destination: Path) -> dict:
    platform, destination = Path(platform).absolute(), Path(destination).absolute()
    if destination.exists():
        raise ValueError("Destination exists; refusing overwrite")
    # Reject a destination inside the source, including its linked aliases.
    if destination.resolve().is_relative_to(platform.resolve()):
        raise ValueError("Destination must be outside platform source")
    for name in FILES:
        ordinary(platform / name, platform)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".individual-bundle-", dir=destination.parent))
    for name in FILES:
        source, target = platform / name, stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(source)
        shutil.copyfile(source, target)
        if digest(source) != before or digest(target) != before:
            raise ValueError("Source changed while copying; unpublished stage retained")
    manifest = {
        "schema_version": 1, "profile": "individual-candidate",
        "engine_included": False, "operationally_qualified": False,
        "files": {name: digest(stage / name) for name in FILES},
    }
    for name in FILES:
        ordinary(platform / name, platform)
        if digest(platform / name) != manifest["files"][name]:
            raise ValueError("Source changed before publication; unpublished stage retained")
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verify(stage)
    stage.rename(destination)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("build")
    create.add_argument("--platform", type=Path, required=True)
    create.add_argument("--destination", type=Path, required=True)
    check = sub.add_parser("verify")
    check.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = build(args.platform, args.destination) if args.command == "build" else verify(args.directory)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
