---
name: qdrant
description: >-
  Utiliser quand la tâche implique Qdrant : upsert de mémoire, recherche
  sémantique, diagnostic de performance, quantisation, sharding, déduplication,
  migration de modèle d'embedding, monitoring, ou toute opération sur les
  collections DEV_CORE. Déclencher pour qdrant_sync.ps1, mémoire vectorielle,
  recherche hybride, et maintenance hebdomadaire.
sources:
  - qdrant/skills (adapté, client-agnostic)
  - https://github.com/qdrant/skills
compatibility: Claude Code · Codex · Gemini CLI · Qwen · tout agent SKILL.md
qdrant_url: http://localhost:6333
collections: [decisions, lessons, patterns, codebase]
---

# Skill — Qdrant DEV_CORE

## Vue d'ensemble

Ce skill encode les décisions d'architecture Qdrant pour DEV_CORE.
Il répond au "quand ?" et "pourquoi ?", pas au "comment ?" (la doc Qdrant
couvre le "comment"). Organisé par symptômes, pas par features.

---

## Collections DEV_CORE

| Collection  | Contenu                        | Embedding model        | Distance |
|-------------|--------------------------------|------------------------|----------|
| `decisions` | Décisions architecturales      | nomic-embed-text       | Cosine   |
| `lessons`   | Leçons apprises, bugs          | nomic-embed-text       | Cosine   |
| `patterns`  | Patterns code et prompts       | nomic-embed-text       | Cosine   |
| `codebase`  | Index codebase (hybrid search) | nomic-embed-text       | Cosine   |

Config commune :
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

client.create_collection(
    collection_name="decisions",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)
```

---

## Opérations standard DEV_CORE

### Upsert (qdrant_sync.ps1)
```python
import hashlib
from qdrant_client.models import PointStruct

def upsert_safe(client, collection, text, metadata):
    # Déduplication par hash
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    existing = client.scroll(
        collection_name=collection,
        scroll_filter={"must": [{"key": "hash", "match": {"value": content_hash}}]},
        limit=1
    )
    if existing[0]:
        # Incrémenter usage_count uniquement
        point_id = existing[0][0].id
        client.set_payload(collection, {"usage_count": existing[0][0].payload["usage_count"] + 1}, [point_id])
        return "updated"

    embedding = get_embedding(text)  # Ollama nomic-embed-text
    client.upsert(collection_name=collection, points=[
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={**metadata, "content": text, "hash": content_hash, "usage_count": 1}
        )
    ])
    return "inserted"
```

### Recherche hybride (mémoire first)
```python
def memory_first_search(client, query, threshold=0.75):
    embedding = get_embedding(query)
    results = client.search(
        collection_name="decisions",
        query_vector=embedding,
        limit=5,
        score_threshold=0.5,
        with_payload=True
    )
    # Chercher aussi dans lessons et patterns
    for collection in ["lessons", "patterns"]:
        r = client.search(collection_name=collection,
                         query_vector=embedding, limit=3,
                         score_threshold=0.5, with_payload=True)
        results.extend(r)

    results.sort(key=lambda x: x.score, reverse=True)
    hit = next((r for r in results if r.score > threshold), None)
    return hit, results
```

---

## Diagnostic — Symptômes courants

### Recherche lente (était rapide avant)
**Cause probable** : trop de segments. Chaque query touche tous les segments en parallèle.
**Action** :
1. Vérifier : `GET /collections/{name}` → champ `segments_count`
2. Si > 5 segments → optimizer en retard
3. Fix : baisser `default_segment_number` à 2 dans la config collection
4. Baisser `hnsw_ef` à 64 si monté — il contrôle la précision, pas le débit
5. Activer scalar quantization si vecteurs > 10GB : réduit ~4x la taille mémoire

```python
client.update_collection("decisions", optimizer_config={
    "default_segment_number": 2,
    "indexing_threshold": 20000
})
```

### Résultats de qualité médiocre
**Cause probable dans 80% des cas** : mauvais modèle d'embedding, pas Qdrant.
**Action** :
1. Tester d'abord avec une recherche exacte (brute force) : si exact aussi mauvais → modèle
2. Vérifier que le même modèle est utilisé à l'insertion ET à la recherche
3. Pour DEV_CORE : toujours `nomic-embed-text` via Ollama local
4. Ne jamais mélanger deux modèles d'embedding dans la même collection

### Mémoire RAM saturée
**Cause** : vecteurs non quantifiés + page cache Linux (comportement normal OS).
**Action** :
1. Ne pas confondre page cache rempli et memory leak (comportement normal)
2. Si vecteurs dans RAM insuffisante → activer scalar int8 quantization avec `always_ram=true`
3. Résultat : compression ~4x, qualité conservée à > 95%

```python
from qdrant_client.models import ScalarQuantizationConfig, ScalarType, QuantizationConfig

client.update_collection("decisions", quantization_config=QuantizationConfig(
    scalar=ScalarQuantizationConfig(type=ScalarType.INT8, always_ram=True)
))
```

### Beaucoup de suppressions → dégradation
**Cause** : Qdrant utilise des soft deletes (tombstones). Les suppressions par filtre
accumulent des points morts que l'optimizer ne rattrape pas en flux continu.
**Action** :
- Ne PAS faire des bulk deletes nocturnes sur une collection active
- Stratégie recommandée pour DEV_CORE : **collection aliasing**
  - Créer des collections mensuelles : `decisions_2026_04`, `decisions_2026_05`
  - Pointer un alias `decisions` sur la collection active
  - Dropper l'ancienne collection au lieu de supprimer individuellement

```python
client.update_aliases(actions=[
    {"create_alias": {"collection_name": "decisions_2026_05", "alias_name": "decisions"}}
])
client.delete_collection("decisions_2026_04")  # Drop propre, zéro tombstone
```

### Index codebase obsolète
**Cause** : fichiers modifiés non ré-indexés.
**Action** : utiliser `index_codebase` incremental avec Merkle-tree (zilliztech/claude-context)
→ seuls les fichiers changés sont ré-embedés.

---

## Déduplication — weekly_maintenance.ps1

```python
def dedup_collection(client, collection_name):
    hashes_seen = set()
    to_delete = []

    all_points, next_offset = client.scroll(collection_name, limit=100, with_payload=True)
    while all_points:
        for point in all_points:
            h = point.payload.get("hash")
            if h in hashes_seen:
                to_delete.append(point.id)
            else:
                hashes_seen.add(h)
        if next_offset is None:
            break
        all_points, next_offset = client.scroll(collection_name, limit=100,
                                                 offset=next_offset, with_payload=True)
    if to_delete:
        client.delete(collection_name, points_selector=to_delete)
    return len(to_delete)
```

---

## Snapshot (backup endday.ps1)

```python
client.create_snapshot(collection_name="decisions")
client.create_snapshot(collection_name="lessons")
client.create_snapshot(collection_name="patterns")
# Fichiers dans : C:\DEV_CORE_DATA\Qdrant\snapshots\
```

---

## Ce qu'il ne faut PAS faire

- Ne pas tuner Qdrant avant de vérifier que l'embedding model est bon (c'est toujours lui le coupable)
- Ne pas mettre HNSW sur disque pour de la production latency-sensitive sans NVMe
- Ne pas supposer que la RAM est saturée quand le page cache est plein (comportement normal)
- Ne pas utiliser deux modèles d'embedding différents dans la même collection
- Ne pas faire de bulk delete nocturne → utiliser collection aliasing
