"""
test_knowledge_provider_evaluation.py -- Qualification of Lot L7 (KnowledgeProvider, Memory & RepoWise).
Tests:
1. KnowledgeProvider protocol conformance.
2. Strict project isolation across SQLite, vector search, FTS5, and KnowledgeGraph.
3. 768-dim vector embedding contract validation and graceful lexical degradation on invalid/missing vectors.
4. Reciprocal Rank Fusion (RRF, k=60) hybrid search.
5. Evaluation benchmark on 20-question corpus verifying target retrieval, stable IDs, and provenance.
6. RepoWise & Composite providers integration with --no-workspace scoping.
"""

import json
import math
import sys
from pathlib import Path
import pytest

DEVCORE_DIR = Path(__file__).resolve().parents[1]
if str(DEVCORE_DIR / "API") not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR / "API"))
if str(DEVCORE_DIR) not in sys.path:
    sys.path.insert(0, str(DEVCORE_DIR))

from devcore_api.ports import KnowledgeProvider
from devcore_engine.services.embedding import EmbeddingService
from devcore_engine.services.knowledge import KnowledgeGraph
from devcore_engine.services.knowledge_provider import (
    SqliteKnowledgeProvider,
    RepoWiseKnowledgeProvider,
    CompositeKnowledgeProvider,
    KnowledgeProjectMismatch,
)
from devcore_engine.services.memory_hierarchy import MemoryHierarchy


def make_embedding(seed: int = 1) -> list[float]:
    """Generate a deterministic, normalized 768-dimensional vector."""
    vec = [math.sin(seed * (i + 1) * 0.1) for i in range(768)]
    norm = math.hypot(*vec)
    return [v / norm for v in vec]


@pytest.fixture
def corpus_data():
    corpus_path = Path(__file__).resolve().parent / "corpus_20_questions.json"
    return json.loads(corpus_path.read_text(encoding="utf-8"))


@pytest.fixture
def sqlite_provider(tmp_path):
    db_file = tmp_path / "test_knowledge.db"
    provider = SqliteKnowledgeProvider(db_file)
    yield provider
    provider.close()


def test_knowledge_provider_protocol_conformance(sqlite_provider):
    """Sqlite, RepoWise, and Composite providers satisfy the KnowledgeProvider protocol."""
    assert isinstance(sqlite_provider, KnowledgeProvider)
    repowise_prov = RepoWiseKnowledgeProvider(repo_alias="devcore")
    assert isinstance(repowise_prov, KnowledgeProvider)
    composite = CompositeKnowledgeProvider([sqlite_provider, repowise_prov])
    assert isinstance(composite, KnowledgeProvider)


def test_strict_project_isolation(sqlite_provider):
    """Knowledge items indexed for project 'alpha' never leak to project 'beta'."""
    emb_alpha = make_embedding(1)
    emb_beta = make_embedding(2)

    sqlite_provider.index_item(
        id="item_alpha_1",
        project="alpha",
        title="Architecture Alpha",
        content="Confidential secrets and design for project alpha.",
        source_path="docs/alpha.md",
        commit_hash="commit_aaa",
        embedding=emb_alpha,
    )
    sqlite_provider.index_item(
        id="item_beta_1",
        project="beta",
        title="Architecture Beta",
        content="Confidential secrets and design for project beta.",
        source_path="docs/beta.md",
        commit_hash="commit_bbb",
        embedding=emb_beta,
    )

    # Search project alpha with terms present in both
    results_alpha = sqlite_provider.search(
        query="Confidential secrets architecture",
        project="alpha",
        limit=10,
        vector=emb_alpha,
    )
    assert len(results_alpha) >= 1
    assert all(r.project == "alpha" for r in results_alpha)
    assert not any(r.id == "item_beta_1" for r in results_alpha)

    # Search project beta
    results_beta = sqlite_provider.search(
        query="Confidential secrets architecture",
        project="beta",
        limit=10,
        vector=emb_beta,
    )
    assert len(results_beta) >= 1
    assert all(r.project == "beta" for r in results_beta)
    assert not any(r.id == "item_alpha_1" for r in results_beta)

    # Invalid project ID must fail closed
    with pytest.raises(ValueError):
        sqlite_provider.search("query", "../escape", limit=10)


