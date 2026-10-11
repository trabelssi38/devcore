"""Read-only inventory of sync conflict copies; never selects a winning file."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


CONFLICT = re.compile(r" \((?:Copie en conflit de|conflicted copy from) ([^)]+)\)(?=\.[^.]+$)", re.I)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tasks_comparison(current: Path, conflict: Path) -> dict:
    with current.open(encoding="utf-8-sig") as source:
        left = json.load(source)
    with conflict.open(encoding="utf-8-sig") as source:
        right = json.load(source)
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError("task document root must be an object")

    def index(document):
        tasks = document.get("tasks")
        if not isinstance(tasks, list):
            raise ValueError("tasks must be a list")
        result = {}
        for task in tasks:
            if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                raise ValueError("each task must have a string id")
            if task["id"] in result:
                raise ValueError("duplicate task id")
            result[task["id"]] = task
        return result

    a, b = index(left), index(right)
    common = a.keys() & b.keys()
    changed = [key for key in common if a[key] != b[key]]
    fields = Counter(
        field for key in changed
        for field in a[key].keys() | b[key].keys()
        if a[key].get(field) != b[key].get(field)
    )
    return {
        "current_count": len(a),
        "conflict_count": len(b),
        "only_current": len(a.keys() - b.keys()),
        "only_conflict": len(b.keys() - a.keys()),
        "shared": len(common),
        "changed_shared": len(changed),
        "changed_fields": dict(sorted(fields.items())),
        "current_task_equal": left.get("current_task") == right.get("current_task"),
    }


def inspect(root: Path) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must be a directory")
    entries = []
    for conflict in sorted(root.rglob("*")):
        if not conflict.is_file() or conflict.is_symlink():
            continue
        match = CONFLICT.search(conflict.name)
        if not match:
            continue
        current = conflict.with_name(CONFLICT.sub("", conflict.name))
        entry = {
            "relative_path": conflict.relative_to(root).as_posix(),
            "writer_label": match.group(1),
            "size_bytes": conflict.stat().st_size,
            "current_exists": current.is_file(),
        }
        if current.is_file():
            entry["current_size_bytes"] = current.stat().st_size
            entry["same_bytes"] = _digest(current) == _digest(conflict)
            if current.name == "tasks.json" and conflict.suffix.lower() == ".json":
                try:
                    entry["tasks"] = _tasks_comparison(current, conflict)
                except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                    entry["tasks_error"] = type(exc).__name__
        entries.append(entry)
    return {"root": str(root), "conflict_count": len(entries), "entries": entries}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.root), ensure_ascii=False, indent=2))
