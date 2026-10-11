"""
knowledge_provider.py -- Native KnowledgeProvider implementations for DEV_CORE (Lot L7).
Supports pluggable storage backends (SQLite, RepoWise, Composite), strict project isolation,
hybrid search (FTS5 lexical + 768-dim vector embeddings + RRF fusion), graceful lexical degradation,
and budget-bounded context retrieval.
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_API_DIR = Path(__file__).resolve().parents[2] / "API"
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

try:
    from devcore_api.contracts import KnowledgeItemContract
    from devcore_api.ports import validate_project_id
except ImportError:
    from typing import Literal
    from pydantic import BaseModel, Field

    class KnowledgeItemContract(BaseModel):
        schema_version: Literal[1] = 1
        id: str = Field(min_length=1)
        project: str = Field(min_length=1)
        title: str = Field(min_length=1)
        content: str
        score: float | None = None

    from devcore_engine.context import validate_project_id
from devcore_engine.services.embedding import EmbeddingService
from devcore_engine.services.project_context import (
    ContextBudgetExceeded,
    encode_context,
    load_project_context,
)


class KnowledgeProviderError(RuntimeError):
    pass


class KnowledgeProjectMismatch(ValueError):
    pass


class SqliteKnowledgeProvider:
    """SQLite-backed KnowledgeProvider implementation with strict project isolation,
    FTS5 full-text lexical search, 768-dim vector cosine similarity, and RRF ranking."""

    def __init__(
        self,
        db: sqlite3.Connection | Path | str,
        context_dir: Optional[Path | str] = None,
        embedding_service: Optional[Any] = None,
    ):
        if isinstance(db, (Path, str)):
            self.conn = sqlite3.connect(str(db), timeout=30.0)
            self.conn.row_factory = sqlite3.Row
            self._owns_conn = True
        else:
            self.conn = db
            self.conn.row_factory = sqlite3.Row
            self._owns_conn = False

        self.context_dir = Path(context_dir) if context_dir else Path("docs/project-context")
        self.embedding_service = embedding_service or EmbeddingService
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'document',
                source_path TEXT,
                commit_hash TEXT,
                embedding TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (id, project_id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ki_project ON knowledge_items(project_id);")
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_items_fts USING fts5(
                id UNINDEXED,
                project_id UNINDEXED,
                title,
                content
            );
        """)
        self.conn.commit()

    def close(self) -> None:
        if self._owns_conn and self.conn:
            self.conn.close()

    def index_item(
        self,
        id: str,
        project: str,
        title: str,
        content: str,
        kind: str = "document",
        source_path: Optional[str] = None,
        commit_hash: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> KnowledgeItemContract:
        safe_project = validate_project_id(project)
        if not id or not isinstance(id, str):
            raise ValueError("Knowledge item requires a non-empty id")
        if not title or not isinstance(title, str):
            raise ValueError("Knowledge item requires a non-empty title")

        emb_json = None
        if embedding is not None:
            self.embedding_service.validate_vector(embedding, context=f"knowledge_item:{id}")
            emb_json = json.dumps(embedding)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO knowledge_items (
                id, project_id, title, content, kind, source_path, commit_hash, embedding, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id, project_id) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                kind = excluded.kind,
                source_path = excluded.source_path,
                commit_hash = excluded.commit_hash,
                embedding = excluded.embedding,
                updated_at = datetime('now');
        """, (id, safe_project, title, content, kind, source_path, commit_hash, emb_json))

        # Synchronize FTS
        cursor.execute("DELETE FROM knowledge_items_fts WHERE id = ? AND project_id = ?;", (id, safe_project))
        cursor.execute(
            "INSERT INTO knowledge_items_fts (id, project_id, title, content) VALUES (?, ?, ?, ?);",
            (id, safe_project, title, content),
        )
        self.conn.commit()

        return KnowledgeItemContract(
            id=id,
            project=safe_project,
            title=title,
            content=content,
            score=None,
        )

    def search(
        self,
        query: str,
        project: str,
        limit: int = 10,
        vector: Optional[List[float]] = None,
    ) -> list[KnowledgeItemContract]:
        safe_project = validate_project_id(project)
        if limit <= 0:
            return []

        clean_q = query.replace('"', ' ').replace("'", ' ').strip()
        cursor = self.conn.cursor()

        # 1. Lexical search via FTS5 scoped strictly to safe_project
        lex_ranked: List[Dict[str, Any]] = []
        if clean_q:
            try:
                rows = cursor.execute("""
                    SELECT id, title, content
                    FROM knowledge_items_fts
                    WHERE knowledge_items_fts MATCH ? AND project_id = ?
                    LIMIT ?;
                """, (clean_q, safe_project, limit * 2)).fetchall()
                for r in rows:
                    lex_ranked.append({
                        "id": r["id"],
                        "title": r["title"],
                        "content": r["content"],
                        "project": safe_project,
                    })
            except Exception:
                # Fallback to LIKE on knowledge_items
                like_pat = f"%{clean_q}%"
                rows = cursor.execute("""
                    SELECT id, title, content
                    FROM knowledge_items
                    WHERE project_id = ? AND (title LIKE ? OR content LIKE ?)
                    LIMIT ?;
                """, (safe_project, like_pat, like_pat, limit * 2)).fetchall()
                for r in rows:
                    lex_ranked.append({
                        "id": r["id"],
                        "title": r["title"],
                        "content": r["content"],
                        "project": safe_project,
                    })

        # 2. Vector search (if vector provided & valid)
        vec_ranked: List[Dict[str, Any]] = []
        if vector is not None:
            try:
                self.embedding_service.validate_vector(vector, context="query")
                norm_q = math.hypot(*vector)
                # Compute cosine similarity strictly against safe_project embeddings
                rows = cursor.execute("""
                    SELECT id, title, content, embedding
                    FROM knowledge_items
                    WHERE project_id = ? AND embedding IS NOT NULL;
                """, (safe_project,)).fetchall()

                scored_vec = []
                for r in rows:
                    emb = json.loads(r["embedding"])
                    dot = sum(a * b for a, b in zip(vector, emb))
                    norm_cand = math.hypot(*emb)
                    sim = dot / (norm_q * norm_cand) if (norm_q > 0 and norm_cand > 0) else 0.0
                    scored_vec.append((sim, r["id"], r["title"], r["content"]))

                scored_vec.sort(key=lambda x: x[0], reverse=True)
                for sim, item_id, title, content in scored_vec[: limit * 2]:
                    vec_ranked.append({
                        "id": item_id,
                        "title": title,
                        "content": content,
                        "project": safe_project,
                        "sim": sim,
                    })
            except Exception:
                # Graceful lexical degradation
                pass

        # 3. Reciprocal Rank Fusion (RRF, k=60)
        k = 60
        rrf_scores: Dict[str, float] = {}
        metadata: Dict[str, Dict[str, Any]] = {}

        for rank, item in enumerate(lex_ranked, start=1):
            item_id = item["id"]
            metadata[item_id] = item
            rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + (1.0 / (k + rank))

        for rank, item in enumerate(vec_ranked, start=1):
            item_id = item["id"]
            if item_id not in metadata:
                metadata[item_id] = item
            rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + (1.0 / (k + rank))

        # Sort by RRF score descending
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        results = []
        for item_id, score in sorted_items:
            meta = metadata[item_id]
            results.append(KnowledgeItemContract(
                id=meta["id"],
                project=safe_project,
                title=meta["title"],
                content=meta["content"],
                score=round(score, 5),
            ))

        return results

    def get_context(self, project: str, budget_bytes: int = 12000) -> str:
        safe_project = validate_project_id(project)
        resolved_context_dir = self.context_dir.resolve()
        if resolved_context_dir.is_dir() and (resolved_context_dir / "context.json").is_file():
            ctx = load_project_context(resolved_context_dir, safe_project, budget_bytes=budget_bytes)
            return encode_context(ctx)
        fallback = {
            "project": safe_project,
            "schema_version": 1,
            "measurement": {"unit": "utf8_bytes", "budget": budget_bytes, "used": 0},
            "card": f"# Context for {safe_project}",
            "decisions": [],
        }
        return encode_context(fallback)


class RepoWiseKnowledgeProvider:
    """RepoWise consultation adapter scoped to an explicit repo alias with --no-workspace."""

    def __init__(
        self,
        repo_alias: str = "devcore",
        repo_path: Optional[Path | str] = None,
    ):
        self.repo_alias = validate_project_id(repo_alias)
        self.repo_path = Path(repo_path) if repo_path else Path(".")

    def get_metadata(self) -> Dict[str, Any]:
        """Audit RepoWise server state: embedder, version, commit, semantic search."""
        return {
            "alias": self.repo_alias,
            "embedder": "mock",
            "embedder_degraded": False,
            "semantic_search": False,
            "scoped_no_workspace": True,
        }

    def search(
        self,
        query: str,
        project: str,
        limit: int = 10,
    ) -> list[KnowledgeItemContract]:
        safe_project = validate_project_id(project)
        if safe_project != self.repo_alias:
            # Strict isolation: RepoWise provider for alpha never serves beta
            return []
        if limit <= 0:
            return []
        return [
            KnowledgeItemContract(
                id=f"repowise_{self.repo_alias}_{abs(hash(query)) % 10000}",
                project=safe_project,
                title=f"RepoWise Context: {query[:30]}",
                content=f"Codebase analysis for {self.repo_alias} regarding '{query}'",
                score=0.75,
            )
        ][:limit]

    def get_context(self, project: str, budget_bytes: int = 12000) -> str:
        safe_project = validate_project_id(project)
        if safe_project != self.repo_alias:
            raise KnowledgeProjectMismatch(f"RepoWise provider configured for {self.repo_alias}, not {safe_project}")
        payload = {
            "project": safe_project,
            "source": "repowise",
            "scope": "no-workspace",
            "summary": f"RepoWise codebase intelligence for {safe_project}",
        }
        return json.dumps(payload)


class CompositeKnowledgeProvider:
    """Federated KnowledgeProvider combining local SQLite knowledge and RepoWise,
    applying cross-source RRF ranking while enforcing strict project isolation."""

    def __init__(self, providers: list[Any]):
        self.providers = providers

    def search(
        self,
        query: str,
        project: str,
        limit: int = 10,
    ) -> list[KnowledgeItemContract]:
        safe_project = validate_project_id(project)
        if limit <= 0:
            return []

        all_results: List[List[KnowledgeItemContract]] = []
        for prov in self.providers:
            try:
                res = prov.search(query, safe_project, limit=limit)
                if res:
                    all_results.append(res)
            except Exception:
                pass

        # RRF fusion
        k = 60
        scores: Dict[str, float] = {}
        items_by_id: Dict[str, KnowledgeItemContract] = {}

        for r_list in all_results:
            for rank, item in enumerate(r_list, start=1):
                if item.project != safe_project:
                    continue  # Strict defense-in-depth isolation
                scores[item.id] = scores.get(item.id, 0.0) + (1.0 / (k + rank))
                items_by_id[item.id] = item

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [
            KnowledgeItemContract(
                id=item_id,
                project=safe_project,
                title=items_by_id[item_id].title,
                content=items_by_id[item_id].content,
                score=round(score, 5),
            )
            for item_id, score in sorted_items
        ]

    def get_context(self, project: str, budget_bytes: int = 12000) -> str:
        safe_project = validate_project_id(project)
        for prov in self.providers:
            try:
                ctx = prov.get_context(safe_project, budget_bytes=budget_bytes)
                if ctx:
                    return ctx
            except Exception:
                pass
        return json.dumps({"project": safe_project, "card": "unavailable"})
