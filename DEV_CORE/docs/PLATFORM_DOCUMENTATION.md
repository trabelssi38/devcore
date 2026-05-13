# DEV_CORE v6 — Documentation Complète

> **Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel
> 
> Gère la mémoire persistante, le cycle de vie des tâches (Tasks), les modes cognitifs (reasoning/coding/bulk), et les compétences (skills) réutilisables.

**Version** : 6.1
**Updated** : 2026-05-13
**Mode** : Single Client (pas de handoffs multi-agents)

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
| `task_prompt_analyzer.ps1` | dc task scan | Analyse sessions pour suggérer tâches |
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
MEMORY.md (index)
    ↓
Qdrant (3 collections)
    ├── decisions (768d cosine)
    ├── patterns (768d cosine)
    └── lessons (768d cosine)
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
#     {"name": "lessons"}
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
| `task_prompt_analyzer.ps1` | Sessions | Analyse patterns verbe+action pour suggerer |

### Workflow

```
dc task scan
    |
    +-- task_git_scanner.ps1   -> task_git_queue.jsonl
    +-- task_spec_parser.ps1   -> task_spec_queue.jsonl
    +-- task_prompt_analyzer.ps1 -> task_prompt_queue.jsonl
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

**Auto-refresh** : 30 secondes

---

## Changelog v6

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
- ✅ `task_prompt_analyzer.ps1` — Analyse sessions pour suggestions
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
