# DEV_CORE v10.0 - Documentation Complete

> **Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel
> 
> Gère la mémoire persistante, le cycle de vie des tâches (Tasks), les modes cognitifs (reasoning/coding/bulk), et les compétences (skills) réutilisables.

**Version** : 10.0
**Updated** : 2026-07-09
**Mode** : Single Client (Multi-Projets / Zero Switch)

---

## Table des matières

1. [Architecture générale](#1-architecture-générale)
2. [Structure des répertoires](#2-structure-des-répertoires)
3. [Workflow Tasks](#3-workflow-tasks)
4. [Modes cognitifs (9Router)](#4-modes-cognitifs-9router)
5. [Scripts PowerShell](#5-scripts-powershell)
6. [Système de Skills](#6-système-de-skills)
7. [Mémoire et Qdrant](#7-mémoire-et-qdrant)
8. [Installation et configuration](#8-installation-et-configuration)
9. [Commandes principales](#9-commandes-principales)
10. [Hermes Agent Integration](#10-hermes-agent-integration)
11. [Dashboard](#11-dashboard)
12. [Automation Hooks v6.1](#12-automation-hooks-v61)
13. [Token Optimization Stack](#13-token-optimization-stack)
14. [Architecture Multi-Projets](#14-architecture-multi-projets-zero-switch)
15. [Repowise MCP et scan continu](#15-repowise-mcp-et-scan-continu)
16. [Stabilisation v10](#16-stabilisation-v10)
17. [Service Layer v10.1](#17-service-layer-v101)

---

## 1. Architecture générale

```
┌──────────────────────────────────────────────────────────────────┐
│                      UTILISATEUR                                 │
│              dc ask "corrige le bug du parser"                   │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  dc.ps1 — Task Dispatcher (Single Client Mode)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │ ask.ps1  │ │launch.ps1│ │task_*.ps1    │ │ endday.ps1    │  │
│  └────┬─────┘ └──────────┘ └──────────────┘ └───────────────┘  │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  9Router — Mode Detection                                │    │
│  │  reasoning → Opus/o3 (32k budget)                        │    │
│  │  coding    → Sonnet/Codex (8k budget)                    │    │
│  │  bulk      → Haiku/Flash (16k budget)                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Memory Layer                                            │    │
│  │  MEMORY.md + Qdrant (decisions/patterns/lessons)         │    │
│  │  tasks.json (T-01 → T-04)                                │    │
│  │  Obsidian Vault                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### Principes clés

- **Single Client** : Un seul agent (Claude Code), pas de handoffs
- **Mode-based routing** : 9Router détecte automatiquement reasoning/coding/bulk
- **Tasks > Missions** : Workflow simplifié avec `tasks.json`
- **Memory-first** : Consulter Qdrant (score > 0.75) avant de régénérer
- **Skills-first** : Vérifier `skills_registry.json` avant toute tâche

---

## 2. Structure des répertoires

```
C:\devcore\
├── DEV_CORE\                    # Plateforme (code, scripts, skills)
│   ├── Scripts\                 # Scripts PowerShell
│   │   ├── dc.ps1              # CLI principale
│   │   ├── launch.ps1          # Démarrage journée
│   │   ├── endday.ps1          # Clôture + sync
│   │   ├── task_*.ps1          # Gestion tasks
│   │   ├── setup.ps1           # Installation initiale
│   │   ├── hermes-daemon.ps1    # Daemon Hermes
│   │   ├── hermes_cron.yaml     # Config cron
│   │   └── Auto\               # Scripts automatiques
│   ├── MCP\                    # MCP Servers
│   │   ├── devcore-scripts\    # Outils DEV_CORE
│   │   ├── qdrant-storage\     # Outils Qdrant
│   │   └── obsidian-vault\     # Outils Obsidian
│   ├── Skills\                 # Compétences réutilisables
│   │   ├── qdrant\
│   │   ├── obsidian\
│   │   ├── fabric-patterns\
│   │   ├── dev-methodology\
│   │   └── devcore\            # Integration Hermes
│   ├── Config\                 # Configuration
│   │   ├── CLAUDE.md           # Instructions Claude
│   │   ├── ROUTER.md           # Détection modes
│   │   ├── projects.json       # Registre projets DEV_CORE
│   │   ├── PATHS.md            # Chemins de référence
│   │   └── hermes_context.md   # Contexte Hermes
│   ├── Dashboard\              # Dashboard HTML
│   └── docs\                   # Documentation
│
└── DEV_CORE_DATA\              # Données persistantes
    ├── Memory\                 # Mémoire partagée
    │   ├── MEMORY.md          # Index central
    │   ├── DECISIONS.md       # Décisions actives
    │   ├── GLOBAL_STATE.md    # État global
    │   ├── tasks.json         # Tâches actives
    │   ├── Patterns\          # Patterns confirmés
    │   └── Scores\            # Scores de réutilisation
    ├── Obsidian\              # Vault Obsidian
    │   ├── 00_Global\
    │   ├── 01_DB\
    │   ├── 02_Python\
    │   ├── 03_Web\
    │   ├── 04_Android\
    │   └── 05_AI\
    ├── Logs\                  # Logs système
    │   ├── scripts\
    │   │   └── session_context.txt
    │   ├── router\
    │   └── token_reports\
    ├── Sessions\              # Sessions de travail
    ├── Backups\               # Sauvegardes auto
    └── qdrant_storage\        # Données Qdrant
```

---

## 3. Workflow Tasks

### Format tasks.json

```json
{
  "project": "cea_dashboard",
  "current_task": "T-01",
  "active_client": "claude",
  "tasks": [
    {
      "id": "T-01",
      "title": "Spec + Plan implementation",
      "mode": "reasoning",
      "status": "active",
      "steps_total": 3,
      "steps_done": 0,
      "depends_on": null,
      "steps": [...]
    }
  ]
}
```

### Cycle de vie

```
1. dc next task          → Charge T-01 (mode: reasoning)
2. Travail sur la tâche  → 9Router route vers Opus
3. git commit -m "feat: [description] [T-01]"
4. Hook post-commit      → Incrémente steps_done
5. dc task done          → Passe à T-02
```

### Dépendances

```
T-01 (reasoning) → T-02 (coding) → T-03 (bulk) → T-04 (reasoning)
```

---

## 4. Modes cognitifs (9Router)

### Détection automatique

| Mode | Mots-clés | Budget | Modèles |
|------|-----------|--------|---------|
| **reasoning** | spec, architecture, pourquoi, décide, analyse, review, conception, strategy, tradeoffs, debug (cause inconnue) | 32k | Opus, o3, kimi-k2-thinking |
| **coding** | implémente, code, fix, patch, test, refactor, écris la fonction, corrige, ajoute, modifie, TDD | 8k | Sonnet, Codex, glm-coder |
| **bulk** | tous les fichiers, migration entière, génère N tests, toutes les docs, batch, en masse, pour chaque fichier | 16k | Haiku, Flash, Qwen, glm |

### Skills par mode

- **reasoning** : `dev-methodology`, `fabric-patterns`, `qdrant`
- **coding** : `dev-methodology`, `python_api`, `web_ui`, `android_release`
- **bulk** : `fabric-patterns`, pas de validation intermédiaire

---

## 5. Scripts PowerShell

### Scripts principaux

| Script | Usage | Description |
|--------|-------|-------------|
| `dc.ps1` | `dc <command>` | CLI principale |
| `setup.ps1` | Une fois | Installation initiale + variables d'env |
| `launch.ps1` | Chaque jour | Démarrage journée |
| `endday.ps1` | Fin de journée | Clôture + sync mémoire |
| `task_next.ps1` | `dc next task` | Charge prochaine tâche |
| `task_done.ps1` | `dc task done` | Valide tâche + sync |
| `task_status.ps1` | `dc task status` | Dashboard tâches |
| `task_scan.ps1` | `dc task scan` | Scan git+spec+prompts |
| `task_sync.ps1` | `dc task sync` | Sync suggestions |
| `task_service.ps1` | `Path`, `Read`, `Add`, `Next`, `Complete`, `Step`, `Edit`, `Pause`, `Skip`, `Sync` | Service central pour lecture, mutation et transitions de taches |
| `memory_service.ps1` | `Path`, `ReadText`, `WriteText`, `AppendText`, `EnsureMemory`, `RotateMemory` | Service central pour chemins et fichiers memoire L2/L3 |
| `context_service.ps1` | `ScoreSources` | Service central pour scorer les sources de contexte |
| `gateway.ps1` | `dc check*`, `dc health*`, `dc verify*` | Gateway typée pour commandes validées |
| `diagnose.ps1` | `dc check`, `dc check --gate`, `dc check --fix --dry-run` | Diagnostic complet, gate release locale et simulation de reparations |
| `health_report.ps1` | `dc health`, `dc health --json` | Rapport court services, secrets, task board et memoire |
| `verify.ps1` | `dc verify --ci`, `dc verify --ci --json` | Agrégateur CI déterministe avec propagation des codes d'échec |
| `hermes-daemon.ps1` | `-Install|-Start|-Status` | Daemon Hermes |
| `ensure_repowise_mcp.ps1` | launch | Configure Repowise MCP pour Codex, Claude, Gemini/Antigravity et opencode |
| `ensure_repowise_watch.ps1` | launch / manuel | Démarre, vérifie ou arrête les watchers Repowise des projets déclarés |
| `repowise_watch_worker.ps1` | interne | Worker long-running `repowise update` + `repowise watch` par projet |

### Scripts automatiques (Auto/)

| Script | Fréquence | Description |
|--------|-----------|-------------|
| `weekly_maintenance.ps1` | Dimanche 23h | Maintenance hebdo |
| `memory_rotate.ps1` | Auto | Rotation mémoire (score < 0.5) |
| `qdrant_sync.ps1` | Auto | Sync Qdrant |
| `obsidian_sync.ps1` | Auto | Sync Obsidian |
| `task_git_scanner.ps1` | Launch + dc task scan | Détecte tags [T-XX] dans les commits git |
| `task_spec_parser.ps1` | dc task scan | Parse fichiers spec pour extraire tâches |
| `task_prompt_analyzer.py` | dc task scan | Analyse les accomplissements et actions de l'agent pour formuler des tâches réelles |
| `lesson_extractor.ps1` | endday | Extraction leçons depuis sessions |

---

## 6. Système de Skills

### Skills core actifs

| Skill | Source | Usage |
|-------|--------|-------|
| `qdrant` | qdrant/skills | Mémoire vectorielle |
| `obsidian` | kepano/obsidian-skills | Vault management |
| `fabric-patterns` | danielmiessler/Fabric | Patterns IA |
| `dev-methodology` | obra/superpowers | Méthodologie dev |

### Installation

Skills installés via symlinks dans `~/.claude/skills/` :

```powershell
# Créés automatiquement par adapt_client.ps1
~/.claude/skills/qdrant -> C:\devcore\DEV_CORE\Skills\qdrant
~/.claude/skills/obsidian -> C:\devcore\DEV_CORE\Skills\obsidian
```

---

## 7. Mémoire et Qdrant

### Architecture mémoire

```
MEMORY.md / LESSONS.md / PATTERNS.md
    ↓
Qdrant (4 collections)
    ├── decisions (768d cosine)
    ├── patterns (768d cosine)
    ├── lessons (768d cosine)
    └── codebase (768d cosine)
    ↓
Obsidian Vault (notes structurées)
```

### Workflow mémoire

1. **Consulter** : Interroger Qdrant (score > 0.75 = réutiliser)
2. **Créer** : Nouvelle décision/pattern/lesson
3. **Embedder** : contrat central `DEV_CORE\Config\embedding.json`
4. **Dimension** : les requêtes embeddings imposent `dimensions=768` avant tout upsert/search Qdrant.
5. **Stocker** : Qdrant + Obsidian + MEMORY.md
6. **Rotate** : Score < 0.5 archivé (weekly_maintenance)

### Memory Service

`memory_service.ps1` centralise les premiers contrats de fichiers memoire :

- `-Action Path` : resout les chemins `MEMORY`, `DECISIONS`, `LESSONS`, `PATTERNS`, `PERSONA` et `SCENARIO`.
- `-Action ReadText` : lit un fichier memoire en UTF-8.
- `-Action WriteText` : ecrit un fichier memoire en creant le repertoire parent.
- `-Action AppendText` : ajoute une entree textuelle a un fichier memoire.
- `-Action EnsureMemory` : initialise `MEMORY.md` si absent.
- `-Action RotateMemory` : archive puis tronque `MEMORY.md` selon `-MaxLines` et `-KeepLines`.

`memory_rotate.ps1` est maintenant un adaptateur vers `memory_service.ps1`. `memory_hierarchy.ps1` utilise le service pour les chemins et fichiers L2/L3, tandis que SQLite L0 et Qdrant L1 restent dans le script d'orchestration.

### Collections Qdrant

```bash
curl http://localhost:6333/collections
# {
#   "collections": [
#     {"name": "decisions"},
#     {"name": "patterns"},
#     {"name": "lessons"},
#     {"name": "codebase"}
#   ]
# }
```

---

## 8. Installation et configuration

### Prérequis

- Windows 10/11
- PowerShell 5.1+
- Python 3.8+
- Git
- Docker (pour Qdrant)
- Ollama (pour embeddings)

### Installation

```powershell
# 1. Cloner le repo
git clone <repo> C:\devcore

# 2. Lancer setup (en admin)
cd C:\devcore\DEV_CORE\Scripts
.\setup.ps1

# 3. Démarrer Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# 4. Démarrer Ollama
ollama serve
ollama pull nomic-embed-text

# 5. Vérifier
dc check
```

### Variables d'environnement

```
DEVCORE_PLATFORM_ROOT = C:\devcore\DEV_CORE
DEVCORE_DATA_ROOT     = C:\devcore\DEV_CORE_DATA
```

---

## 9. Commandes principales

### Tâches

```powershell
dc next task (nt)              # Prochaine tâche + mode auto
dc task done (td)              # Valide + sync mémoire auto
dc task status (ts)            # Dashboard tâches
dc task pause                  # Pause sans valider
dc task skip                   # Passe a la suivante
dc task scan                   # Scan git+spec+prompts -> suggestions
dc task sync                   # Sync suggestions dans tasks.json
dc new task [titre] -[mode]    # Ajoute une tâche
```

### Projet

```powershell
dc new project [nom] -stack [x] # Init + lier un projet
dc link project [nom]           # Lier un projet existant
```

### Cycle

```powershell
dc launch                       # Démarrage journée
dc endday                       # Clôture + sync auto
dc weekly                       # Maintenance hebdo
dc check                        # Diagnostic complet
dc ask [prompt]                 # Routing mode auto
dc rtk [commande]               # Execute et compresse la sortie (-40%)
```

---

## 10. Hermes Agent Integration

### Overview

Hermes Agent (Nous Research) est un agent IA autonome qui fonctionne en daemon et orchestre DEV_CORE via MCP (Model Context Protocol).

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Hermes Agent v0.13.0 (Daemon)                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  MCP Servers (3)                                           │  │
│  │  ├── devcore-scripts  (8 tools)                            │  │
│  │  ├── qdrant-storage  (6 tools)                             │  │
│  │  └── obsidian-vault  (6 tools)                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  DEV_CORE Scripts + Cron                                     │  │
│  │  ├── daily_launch   (10:00)                                │  │
│  │  ├── daily_endday   (04:00)                                │  │
│  │  └── weekly_maintenance (Sunday 05:00)                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### MCP Servers

| Server | Path | Outils |
|--------|------|--------|
| `devcore-scripts` | `MCP/devcore-scripts/server.py` | launch, endday, task_*, diagnose |
| `qdrant-storage` | `MCP/qdrant-storage/server.py` | collections, search, upsert, delete |
| `obsidian-vault` | `MCP/obsidian-vault/server.py` | daily_note, search, create_note |

### Installation Hermes

```powershell
# Cloner Hermes
git clone https://github.com/nousresearch/hermes-agent.git C:\devcore\hermes_temp
cd C:\devcore\hermes_temp

# Installer
uv venv .venv
uv pip install .
uv pip install pip

# Configurer API keys dans ~/.hermes/.env
```

### Configuration

`~/.hermes/config.yaml`:
```yaml
agent:
  name: "DEV_CORE Assistant"
  default_model: "anthropic/claude-sonnet-4-20250514"
model:
  provider: "openai"
  base_url: "https://api.anthropic.com/v1"
  default: "anthropic/claude-sonnet-4-20250514"
tools:
  terminal: {enabled: true}
  filesystem: {enabled: true}
context:
  - "C:/devcore/DEV_CORE/Config/hermes_context.md"
```

### Commandes Daemon

```powershell
.\hermes-daemon.ps1 -Install    # Installe scheduled tasks
.\hermes-daemon.ps1 -Uninstall  # Desinstalle
.\hermes-daemon.ps1 -Start      # Lance Hermes en background
.\hermes-daemon.ps1 -Stop       # Arrete Hermes
.\hermes-daemon.ps1 -Status     # Status + scheduled tasks
.\hermes-daemon.ps1 -Test       # Test configuration
```

### Cron Tasks (Windows Scheduled Tasks)

| Task | Schedule | Script | Description |
|------|----------|--------|-------------|
| `DEV_CORE_Daily_Launch` | 10:00 daily | `launch.ps1` | Demarrage quotidien |
| `DEV_CORE_Daily_Endday` | 04:00 daily | `endday.ps1` | Cloture + sync |
| `DEV_CORE_Weekly_Maintenance` | Sunday 05:00 | `weekly_maintenance.ps1` | Maintenance hebdo |
| `HERMES_Daemon` | AtLogOn | `hermes-daemon.ps1 -Start` | Redemarrage auto |

### Fichiers Hermes

| Fichier | Emplacement | Role |
|---------|------------|------|
| `hermes-daemon.ps1` | `Scripts/` | Daemon + installation tasks |
| `hermes_cron.yaml` | `Scripts/` | Configuration cron |
| `hermes_context.md` | `Config/` | Contexte DEV_CORE pour Hermes |
| `devcore/SKILL.md` | `Skills/` | Skill Hermes pour DEV_CORE |

### Test Integration

```powershell
.\test_hermes_integration.ps1 -All
```

### Test Results (v6.1)

| Component | Status |
|-----------|--------|
| Hermes v0.13.0 | PASS |
| 3 MCP Servers | PASS |
| 3 Scheduled Tasks | PASS |
| HERMES_Daemon | Requires admin |
| Qdrant (Docker) | PASS |
| Ollama | PASS |
| 6 Skills | PASS |
| 19 Scripts | PASS |

---

## 11. Detection automatique des taches

### Vue d'ensemble

DEV_CORE v6 inclut 3 scanners automatiques pour detecter les taches :

| Scanner | Source | Description |
|---------|--------|-------------|
| `task_git_scanner.ps1` | Commits git | Detecte les tags [T-XX] manquants dans tasks.json |
| `task_spec_parser.ps1` | Fichiers spec | Extrait sections (##, ###) et TODOs |
| `task_prompt_analyzer.py` | Sessions | Analyse les accomplissements réels et fichiers modifiés de l'agent |

### Workflow

```
dc task scan
    |
    +-- task_git_scanner.ps1   -> task_git_queue.jsonl
    +-- task_spec_parser.ps1   -> task_spec_queue.jsonl
    +-- task_prompt_analyzer.py -> task_prompt_queue.jsonl
    |
    v
dc task sync
    |
    +-- Lit les queues
    +-- Limite a 10 taches par sync
    +-- Ajoute dans tasks.json
    +-- Nettoie les queues
```

### Commandes

```powershell
# Scanner toutes les sources (git + spec + prompts)
dc task scan

# Synchroniser les suggestions dans tasks.json
dc task sync
```

### Output exemple

```
  DEV_CORE v6 -- TASK SCAN
  ========================================
  [1/3] Git scanner...
      [TACHE SANS COMMIT RECENT : T-01 - Spec + Plan]
  [2/3] Spec parser...
      [SECTION] 1. Intent [coding]
      [SECTION] 2. Design Position [reasoning]
  [3/3] Prompt analyzer...

  DEV_CORE v6 -- TASK SYNC
  ========================================
    0 suggestions depuis git
    234 suggestions depuis spec
    0 suggestions depuis prompt
  [INFO] Limite a 10 suggestions par sync
    + T-35 [coding] dev core fr parser design - 1. Intent
    + T-36 [reasoning] dev core fr parser design - 2. Design Position
  10 taches ajoutees a tasks.json
```

### Integration launch

Le launch inclut une detection automatique (etape 5/8) :

```powershell
# 5. Task Detection (git scanner)
Log "5/8 Task detection" "Cyan"
if (-not $QuickStart) {
    & "$DEV_CORE\Scripts\Auto\task_git_scanner.ps1" 2>$null
}
```

### Detection mode automatique

Les scanners detectent automatiquement le mode approprie :

| Mot-cles | Mode propose |
|----------|---------------|
| architecture, design, spec, decision, plan, review | `reasoning` |
| implement, code, fix, add, create, patch | `coding` |
| test, doc, readme, bulk, deploy, optimize | `bulk` |

---

## 12. Dashboard

**URL** : `file:///C:/devcore/DEV_CORE/Dashboard/index.html`
**API Server** : `http://localhost:20129`

### Sections

- **Métriques** : Client actif, tâche active, skills, score global
- **Infrastructure** : Scripts, 9Router, session context
- **Qdrant** : Collections + status
- **Ollama** : Embeddings + modèles
- **Obsidian** : Vault + structure
- **Mémoire** : MEMORY.md, DECISIONS.md, GLOBAL_STATE.md
- **Skills** : Core skills actifs
- **Tokens** : 3 couches d'optimisation
- **Tasks Pipeline** : T-01 → T-04 avec dépendances

### Mode de rafraîchissement dynamique

Le cockpit n'utilise plus de rafraîchissement complet de page (meta-refresh). À la place, il embarque une logique de rafraîchissement partiel par AJAX (poller à 15 secondes) :
- **Endpoint `/api/refresh`** : Interroge le serveur local Python (`dashboard_api.py` sur le port `20129`) qui compile et renvoie la vue complète en temps réel.
- **Comparaison DOM (DOM Diffing)** : Met à jour dynamiquement les parties modifiées de la page sans recharger l'intégralité du document HTML.
- **Rétention d'État** : Préserve la position de défilement (scroll), l'état d'ouverture des accordéons `<details>`, les tooltips et l'état des bulles cartographiques.
- **Indicateur de Synchronisation LED (#sync-indicator)** : Un voyant LED interactif dans le header affiche le statut de la synchronisation :
  - `Clignotant Violet` : Synchronisation en cours.
  - `Vert` : Synchronisation réussie et état à jour.
  - `Rouge` : Erreur de communication ou serveur API hors-ligne.

---

## 12. Automation Hooks v6.1

### Vue d'ensemble

Les automation hooks automatisent le workflow DEV_CORE sans intervention manuelle :

| Hook | Trigger | Actions |
|------|---------|---------|
| `post-commit.hook` | Après chaque commit | steps_done++, task_sync, auto-done si complete |
| `session_start.hook` | Demarrage session | task_scan, endday_check, gen_context |
| `session_end.hook` | Fin session | qdrant_sync, obsidian_sync, metrics |

### post-commit.hook

```powershell
# Exemple de workflow automatise
git commit -m "feat: add auth module [T-02]"

# Hook execute automatiquement :
# 1. Parse [T-XX] depuis commit message
# 2. Incrémente steps_done dans tasks.json
# 3. Si steps_done >= steps_total -> task_done.ps1
```

### session_start.hook

```powershell
# Au demarrage de session :
# 1. task_scan.ps1 — Detecte taches depuis git/spec/prompts
# 2. endday_check.ps1 — Verifie si clotureveille passee
# 3. gen_context.ps1 — Genere session_context.txt
```

### session_end.hook

```powershell
# A la fin de session :
# 1. qdrant_sync.ps1 — Sync decisions/patterns/lessons
# 2. obsidian_sync.ps1 — Update daily note
# 3. metrics.ps1 — Collecte KPIs (tokens, savings)
```

### Qdrant Sync (qdrant_sync.ps1)

Implementation technique :

```powershell
# 1. Embedding via Ollama
POST http://localhost:11434/api/embeddings
{"model": "nomic-embed-text", "prompt": "..."}

# 2. Stockage dans Qdrant (UUID auto-genere)
PUT http://localhost:6333/collections/{collection}/points
{"points": [{"id": "<uuid>", "vector": [...], "payload": {...}}]}
```

**Problemes resolus :**
- Locale française (virgule decimal) → `InvariantCulture`
- BOM UTF-8 → `UTF8NoBomEncoding`
- API Qdrant from PowerShell → Python subprocess + curl

---

## 13. Token Optimization Stack

### 6 couches de reduction

| Couche | Technologie | Reduction | Description |
|--------|-------------|-----------|-------------|
| 1 | CLAUDE.md terse | -69% | Instructions concises, caveman-compress |
| 2 | MEMORY.md compress | -46% | Memoire partagee structuree |
| 3 | MCP cache | -95% | Contexte des outils mis en cache |
| 4 | DEV_CORE RTK | -40% | Compression native des outputs (dc rtk / MCP) |
| 5 | Ghost finder audit | maintenance | Detection code mort |
| 6 | TOON tasks+skills | -90% | tasks.json compresse (5128 → 514 chars) |

### Reduction cumulee

```
~98% de reduction (tasks.json: 5128 → 514 chars)
```

### TOON Integration (v6.2)

TOON (Token-Oriented Object Notation) compresse l'état pour les prompts :

```json
// tasks.json (JSON, ~8.4KB)
{"project": "cea_dashboard", "current_task": "T-01", ...}

// tasks.toon (TOON format, ~2KB) - Gain ~75-90%
project: cea_dashboard
current_task: T-01
tasks[5]:
  - id: T-01
...
```
---

## 14. Architecture Multi-Projets (Zero Switch)

### Vue d'ensemble

DEV_CORE v6.3 introduit une architecture **Multi-Projets / Zero Config**, où chaque dépôt Git devient un univers de tâches autonome, sans nécessiter de configuration manuelle ou de changement de contexte explicite de la part de l'utilisateur.

### Fonctionnement "Zero Switch"

1. **Détection Automatique** : `Get-ActiveProject.ps1` détecte instantanément le contexte via `git rev-parse --show-toplevel` (ou le dossier courant en fallback).
2. **Isolation des Données** : Les fichiers d'état (`tasks.json`, `.toon`, fichiers de contexte) sont isolés dans `DEV_CORE_DATA\Memory\<nom_du_projet>\`.
3. **Mise en Cache Intelligente** : Le contexte projet est mis en cache dans les variables d'environnement (`$env:DEVCORE_ACTIVE_PROJECT_NAME`). Si l'utilisateur navigue vers un autre dossier (`cd`), le cache est automatiquement invalidé et mis à jour (`$env:DEVCORE_ACTIVE_PROJECT_PWD`).
4. **Scanners Isolés** : Les queues d'attente (`.jsonl`) de détection de tâches sont spécifiques à chaque projet pour éviter toute collision.
5. **Indépendance des IDEs** : Deux fenêtres d'éditeurs différentes travaillant sur deux projets distincts opèrent de manière 100% étanche grâce à l'isolation par processus.

### Workflow Multi-Projets

- Vous n'avez plus besoin d'exécuter `dc switch`. 
- Placez-vous simplement dans le dossier de votre projet (ex: `C:\Projet_A`).
- Toute commande `dc` (`dc task status`, `dc next task`, etc.) ciblera automatiquement le projet local sans interférer avec les autres projets.

---

## 15. Repowise MCP et scan continu

### Objectif

Repowise fournit l'intelligence codebase utilisée par les agents : wiki, symboles, graphes, risques, décisions, dead code et recherche enrichie. DEV_CORE garantit maintenant deux choses au lancement :

1. le MCP Repowise est déclaré dans les clients utilisés avec DEV_CORE ;
2. les projets déclarés sont scannés en continu par Repowise.

### Configuration MCP multi-client

`launch.ps1` exécute `ensure_repowise_mcp.ps1`.

Le script écrit une entrée `repowise` dans :

| Client | Fichier |
|---|---|
| Codex global | `C:\Users\trb_m\.codex\config.toml` |
| Codex projet | `C:\devcore\.codex\config.toml` |
| Claude Code | `C:\Users\trb_m\.claude\settings.json` |
| MCP projet | `C:\devcore\.mcp.json` |
| Gemini | `C:\Users\trb_m\.gemini\settings.json` |
| Antigravity | `C:\Users\trb_m\.gemini\antigravity\settings.json` et `mcp_config.json` |
| opencode | `C:\Users\trb_m\.config\opencode\opencode.json` |

Le binaire Repowise est résolu via `REPOWISE_EXE`, puis via les chemins Python utilisateur connus, puis via `PATH`.

### Couverture registry globale

DEV_CORE execute `ensure_repowise_web_languages.ps1` avant le lancement des watchers Repowise. Le script enrichit l'installation Python Repowise locale, donc la couverture s'applique a tous les repos scannes avec ce meme binaire, pas seulement au repo `devcore`.

Langages ajoutes en passthrough indexable :

| Famille | Extensions |
|---|---|
| HTML / web markup | `.html`, `.htm`, `.vue`, `.svelte`, `.astro` |
| CSS / stylesheets | `.css`, `.scss`, `.sass`, `.less`, `.pcss`, `.postcss` |
| PowerShell | `.ps1`, `.psm1`, `.psd1` |

Ces fichiers entrent dans le graphe, le git index, les metriques et les lectures MCP par plage (`get_symbol("path:line-line")`). Les reponses synthetiques `get_answer()` restent dependantes des pages wiki ; le watcher lance donc un scan structurel rapide puis un refresh docs controle quand HEAD change.

### Registre projets

Les projets surveillés sont définis dans :

```text
C:\devcore\DEV_CORE\Config\projects.json
```

Format :

```json
{
  "projects": [
    { "name": "devcore", "path": "C:/devcore" },
    { "name": "job_tracker", "path": "C:/src/job_tracker" }
  ]
}
```

`new_project.ps1` écrit aussi le champ `path` dans `.devcore\project.json` et met à jour ce registre pour les nouveaux projets ou projets liés.

### Scan continu

`launch.ps1` exécute `ensure_repowise_watch.ps1`.

Le script :

1. lit les projets dans `DEV_CORE_DATA\Memory\<projet>\tasks.json`;
2. résout leur chemin via `Config\projects.json`, `.devcore\project.json`, puis les racines candidates `C:\devcore` et `C:\src`;
3. démarre un `repowise_watch_worker.ps1` par projet ;
4. évite les doublons en inspectant les processus PowerShell déjà lancés ;
5. écrit un état dans `DEV_CORE_DATA\Logs\scripts\repowise_watch_state.json`.

Chaque worker exécute :

```powershell
repowise update --index-only --no-docs --no-workspace <project-path>
repowise update --docs --no-workspace <project-path>
repowise update --full --docs --no-workspace <project-path>  # si le wiki est vide
repowise watch --no-workspace <project-path>
```

`--index-only` maintient le graphe, les symboles, l'historique git et le dead-code rapidement. Le refresh docs avec `--docs` force la generation des pages wiki utilisees par `get_answer()`. Si le repo a ete initialise en fast/index-only et que le wiki est vide, `--full --docs` backfill les pages LLM. Le worker charge aussi `DEV_CORE\Config\gemini_api_key.txt` comme fallback Gemini, comme `gemini_router.py`. Si aucun provider/API key non interactif n'est disponible, il journalise `provider_missing`, continue le watch index-only et retente au prochain lancement. `--no-workspace` force un scope par projet declare et evite de scanner des sous-repos non declares.

### Commandes opérationnelles

```powershell
# Statut watchers
powershell -File C:\devcore\DEV_CORE\Scripts\ensure_repowise_watch.ps1 -StatusOnly

# Arrêter tous les watchers
powershell -File C:\devcore\DEV_CORE\Scripts\ensure_repowise_watch.ps1 -Stop

# Relancer les watchers
powershell -File C:\devcore\DEV_CORE\Scripts\ensure_repowise_watch.ps1
```

Logs :

```text
C:\devcore\DEV_CORE_DATA\Logs\scripts\repowise_watch\
```

### Comportement attendu

- `dc launch` configure MCP + watchers.
- Relancer `dc launch` ne crée pas de doublons.
- Les clients déjà ouverts doivent être redémarrés pour charger le MCP Repowise.
- Le scan continu met à jour l'index de code, pas les docs LLM.
- Les docs Repowise complètes restent une action explicite : `repowise update --docs <repo>`.

---

## 16. Stabilisation v10

### Objectif

DEV_CORE v10 stabilise le noyau avant la couche services : configuration propre, diagnostic exploitable, secrets gates et commandes observables.

### Commandes de controle

```powershell
dc check
dc check --gate
dc check --fix --dry-run
dc health
dc health --json
dc verify --ci
dc verify --ci --json
```

### Gates locales

- `dc check --gate` retourne `1` si `diagnose.ps1` detecte au moins un `FAIL`.
- `dc check --fix --dry-run` affiche les reparations `AutoFix` sans executer d'ecriture.
- Les `WARN` restent visibles mais ne bloquent pas la gate.
- `dc health --json` expose `overall`, `ok`, `warn`, `fail`, `duration_ms` et la liste des checks.
- `dc verify --ci` échoue sur un code enfant non nul ou un marqueur textuel `[FAIL]`.
- `dc verify --ci --json` produit un rapport versionné avec le détail de chaque check.
- `dc health --json` et `dc verify --ci --json` exposent `platform_version` depuis `DEV_CORE\Config\platform.json`.
- Le profil `dc verify --ci` est portable CI : lint PowerShell/Python, tests Python, tests PowerShell, secret scan, contrats et benchmarks.
- Le workflow GitHub Actions `.github/workflows/ci.yml` exécute les mêmes gates sur `windows-latest`.
- `benchmark_reference.ps1` produit un artefact JSON `DEV_CORE_DATA\Logs\benchmarks\benchmark-reference-*.json`, uploadé par GitHub Actions.
- Les benchmarks de référence actuels couvrent `dashboard_payload_size` et `verify_config_load`.
- Le profil local `verify.ps1 -Json` inclut un contrat Qdrant live : collections 768d, embedding 768d, upsert et search temporaires.
- `diagnose.ps1` integre le scan de secrets des fichiers suivis par Git.

### Contrat reseau local-first

- `DEV_CORE\Config\network.json` declare les hosts et ports des services locaux.
- Le host par defaut est `127.0.0.1`; `dashboard_api`, `gemini_router`, `headroom_proxy` et `repowise` sont declares en loopback.
- `dashboard_api.py` lit `DEVCORE_DASHBOARD_BIND`, puis `network.json`, puis retombe sur `127.0.0.1`.
- `gemini_router.py` lit `DEVCORE_GEMINI_ROUTER_BIND`, puis `network.json`, puis retombe sur `127.0.0.1`.
- Un bind public (`0.0.0.0`, `::` ou vide) exige `DEVCORE_ALLOW_PUBLIC_BIND=1`.
- `test_network_bind_contract.ps1` bloque les regressions vers un bind toutes interfaces implicite.

### Etat v10.0

- Aucun `Invoke-Expression` dans le chemin principal du CLI.
- `.env.example` remplace les fallbacks secrets hardcodes.
- La version plateforme affichée par les scripts runtime principaux est centralisée dans `DEV_CORE\Config\platform.json`.
- Repowise MCP et watchers restent configures au lancement pour les clients DEV_CORE.
- Les task boards sont isolees par projet dans `DEV_CORE_DATA\Memory\<project>\tasks.json`.

## 17. Service Layer v10.1

### Gateway

`gateway.ps1` introduit le premier adaptateur de Service Layer. Le script expose un registre de commandes typées et refuse les variantes inconnues avant d'appeler les scripts existants.

```powershell
powershell -File C:\devcore\DEV_CORE\Scripts\gateway.ps1 -List
powershell -File C:\devcore\DEV_CORE\Scripts\gateway.ps1 -List -Json
```

### Couverture actuelle

- `dc check`
- `dc check --fix`
- `dc check --gate`
- `dc check --fix --gate`
- `dc check --fix --dry-run`
- `dc check --fix --gate --dry-run`
- `dc health`
- `dc health --json`
- `dc verify --ci`
- `dc verify --ci --json`

`dc.ps1` reste l'interface utilisateur, mais délègue ces commandes au Gateway pour centraliser validation et dispatch.

### Task Service

`task_service.ps1` centralise les premiers contrats du cycle de taches :

- `-Action Path` : resout le chemin `DEV_CORE_DATA\Memory\<project>\tasks.json`.
- `-Action Read` : lit ou initialise la board projet.
- `-Action Add` : cree une tache avec ID, mode, dependance et worktree.
- `-Action Next` : active la prochaine tache eligible et met a jour `current_task`.
- `-Action Complete` : marque la tache active done, corrige les steps en `-Force`, et retourne la prochaine tache eligible.
- `-Action Step` : marque la prochaine step ou une step cible comme terminee et retourne la progression.
- `-Action Edit` : modifie les champs autorises d'une tache sans exposer l'ecriture board aux adaptateurs.
- `-Action Pause` : suspend la tache active ou cible et libere `current_task` si necessaire.
- `-Action Skip` : marque une tache comme ignoree et conserve sa trace dans la board.
- `-Action Sync` : fusionne les suggestions detectees depuis un fichier JSON, avec generation d'ID et deduplication par ID/titre.

`task_add.ps1`, `task_next.ps1`, `task_done.ps1`, `task_step_done.ps1` et `task_sync.ps1` sont maintenant des adaptateurs vers `task_service.ps1`, ce qui garde les mutations de `tasks.json` dans un seul service.

### Dashboard API stable

`dashboard_api.py` expose `GET /api/dashboard` comme contrat JSON stable pour le Cockpit :

- `schema_version` : version du contrat, actuellement `1`.
- `generated_at` : horodatage de generation.
- `sections.project_cards` : HTML de la liste projets.
- `sections.tasks_pipeline` : HTML de la pipeline taches/sessions.
- `sections.services_monitoring` : HTML infrastructure et services.
- `sections.automation_hooks` : HTML des hooks d'automatisation.
- `sections.token_activity_report` : HTML du rapport tokens.
- `task_details` : dictionnaire des details par cle projet/tache.
- `token_metrics` : metriques tokens parsees depuis `token_metrics_summary.json`.

`gen_dashboard.ps1 -Json` produit ce contrat. `template.html` lit maintenant `/api/dashboard` pour les rafraichissements dynamiques, au lieu de parser le HTML complet retourne par `/api/refresh`. L'ancien endpoint `/api/refresh` reste disponible en compatibilite.

### Model Pricing Registry

`DEV_CORE/Config/model_pricing.json` centralise les tarifs par modele pour le rapport de tokens.

- `models.<id>.pricing_per_million_usd.input` : prix input normal par million de tokens.
- `models.<id>.pricing_per_million_usd.cached_input` : prix input servi depuis le cache par million de tokens.
- `models.<id>.pricing_per_million_usd.output` : prix output par million de tokens.
- `aliases` : mapping des noms exposes par les clients/routeurs vers un profil canonique.
- `client_defaults` : modele par defaut a appliquer quand un client ne logge pas le modele pour un tour.
- `default_model` : profil fallback quand le log de session ne contient pas de modele.

`token_report.py` detecte les champs `model`, `model_slug`, `model_name`, `selected_model`, `requested_model` ou `original_model` dans les logs Codex, Claude, Antigravity/Gemini et opencode. Il lit aussi les blocs Antigravity `<USER_SETTINGS_CHANGE>` du type `Model Selection ... to Gemini 3.5 Flash (Medium)`. La resolution se fait pour chaque tour/prompt modele : modele explicite du payload, modele courant de la timeline, `client_defaults`, puis `default_model`. Le resume `token_metrics_summary.json` conserve les champs existants (`tokens`, `cache_hits`, `output_tokens`, `cost_usd`) et ajoute `models`, `pricing_profiles`, `model_usage` et `model_turns`. `model_turns[].source` indique si le modele vient du `payload`, de la `timeline`, de `client_default` ou du fallback `default_model`.

Pour le dashboard, le resume expose aussi des vues directes de cout par modele : `totals.cost_by_model` pour le global, `projects.<project>.cost_by_model` pour chaque projet, et `model_costs.global` / `model_costs.projects` comme contrat stable dedie aux graphiques.

`model_pricing_sync.py` verifie les sources de prix et ecrit `DEV_CORE_DATA/Logs/pricing/model_pricing_sync_report.json`. Par defaut, `endday.ps1` lance ce check avant le rapport token. Les catalogues structures JSON sont consideres `high` confidence et peuvent etre appliques avec `--apply`, `sync.auto_apply=true` ou `DEVCORE_PRICING_AUTO_APPLY=1`. Les extractions HTML/texte sont seulement signalees en `medium` confidence et ne sont pas appliquees sans `--allow-medium-confidence`.

### Context Service

`context_service.ps1` demarre le Context Engine v1 avec `-Action ScoreSources`.

Le contrat retourne :

- `schema_version` : version du contrat, actuellement `1`.
- `query` et `task_type` : demande courante.
- `include_threshold` : seuil d'inclusion.
- `sources[]` : sources triees par `score`, avec `tier`, `type`, `path`, `relevance`, `freshness`, `authority` et `included`.

Le score combine pertinence, fraicheur et autorite de source. `memory_hierarchy.ps1 -Action Query` affiche les sources incluses dans un bloc `CONTEXT SOURCE SCORES` avant les contenus L3/L2/L1/L0.

## Changelog v9

### 2026-07-08 — v9.2 Repowise MCP & Continuous Watch

- ✅ Configuration MCP Repowise automatique pour Codex, Claude Code, Gemini/Antigravity, opencode et `.mcp.json`.
- ✅ Ajout du registre `DEV_CORE\Config\projects.json`.
- ✅ Scan continu Repowise des projets déclarés via `ensure_repowise_watch.ps1`.
- ✅ Démarrage idempotent des watchers depuis `launch.ps1`.
- ✅ `new_project.ps1` persiste le chemin projet et met à jour le registre global.

### 2026-07-01 — v9.0 Port Separation, CORS Resolution & HTTP Cockpit Server

- ✅ **Résolution du conflit de port 20129** : Séparation définitive des ports de communication. Le serveur de routage intelligent `gemini_router.py` a été déplacé sur le port **`20130`** (avec mise à jour de toutes ses dépendances, notamment `headroom_start.ps1`, `qdrant_sync.ps1`, `memory_hierarchy.ps1`), libérant ainsi le port **`20129`** pour le serveur API Dashboard (`dashboard_api.py`).
- ✅ **Boutons d'Actions & Bégaiement CORS** : Remplacement des appels AJAX vers `localhost` par `127.0.0.1` pour contourner les comportements capricieux de résolution IPv6 sous Windows.
- ✅ **Cockpit disponible en HTTP** : Mise à jour de `dashboard_api.py` pour servir directement la page HTML du Cockpit sur l'URL racine `GET /`. Cela permet de charger le Cockpit via `http://127.0.0.1:20129/` au lieu du protocole local `file://`, évitant ainsi le blocage des requêtes AJAX dynamiques par les politiques de sécurité (CORS) des navigateurs modernes.
- ✅ **Nettoyage automatique** : Ajustement de `launch.ps1` pour purger automatiquement les anciens processus orphelins (notamment sur le port `8787` pour Headroom Proxy) lors du démarrage de la plateforme.

### 2026-05-24 — v9.0 Detached Daemon & Resilient API

- ✅ **Lancement autonome via WMI** : Remplacement de l'instable `Start-Process` dans `hermes-daemon.ps1` par la création de processus détachés à l'aide de la méthode WMI `Win32_Process.Create` de façon à ce que le démon de tick survive à la fermeture du terminal parent.
- ✅ **Prise en charge de flux stdout nuls/fermés** : Robustesse accrue du script `hermes_cron_tick.py` (le gestionnaire de logs `StreamHandler` n'est configuré que si `sys.stdout` n'est pas `None`, et l'action de vidage de flux `flush()` est désormais protégée par un `try...except OSError`).
- ✅ **Résilience de dashboard_api.py** : Ajout d'une capture propre du signal `ConnectionError` (ConnectionAborted, Reset, Broken Pipe) lors de l'envoi de la régénération d'index afin d'éviter tout crash secondaire ou affichage de tracebacks inutiles.
- ✅ **Nettoyage des étapes de tâches Git autonomes** : Retrait de l'étape générique redondante *"Execution et implémentation"* des tâches créées via `post-commit.hook`. Les tâches basées sur des commits Git n'ont plus d'étapes superflues, rendant leur affichage sur le Cockpit beaucoup plus épuré.

### 2026-05-22 — v7.2 Dynamic Partial Refresh & Live Cockpit API

- ✅ **Remplacement du Meta-Refresh par AJAX** : Retrait du tag HTML meta-refresh obsolète qui causait une réactualisation totale de la page toutes les 30 secondes, entraînant la perte du défilement, de l'état d'ouverture des accordéons `<details>`, et des tooltips.
- ✅ **Nouvel Endpoint `/api/refresh`** : Ajout d'une route `GET /api/refresh` dans le serveur API local `dashboard_api.py` (port `20129`) qui compile et retourne de manière dynamique le dernier contenu HTML généré.
- ✅ **Algorithme de DOM Diffing Partiel** : Implémentation d'une logique JavaScript robuste de comparaison et de mise à jour partielle intelligente dans `template.html`. Met à jour uniquement le contenu dynamique modifié tout en conservant l'état d'interaction de l'utilisateur (scroll, expansions `<details>`, bulles cartographiques).
- ✅ **Indicateur de Synchronisation (#sync-indicator)** : Ajout d'un voyant LED interactif dans le header du dashboard indiquant l'état en temps réel du rafraîchissement (Violet clignotant = rafraîchissement en cours, Vert = synchronisé, Rouge = erreur de communication avec le serveur).
- ✅ **Poller Intelligent** : Mise en place d'un intervalle de rafraîchissement dynamique à 15 secondes avec gestion d'erreurs et reprise automatique en cas de déconnexion/reconnexion de l'API.

### 2026-05-21 — v7.1 Robustesse du Cockpit & Simulation des Métriques de Cache

- ✅ **Résolution des Projets Fantômes** : Déploiement d'une liste noire insensible à la casse de dossiers système Windows (`Documents`, `Desktop`, `Downloads`, `OneDrive`, `System32`, `Users`, `Windows`, `Temp`, `AppData`, `Local`) dans `Get-ActiveProject.ps1` et `task_prompt_analyzer.py` pour éviter le chargement de projets fantômes lorsque les tâches d'arrière-plan s'exécutent depuis le répertoire utilisateur.
- ✅ **Métriques de prompt caching (85%)** : Clarification de l'estimation de tokens hors-ligne dans `token_report.py` (comme l'API de Gemini ne logge pas son statut de cache réel dans le fichier local `overview.txt`, le script applique un taux d'efficacité empirique constant de 85% correspondant à la rétention moyenne de contexte).

### 2026-05-21 — v7.0 Dynamic Agent-Action Task Extraction & Timezone Safety

- ✅ **Analyseur IA Réécrit en Python** : Migration complète de `task_prompt_analyzer.ps1` vers un analyseur Python hautement intelligent `task_prompt_analyzer.py`. Au lieu d'extraire des tâches à partir des requêtes brutes de l'utilisateur, le système formule désormais des titres et détails pertinents basés uniquement sur les actions et accomplissements réels de l'agent (`PLANNER_RESPONSE` et outils d'écriture de fichiers).
- ✅ **Champs de Détails et Historique du Dashboard** : Prise en charge complète du champ `details` pour chaque tâche, permettant d'afficher la description d'origine formatée dans le Dashboard HTML avec une bordure de couleur thématique et le style `white-space: pre-wrap`.
- ✅ **Horodatage Dynamique & fuseaux horaires** : Détermination dynamique des heures de début (`started_at`) et de fin (`completed_at`) calculées automatiquement à partir de la date de modification des répertoires de session d'Antigravity, avec formatage rigoureux respectant le fuseau horaire local (`+01:00`).
- ✅ **Synchronisation Robuste & Déduplication** : Mise à jour de `task_sync.ps1` pour déléguer la fusion des métadonnées et la déduplication par ID/titre au Task Service central.

### 2026-05-18 — v6.5 Cockpit API Operations & Task Synchronization

- ✅ **Boutons d'Actions Intégrés** : Ajout de boutons interactifs ("Clôturer" et "Supprimer") directement sur les tâches dans le Cockpit HTML.
- ✅ **Dashboard local API Server** : Implémentation d'un serveur API local Python (`dashboard_api.py`) sur le port 20129 pour traiter en temps réel la complétion et la suppression des tâches, avec démarrage automatique via le script `gen_dashboard.ps1`.
- ✅ **Nettoyage des Tâches devcore** : Nettoyage des anciennes tâches obsolètes `T-09` à `T-18` et renumérotation des nouvelles tâches avec synchronisation `.json` et `.toon`.
- ✅ **Synchronisation job_tracker** : Indexation et validation de l'historique des commits des 17 et 18 mai n'ayant pas de tags de tâches (`T-04` à `T-06`), avec validation visuelle autonome via un sous-agent de navigation (complétion de 100%).

### 2026-05-16 — Architecture Multi-Projets / Zero Config

- ✅ Refonte de l'architecture pour le support "Multi-Projets" simultané sans configuration.
- ✅ Isolation complète des données par projet (`Memory/<nom_du_projet>/tasks.json`).
- ✅ Détection dynamique via `Get-ActiveProject.ps1` avec système de cache d'environnement intelligent (`PWD`).
- ✅ Isolation des files d'attente des scanners automatiques (`task_*.jsonl`).
- ✅ Correction globale des chemins absolus remplacés par `$PSScriptRoot` pour une portabilité totale.
- ✅ Le système gère parfaitement l'utilisation concurrente via plusieurs fenêtres IDE (VS Code, etc.).
- ✅ **Correction des Hooks Antigravity** : Correction du script `install_universal_hooks.ps1` pour installer correctement les déclencheurs dans le dossier utilisateur d'Antigravity (`.gemini\antigravity`) au lieu de `.antigravity`.
- ✅ **Cycle des Tâches 100% Autonome** : Amélioration de `session_start.ps1` pour lier automatiquement un projet (`dc link project`) et créer la première tâche (`dc new task`) si aucun tableau de bord n'existe encore. Plus de blocage manuel pour l'initialisation.

### 2026-05-16 — Intégration Native RTK

- ✅ Migration de la logique RTK (Result Tool Kit) de 9Router vers DEV_CORE.
- ✅ Création du filtre universel `rtk.ps1` (Smart Truncate, minification, suppression des espaces inutiles).
- ✅ Ajout de la commande CLI `dc rtk <commande>` pour l'optimisation des outputs de l'agent.
- ✅ Middleware MCP (`server.py`) pour appliquer la compression aux retours des outils Hermes.
- ✅ Télémétrie et enregistrement des KPIs de compression dans `kpi.csv`.

### 2026-05-15 — Autonomie 100% v6.2

- ✅ Synchronisation Qdrant complète : 4 collections (`decisions`, `lessons`, `patterns`, `codebase`).
- ✅ Génération automatique de `CODEBASE_INDEX.md` pour l'indexation RAG du code.
- ✅ Extraction des leçons : Refonte de `lesson_extractor.ps1` (génère `LESSONS.md` et `PATTERNS.md` via l'historique de tâches et git).
- ✅ TOON Intégration 100% : Utilisation de `npx @toon-format/cli` encapsulé dans `toonify.ps1`.
- ✅ Auto-synchronisation `tasks.toon` à chaque étape du cycle de vie via hooks.
- ✅ Fix bugs Windows paths & Node.js experimental warnings filtering.
- ✅ Le système est désormais 100% autonome sur son cycle de données.

### 2026-05-14 — Automation Hooks v6.1

- ✅ `post-commit.hook` — steps_done auto-increment + task_sync + auto-done
- ✅ `session_start.hook` — task_scan + endday_check + gen_context
- ✅ `session_end.hook` — qdrant + obsidian + metrics sync
- ✅ Qdrant sync completement reimplémenté avec Python+curl (Ollama embeddings)
- ✅ TOON integration (tasks.json 5128 → 514 chars = -90%)
- ✅ `qdrant_sync.ps1` — InvariantCulture + UTF8NoBomEncoding fixes
- ✅ Dashboard mis à jour avec T-04 complet (2/2 steps)
- ✅ DECISIONS.md et MEMORY.md mis à jour avec hooks docs
- ✅ Documentation mise à jour

### 2026-05-13 — Hermes Agent Integration

- ✅ Hermes Agent v0.13.0 (Nous Research) installe
- ✅ 3 MCP servers : devcore-scripts, qdrant-storage, obsidian-vault
- ✅ hermes-daemon.ps1 avec scheduled tasks Windows
- ✅ hermes_cron.yaml avec schedule daily/weekly
- ✅ hermes_context.md pour contexte DEV_CORE
- ✅ devcore/SKILL.md pour integration Hermes
- ✅ test_hermes_integration.ps1 (47/48 tests pass)
- ✅ Documentation mise a jour
- ✅ Commits : `f685e45` -> `ac4eb79`

### 2026-05-12 — Detection automatique des taches

- ✅ `task_git_scanner.ps1` — Scan git commits pour tags [T-XX]
- ✅ `task_spec_parser.ps1` — Parse fichiers spec -> taches candidates
- ✅ `task_prompt_analyzer.py` — Formule intelligemment les tâches d'après les actions de l'agent en Python
- ✅ `dc task scan` — Lance les 3 scanners
- ✅ `dc task sync` — Synchronise dans tasks.json (max 10/sync)
- ✅ `launch.ps1` — Integration detection automatique (etape 5/8)
- ✅ Documentation mise a jour

### 2026-05-11 — Single Client Migration

- Missions → Tasks (workflow simplifié)
- Scripts `mission_*.ps1` archivés
- `tasks.json` avec modes (reasoning/coding/bulk)
- Tags git `[T-XX]` au lieu de `[M-XX]`
- CLAUDE.md, DECISIONS.md, MEMORY.md mis à jour
- Dashboard adapté pour tasks
- Structure déplacée : `C:\devcore\`
- Variables d'env mises à jour

### Architecture

- **Avant** : Multi-client (claude → codex → antigravity)
- **Après** : Single client (claude + 9Router)
- **Gain** : Simplicité, pas de handoffs, routing automatique

---

## Support

- **Issues** : GitHub repo
- **Diagnostic** : `dc check`
- **Logs** : `C:\devcore\DEV_CORE_DATA\Logs\`
- **Dashboard** : `C:\devcore\DEV_CORE\Dashboard\index.html`
