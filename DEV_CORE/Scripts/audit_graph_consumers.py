"""Inventory code consumers of the kg_edges table for migration review."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PATTERNS = {
    "raw_count": re.compile(r"COUNT\(\s*\*\s*\).*kg_edges|kg_edges.*COUNT\(\s*\*\s*\)", re.I),
    "traversal": re.compile(r"SELECT[^\n]*\b(from_node|to_node)\b[^\n]*FROM\s+kg_edges|FROM\s+kg_edges[^\n]*\b(from_node|to_node)\b", re.I),
    "write": re.compile(r"(?:INSERT|UPDATE|DELETE)[^\n]*\bkg_edges\b|\bkg_edges\b[^\n]*(?:INSERT|UPDATE|DELETE)", re.I),
    "export_or_file_graph": re.compile(r"graph\.json|knowledge_graph|kg_edges", re.I),
}


def audit(root: Path, output: Path) -> dict:
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "build" in path.parts or path.suffix.lower() not in {".py", ".ps1", ".js", ".html"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            if "kg_edges" not in line and "graph.json" not in line and "knowledge_graph" not in line:
                continue
            categories = [name for name, pattern in PATTERNS.items() if pattern.search(line)]
            if categories:
                findings.append({"file": str(path.relative_to(root)).replace("\\", "/"), "line": number, "categories": categories, "snippet": line.strip()[:240]})
    summary = {category: sum(category in finding["categories"] for finding in findings) for category in PATTERNS}
    report = {
        "report_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "inventory_only",
        "root": str(root),
        "finding_count": len(findings),
        "summary": summary,
        "findings": findings,
        "migration_guidance": {
            "raw_count": "Expose both physical row count and distinct relation count if deduplication is approved.",
            "traversal": "Validate reachability and preserve project scoping before switching tables.",
            "write": "Route future writes through a uniqueness/provenance policy; do not silently reintroduce duplicates.",
            "export_or_file_graph": "Validate JSON/export consumers independently from SQL projections.",
        },
        "policy": "inventory only; no source or operational database is changed",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"output": str(output), "status": "inventory_only", "finding_count": len(findings), "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
