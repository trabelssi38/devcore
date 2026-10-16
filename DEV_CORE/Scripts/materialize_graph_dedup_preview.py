"""Materialize a read-only graph deduplication preview after repair projection."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def materialize(source: Path, output: Path) -> dict:
    if output.exists():
        output.unlink()
    with sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as src, sqlite3.connect(output, uri=True) as dst:
        dst.execute("ATTACH DATABASE ? AS source_db", (f"file:{source.resolve().as_posix()}?mode=ro&immutable=1",))
        dst.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE graph_dedup_manifest (created_utc TEXT NOT NULL, source_db TEXT NOT NULL, automatic_write_allowed INTEGER NOT NULL CHECK(automatic_write_allowed=0));
            CREATE TABLE kg_nodes_preview (id TEXT PRIMARY KEY, type TEXT NOT NULL, label TEXT NOT NULL, properties TEXT);
            CREATE TABLE kg_edges_dedup_preview (id INTEGER PRIMARY KEY, from_node TEXT NOT NULL, to_node TEXT NOT NULL, type TEXT NOT NULL, properties TEXT, source_rows INTEGER NOT NULL, FOREIGN KEY(from_node) REFERENCES kg_nodes_preview(id), FOREIGN KEY(to_node) REFERENCES kg_nodes_preview(id));
            CREATE TABLE kg_edges_quarantine_grouped_preview (from_node TEXT NOT NULL, to_node TEXT NOT NULL, type TEXT NOT NULL, properties TEXT, source_rows INTEGER NOT NULL, PRIMARY KEY(from_node,to_node,type,properties));
            """
        )
        dst.execute("INSERT INTO graph_dedup_manifest VALUES (?, ?, 0)", (datetime.now(timezone.utc).isoformat(), str(source)))
        dst.executemany("INSERT INTO kg_nodes_preview VALUES (?, ?, ?, ?)", src.execute("SELECT id, type, label, properties FROM kg_nodes"))
        dst.execute(
            """
            INSERT INTO kg_edges_dedup_preview(from_node,to_node,type,properties,source_rows)
            SELECT COALESCE(proposed_from_node, original_from_node), COALESCE(proposed_to_node, original_to_node), e.type, r.properties, COUNT(*)
            FROM source_db.kg_edges_repair_preview r JOIN source_db.kg_edges e ON e.id=r.edge_rowid
            WHERE r.status IN ('valid','repaired')
            GROUP BY COALESCE(proposed_from_node, original_from_node), COALESCE(proposed_to_node, original_to_node), e.type, r.properties
            """
        )
        dst.execute(
            """
            INSERT INTO kg_edges_quarantine_grouped_preview
            SELECT original_from_node, original_to_node, e.type, r.properties, COUNT(*)
            FROM source_db.kg_edges_repair_preview r JOIN source_db.kg_edges e ON e.id=r.edge_rowid
            WHERE r.status='unresolved'
            GROUP BY original_from_node, original_to_node, e.type, r.properties
            """
        )
        dst.commit()
        counts = {
            "source_rows": src.execute("SELECT COUNT(*) FROM kg_edges").fetchone()[0],
            "source_distinct_relations": src.execute("SELECT COUNT(*) FROM (SELECT DISTINCT from_node,to_node,type,properties FROM kg_edges)").fetchone()[0],
            "dedup_rows": dst.execute("SELECT COUNT(*) FROM kg_edges_dedup_preview").fetchone()[0],
            "dedup_source_rows": dst.execute("SELECT COALESCE(SUM(source_rows),0) FROM kg_edges_dedup_preview").fetchone()[0],
            "quarantine_groups": dst.execute("SELECT COUNT(*) FROM kg_edges_quarantine_grouped_preview").fetchone()[0],
            "quarantine_source_rows": dst.execute("SELECT COALESCE(SUM(source_rows),0) FROM kg_edges_quarantine_grouped_preview").fetchone()[0],
            "integrity_check": dst.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": len(dst.execute("PRAGMA foreign_key_check").fetchall()),
        }
    report = {"report_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(), "status": "preview_only", **counts, "policy": "deduplication is not applied to any operational database; source_rows preserves multiplicity for review"}
    report_path = output.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "report": str(report_path), "status": "preview_only", "dedup_rows": counts["dedup_rows"], "quarantine_source_rows": counts["quarantine_source_rows"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.source, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
