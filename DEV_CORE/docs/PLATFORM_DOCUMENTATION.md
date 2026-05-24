# DEV_CORE v7 — Documentation Complète

> **Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel
> 
> Gère la mémoire persistante, le cycle de vie des tâches (Tasks), les modes cognitifs (reasoning/coding/bulk), et les compétences (skills) réutilisables.

**Version** : 7.2
**Updated** : 2026-05-22
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
27. [Token Optimization Stack](#13-token-optimization-stack)
28. [Architecture Multi-Projets](#14-architecture-multi-projets-zero-switch)

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
│   │   ├── graphify\
│   │   ├── fabric-patterns\
│   │   ├── dev-methodology\
│   │   └── devcore\            # Integration Hermes
│   ├── Config\                 # Configuration
│   │   ├── CLAUDE.md           # Instructions Claude
│   │   ├── ROUTER.md           # Détection modes
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
| `diagnose.ps1` | `dc check` | Diagnostic complet |
| `hermes-daemon.ps1` | `-Install|-Start|-Status` | Daemon Hermes |

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
| `graphify` | Custom | Graphes de connaissances |
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
3. **Embedder** : nomic-embed-text via Ollama
4. **Stocker** : Qdrant + Obsidian + MEMORY.md
5. **Rotate** : Score < 0.5 archivé (weekly_maintenance)

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

## Changelog v7

### 2026-05-24 — v7.3 Detached Daemon & Resilient API

- ✅ **Lancement autonome via WMI** : Remplacement de l'instable `Start-Process` dans `hermes-daemon.ps1` par la création de processus détachés à l'aide de la méthode WMI `Win32_Process.Create` de façon à ce que le démon de tick survive à la fermeture du terminal parent.
- ✅ **Prise en charge de flux stdout nuls/fermés** : Robustesse accrue du script `hermes_cron_tick.py` (le gestionnaire de logs `StreamHandler` n'est configuré que si `sys.stdout` n'est pas `None`, et l'action de vidage de flux `flush()` est désormais protégée par un `try...except OSError`).
- ✅ **Résilience de dashboard_api.py** : Ajout d'une capture propre du signal `ConnectionError` (ConnectionAborted, Reset, Broken Pipe) lors de l'envoi de la régénération d'index afin d'éviter tout crash secondaire ou affichage de tracebacks inutiles.

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
- ✅ **Synchronisation Robuste & Déduplication** : Mise à jour de `task_sync.ps1` pour traiter et fusionner intelligemment les métadonnées étendues (status, dates, détails, étapes), avec déduplication stricte par ID et par titre de tâche.

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
