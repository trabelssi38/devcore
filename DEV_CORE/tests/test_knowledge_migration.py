"""Knowledge import must be repeatable and keep dangling edges out of the graph."""

import json

from devcore_engine.migrate_to_unified_db import DevCoreMigrator


def test_knowledge_import_is_idempotent_and_checks_node_references(tmp_path):
    data_root = tmp_path / "shared"
    knowledge = data_root / "Knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "a.json").write_text(json.dumps({
        "nodes": [{"id": "a", "type": "file", "label": "A"}],
        "edges": [
            {"from": "a", "to": "b", "type": "link"},
            {"from": "a", "to": "missing", "type": "link"},
        ],
    }), encoding="utf-8")
    (knowledge / "b.json").write_text(json.dumps({
        "nodes": [{"id": "b", "type": "file", "label": "B"}],
        "edges": [{"from": "a", "to": "b", "type": "link"}],
    }), encoding="utf-8")

    migrator = DevCoreMigrator(data_root, tmp_path / "local.db")
    try:
        migrator.migrate_knowledge_graph()
        assert migrator.conn.execute("SELECT count(*) FROM kg_nodes").fetchone()[0] == 2
        assert migrator.conn.execute("SELECT count(*) FROM kg_edges").fetchone()[0] == 1
        migrator.migrate_knowledge_graph()
        assert migrator.conn.execute("SELECT count(*) FROM kg_edges").fetchone()[0] == 1
        migrator.conn.execute("PRAGMA foreign_keys=ON")
        assert migrator.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        migrator.conn.close()
