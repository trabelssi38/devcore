"""Validate a graph repair preview without changing either database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)


def validate(source_db: Path, preview_db: Path) -> dict:
    with _connect(source_db) as source, _connect(preview_db) as preview:
        source_edges = source.execute("SELECT rowid, from_node, to_node, type, properties FROM kg_edges").fetchall()
        preview_rows = preview.execute(
            "SELECT edge_rowid, original_from_node, original_to_node, proposed_from_node, "
            "proposed_to_node, repair_rule, status, properties FROM kg_edges_repair_preview"
        ).fetchall()
        counts = Counter(row[6] for row in preview_rows)
        changed_types: Counter[str] = Counter()
        for edge_rowid, original_source, original_target, proposed_source, proposed_target, _rule, status, _properties in preview_rows:
            if status == "repaired":
                row = source.execute("SELECT type FROM kg_edges WHERE rowid=?", (edge_rowid,)).fetchone()
                if row:
                    changed_types[str(row[0])] += 1
        source_duplicates = source.execute(
            "SELECT from_node, to_node, type, properties, COUNT(*) AS n "
            "FROM kg_edges GROUP BY from_node, to_node, type, properties HAVING n > 1"
        ).fetchall()
        duplicates = preview.execute(
            "SELECT p.proposed_from_node, p.proposed_to_node, e.type, e.properties, COUNT(*) AS n "
            "FROM kg_edges_repair_preview p JOIN kg_edges e ON e.rowid=p.edge_rowid "
            "WHERE p.status IN ('valid','repaired') "
            "GROUP BY p.proposed_from_node, p.proposed_to_node, e.type, e.properties HAVING n > 1"
        ).fetchall()
        unresolved_bad = preview.execute(
            "SELECT COUNT(*) FROM kg_edges_repair_preview p "
            "LEFT JOIN kg_nodes s ON s.id=p.proposed_from_node "
            "LEFT JOIN kg_nodes t ON t.id=p.proposed_to_node "
            "WHERE p.status='repaired' AND (s.id IS NULL OR t.id IS NULL)"
        ).fetchone()[0]
        source_integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
        preview_integrity = preview.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_preview",
        "source_edges": len(source_edges),
        "preview_edges": len(preview_rows),
        "status_counts": dict(counts),
        "repaired_relation_types": dict(changed_types),
        "duplicate_groups_after_repair": len(duplicates),
        "duplicate_rows_after_repair": sum(int(row[4]) for row in duplicates),
        "duplicate_groups_before_repair": len(source_duplicates),
        "duplicate_rows_before_repair": sum(int(row[4]) for row in source_duplicates),
        "duplicate_group_delta": len(duplicates) - len(source_duplicates),
        "repaired_rows_with_missing_nodes": int(unresolved_bad),
        "source_integrity": source_integrity,
        "preview_integrity": preview_integrity,
        "source_unchanged_by_row_count": len(source_edges) == len(preview_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--preview-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.source_db, args.preview_db)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
