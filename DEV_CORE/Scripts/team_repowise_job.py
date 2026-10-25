"""Refresh one clean Git repository's RepoWise index, then verify its commit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def call(argv: list[str], root: Path, *, timeout: int, env=None) -> subprocess.CompletedProcess:
    result = subprocess.run(argv, cwd=str(root), env=env, capture_output=True,
                            text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise ValueError("Qualified command failed")
    return result


def index(project: str, root: Path, revision: str, executable: Path, *, force: bool) -> dict:
    if os.environ.get("DEVCORE_PROJECT_ID") != project:
        raise ValueError("Run project mismatch")
    if (not root.is_absolute() or not root.is_dir() or not executable.is_absolute()
            or not executable.is_file() or not SHA.fullmatch(revision)):
        raise ValueError("Qualified repository, revision and RepoWise executable required")
    root = root.resolve()
    top = call(["git", "rev-parse", "--show-toplevel"], root, timeout=10).stdout.strip()
    head = call(["git", "rev-parse", "HEAD"], root, timeout=10).stdout.strip().lower()
    dirty = call(["git", "status", "--porcelain"], root, timeout=20).stdout.strip()
    if Path(top).resolve() != root or head != revision or dirty:
        raise ValueError("Git repository changed or has uncommitted files")

    def status() -> dict:
        raw = call([str(executable), "status", "--format", "json", "--no-workspace"],
                   root, timeout=180).stdout
        if len(raw.encode("utf-8")) > 65536:
            raise ValueError("RepoWise status exceeds bound")
        return json.loads(raw)

    before = status()
    refreshed = force or before.get("state", {}).get("last_sync_commit") != revision
    if refreshed:
        env = os.environ.copy()
        env.update(REPOWISE_EMBEDDER="mock", REPOWISE_TELEMETRY_DISABLED="1")
        call([str(executable), "update", "--index-only", "--no-docs", "--no-workspace"],
             root, timeout=300, env=env)
    after = status()
    if not after.get("indexed") or after.get("state", {}).get("last_sync_commit") != revision:
        raise ValueError("RepoWise index does not match Git commit")
    if call(["git", "rev-parse", "HEAD"], root, timeout=10).stdout.strip().lower() != revision:
        raise ValueError("Git HEAD changed during indexing")
    file_pages = after.get("index_scope", {}).get("file_pages", {})
    omitted = file_pages.get("omitted")
    return {"project": project, "revision": revision, "indexed_commit": revision,
            "refreshed": refreshed, "file_pages_omitted": omitted if type(omitted) is int else None,
            "coverage_known": type(omitted) is int, "source": "repowise_project_index"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(index(args.project, args.root, args.revision,
                               args.executable, force=args.force), sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
