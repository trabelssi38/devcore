"""Compare graph relations from two SQLite sources without merging them."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _edges(path: Path) -> Counter[tuple[str, str, str, str | None]]:
    with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as connection:
        return Counter((str(source), str(target), str(kind), properties) for source, target, kind, properties in connection.execute("SELECT from_node, to_node, type, properties FROM kg_edges"))


def compare(current_db: Path, other_db: Path, output: Path) -> dict:
    current = _edges(current_db)
    other = _edges(other_db)
    shared = current.keys() & other.keys()
    only_current = current.keys() - other.keys()
    only_other = other.keys() - current.keys()
    relation_delta = Counter()
    for source, target, kind, _properties in only_other:
        relation_delta[kind] += other[(source, target, kind, _properties)]
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "comparison_only",
        "current": {"rows": sum(current.values()), "distinct_relations": len(current), "sha256_keys": hashlib.sha256("\n".join(map(str, sorted(current))).encode()).hexdigest()},
        "other": {"rows": sum(other.values()), "distinct_relations": len(other), "sha256_keys": hashlib.sha256("\n".join(map(str, sorted(other))).encode()).hexdigest()},
        "shared_distinct_relations": len(shared),
        "only_current_distinct_relations": len(only_current),
        "only_other_distinct_relations": len(only_other),
        "only_other_rows": sum(other[key] for key in only_other),
        "only_other_by_type": dict(relation_delta),
        "examples_only_other": [
            {"from_node": source, "to_node": target, "type": kind, "properties": properties, "rows": other[(source, target, kind, properties)]}
            for source, target, kind, properties in sorted(only_other, key=lambda key: (-other[key], key))[:25]
        ],
        "policy": "no relation is imported automatically; only_other requires provenance review",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": "comparison_only", "only_other_rows": report["only_other_rows"], "only_other_distinct_relations": len(only_other)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.current_db, args.other_db, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
