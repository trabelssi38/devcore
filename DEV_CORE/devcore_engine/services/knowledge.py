"""
knowledge.py -- DEV_CORE Knowledge Graph Service (Python Native)
Replaces knowledge_graph.ps1 by building and querying code graph relationships in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import sqlite3
from typing import Any, Dict, List, Optional, Set

from devcore_engine.db import connect_db, init_db, get_db_path


class KnowledgeGraph:
    def __init__(self, conn: Optional[sqlite3.Connection | Path | str] = None):
        if isinstance(conn, (Path, str)):
            p = Path(conn)
            if p.is_dir():
                p = get_db_path()
            self.conn = connect_db(p)
        elif conn is not None:
            self.conn = conn
        else:
            self.conn = connect_db()


    def _has_project_column(self, table: str) -> bool:
        cursor = self.conn.cursor()
        cols = {row[1] for row in cursor.execute(f"PRAGMA table_info({table});").fetchall()}
        return "project_id" in cols

    def get_stats(self, project_id: Optional[str] = None) -> Dict[str, int]:
        cursor = self.conn.cursor()
        has_node_proj = self._has_project_column("kg_nodes")
        has_edge_proj = self._has_project_column("kg_edges")
        if project_id and has_node_proj and has_edge_proj:
            node_count = cursor.execute("SELECT COUNT(*) FROM kg_nodes WHERE project_id = ?;", (project_id,)).fetchone()[0]
            edge_count = cursor.execute("SELECT COUNT(*) FROM kg_edges WHERE project_id = ?;", (project_id,)).fetchone()[0]
            distinct_edge_count = cursor.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT from_node, to_node, type, properties FROM kg_edges WHERE project_id = ?);",
                (project_id,),
            ).fetchone()[0]
        else:
            node_count = cursor.execute("SELECT COUNT(*) FROM kg_nodes;").fetchone()[0]
            edge_count = cursor.execute("SELECT COUNT(*) FROM kg_edges;").fetchone()[0]
            distinct_edge_count = cursor.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT from_node, to_node, type, properties FROM kg_edges);"
            ).fetchone()[0]
        return {"nodes": node_count, "edges": edge_count, "edge_rows": edge_count, "distinct_edges": distinct_edge_count}

    def add_node(self, node_id: str, node_type: str, label: str, properties: Optional[Dict[str, Any]] = None, project_id: str = "devcore") -> None:
        props_json = json.dumps(properties or {})
        if self._has_project_column("kg_nodes"):
            self.conn.execute(
                """
                INSERT INTO kg_nodes (id, project_id, type, label, properties)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_id = excluded.project_id,
                    label = excluded.label,
                    properties = excluded.properties;
                """,
                (node_id, project_id, node_type, label, props_json),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO kg_nodes (id, type, label, properties)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label = excluded.label,
                    properties = excluded.properties;
                """,
                (node_id, node_type, label, props_json),
            )
        self.conn.commit()

    def add_edge(self, from_node: str, to_node: str, edge_type: str = "relates_to", properties: Optional[Dict[str, Any]] = None, project_id: str = "devcore") -> None:
        props_json = json.dumps(properties or {})
        if self._has_project_column("kg_edges"):
            self.conn.execute(
                """
                INSERT INTO kg_edges (project_id, from_node, to_node, type, properties)
                VALUES (?, ?, ?, ?, ?);
                """,
                (project_id, from_node, to_node, edge_type, props_json),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO kg_edges (from_node, to_node, type, properties)
                VALUES (?, ?, ?, ?);
                """,
                (from_node, to_node, edge_type, props_json),
            )
        self.conn.commit()

    def impact_analysis(self, target_node_id: str, max_depth: int = 2, project_id: Optional[str] = None) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        visited: Set[str] = set()
        queue = [(target_node_id, 0)]
        affected = []
        has_proj = self._has_project_column("kg_nodes") and project_id is not None

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            if has_proj:
                node = cursor.execute("SELECT * FROM kg_nodes WHERE id = ? AND project_id = ?;", (current, project_id)).fetchone()
            else:
                node = cursor.execute("SELECT * FROM kg_nodes WHERE id = ?;", (current,)).fetchone()
            if node:
                item = {"id": current, "label": node["label"], "type": node["type"], "depth": depth}
                if has_proj:
                    item["project_id"] = project_id
                affected.append(item)

            # Find incoming & outgoing edges
            if has_proj:
                edges = cursor.execute(
                    "SELECT from_node, to_node FROM kg_edges WHERE (from_node = ? OR to_node = ?) AND project_id = ?;",
                    (current, current, project_id),
                ).fetchall()
            else:
                edges = cursor.execute(
                    "SELECT from_node, to_node FROM kg_edges WHERE from_node = ? OR to_node = ?;",
                    (current, current),
                ).fetchall()

            for e in edges:
                neighbor = e["to_node"] if e["from_node"] == current else e["from_node"]
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        res = {
            "target": target_node_id,
            "blast_radius_count": len(affected),
            "affected_nodes": affected,
        }
        if project_id:
            res["project_id"] = project_id
        return res


if __name__ == "__main__":
    kg = KnowledgeGraph()
    stats = kg.get_stats()
    print(f"[KnowledgeGraph] Total nodes: {stats['nodes']}, edges: {stats['edges']}")
    if stats['nodes'] > 0:
        sample_node = kg.conn.execute("SELECT id FROM kg_nodes LIMIT 1;").fetchone()[0]
        impact = kg.impact_analysis(sample_node)
        print(f"[KnowledgeGraph] Impact analysis for '{sample_node}': {impact['blast_radius_count']} nodes affected")
