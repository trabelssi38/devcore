---
name: graphify
description: >-
  Utiliser quand la tâche implique de comprendre la structure d'une codebase,
  des relations entre composants, l'impact d'un refactoring, une analyse
  d'architecture, ou une review de code sur un projet inconnu. Graphify
  construit un knowledge graph interrogeable depuis code, SQL, docs, images,
  vidéos. Déclencher avec /graphify (Claude Code) ou $graphify (Codex).
  Complémentaire à Qdrant (sémantique) — graphify couvre les relations
  structurelles (qui appelle qui, quelles dépendances, quels clusters).
sources:
  - safishamsi/graphify v5 (adapté, client-agnostic)
  - https://github.com/safishamsi/graphify
compatibility: Claude Code · Codex Desktop · Gemini CLI · Antigravity · Qwen
install: pip install graphifyy && graphify install
output_dir: DEV_CORE_DATA\Vault\docs\graphify\
---

# Skill — Graphify DEV_CORE

## Vue d'ensemble

Graphify construit un knowledge graph structurel depuis n'importe quel corpus.
Il est **complémentaire à Qdrant**, pas redondant :

| | Qdrant | Graphify |
|---|---|---|
| Type | Vectoriel / sémantique | Structurel / relationnel |
| Question | "Trouve quelque chose de similaire à X" | "Comment X est connecté à Y et pourquoi" |
| Output | Embeddings + score similarité | Nœuds + arêtes + communautés |
| Usage | Memory first, patterns | Architecture review, impact analysis |

---

## Installation (une seule fois)

```bash
# Recommandé
uv tool install graphifyy && graphify install

# Ou
pipx install graphifyy && graphify install

# Ou pip classique
pip install graphifyy && graphify install
```

**Codex Desktop** — activer multi-agent dans `~/.codex/config.toml` :
```toml
[features]
multi_agent = true
```

**Claude Code** — graphify installe automatiquement :
- Un hook `PreToolUse` dans `settings.json` (intercepte les Bash search-like calls)
- Une section dans `CLAUDE.md` pour lire `GRAPH_REPORT.md` avant chaque question d'architecture

---

## Commandes par client

| Client | Commande | Notes |
|---|---|---|
| Claude Code | `/graphify <chemin>` | Hook auto-actif après install |
| Codex Desktop | `$graphify <chemin>` | Requiert `multi_agent = true` |
| Gemini CLI / Antigravity | `/graphify <chemin>` | Support natif |
| Qwen / autre | `graphify build <chemin>` | CLI direct si skill non supporté |

---

## Cas d'usage DEV_CORE

### 1. Onboarding sur un projet inconnu
```
/graphify C:\DEV_CORE\Tools\devcore
```
Produit en quelques minutes :
- `GRAPH_REPORT.md` — nœuds centraux, surprises, questions suggérées
- `graph.html` — visualisation interactive des dépendances
- `graph.json` — graph persistant interrogeable

### 2. Avant une review d'architecture (M-01 Claude)
```
/graphify .
# Claude lit automatiquement GRAPH_REPORT.md avant de répondre
# → Contexte structurel complet sans token overhead
```

### 3. Impact analysis avant refactoring (M-02 Codex)
```
$graphify .
# Puis demander : "Quels modules dépendent de router.py ?"
# → graph.json répond sans re-parcourir la codebase
```

### 4. Analyse multi-modale (docs + code + schémas SQL)
```
/graphify C:\DEV_CORE_DATA\Vault\docs\superpowers
# Indexe les plans, specs, docs Markdown + tout asset lié
```

### 5. Mise à jour incrémentale (mode --update)
```
graphify build --update .
# Ne ré-indexe que les fichiers modifiés (hash check)
# Compatible Obsidian sync — les mtime bumps ne déclenchent pas de re-extraction
```

---

## Outputs — structure DEV_CORE

```
DEV_CORE_DATA\Vault\docs\graphify\
├── [nom-projet]\
│   ├── GRAPH_REPORT.md    ← Lu automatiquement par Claude avant architecture
│   ├── graph.html         ← Visualisation interactive (ouvrir dans browser)
│   └── graph.json         ← Persistant, interrogeable par query_graph
└── devcore-platform\
    ├── GRAPH_REPORT.md
    ├── graph.html
    └── graph.json
```

