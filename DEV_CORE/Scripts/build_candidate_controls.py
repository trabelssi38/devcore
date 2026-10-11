"""Publish a minimal, immutable set of candidate launch and stop controls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


FILES = (
    "Scripts/build_candidate_controls.py",
    "Scripts/build_individual_bundle.py",
    "Scripts/verify_engine_release.py",
    "Scripts/launch_individual_candidate.py",
    "Scripts/launch_individual_mcp_candidate.py",
    "Scripts/service_runtime.py",
    "Scripts/stop_service.py",
    "Scripts/qualify_individual_managed.py",
    "Scripts/install_individual_service.py",
    "Scheduler/scheduler_lock.py",
    "Scheduler/scheduler_storage.py",
    "Scheduler/windows_process_identity.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(path: Path, root: Path) -> None:
    if not path.is_relative_to(root):
        raise ValueError("Control path outside root")
    for part in (path, *path.parents):
        if part == root.parent:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError("Linked control path")
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Missing or oversized control file")


def verify(directory: Path) -> dict:
    directory = Path(directory).resolve(strict=True)
    ordinary(directory / "manifest.json", directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    records = manifest.get("files")
    if manifest.get("schema_version") != 1 or manifest.get("profile") != "individual-candidate-controls":
        raise ValueError("Unsupported control manifest")
    if not isinstance(records, dict) or set(records) != set(FILES):
        raise ValueError("Control inventory differs")
    actual = {path.relative_to(directory).as_posix() for path in directory.rglob("*")
              if path.is_file() and "__pycache__" not in path.relative_to(directory).parts}
    if actual != {*FILES, "manifest.json"}:
        raise ValueError("Unexpected control file")
    for name in FILES:
        path = directory / name
        ordinary(path, directory)
        if records[name] != digest(path):
            raise ValueError("Control hash differs")
    return manifest


def build(platform: Path, destination: Path) -> dict:
    platform, destination = Path(platform).resolve(strict=True), Path(destination).absolute()
    if destination.exists() or destination.resolve().is_relative_to(platform):
        raise ValueError("Control destination exists or lies inside source")
    for name in FILES:
        ordinary(platform / name, platform)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".candidate-controls-", dir=destination.parent))
    for name in FILES:
        source, target = platform / name, stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(source)
        shutil.copyfile(source, target)
        if digest(source) != before or digest(target) != before:
            raise ValueError("Control source changed while copying")
    manifest = {"schema_version": 1, "profile": "individual-candidate-controls",
                "files": {name: digest(stage / name) for name in FILES}}
    for name in FILES:
        if digest(platform / name) != manifest["files"][name]:
            raise ValueError("Control source changed before publication")
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
