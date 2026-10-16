"""Build a provenance-preserving graph projection from a repair preview."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _node_for_missing(node_id: str, known: set[str], repo_root: Path) -> tuple[str, str, str]:
    if node_id in known:
        return node_id, "existing", ""
    relative = node_id.removeprefix("file:")
    candidate = repo_root / relative
    if relative.startswith("DEV_CORE/") and candidate.is_file() and candidate.resolve().is_relative_to(repo_root):
        target = f"file:{relative}"
        return target, "heuristic_existing_file", relative
    return node_id, "unresolved_placeholder", ""


def materialize(preview_db: Path, repo_root: Path, output_db: Path) -> dict:
    preview_db = preview_db.resolve(strict=True)
    repo_root = repo_root.resolve(strict=True)
    output_db = output_db.resolve()
    if output_db.exists() or output_db.is_relative_to(repo_root):
        raise ValueError("Output must be a new database outside the repository")
    wal = preview_db.with_name(preview_db.name + "-wal")
    if wal.is_file() and wal.stat().st_size:
        raise ValueError("Source has a non-empty WAL")
    source_hash = sha256(preview_db)
    output_db.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{preview_db.as_posix()}?mode=ro&immutable=1"
    with closing(sqlite3.connect(source_uri, uri=True)) as source:
        with closing(sqlite3.connect(output_db)) as output:
            output.execute("PRAGMA foreign_keys=ON")
            output.executescript("""
                CREATE TABLE manifest (source_sha256 TEXT NOT NULL, status TEXT NOT NULL,
                    ready_for_cutover INTEGER NOT NULL CHECK(ready_for_cutover=0));
                CREATE TABLE nodes (id TEXT PRIMARY KEY, type TEXT NOT NULL, label TEXT NOT NULL,
                    properties TEXT NOT NULL);
                CREATE TABLE edges (edge_rowid INTEGER PRIMARY KEY, from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL, type TEXT NOT NULL, properties TEXT,
                    repair_status TEXT NOT NULL, repair_rule TEXT NOT NULL,
                    original_from_node TEXT NOT NULL, original_to_node TEXT NOT NULL,
                    FOREIGN KEY(from_node) REFERENCES nodes(id),
                    FOREIGN KEY(to_node) REFERENCES nodes(id));
            """)
            output.execute("INSERT INTO manifest VALUES (?, 'preview_only', 0)", (source_hash,))
            original_nodes = source.execute("SELECT id, type, label, properties FROM kg_nodes").fetchall()
            known = {row[0] for row in original_nodes}
            output.executemany("INSERT INTO nodes VALUES (?, ?, ?, ?)", original_nodes)
            synthetic: dict[str, tuple[str, str, str]] = {}
            counts: Counter[str] = Counter()
            records = source.execute("""
                SELECT p.edge_rowid, p.original_from_node, p.original_to_node,
                       p.proposed_from_node, p.proposed_to_node, e.type, p.properties,
                       p.status, p.repair_rule
                FROM kg_edges_repair_preview p JOIN kg_edges e ON e.rowid=p.edge_rowid
                ORDER BY p.edge_rowid
            """)
            for rowid, original_from, original_to, proposed_from, proposed_to, edge_type, properties, status, rule in records:
                endpoints = []
                for original, proposed in ((original_from, proposed_from), (original_to, proposed_to)):
                    if proposed in known:
                        endpoints.append(proposed)
                        continue
                    target, category, file_path = _node_for_missing(original, known, repo_root)
                    if target not in known and target not in synthetic:
                        metadata = {"origin_id": original, "resolution": category,
                                    "file_path": file_path or None, "source_sha256": source_hash}
                        synthetic[target] = (target, "file" if category == "heuristic_existing_file" else "unresolved",
                                             Path(file_path).name if file_path else original,
                                             json.dumps(metadata, ensure_ascii=False, sort_keys=True))
                        output.execute("INSERT INTO nodes VALUES (?, ?, ?, ?)", synthetic[target])
                    endpoints.append(target)
                    counts[category + "_edge_endpoints"] += 1
                output.execute("INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (rowid, endpoints[0], endpoints[1], edge_type, properties,
                                status, rule, original_from, original_to))
                counts[status + "_edges"] += 1
            output.commit()
            integrity = output.execute("PRAGMA integrity_check").fetchone()[0]
            fk_violations = len(output.execute("PRAGMA foreign_key_check").fetchall())
            edge_count = output.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            node_count = output.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    return {"status": "preview_only", "ready_for_cutover": False,
            "source": str(preview_db), "output": str(output_db),
            "source_sha256": source_hash, "output_sha256": sha256(output_db),
            "nodes": node_count, "edges": edge_count, "synthetic_nodes": len(synthetic),
            "counts": dict(counts), "integrity": integrity,
            "foreign_key_violations": fk_violations}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-db", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = materialize(args.preview_db, args.repo_root, args.output_db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["integrity"] == "ok" and report["foreign_key_violations"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
