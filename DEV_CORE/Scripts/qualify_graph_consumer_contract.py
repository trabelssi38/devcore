"""Read-only graph consumer qualification against an isolated SQLite candidate."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def qualify(candidate: Path, inventory: Path) -> dict:
    findings = json.loads(inventory.read_text(encoding="utf-8"))["findings"]
    runtime = [
        item for item in findings
        if item["file"] == "devcore_engine/services/knowledge.py"
        and set(item["categories"]) & {"raw_count", "traversal", "write"}
    ]
    with tempfile.TemporaryDirectory(prefix="devcore-graph-contract-") as temporary:
        os.environ["DEVCORE_LOCAL_ROOT"] = str(Path(temporary) / "local")
        os.environ["DEVCORE_DATA_ROOT"] = str(Path(temporary) / "data")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from devcore_engine.services.knowledge import KnowledgeGraph

        db = sqlite3.connect(candidate.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            columns = {
                table: [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
                for table in ("kg_nodes", "kg_edges")
            }
            graph = KnowledgeGraph(db)
            stats = graph.get_stats()
            project_stats = graph.get_stats("devcore")
            sample = db.execute("SELECT id FROM kg_nodes ORDER BY id LIMIT 1").fetchone()
            impact = graph.impact_analysis(sample[0], max_depth=2, project_id="devcore") if sample else None
            fks = db.execute("PRAGMA foreign_key_check").fetchall()
            report = {
                "report_version": 1,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "consumer_contract_reviewed_with_blockers",
                "candidate": str(candidate.resolve()),
                "read_only": True,
                "runtime_inventory_lines": [item["line"] for item in runtime],
                "inventory_counts": {
                    category: sum(category in item["categories"] for item in findings)
                    for category in ("raw_count", "traversal", "write")
                },
                "schema_columns": columns,
                "stats": stats,
                "project_stats": project_stats,
                "impact_sample": {
                    "target": sample[0],
                    "blast_radius_count": impact["blast_radius_count"],
                    "returned_project_id": impact.get("project_id"),
                } if impact else None,
                "foreign_key_violations": len(fks),
                "checks": {
                    "raw_and_distinct_counts_exposed": stats["edge_rows"] >= stats["distinct_edges"],
                    "project_scope_columns_present": all("project_id" in columns[t] for t in columns),
                    "project_stats_distinguishable": project_stats != stats,
                    "foreign_keys_valid": not fks,
                },
            }
            report["blockers"] = [key for key, passed in report["checks"].items() if not passed]
            report["status"] = "consumer_contract_qualified" if not report["blockers"] else "consumer_contract_reviewed_with_blockers"
            return report
        finally:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.candidate, args.inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "blockers": report["blockers"], "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
