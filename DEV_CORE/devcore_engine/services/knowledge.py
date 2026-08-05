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

from devcore_engine.db import connect_db, init_db


class KnowledgeGraph:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()

    def get_stats(self) -> Dict[str, int]:
        cursor = self.conn.cursor()
        node_count = cursor.execute("SELECT COUNT(*) FROM kg_nodes;").fetchone()[0]
        edge_count = cursor.execute("SELECT COUNT(*) FROM kg_edges;").fetchone()[0]
        return {"nodes": node_count, "edges": edge_count}

    def add_node(self, node_id: str, node_type: str, label: str, properties: Optional[Dict[str, Any]] = None) -> None:
        props_json = json.dumps(properties or {})
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

    def add_edge(self, from_node: str, to_node: str, edge_type: str = "relates_to", properties: Optional[Dict[str, Any]] = None) -> None:
        props_json = json.dumps(properties or {})
        self.conn.execute(
            """
            INSERT INTO kg_edges (from_node, to_node, type, properties)
            VALUES (?, ?, ?, ?);
            """,
            (from_node, to_node, edge_type, props_json),
        )
        self.conn.commit()

    def impact_analysis(self, target_node_id: str, max_depth: int = 2) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        visited: Set[str] = set()
        queue = [(target_node_id, 0)]
        affected = []

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            node = cursor.execute("SELECT * FROM kg_nodes WHERE id = ?;", (current,)).fetchone()
            if node:
                affected.append({"id": current, "label": node["label"], "type": node["type"], "depth": depth})

            # Find incoming & outgoing edges
            edges = cursor.execute(
                "SELECT from_node, to_node FROM kg_edges WHERE from_node = ? OR to_node = ?;",
                (current, current),
            ).fetchall()

            for e in edges:
                neighbor = e["to_node"] if e["from_node"] == current else e["from_node"]
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        return {
            "target": target_node_id,
            "blast_radius_count": len(affected),
            "affected_nodes": affected,
        }


if __name__ == "__main__":
    kg = KnowledgeGraph()
    stats = kg.get_stats()
    print(f"[KnowledgeGraph] Total nodes: {stats['nodes']}, edges: {stats['edges']}")
    if stats['nodes'] > 0:
        sample_node = kg.conn.execute("SELECT id FROM kg_nodes LIMIT 1;").fetchone()[0]
        impact = kg.impact_analysis(sample_node)
        print(f"[KnowledgeGraph] Impact analysis for '{sample_node}': {impact['blast_radius_count']} nodes affected")
