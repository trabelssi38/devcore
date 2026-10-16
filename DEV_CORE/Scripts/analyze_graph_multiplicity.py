"""Analyze duplicate multiplicities for shared graph relations, read-only."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _edges(path: Path) -> Counter[tuple[str, str, str, str | None]]:
    with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as connection:
        return Counter(
            (str(source), str(target), str(kind), properties)
            for source, target, kind, properties in connection.execute(
                "SELECT from_node, to_node, type, properties FROM kg_edges"
            )
        )


def analyze(current_db: Path, other_db: Path, output: Path) -> dict:
    current = _edges(current_db)
    other = _edges(other_db)
    shared = current.keys() & other.keys()
    same_count = sum(current[key] == other[key] for key in shared)
    current_extra_rows = sum(current[key] - other[key] for key in shared if current[key] > other[key])
    other_extra_rows = sum(other[key] - current[key] for key in shared if other[key] > current[key])
    current_excess_by_type = Counter()
    for source, target, kind, properties in shared:
        delta = current[(source, target, kind, properties)] - other[(source, target, kind, properties)]
        if delta > 0:
            current_excess_by_type[kind] += delta
    top_excess = []
    for key in sorted(shared, key=lambda item: (-(current[item] - other[item]), item)):
        delta = current[key] - other[key]
        if delta <= 0:
            break
        source, target, kind, properties = key
        top_excess.append({"from_node": source, "to_node": target, "type": kind, "properties": properties, "current_rows": current[key], "other_rows": other[key], "excess_rows": delta})
        if len(top_excess) >= 50:
            break
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "analysis_only",
        "shared_distinct_relations": len(shared),
        "same_multiplicity_relations": same_count,
        "different_multiplicity_relations": len(shared) - same_count,
        "current_extra_rows_against_other": current_extra_rows,
        "other_extra_rows_against_current": other_extra_rows,
        "current_excess_by_type": dict(current_excess_by_type),
        "top_current_excess": top_excess,
        "policy": "no rows are deleted or imported; multiplicity differences require provenance review",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": "analysis_only", "different_multiplicity_relations": report["different_multiplicity_relations"], "current_extra_rows": current_extra_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.current_db, args.other_db, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