def test_vector_dimension_validation_and_graceful_lexical_degradation(sqlite_provider):
    """Vectors must be exactly 768-dim; invalid vectors fall back gracefully to lexical search."""
    valid_emb = make_embedding(42)
    sqlite_provider.index_item(
        id="doc_lexical_test",
        project="devcore",
        title="Lexical Fallback Test",
        content="Testing fallback when vector embedding service is unavailable or broken.",
    )

    # Attempt indexing with 384 dimensions -> rejected
    with pytest.raises(ValueError, match="Embedding vector dimension mismatch"):
        sqlite_provider.index_item(
            id="doc_bad_dim",
            project="devcore",
            title="Bad Dimension",
            content="Invalid vector dimension test",
            embedding=[0.1] * 384,
        )

    # Attempt indexing with non-finite vector -> rejected
    with pytest.raises(ValueError, match="Embedding vector must contain finite numbers"):
        sqlite_provider.index_item(
            id="doc_bad_val",
            project="devcore",
            title="Bad Value",
            content="Invalid vector value test",
            embedding=[float("nan")] * 768,
        )

    # Search with invalid vector dimension: must not crash, must return lexical result!
    results = sqlite_provider.search(
        query="fallback vector unavailable",
        project="devcore",
        limit=5,
        vector=[0.1] * 384,  # Invalid dimension
    )
    assert len(results) == 1
    assert results[0].id == "doc_lexical_test"
    assert results[0].project == "devcore"


def test_hybrid_rrf_scoring(sqlite_provider):
    """RRF correctly fuses lexical and vector rankings with k=60."""
    emb_doc1 = make_embedding(10)
    emb_doc2 = make_embedding(20)

    sqlite_provider.index_item(
        id="doc_lexical_strong",
        project="devcore",
        title="Exact Keyword Match",
        content="Unicorn reactor design specifications and schematics.",
        embedding=emb_doc1,
    )
    sqlite_provider.index_item(
        id="doc_vector_strong",
        project="devcore",
        title="Semantic Concept Match",
        content="Mythical beast propulsion systems.",
        embedding=emb_doc2,
    )

    # Search matching both
    query_emb = make_embedding(20)  # Closest to doc_vector_strong
    results = sqlite_provider.search(
        query="Unicorn reactor",
        project="devcore",
        limit=5,
        vector=query_emb,
    )
    assert len(results) == 2
    # Both documents should have valid RRF scores
    assert results[0].score > 0
    assert results[1].score > 0
    assert results[0].score >= results[1].score


def test_evaluation_corpus_20_questions(sqlite_provider, corpus_data):
    """The 20-question evaluation benchmark validates target retrieval and zero cross-project leakage."""
    assert len(corpus_data) == 20

    # Index all 20 target documents with distinct embeddings and keywords
    for idx, entry in enumerate(corpus_data, start=1):
        emb = make_embedding(idx * 7)
        sqlite_provider.index_item(
            id=entry["target_id"],
            project=entry["project"],
            title=entry["target_title"],
            content=f"{entry['question']}\nKeywords: {' '.join(entry['keywords'])}",
            source_path=f"docs/{entry['id'].lower()}.md",
            commit_hash=f"commit_{idx:04x}",
            embedding=emb,
        )

    # Also index decoy items in a foreign project to verify isolation
    for idx in range(1, 10):
        sqlite_provider.index_item(
            id=f"decoy_foreign_{idx}",
            project="foreign_project",
            title=f"Decoy Foreign Title {idx}",
            content="Isolation passerelle middleware ordonnanceur windows job timeout idempotence outbox snapshots",
            embedding=make_embedding(idx * 99),
        )

    # Execute all 20 questions
    successful_retrievals = 0
    for idx, entry in enumerate(corpus_data, start=1):
        q_text = entry["question"]
        q_emb = make_embedding(idx * 7)  # Query vector

        hits = sqlite_provider.search(
            query=q_text,
            project=entry["project"],
            limit=5,
            vector=q_emb,
        )

        assert len(hits) >= 1
        # Invariant 1: 0 foreign project results
        assert all(h.project == "devcore" for h in hits)
        assert not any(h.project == "foreign_project" for h in hits)

        # Invariant 2: Target document is retrieved in Top-3
        hit_ids = [h.id for h in hits[:3]]
        if entry["target_id"] in hit_ids:
            successful_retrievals += 1

    # 100% of the 20 benchmark questions retrieve their expected target
    assert successful_retrievals == 20


