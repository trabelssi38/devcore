"""Materialize valid/repaired graph edges and keep unresolved edges separate."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def materialize(preview_db: Path, output_db: Path) -> dict:
    if output_db.exists():
        raise FileExistsError(output_db)
    with sqlite3.connect(f"file:{preview_db.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as source:
        nodes = source.execute("SELECT id FROM kg_nodes ORDER BY id").fetchall()
        repaired = source.execute(
            "SELECT edge_rowid, proposed_from_node, proposed_to_node, properties "
            "FROM kg_edges_repair_preview WHERE status IN ('valid', 'repaired') "
            "ORDER BY edge_rowid"
        ).fetchall()
        unresolved = source.execute(
            "SELECT edge_rowid, original_from_node, original_to_node, repair_rule, properties "
            "FROM kg_edges_repair_preview WHERE status='unresolved' ORDER BY edge_rowid"
        ).fetchall()
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_db) as target:
        target.executescript("""
            CREATE TABLE graph_preview_manifest (created_utc TEXT NOT NULL, status TEXT NOT NULL,
                source_db TEXT NOT NULL, automatic_write_allowed INTEGER NOT NULL CHECK(automatic_write_allowed=0));
            CREATE TABLE kg_nodes_preview (id TEXT PRIMARY KEY);
            CREATE TABLE kg_edges_fk_preview (edge_rowid INTEGER PRIMARY KEY, from_node TEXT NOT NULL,
                to_node TEXT NOT NULL, properties TEXT, FOREIGN KEY(from_node) REFERENCES kg_nodes_preview(id),
                FOREIGN KEY(to_node) REFERENCES kg_nodes_preview(id));
            CREATE TABLE kg_edges_quarantine_preview (edge_rowid INTEGER PRIMARY KEY, from_node TEXT NOT NULL,
                to_node TEXT NOT NULL, repair_rule TEXT NOT NULL, properties TEXT);
        """)
        target.execute("INSERT INTO graph_preview_manifest VALUES (?, 'preview_only', ?, 0)", (datetime.now(timezone.utc).isoformat(), str(preview_db.resolve())))
        target.executemany("INSERT INTO kg_nodes_preview VALUES (?)", nodes)
        target.executemany("INSERT INTO kg_edges_fk_preview VALUES (?, ?, ?, ?)", repaired)
        target.executemany("INSERT INTO kg_edges_quarantine_preview VALUES (?, ?, ?, ?, ?)", unresolved)
        target.execute("PRAGMA foreign_keys=ON")
        target.commit()
        integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = target.execute("PRAGMA foreign_key_check").fetchall()
    return {"output": str(output_db), "status": "preview_only", "nodes": len(nodes), "repaired_edges": len(repaired), "quarantine_edges": len(unresolved), "integrity": integrity, "foreign_key_violations": len(foreign_keys), "created_utc": datetime.now(timezone.utc).isoformat()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-db", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = materialize(args.preview_db, args.output_db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
