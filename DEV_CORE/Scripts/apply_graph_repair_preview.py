"""Materialize deterministic graph repairs in a new review-only SQLite copy.

The source is copied with SQLite's online backup API.  Original ``kg_edges``
rows are never changed.  The output receives ``kg_edges_repair_preview`` with
the proposed endpoints and an auditable status for every edge.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _load_sqlite_vec(connection: sqlite3.Connection) -> None:
    try:
        import sqlite_vec

        connection.enable_load_extension(True)
        try:
            sqlite_vec.load(connection)
        finally:
            connection.enable_load_extension(False)
    except ImportError:
        pass


def _candidate(node_id: str, nodes: set[str]) -> tuple[str | None, str]:
    prefixed = f"file:{node_id}"
    if not node_id.startswith("file:") and prefixed in nodes:
        return prefixed, "exact_file_prefix"
    if node_id.startswith("function:UNKNOWN/"):
        suffix = "/" + node_id.rsplit("/", 1)[-1]
        matches = sorted(item for item in nodes if item.startswith("function:") and item.endswith(suffix))
        if len(matches) == 1:
            return matches[0], "unique_function_suffix"
    return None, "no_unambiguous_candidate"


def build_preview(source: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(output)
    source_uri = f"file:{source.resolve().as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(source_uri, uri=True) as source_connection:
        _load_sqlite_vec(source_connection)
        nodes = {str(row[0]) for row in source_connection.execute("SELECT id FROM kg_nodes")}
        output.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(output) as target:
            source_connection.backup(target)
            target.execute("""
                CREATE TABLE kg_edges_repair_preview (
                    edge_rowid INTEGER PRIMARY KEY,
                    original_from_node TEXT NOT NULL,
                    original_to_node TEXT NOT NULL,
                    proposed_from_node TEXT,
                    proposed_to_node TEXT,
                    repair_rule TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('valid', 'repaired', 'unresolved')),
                    properties TEXT,
                    UNIQUE(edge_rowid)
                )
            """)
            counts: Counter[str] = Counter()
            rows = []
            for rowid, source_node, target_node, edge_type, properties in source_connection.execute(
                "SELECT rowid, from_node, to_node, type, properties FROM kg_edges"
            ):
                proposed_source, source_rule = (None, "already_present") if str(source_node) in nodes else _candidate(str(source_node), nodes)
                proposed_target, target_rule = (None, "already_present") if str(target_node) in nodes else _candidate(str(target_node), nodes)
                final_source = proposed_source or (str(source_node) if str(source_node) in nodes else None)
                final_target = proposed_target or (str(target_node) if str(target_node) in nodes else None)
                if final_source and final_target and (proposed_source or proposed_target):
                    status, rule = "repaired", ";".join(x for x in (source_rule, target_rule) if x != "already_present")
                elif final_source and final_target:
                    status, rule = "valid", "already_valid"
                else:
                    status, rule = "unresolved", ";".join(x for x in (source_rule, target_rule) if x != "already_present")
                counts[status] += 1
                rows.append((rowid, source_node, target_node, final_source, final_target, rule, status, properties))
                if len(rows) >= 10_000:
                    target.executemany("INSERT INTO kg_edges_repair_preview VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
                    rows.clear()
            if rows:
                target.executemany("INSERT INTO kg_edges_repair_preview VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
            target.commit()
    return {
        "output": str(output),
        "status": "preview_only",
        "source_edges": sum(counts.values()),
        "valid_edges": counts["valid"],
        "repaired_edges": counts["repaired"],
        "unresolved_edges": counts["unresolved"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = build_preview(args.source_db, args.output_db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
