"""Propose deterministic graph-node repairs without changing graph data."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _connection(path: Path) -> sqlite3.Connection:
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


def inspect(path: Path) -> dict:
    with _connection(path) as connection:
        nodes = {str(row[0]) for row in connection.execute("SELECT id FROM kg_nodes")}
        missing: dict[tuple[str, str], int] = Counter()
        for source, target in connection.execute("SELECT from_node, to_node FROM kg_edges"):
            if str(source) not in nodes:
                missing[("source", str(source))] += 1
            if str(target) not in nodes:
                missing[("target", str(target))] += 1
        proposals = []
        for (role, node_id), count in sorted(missing.items(), key=lambda item: (-item[1], item[0])):
            candidate, rule = _candidate(node_id, nodes)
            proposals.append({"role": role, "missing_node_id": node_id, "edge_count": count,
                              "candidate_node_id": candidate, "rule": rule,
                              "decision": "candidate" if candidate else "retain_in_quarantine"})
        return {
            "path": str(path.resolve()),
            "missing_identifiers": len(missing),
            "candidate_identifiers": sum(row["decision"] == "candidate" for row in proposals),
            "candidate_edges": sum(row["edge_count"] for row in proposals if row["decision"] == "candidate"),
            "quarantine_edges": sum(row["edge_count"] for row in proposals if row["decision"] != "candidate"),
            "proposals": proposals,
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
        "status": "proposal_only",
        "policy": "only exact file-prefix or unique function-suffix matches are candidates",
        "sources": {"current": inspect(args.current_db), "other": inspect(args.other_db)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": "proposal_only"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
