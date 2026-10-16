"""Inspect missing graph nodes and produce a repair-oriented report.

The input SQLite databases are opened read-only.  The command only writes a
JSON report; it never rewrites, deletes or reattaches graph edges.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        import sqlite_vec

        connection.enable_load_extension(True)
        try:
            sqlite_vec.load(connection)
        finally:
            connection.enable_load_extension(False)
    except ImportError:
        pass
    return connection


def inspect_graph(path: Path) -> dict:
    with _connect(path) as connection:
        nodes = {str(row[0]) for row in connection.execute("SELECT id FROM kg_nodes")}
        missing_sources: Counter[str] = Counter()
        missing_targets: Counter[str] = Counter()
        relation_types: Counter[str] = Counter()
        examples: list[dict] = []
        total = 0
        for edge_id, source, target, relation_type, properties in connection.execute(
            "SELECT rowid, from_node, to_node, type, properties FROM kg_edges"
        ):
            total += 1
            source_missing = str(source) not in nodes
            target_missing = str(target) not in nodes
            if source_missing:
                missing_sources[str(source)] += 1
            if target_missing:
                missing_targets[str(target)] += 1
            if source_missing or target_missing:
                relation_types[str(relation_type)] += 1
                if len(examples) < 20:
                    examples.append({
                        "rowid": edge_id,
                        "from_node": source,
                        "to_node": target,
                        "type": relation_type,
                        "properties": properties,
                        "source_missing": source_missing,
                        "target_missing": target_missing,
                    })
        return {
            "path": str(path.resolve()),
            "nodes": len(nodes),
            "edges": total,
            "source_missing_edges": sum(missing_sources.values()),
            "target_missing_edges": sum(missing_targets.values()),
            "edges_with_any_missing_node": sum(
                1 for row in connection.execute(
                    "SELECT e.from_node, e.to_node FROM kg_edges e "
                    "LEFT JOIN kg_nodes s ON s.id=e.from_node "
                    "LEFT JOIN kg_nodes t ON t.id=e.to_node "
                    "WHERE s.id IS NULL OR t.id IS NULL"
                )
            ),
            "missing_source_node_ids": len(missing_sources),
            "missing_target_node_ids": len(missing_targets),
            "top_missing_sources": missing_sources.most_common(100),
            "top_missing_targets": missing_targets.most_common(100),
            "relation_types": relation_types,
            "examples": examples,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-db", type=Path, required=True)
    parser.add_argument("--other-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "inspection_only",
        "sources": {
            "current": inspect_graph(args.current_db),
            "other": inspect_graph(args.other_db),
        },
        "repair_policy": {
            "automatic_repair": False,
            "required_evidence": ["exact_node_id", "source_content_or_signature", "project_scope"],
            "unresolved_disposition": "retain_in_quarantine",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": "inspection_only"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
