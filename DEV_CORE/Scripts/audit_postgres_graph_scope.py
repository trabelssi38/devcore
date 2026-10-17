"""Compare the scoped historical graph with active PostgreSQL, read only.

The scoped SQLite candidate is immutable. This command does not modify either
database and never prints the PostgreSQL connection string or password.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import unquote, urlparse

import pg8000.dbapi


def _normalized_json(value: object) -> str:
    if isinstance(value, str):
        value = json.loads(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest_rows(cursor, count: int) -> str:
    digest = hashlib.sha256()
    seen = 0
    while rows := cursor.fetchmany(2048):
        for row in rows:
            values = list(row)
            values[-1] = _normalized_json(values[-1])
            digest.update(json.dumps(values, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8"))
            digest.update(b"\n")
            seen += 1
    if seen != count:
        raise ValueError(f"Graph stream count changed: {seen} != {count}")
    return digest.hexdigest()


def audit(candidate: Path, config: Path) -> dict:
    if not candidate.is_absolute() or not config.is_absolute():
        raise ValueError("Candidate and configuration paths must be absolute")
    candidate = candidate.resolve(strict=True)
    settings = json.loads(config.read_text(encoding="utf-8"))
    dsn = settings.get("environment", {}).get("DEVCORE_DATABASE_URL", "")
    parsed = urlparse(dsn)
    if parsed.scheme != "postgresql" or parsed.hostname != "127.0.0.1":
        raise ValueError("Expected a loopback PostgreSQL connection")
    source = sqlite3.connect(candidate.as_uri() + "?mode=ro&immutable=1", uri=True)
    target = pg8000.dbapi.connect(
        user=unquote(parsed.username or ""), password=unquote(parsed.password or ""),
        host="127.0.0.1", port=parsed.port or 5432, database=parsed.path.lstrip("/"))
    try:
        result = {"source": str(candidate), "database": parsed.path.lstrip("/")}
        source.execute("PRAGMA query_only=ON")
        for table, legacy, columns in (
            ("kg_nodes", "legacy_kg_nodes", "id,type,label,properties"),
            ("kg_edges", "legacy_kg_edges", "id,from_node,to_node,type,properties"),
        ):
            source_count = source.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            pg_cursor = target.cursor()
            pg_cursor.execute(f"SELECT count(*) FROM {legacy}")
            pg_count = pg_cursor.fetchone()[0]
            if source_count != pg_count:
                raise ValueError(f"{table} row count differs: {source_count} != {pg_count}")
            sqlite_cursor = source.execute(f"SELECT {columns} FROM {table} ORDER BY id")
            ordering = 'id COLLATE "C"' if table == "kg_nodes" else "id"
            pg_cursor.execute(f"SELECT {columns} FROM {legacy} ORDER BY {ordering}")
            source_digest = _digest_rows(sqlite_cursor, source_count)
            target_digest = _digest_rows(pg_cursor, pg_count)
            if source_digest != target_digest:
                raise ValueError(f"{table} content differs from PostgreSQL")
            result[table] = {"rows": source_count, "sha256": source_digest,
                             "identical_to_postgres": True}
        result["node_scope"] = dict(source.execute(
            "SELECT project_id,count(*) FROM kg_nodes GROUP BY project_id"))
        result["edge_scope"] = dict(source.execute(
            "SELECT project_id,count(*) FROM kg_edges GROUP BY project_id"))
        valid = source.execute("""SELECT count(*) FROM kg_edges e
            JOIN kg_nodes a ON a.id=e.from_node JOIN kg_nodes b ON b.id=e.to_node
            WHERE a.project_id=e.project_id AND b.project_id=e.project_id""").fetchone()[0]
        total = result["kg_edges"]["rows"]
        result["same_project_edges"] = valid
        result["cross_project_edges_for_quarantine"] = total - valid
        result["status"] = "postgres_graph_scope_audited"
        return result
    finally:
        target.rollback()
        target.close()
        source.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.candidate, args.config)
    except Exception as exc:
        print(json.dumps({"status": "postgres_graph_scope_refused", "reason": str(exc)}))
        return 1
    if args.output:
        if not args.output.is_absolute():
            parser.error("Output path must be absolute")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