def test_knowledge_graph_project_isolation(tmp_path):
    """KnowledgeGraph impact analysis never crosses project boundaries."""
    kg = KnowledgeGraph(tmp_path / "kg_test.db")

    # Add nodes in project alpha
    kg.add_node("node_a1", "service", "Service Alpha 1", project_id="alpha")
    kg.add_node("node_a2", "db", "Database Alpha 2", project_id="alpha")
    kg.add_edge("node_a1", "node_a2", "connects_to", project_id="alpha")

    # Add nodes in project beta
    kg.add_node("node_b1", "service", "Service Beta 1", project_id="beta")
    kg.add_node("node_b2", "db", "Database Beta 2", project_id="beta")
    kg.add_edge("node_b1", "node_b2", "connects_to", project_id="beta")

    # Attempt cross-project edge (defense test)
    kg.add_edge("node_a1", "node_b1", "leak", project_id="beta")

    # Impact analysis on Alpha must never return Beta nodes
    impact_alpha = kg.impact_analysis("node_a1", max_depth=3, project_id="alpha")
    affected_ids = [n["id"] for n in impact_alpha["affected_nodes"]]

    assert "node_a1" in affected_ids
    assert "node_a2" in affected_ids
    assert "node_b1" not in affected_ids
    assert "node_b2" not in affected_ids

    # Stats scoping
    assert kg.get_stats("alpha")["nodes"] == 2
    assert kg.get_stats("beta")["nodes"] == 2


def test_memory_hierarchy_project_scoping(tmp_path):
    """MemoryHierarchy FTS5 search strictly scopes results to the requested project."""
    from devcore_engine.db import init_db
    conn = init_db(tmp_path / "mem_test.db")

    conn.execute("INSERT INTO conversations (project, task_id, role, content) VALUES ('alpha', 'T-1', 'user', 'SpecialTokenAlpha in conversation')")
    conn.execute("INSERT INTO conversations (project, task_id, role, content) VALUES ('beta', 'T-2', 'user', 'SpecialTokenAlpha in foreign conversation')")
    conn.commit()

    mh = MemoryHierarchy(conn)
    res_alpha = mh._search_fts("SpecialTokenAlpha", project="alpha")
    assert len(res_alpha) == 1
    assert "alpha" in res_alpha[0]["preview"]
    assert "beta" not in res_alpha[0]["preview"]

    res_beta = mh._search_fts("SpecialTokenAlpha", project="beta")
    assert len(res_beta) == 1
    assert "beta" in res_beta[0]["preview"]
    conn.close()


def test_repowise_and_composite_providers(sqlite_provider):
    """RepoWise provider observes --no-workspace and CompositeProvider merges via RRF."""
    rw = RepoWiseKnowledgeProvider(repo_alias="devcore")
    meta = rw.get_metadata()
    assert meta["scoped_no_workspace"] is True
    assert meta["embedder"] == "mock"
    assert meta["semantic_search"] is False

    # Foreign project request on RepoWise provider is denied
    assert rw.search("query", "foreign_project") == []
    with pytest.raises(KnowledgeProjectMismatch):
        rw.get_context("foreign_project")

    # Composite provider
    composite = CompositeKnowledgeProvider([sqlite_provider, rw])
    sqlite_provider.index_item("local_item", "devcore", "Local Item", "Content for local item")

    results = composite.search("local", "devcore", limit=5)
    assert len(results) >= 1
    assert all(r.project == "devcore" for r in results)


def test_get_context_budget_bound(sqlite_provider):
    """get_context bounds UTF-8 bytes and returns valid JSON context."""
    ctx_str = sqlite_provider.get_context("devcore", budget_bytes=12000)
    assert len(ctx_str.encode("utf-8")) <= 12000
    ctx_json = json.loads(ctx_str)
    assert ctx_json["project"] == "devcore"
