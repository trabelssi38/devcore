"""
memory_hierarchy.py -- DEV_CORE Memory Hierarchy & Vector Search (Python Native)
Replaces memory_hierarchy.ps1 & Qdrant HTTP calls by using sqlite-vec and FTS5 directly in devcore.db.
"""

from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import json
import sqlite3
from typing import Any, Dict, List, Optional

from devcore_engine.db import connect_db, init_db, HAS_SQLITE_VEC
from devcore_engine.services.memory import MemoryService


class MemoryHierarchy:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or init_db()
        self.memory_service = MemoryService(self.conn)

    def query(self, query_text: str, task_type: str = "devcore", query_vector: Optional[List[float]] = None) -> str:
        results = ["=== MEMORY HIERARCHY SEARCH RESULTS ==="]

        # 1. L3 Persona & L2 Scenario (Immediate load)
        persona = self.memory_service.get_text("PERSONA")
        if persona:
            results.append("\n[L3 Persona]")
            results.append(persona.strip())

        scenario = self.memory_service.get_text("SCENARIO", task_type)
        if scenario:
            results.append(f"\n[L2 Scenario: {task_type}]")
            results.append(scenario.strip())

        # 2. Parallel Search Simulation: FTS5 Full-Text Search + sqlite-vec Vector Search
        ranked_lists: List[List[Dict[str, Any]]] = []

        # Job 1: FTS5 Full-Text Search
        fts_items = self._search_fts(query_text)
        if fts_items:
            ranked_lists.append(fts_items)

        # Job 2: sqlite-vec Vector Search (if vector provided & HAS_SQLITE_VEC)
        if query_vector and HAS_SQLITE_VEC:
            vec_items = self._search_vectors(query_vector)
            if vec_items:
                ranked_lists.extend(vec_items)

        # 3. Reciprocal Rank Fusion (RRF) with k=60
        k = 60
        rrf_scores: Dict[str, float] = {}
        previews: Dict[str, str] = {}

        for r_list in ranked_lists:
            for rank, item in enumerate(r_list, start=1):
                item_id = item["id"]
                previews[item_id] = item["preview"]
                contribution = 1.0 / (k + rank)
                rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + contribution

        # Sort and extract Top 5
        top_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:5]

        if top_results:
            results.append("\n=== HYBRID RRF SEARCH RESULTS (Top 5) ===")
            for item_id, score in top_results:
                results.append(f"- [RRF Score: {score:.5f}] {previews[item_id]}")

        return "\n".join(results)

    def _search_fts(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        items = []

        # Clean query for FTS5 syntax
        clean_q = query_text.replace('"', ' ').replace("'", ' ').strip()
        if not clean_q:
            return items

        try:
            rows = cursor.execute(
                """
                SELECT project, task_id, content
                FROM conversations_fts
                WHERE content MATCH ?
                LIMIT ?;
                """,
                (clean_q, limit),
            ).fetchall()
            for r in rows:
                items.append({
                    "id": f"fts_{r['project']}_{r['task_id'] or 'main'}",
                    "type": "fts",
                    "preview": f"[{r['project']}/{r['task_id'] or 'main'}] {r['content'][:250]}...",
                })
        except Exception:
            # Fallback to LIKE if FTS expression fails
            rows = cursor.execute(
                """
                SELECT project, task_id, content
                FROM conversations
                WHERE content LIKE ?
                LIMIT ?;
                """,
                (f"%{clean_q}%", limit),
            ).fetchall()
            for r in rows:
                items.append({
                    "id": f"fts_{r['project']}_{r['task_id'] or 'main'}",
                    "type": "fts",
                    "preview": f"[{r['project']}/{r['task_id'] or 'main'}] {r['content'][:250]}...",
                })

        return items

    def _search_vectors(self, vector: List[float], limit: int = 5) -> List[List[Dict[str, Any]]]:
        cursor = self.conn.cursor()
        collections = ["decisions", "lessons", "patterns", "codebase"]
        result_lists = []

        vec_blob = json.dumps(vector)

        for col in collections:
            col_list = []
            try:
                table_name = f"vec_{col}"
                rows = cursor.execute(
                    f"""
                    SELECT id, preview, distance
                    FROM {table_name}
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?;
                    """,
                    (vec_blob, limit),
                ).fetchall()

                for pt in rows:
                    col_list.append({
                        "id": f"{col}_{pt['id']}",
                        "type": f"vec_{col}",
                        "preview": f"[L1 Vector: {col}] {pt['preview']}",
                    })
                if col_list:
                    result_lists.append(col_list)
            except Exception:
                pass

        return result_lists


if __name__ == "__main__":
    mh = MemoryHierarchy()
    res = mh.query("JWT auth", "auth")
    print(res[:500])