---

## Intégration dans le cycle DEV_CORE

### Dans launch.ps1 — update incrémental au démarrage
```powershell
# Après les 7 étapes existantes — Étape optionnelle 8
$graphDir = "$DEV_CORE_DATA\Vault\docs\graphify\devcore-platform\graph.json"
if (Test-Path $graphDir) {
    Write-Host "  Graphify — mise à jour incrémentale..." -ForegroundColor Cyan
    Set-Location $DEV_CORE
    graphify build --update . --output "$DEV_CORE_DATA\Vault\docs\graphify\devcore-platform" 2>$null
    Write-Host "  Graph mis à jour" -ForegroundColor Green
}
```

### Dans mission_next.ps1 — hint graphify pour M-01 (architecture)
```powershell
# Si la mission est pour Claude et de type architecture/review
if ($current.agent -eq "claude" -and $current.title -match "spec|architecture|review") {
    $graphReport = "$DEV_CORE_DATA\Vault\docs\graphify\devcore-platform\GRAPH_REPORT.md"
    if (Test-Path $graphReport) {
        Write-Host "  Graph disponible — Claude chargera GRAPH_REPORT.md automatiquement" -ForegroundColor DarkGray
    }
}
```

### Dans le handoff (next_actions.md)
```markdown
### Graphify
Graph disponible : DEV_CORE_DATA\Vault\docs\graphify\[projet]\graph.json
Query suggérée : query_graph "router" pour voir les dépendances
```

---

## Requêtes graph utiles (dans Claude Code après /graphify)

```
# Après /graphify, Claude peut interroger le graph directement :

"Quels sont les nœuds centraux (god nodes) de ce projet ?"
→ Répond depuis GRAPH_REPORT.md — 0 tokens de codebase

"Quelles dépendances si je modifie router.py ?"
→ query_graph + get_neighbors("router") depuis graph.json

"Trouve le chemin entre cli.py et qdrant_queue.py"
→ shortest_path("cli", "qdrant_queue")

"Quels clusters architecturaux existent ?"
→ Leiden community detection — déjà calculé dans graph.json
```

---

## Inputs supportés

| Type | Extension | Méthode |
|---|---|---|
| Code Python | `.py` | Tree-sitter AST déterministe |
| PowerShell | `.ps1` | Tree-sitter AST |
| JavaScript/TypeScript | `.js/.ts` | Tree-sitter AST |
| SQL | `.sql` | AST — tables, vues, FK, JOIN mappés |
| Markdown / Docs | `.md` | LLM semantic extraction |
| YAML / Config | `.yml/.yaml` | Semantic extraction |
| PDF / Papers | `.pdf` | LLM semantic extraction |
| Images / Diagrams | `.png/.jpg` | Multimodal extraction |
| Vidéo | `.mp4` etc. | Whisper transcription + extraction |

**25 langages supportés** via Tree-sitter : Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, PowerShell, R, et plus.

---

## Tags sur les relations

| Tag | Signification |
|---|---|
| `EXTRACTED` | Relation trouvée directement dans le source |
| `INFERRED` | Inférence raisonnée (avec score de confiance) |
| `AMBIGUOUS` | Flagué pour review humaine |

---

## .graphifyignore — exclure les fichiers non pertinents

Créer `.graphifyignore` à la racine du projet (syntaxe gitignore) :

```
# DEV_CORE — graphifyignore
Cache/
__pycache__/
*.pyc
*.log
*.csv
Backups/
DEV_CORE_DATA/Logs/
DEV_CORE_DATA/Backups/
DEV_CORE_DATA/qdrant_storage/
node_modules/
.git/
```

---

## Erreurs fréquentes

- **`graphify: command not found`** → utiliser `uv tool install graphifyy` ou ajouter `~/.local/bin` au PATH (Linux/Mac), `%APPDATA%\Python\PythonXY\Scripts` au PATH (Windows)
- **Graph vide sur Codex** → vérifier `multi_agent = true` dans `~/.codex/config.toml`
- **Hook silencieux sur Claude Code v2.1.117+** → relancer `graphify install` (hook migré de Glob/Grep vers Bash)
- **Mtime bumps Obsidian déclenchent re-extraction** → utiliser `--update` (hash check activé, mtime ignoré)
