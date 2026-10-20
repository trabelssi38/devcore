"""Read-only Git/task comparison for one qualified durable run."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess


TAG = re.compile(r"\[T-(\d{1,8})\]")
SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise ValueError("Git scan failed")
    return result.stdout.strip()


def scan(project: str, root: Path, revision: str, task_ids: list[str]) -> dict:
    if os.environ.get("DEVCORE_PROJECT_ID") != project:
        raise ValueError("Run project mismatch")
    if not root.is_absolute() or not root.is_dir() or not SHA.fullmatch(revision):
        raise ValueError("Qualified Git root and revision required")
    root = root.resolve()
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("Registered Git root mismatch")
    if git(root, "rev-parse", "--verify", f"{revision}^{{commit}}").lower() != revision:
        raise ValueError("Commit mismatch")
    known = set(task_ids)
    if len(known) != len(task_ids) or any(not re.fullmatch(r"T-\d{1,8}", item) for item in known):
        raise ValueError("Bounded task snapshot required")
    output = git(root, "log", "--max-count=100", "--format=%H%x00%s", revision)
    observed: set[str] = set()
    missing: set[str] = set()
    commits = 0
    for line in output.splitlines():
        if "\x00" not in line:
            continue
        commit_sha, subject = line.split("\x00", 1)
        if not SHA.fullmatch(commit_sha.lower()):
            continue
        commits += 1
        for match in TAG.finditer(subject):
            task_id = "T-" + match.group(1)
            observed.add(task_id)
            if task_id not in known:
                missing.add(task_id)
    return {"project": project, "revision": revision, "commits_scanned": commits,
            "task_tags_observed": sorted(observed), "missing_task_tags": sorted(missing),
            "tasks_without_recent_tag": sorted(known - observed),
            "task_changes": 0, "source": "git_read_only"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--task-ids-json", required=True)
    args = parser.parse_args(argv)
    if len(args.task_ids_json.encode("utf-8")) > 12000:
        parser.error("Task snapshot exceeds bound")
    try:
        task_ids = json.loads(args.task_ids_json)
        if not isinstance(task_ids, list):
            raise ValueError("Task snapshot must be a list")
        print(json.dumps(scan(args.project, args.root, args.revision, task_ids),
                         ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
