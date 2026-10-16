"""Compare graph impact reachability before and after deduplication preview."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path


def _adjacency_from_repair(db: sqlite3.Connection) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    rows = db.execute(
        """SELECT COALESCE(r.proposed_from_node, r.original_from_node),
                         COALESCE(r.proposed_to_node, r.original_to_node)
                  FROM kg_edges_repair_preview r
                 WHERE r.status IN ('valid','repaired')"""
    )
    for source, target in rows:
        adjacency[str(source)].add(str(target))
        adjacency[str(target)].add(str(source))
    return adjacency


def _adjacency_from_dedup(db: sqlite3.Connection) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for source, target in db.execute("SELECT from_node,to_node FROM kg_edges_dedup_preview"):
        adjacency[str(source)].add(str(target))
        adjacency[str(target)].add(str(source))
    return adjacency


def _reachable(adjacency: dict[str, set[str]], start: str, depth: int) -> set[str]:
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, distance = queue.popleft()
        if distance >= depth:
            continue
        for neighbor in adjacency.get(node, ()):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, distance + 1))
    seen.discard(start)
    return seen


def validate(graph_preview: Path, dedup_preview: Path, output: Path, depth: int = 2) -> dict:
    with sqlite3.connect(f"file:{graph_preview.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as graph, sqlite3.connect(f"file:{dedup_preview.resolve().as_posix()}?mode=ro&immutable=1", uri=True) as dedup:
        before = _adjacency_from_repair(graph)
        after = _adjacency_from_dedup(dedup)
        nodes = {str(row[0]) for row in graph.execute("SELECT id FROM kg_nodes")}
        mismatches = []
        for node in sorted(nodes):
            left = _reachable(before, node, depth)
            right = _reachable(after, node, depth)
            if left != right:
                mismatches.append({"node": node, "before_count": len(left), "after_count": len(right), "lost": sorted(left - right)[:20], "gained": sorted(right - left)[:20]})
                if len(mismatches) >= 25:
                    break
        report = {
            "report_version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "validation_only",
            "depth": depth,
            "nodes_examined": len(nodes),
            "before_relation_rows": graph.execute("SELECT COUNT(*) FROM kg_edges_repair_preview WHERE status IN ('valid','repaired')").fetchone()[0],
            "after_distinct_rows": dedup.execute("SELECT COUNT(*) FROM kg_edges_dedup_preview").fetchone()[0],
            "mismatch_nodes": len(mismatches),
            "mismatch_examples": mismatches,
            "impact_reachability_equal": not mismatches,
            "policy": "reachability validation only; no operational graph is changed",
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": "validation_only", "mismatch_nodes": len(mismatches), "impact_reachability_equal": not mismatches}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-preview", type=Path, required=True)
    parser.add_argument("--dedup-preview", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--depth", type=int, default=2)
    args = parser.parse_args()
    if args.depth < 1:
        parser.error("--depth must be positive")
    print(json.dumps(validate(args.graph_preview, args.dedup_preview, args.output, args.depth), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
