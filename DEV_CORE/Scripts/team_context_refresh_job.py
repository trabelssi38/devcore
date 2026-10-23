"""Refresh verifiable project facts without asserting a narrative review."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def refresh(project: str, root: Path, *, now: datetime | None = None) -> dict:
    from devcore_engine.services.project_context import _read_inside, _validate

    root = Path(root).resolve(strict=True)
    context_dir = (root / "docs" / "project-context").resolve(strict=True)
    if not context_dir.is_relative_to(root):
        raise ValueError("Context directory must be inside the registered project")
    manifest_raw = _read_inside(context_dir, "context.json")
    manifest = json.loads(manifest_raw)
    _validate(manifest, project)
    if manifest.get("automatic_context") != "automatic.json":
        raise ValueError("Project has not enabled automatic context")
    card_raw = _read_inside(context_dir, manifest["card"])
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel", "HEAD"],
        capture_output=True, text=True, check=True, timeout=20,
    )
    lines = completed.stdout.splitlines()
    if len(lines) != 2 or Path(lines[0]).resolve() != root or len(lines[1]) != 40:
        raise ValueError("Registered root must be the Git repository root")
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True, text=True, check=True, timeout=20,
    )
    stamp = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    result = {
        "schema_version": 1, "project": project, "generated_at": stamp,
        "git_head": lines[1], "tracked_changes": bool(status.stdout.strip()),
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "card_sha256": hashlib.sha256(card_raw).hexdigest(),
        "card_matches_review": hashlib.sha256(card_raw).hexdigest() == manifest["card_sha256"],
    }
    output = context_dir / "automatic.json"
    fd, temporary = tempfile.mkstemp(prefix=".automatic-", suffix=".json", dir=context_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = refresh(args.project, args.root)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
