from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Scripts.inspect_fusion_sources import build_report, main


def _make_db(path: Path, *, broken_fk: bool = False) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys=OFF;
            CREATE TABLE projects(id TEXT PRIMARY KEY);
            CREATE TABLE tasks(id TEXT, project_id TEXT);
            CREATE TABLE kg_nodes(id TEXT PRIMARY KEY);
            CREATE TABLE kg_edges(from_node TEXT, to_node TEXT,
                                  FOREIGN KEY(from_node) REFERENCES kg_nodes(id),
                                  FOREIGN KEY(to_node) REFERENCES kg_nodes(id));
            INSERT INTO projects VALUES ('alpha');
            INSERT INTO tasks VALUES ('T-01', 'alpha');
            INSERT INTO kg_nodes VALUES ('node-a');
            INSERT INTO kg_edges VALUES ('node-a', 'missing');
            """
        )
        if broken_fk:
            connection.execute("CREATE TABLE legacy(value TEXT)")


def test_build_report_is_read_only_and_reports_fk_findings(tmp_path: Path) -> None:
    current = tmp_path / "current.db"
    other = tmp_path / "other.db"
    _make_db(current)
    _make_db(other, broken_fk=True)
    before = current.read_bytes()

    report = build_report(current, other)

    assert report["read_only"] is True
    assert report["merge_status"] == "inventory_only"
    assert report["sources"]["current"]["counts"]["tasks"] == 1
    assert "legacy" in report["comparison"]["tables_only_other"]
    assert report["blocking_findings"]["current_foreign_key_errors"]["total"] == 1
    assert current.read_bytes() == before


def test_main_writes_only_requested_report(tmp_path: Path, monkeypatch) -> None:
    current = tmp_path / "current.db"
    other = tmp_path / "other.db"
    output = tmp_path / "reports" / "inventory.json"
    _make_db(current)
    _make_db(other)
    monkeypatch.setattr(
        "sys.argv",
        ["inspect_fusion_sources", "--current-db", str(current), "--other-db", str(other), "--output", str(output)],
    )

    assert main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["merge_status"] == "inventory_only"
    assert payload["read_only"] is True
