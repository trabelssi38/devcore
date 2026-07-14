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
| `gateway.ps1` | `dc check*`, `dc health*`, `dc verify*`, `dc guide*` | Gateway typée pour commandes validées |
| `diagnose.ps1` | `dc check`, `dc check --gate`, `dc check --fix --dry-run` | Diagnostic complet, gate release locale et simulation de reparations |
| `guided_recovery.ps1` | `dc guide onboarding`, `dc guide diagnostic`, `dc guide recovery` | Guides operateur non destructifs pour onboarding, diagnostic et recovery |
| `health_report.ps1` | `dc health`, `dc health --json` | Rapport court services, secrets, task board et memoire |
| `verify.ps1` | `dc verify --ci`, `dc verify --ci --json` | Agrégateur CI déterministe avec propagation des codes d'échec |
| `hermes-daemon.ps1` | `-Install|-Start|-Status` | Daemon Hermes |
| `ensure_repowise_mcp.ps1` | launch | Configure Repowise MCP pour Codex, Claude, Gemini/Antigravity et opencode |
| `ensure_repowise_watch.ps1` | launch / manuel | Démarre, vérifie ou arrête les watchers Repowise des projets déclarés |
| `repowise_watch_worker.ps1` | interne | Worker long-running `repowise update` + `repowise watch` par projet |

### Documentation opérateur et API

| Document | Usage |
|---|---|
| `API_REFERENCE.md` | Référence API v1, endpoints publics, headers webhook GitHub, client `DevCoreApiClient` et contrat OpenAPI. |
| `OPERATOR_GUIDE.md` | Procédures opérateur pour first run, `dc launch`, guides onboarding/diagnostic/recovery, checks et endday. |
| `DEV_CORE/Schemas/openapi-v1.json` | Source de vérité OpenAPI 3.1 du gateway. |

Les deux documents sont couverts par `DEV_CORE/docs/test_operator_docs.py` et exécutés dans `ci_python_tests.ps1`.

### Tests de charge locaux

`DEV_CORE/Performance/devcore_load.py` fournit un harnais de charge contractuel CI-friendly pour API, SSE, workers et repositories DB. Il mesure des p95 locaux sur des boucles courtes via `test_load_contracts.py`; ce n'est pas un soak test production, mais un garde-fou de régression rapide pour Sprint 11.

### Tests de panne locaux

`DEV_CORE/Performance/devcore_chaos.py` fournit des drills non destructifs pour Sprint 11 : process kill simulé, restart DB simulé et Qdrant indisponible simulé. Les tests vérifient les contrats de reprise sans arrêter Docker, Qdrant ni la base réelle.

### Security review et SBOM

`DEV_CORE/Security/security_review.py` génère un inventaire SBOM CycloneDX-like depuis `package.json`, `Web/package.json` et `MCP/requirements.txt`. Le rapport `security-review.json` valide les contrôles minimaux de release : secret scan disponible, SBOM présent, inventaire dépendances et zéro finding critique ou élevé accepté. `test_security_review.py` couvre la stabilité JSON et l'inventaire npm/pip.

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

### Compatibilité Agent Skills

DEV_CORE supporte un contrôle de compatibilité avec la convention Agent Skills documentée par `anthropics/skills`.

```powershell
# Audit non bloquant pour les skills historiques DEV_CORE
powershell -File C:\devcore\DEV_CORE\Scripts\skill_lint.ps1 -Path C:\devcore\DEV_CORE\Skills\dev-methodology -AgentSpec

# Gate bloquant pour les nouveaux skills promus
powershell -File C:\devcore\DEV_CORE\Scripts\skill_lint.ps1 -Path C:\devcore\DEV_CORE\Skills\dev-methodology -StrictAgentSpec
```

Règles principales :

- un skill reste un dossier contenant un `SKILL.md`;
- le frontmatter doit exposer `name` et `description`;
- en mode strict, le nom doit correspondre au dossier et utiliser uniquement minuscules, chiffres et tirets;
- les contenus longs doivent être déplacés vers `references/`, `scripts/` ou `assets/`;
- le mode strict s’applique aux nouveaux skills, pas rétroactivement aux skills historiques contenant des underscores.

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
dc guide onboarding             # Guide premier lancement
dc guide diagnostic             # Guide diagnostic runtime
dc guide recovery               # Guide recovery non destructif
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
git clone https://github.com/nousresearch/hermes-agent.git C:\devcore\hermes
cd C:\devcore\hermes

# Installer
uv venv .venv
uv pip install .
uv pip install pip

# Configurer API keys dans le home Hermes natif.
# Windows Hermes v0.18+ : $env:LOCALAPPDATA\hermes\.env
# Anciennes installations : ~/.hermes/.env
```

### Configuration

`$env:LOCALAPPDATA\hermes\config.yaml`:
```yaml
agent:
  name: "DEV_CORE Assistant"
  default_model: "devcore-always-on"
model:
  provider: "custom"
  base_url: "http://127.0.0.1:20130/v1"
  default: "devcore-always-on"
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

Notes d'exploitation :
- `launch.ps1` demarre les services DEV_CORE principaux, mais ne lance pas le tick loop Hermes.
- `launch_all.ps1` demarre `launch.ps1` puis `hermes-daemon.ps1 -Start`.
- `hermes-daemon.ps1` resout Python dynamiquement dans cet ordre : `HERMES_PYTHON`, `DEVCORE_PYTHON`, `C:\devcore\hermes\.venv\Scripts\python.exe`, `python` du PATH, puis `py`.
- Si `hermes-daemon.ps1 -Test` affiche `Python binaire: NON TROUVE`, definir `HERMES_PYTHON` vers un `python.exe` valide ou corriger le PATH avant `-Start`.

### Cron Tasks (Windows Scheduled Tasks)

| Task | Schedule | Script | Description |
|------|----------|--------|-------------|
| `HERMES_Daemon` | AtLogOn | `hermes-daemon.ps1 -Start` | Redemarrage auto du tick loop |
| Jobs Hermes `%LOCALAPPDATA%\hermes\cron\jobs.json` | Cron expressions | wrappers DEV_CORE | Daily Launch, Endday, scan, sync, maintenance |

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

### Dashboard Repowise local

DEV_CORE démarre Repowise avec des ports explicites :

| Composant | URL |
|---|---|
| API Repowise | `http://127.0.0.1:7337` |
| UI Repowise | `http://127.0.0.1:3101` |
| Compatibilité navigateur | `http://localhost:7337` via proxy `::1:7337 -> 127.0.0.1:7337` |

Deux scripts rendent le dashboard robuste sous Windows :

- `ensure_repowise_web_proxy.ps1` patche le cache UI Repowise (`%USERPROFILE%\.repowise\web`) pour remplacer les rewrites Next.js `http://localhost:7337` par `http://127.0.0.1:7337`, en conservant l'UTF-8 sans BOM.
- `ensure_repowise_ipv6_proxy.ps1` lance `repowise_ipv6_proxy.py`, un proxy TCP local qui écoute `::1:7337` et redirige vers `127.0.0.1:7337`.

Raison : selon la configuration Windows/Node/Chrome, `localhost` peut être résolu en IPv6 (`::1`). Repowise écoute en IPv4. Sans proxy, l'UI peut se charger mais afficher `0 repositories registered` parce que ses appels API échouent.

Contrôles opérationnels :

```powershell
Invoke-WebRequest http://127.0.0.1:3101/api/repos
Invoke-WebRequest http://localhost:7337/api/repos
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 7337,3101 }
```

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
- Le dashboard Repowise doit exposer les repos via `http://127.0.0.1:3101/api/repos` et `http://localhost:7337/api/repos`.

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

### Authentification locale Dashboard API

- `dashboard_api.py` protege les endpoints API par token Bearer local.
- Les chemins publics restent limites a `/`, `/index.html` et `/api/status`.
- Le token est stocke hors configuration versionnee dans `DEV_CORE_DATA\Security\dashboard_api_token.json`.
- Le bootstrap local pour le cockpit est stocke dans `DEV_CORE_DATA\Security\dashboard_api_token.bootstrap`.
- `rotate_dashboard_token.ps1` regenere le token local et affiche la nouvelle valeur une seule fois dans le terminal.
- `test_dashboard_auth_contract.ps1` et `test_dashboard_api.py` bloquent les regressions : absence de token, mauvais schema `Authorization`, rotation et anciens tokens invalides.
- Les mutations dashboard n'utilisent plus GET :
  - cloture de tache : `POST /api/done` avec body JSON `{ "project": "...", "id": "T-..." }`;
  - suppression de tache : `DELETE /api/delete` avec body JSON `{ "project": "...", "id": "T-..." }`.
- Les anciens GET `/api/done` et `/api/delete` retournent `405 Method Not Allowed`.
- `test_dashboard_mutation_methods.ps1` bloque les regressions vers des mutations par query-string GET.

### CORS, CSRF et limites de taille

- `DEV_CORE\Config\security.json` declare la politique HTTP locale.
- CORS n'utilise plus `*` : les origines autorisees par defaut sont `http://127.0.0.1:20129` et `http://localhost:20129`.
- Les preflights `OPTIONS` refusent les origines non allowlist avec `403`.
- Les mutations API (`POST`, `DELETE`, `PATCH`, `PUT`) exigent `X-CSRF-Token`.
- Le cockpit injecte `Authorization: Bearer ...` et `X-CSRF-Token` sur les appels `/api/*`.
- La limite de body par defaut est `1048576` octets ; les depassements retournent `413 Payload Too Large`.
- `test_dashboard_security_contract.ps1` et `test_dashboard_api.py` couvrent allowlist CORS, CSRF et limites de taille.

### Canonicalisation des chemins et racines autorisees

- `dashboard_api.py` resout les chemins via `Path.resolve()` et verifie `relative_to()` avant acces fichier.
- Les fichiers runtime Dashboard restent confines sous `DEV_CORE_DATA`; les fichiers plateforme restent confines sous `DEV_CORE`.
- Les IDs projet utilises pour `DEV_CORE_DATA\Memory\<project>\tasks.json` refusent `/`, `\`, `:`, `..` et tout format hors `[a-zA-Z0-9._-]`.
- Le serveur MCP `obsidian-vault` resout les chemins relatifs depuis la racine du vault et bloque les traversals hors `DEV_CORE_DATA\Vault`.
- `test_dashboard_api.py` et `test_obsidian_vault_paths.py` couvrent les cas negatifs `../` et les chemins valides sous racine.

### Separation secrets, configuration versionnee et etat runtime

- `/api/settings` ne retourne plus les cles sensibles `gemini_api_key` et `anthropic_api_key`.
- `dashboard_api.py` ecrit la configuration publique dans `DEV_CORE\Config\settings.json`.
- Les secrets saisis via le dashboard sont stockes localement hors Git dans `DEV_CORE_DATA\Security\dashboard_settings_secrets.json`.
- L'etat runtime `active_client` est stocke dans `DEV_CORE_DATA\Runtime\active_client.txt`, avec lecture legacy de `DEV_CORE\Config\active_client.txt` pour compatibilite.
- `test_dashboard_api.py` bloque les regressions : secret dans settings publics, secret dans config versionnee, et etat runtime ecrit dans `Config`.

### Dashboard read model incremental

- `dashboard_read_model.ps1` construit un snapshot regenerable depuis les fichiers Event Bus `DEV_CORE_DATA\Bus\events\events-*.jsonl`.
- Le snapshot est ecrit dans `DEV_CORE_DATA\Dashboard\read_model.json`.
- Le modele expose un curseur (`total_events`, dernier evenement, fichier et ligne), des compteurs par type/source, les evenements recents, la tache active, les dernieres metriques et le dernier refresh dashboard.
- `dashboard_api.py` charge ce snapshot et l'ajoute au contrat JSON `/api/dashboard` via le champ `read_model`.
- `test_dashboard_read_model.ps1` couvre la reconstruction depuis des evenements `TaskCreated`, `MetricRecorded` et `DashboardRefreshed`.

### Dashboard resources paginees

- `GET /api/dashboard/resource?name=<resource>&page=<n>&page_size=<n>` expose une ressource paginee sans relancer `gen_dashboard.ps1`.
- La premiere ressource supportee est `read_model.events.recent`.
- `page` commence a 1 ; `page_size` est borne par defaut a 20 et au maximum a 100.
- La reponse contient `schema_version`, `resource`, `page`, `page_size`, `total`, `has_next` et `items`.
- `test_dashboard_api.py` couvre la pagination et verifie que l'appel n'invoque pas de sous-processus.

### Lectures dashboard sans sous-processus

- `GET /api/dashboard` lit `DEV_CORE_DATA\Dashboard\dashboard_payload.json` quand le cache existe.
- En absence de cache, `GET /api/dashboard` retourne un payload minimal avec `read_model` sans appeler PowerShell.
- `GET /api/refresh` retourne maintenant `405 Method Not Allowed`.
- La regeneration dashboard est explicite via `POST /api/refresh`, qui lance `gen_dashboard.ps1 -Json`, met a jour `dashboard_payload.json`, puis retourne le payload.
- `test_dashboard_api.py` bloque les regressions : les builders de lecture n'appellent pas `subprocess.run`.

### Cache HTTP dashboard

- `GET /api/dashboard` et `GET /api/dashboard/resource` renvoient un `ETag` stable calcule sur le JSON non compresse.
- Les clients qui renvoient `If-None-Match` avec le meme `ETag` recoivent `304 Not Modified` avec un corps vide.
- Les reponses JSON volumineuses sont compressees en `gzip` quand `Accept-Encoding` annonce `gzip`.
- Les headers `Cache-Control: private, max-age=5, must-revalidate` et `Vary: Accept-Encoding` encadrent le cache local sans exposer de donnees partagees.
- `test_dashboard_api.py` couvre le contrat `ETag`, `304` et compression gzip.

### Deltas dashboard par SSE

- `GET /api/dashboard/stream` ouvre un flux `text/event-stream` authentifie par le meme Bearer token que les autres endpoints prives.
- Le flux publie d'abord `dashboard.snapshot`, puis des evenements `dashboard.delta` quand le read model change.
- Les deltas listent les cles top-level modifiees et embarquent uniquement les fragments de `read_model` concernes.
- Le client dashboard consomme ce SSE via `fetch` streaming pour conserver les headers d'authentification injectes ; le polling periodique reste en fallback.
- `test_dashboard_api.py` couvre la detection de delta et le format SSE.

### Non-regression payload et latence dashboard

- `test_dashboard_api.py` contient un garde-fou sur un payload dashboard cache representatif.
- Le test verifie que la construction depuis cache reste sous 500 ms en local et que la reponse gzip reste sous 50 Ko pour un payload repetitif volumineux.
- Ce test complete les benchmarks de reference en CI avec un contrat rapide, deterministe et bloquant.

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

### FastAPI Gateway v1

`DEV_CORE\API\devcore_api` introduit le gateway HTTP moderne pour les prochains contrats de domaine.

- `POST /api/v1/integrations/github/webhook` accepte les webhooks GitHub signes avec `X-Hub-Signature-256`.
- Le secret est lu depuis `DEVCORE_GITHUB_WEBHOOK_SECRET`; si absent, l'endpoint retourne `503 github_webhook_secret_missing`.
- Les headers `X-GitHub-Event` et `X-GitHub-Delivery` deviennent le contrat stable minimal pour idempotence et routage futur.
- `DEV_CORE\API\test_github_webhooks.py` couvre ping signe, signature invalide et configuration manquante.

### Schedules persistants

- Le schema PostgreSQL expose `schedules` pour les definitions planifiees par projet et `schedule_history` pour tracer creations, executions, echecs et reprises.
- `schedules` stocke `cron`, `timezone`, `status`, `next_run_at`, `last_run_at` et `metadata`.
- `schedule_history` référence `schedule_id`, optionnellement `run_id`, puis conserve `event_type`, `status`, `details` et `occurred_at`.
- `SqlScheduleRepository` centralise `create_schedule`, `record_history` et `list_due_schedules`.
- `DEV_CORE\Database\test_schedules_persistence.py` verrouille le contrat schema + repository.

### Templates de workflows versionnes

- `DEV_CORE\Templates\workflow_templates.json` declare le registre versionne des workflows reutilisables.
- Le registre est date-versionne via `registry_version` et chaque template utilise une version `MAJOR.MINOR.PATCH`.
- Les templates initiaux couvrent `bugfix-safe`, `feature-sprint` et `release-hardening`.
- `DEV_CORE\Templates\workflow_templates.py` valide schema, unicite `id@version`, statut, inputs et steps.
- `DEV_CORE\Templates\test_workflow_templates.py` verrouille le contrat et le format JSON stable.

- `create_app()` construit l'application FastAPI.
- Le prefixe versionne est `/api/v1`.
- `GET /api/v1/health` retourne un contrat Pydantic stable : `schema_version`, `service`, `status`, `api_version`, `trace_id`.
- `GET /api/v1/contracts` expose le catalogue initial des contrats de domaine.
- Les contrats Pydantic initiaux couvrent `TaskContract`, `RunContract`, `DomainEvent`, `PluginContract`, `HealthContract`, `UserContract`, `OrganizationContract` et `WorkspaceContract`.
- `WorkspaceMembershipContract` definit l'appartenance utilisateur/workspace avec role borne a `owner`, `admin`, `developer` ou `viewer`.
- `WorkspaceQuotaContract` definit les limites non negatives `runs_per_day`, `model_tokens_per_day` et `storage_mb`.
- `GET /api/v1/tasks?project=<id>` lit la board taches via le port `TaskRepository`.
- OpenAPI est expose sur `/api/v1/openapi.json`; docs locales sur `/api/v1/docs`.
- Les erreurs HTTP et validations suivent une enveloppe stable : `schema_version`, `error.code`, `error.message`, `error.details`, `trace_id`.
- `DEV_CORE\API\run_api.py` demarre le gateway local sur `127.0.0.1:20131`.
- `DEV_CORE\API\test_api_v1.py` couvre health, OpenAPI versionne et enveloppe d'erreur.
- `DEV_CORE\API\test_domain_contracts.py` couvre les modeles de domaine et leur presence dans OpenAPI.
- `DEV_CORE\API\devcore_api\ports.py` introduit les premiers ports Python : `TaskRepository` et `HealthPort`.
- `FileTaskRepository` est l'adaptateur de compatibilite lecture seule vers `DEV_CORE_DATA\Memory\<project>\tasks.json`.
- `DEV_CORE\API\test_ports.py` couvre l'adaptateur fichier, l'injection de repository et l'erreur stable `task_board_not_found`.
- `DEV_CORE\API\compat_task_list.py` fournit un CLI de compatibilite base sur le port Python.
- `task_list.ps1` devient un wrapper PowerShell fin vers ce CLI et ne lit plus `tasks.json` directement.
- `test_task_list_adapter.ps1` bloque les regressions vers une lecture directe du JSON par PowerShell.
- `DEV_CORE\API\export_openapi.py` genere le schema versionne `DEV_CORE\Schemas\openapi-v1.json`.
- `DEV_CORE\API\clients\typescript\devcore-api-client.ts` fournit un client TypeScript sans dependance pour `health`, `contracts` et `tasks`.
- `DEV_CORE\API\test_openapi_client_generation.py` verrouille la generation OpenAPI et client TypeScript.
- `docs\API_VERSIONING_POLICY.md` definit les regles de compatibilite `/api/v1`, breaking change et regeneration OpenAPI/client.
- `DEV_CORE\API\test_api_versioning_policy.py` verrouille les routes versionnees, la coherence OpenAPI runtime/committe et la presence de la politique.

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

### PostgreSQL schema v1

`DEV_CORE\Database\postgres_schema_v1.sql` definit le contrat cible pour Sprint 4.

- Tables canoniques : `organizations`, `users`, `workspaces`, `workspace_memberships`, `projects`, `tasks`, `runs`, `events`, `plugins`, `audit_log`.
- Les relations utilisent `organization_id`, `workspace_id`, `project_id`, `task_id`, `run_id` et `plugin_id` avec cles etrangeres explicites.
- Les extensions evolutives passent par `metadata`, `payload` et `details` en `jsonb`.
- Les indexes operationnels couvrent les lectures courantes : taches par projet/statut, runs par tache/statut, evenements/audit par projet/date.
- `DEV_CORE\Database\test_postgres_schema_contract.py` verrouille le contrat avant l'introduction SQLAlchemy/Alembic.
- `DEV_CORE\Database\devcore_db\models.py` expose le meme contrat sous forme de `MetaData` SQLAlchemy.
- `DEV_CORE\Database\devcore_db\config.py` lit `DEVCORE_DATABASE_URL` avec un defaut local `127.0.0.1:5432/devcore`.
- `DEV_CORE\Database\alembic.ini` et `DEV_CORE\Database\alembic\env.py` initialisent les migrations Alembic locales.
- `DEV_CORE\Database\test_sqlalchemy_alembic_setup.py` verrouille la config locale, les tables core et le branchement Alembic.
- `DEV_CORE\Database\devcore_db\repositories.py` introduit `SqlTaskRepository` et `UnitOfWork`.
- `SqlTaskRepository` expose `list_tasks(project)` compatible avec les contrats API existants et `create_task(...)` pour les futures mutations transactionnelles.
- `UnitOfWork` commit automatiquement en succes, rollback en exception, et ferme toujours la session.
- `DEV_CORE\Database\test_repositories_transactions.py` couvre le mapping repository et les garanties transactionnelles sans exiger PostgreSQL local.
- `DEV_CORE\Database\devcore_db\importer.py` importe un `tasks.json` existant vers `organizations`, `users`, `workspaces`, `projects` et `tasks` avec une organisation et un workspace par defaut.
- L'import ajoute aussi une appartenance `usr_system` owner du workspace par defaut pour initialiser le modele RBAC sans bloquer le mode mono-utilisateur.
- L'import initialise `workspace_quotas` avec des quotas locaux par defaut pour runs, tokens modele et stockage.
- `DEV_CORE\Database\devcore_db\workspace_isolation.py` centralise les racines isolees par workspace : `Data`, `Secrets`, `Artifacts` et `Indexes` sous `DEV_CORE_DATA\Workspaces\<workspace_id>`.
- Le helper refuse les `workspace_id` invalides et toute resolution de chemin qui sort de la racine du workspace.
- Les noms de collections/index Qdrant peuvent etre derives par workspace avec le prefixe `<workspace_id>_<collection>`.
- `DEV_CORE\Database\devcore_db\audit_log.py` construit les requetes de lecture audit filtrables par workspace, projet, acteur, action, entite, dates et pagination bornee.
- Le service exporte les resultats audit en JSONL ou CSV avec colonnes stables et redaction recursive des champs sensibles (`secret`, `token`, `password`, `api_key`, `key`).
- `DEV_CORE\Database\test_tenant_isolation_matrix.py` verrouille l'isolation tenant de bout en bout : contrats API, schema DB via requetes audit, prefixes Qdrant et chemins d'artefacts.
- `DEV_CORE\Database\test_audit_log_service.py` couvre le contrat de requete workspace/project, les limites de pagination et les exports JSONL/CSV.
- L'import genere un `ReconciliationReport` avec `tasks_seen`, `tasks_imported`, `tasks_skipped`, `warnings` et statut `ok|partial`.
- Les taches invalides sont ignorees avec warning au lieu de bloquer toute la migration.
- `DEV_CORE\Database\test_importer_reconciliation.py` couvre l'import nominal et les erreurs de reconciliation.

### Dual-read tasks

`DualReadTaskRepository` dans `DEV_CORE\API\devcore_api\ports.py` controle la migration lecture JSON -> SQL.

- `DEVCORE_TASK_READ_MODE=json` : source legacy `tasks.json`, mode par defaut.
- `DEVCORE_TASK_READ_MODE=dual` : sert `tasks.json`, lit aussi SQL et signale les divergences sans bloquer.
- `DEVCORE_TASK_READ_MODE=sql` : cutover lecture SQL.
- En mode `dual`, une indisponibilite SQL retombe sur la source legacy pour ne pas bloquer l'API.
- `DEV_CORE\API\test_dual_read_cutover.py` couvre legacy, dual-read, fallback et cutover SQL.

### Database backup, restore, downgrade

- `DEV_CORE\Database\devcore_db\backup.py` construit des commandes explicites `pg_dump` et `pg_restore` sans shell interpolation.
- `DEV_CORE\Database\alembic\versions\0001_schema_v1.py` applique `postgres_schema_v1.sql` en upgrade.
- La migration descendante supprime les tables dans l'ordre inverse des dependances : `audit_log`, `events`, `plugins`, `runs`, `tasks`, `projects`, `workspaces`, `users`, `organizations`.
- `DEV_CORE\Database\test_backup_restore_downgrade.py` verrouille les commandes backup/restore et la presence du downgrade.

### Run state machine

### Plugin Manifest v2

`DEV_CORE\Plugins\manifest_v2.py` definit le contrat minimal des plugins DEV_CORE v2.

- `manifest_version` remplace `schema_version` pour éviter l'ambiguite entre schema interne et contrat public.
- Les champs obligatoires sont : `id`, `name`, `version`, `description`, `devcore_min_version`, `devcore_max_version`, `entrypoint`, `capabilities`, `permissions`.
- Les versions utilisent le format semver `MAJOR.MINOR.PATCH`.
- La compatibilite est refusee si la version courante DEV_CORE est hors bornes `devcore_min_version` / `devcore_max_version`.
- Les entrypoints supportes sont `command`, `python_module` et `powershell_script`.
- `DEV_CORE\Plugins\manifest_v2.schema.json` documente le schema JSON public.
- `DEV_CORE\Plugins\test_manifest_v2_contract.py` verrouille le comportement attendu avant migration des plugins internes.
- Les permissions sont explicites et default-deny avec quatre scopes seulement : `filesystem`, `network`, `secrets`, `process`.
- `filesystem.read/write` accepte uniquement des racines logiques connues : `workspace`, `project`, `data`, `cache`, `templates`, `logs`, `vault`.
- `network.allow` accepte uniquement des cibles explicites `host:port`; les wildcards sont refusees.
- `secrets.read` accepte uniquement des noms explicites de secrets style variable d'environnement.
- `process.allow` accepte uniquement des executables nommes et `process.allow_shell` doit rester `false`.
- `DEV_CORE\Scripts\plugin_service.ps1` execute les health checks dans un processus enfant isole : `WorkingDirectory` pointe vers `DEV_CORE_DATA\Plugins\<plugin_id>`, l'environnement est minimal et expose seulement les variables DEV_CORE plugin explicites.
- Le resultat de check publie `isolated_process`, `process_id`, `working_directory` et `environment_policy` pour audit dashboard.
- Un timeout tue le processus enfant et son arbre quand la plateforme le supporte.
- L'installation calcule et persiste `package_integrity.algorithm`, `manifest_sha256`, `package_sha256`, `verified` et `verified_at`.
- Si un manifeste declare `package_integrity.manifest_sha256` ou `package_integrity.package_sha256`, l'installation refuse le package si le checksum ne correspond pas.
- La provenance installee conserve `source`, `publisher`, `installed_by`, `source_manifest_path` et `package_root`.
- L'installation plugin est atomique : le manifeste normalise est d'abord ecrit dans `DEV_CORE_DATA\Plugins\staging`, puis deplace vers `installed`.
- En cas d'echec pendant l'installation, `plugin_service.ps1` restaure le repertoire installe et le registre depuis un snapshot rollback.
- Les migrations declarees dans `capabilities.migrations` sont normalisees et auditees dans `plugin.migrations` avec `applied_count`, `items`, `status` et `applied_at`.
- Les quatre plugins internes `python-fastapi`, `web-react`, `android-gradle` et `notifications-webhook` sont declares en Manifest v2.
- `notifications-webhook` expose `notifications:send` et les hooks `task.done`, `run.failed`, `schedule.failed` avec permissions reseau explicites vers `hooks.slack.com:443` et `outlook.office.com:443`.
- Les secrets de notification restent hors depot : `SLACK_WEBHOOK_URL` et `TEAMS_WEBHOOK_URL` sont declares comme secrets lisibles par le plugin.
- `plugin_service.ps1` traduit les scopes v2 `permissions.filesystem.write` en racines d'ecriture internes pour conserver la compatibilite d'installation.
- `DEV_CORE\Scripts\test_internal_plugins.ps1` verifie Manifest v2, les quatre scopes de permission, `allow_shell=false`, l'installation et le diagnostic sans violation de scope.

`DEV_CORE\API\devcore_api\run_state.py` definit les transitions durables des runs.

- Etats actifs : `queued`, `running`.
- Etat suspendu : `paused`.
- Etats terminaux : `succeeded`, `failed`, `cancelled`, `timed_out`.
- Transitions autorisees : `queued/start`, `queued/cancel`, `queued/pause`, `running/succeed`, `running/fail`, `running/timeout`, `running/cancel`, `running/pause`, `paused/resume`, `paused/cancel`.
- Les transitions invalides levent `InvalidRunTransition`.
- `DEV_CORE\API\test_run_state_machine.py` verrouille les transitions et les etats terminaux.

### Execution worker

`DEV_CORE\API\devcore_api\worker.py` extrait l'execution des runs hors du processus HTTP.

- `Worker.run_once()` reclame un run `queued`, applique `start`, execute un handler, puis applique `succeed` ou `fail`.
- Sans run disponible, le worker retourne `idle`.
- Un run `paused` est ignore par `run_once()` et peut etre repris via `resume_after_restart()`.
- Le worker depend d'un port `RunRepository`, pas de FastAPI.
- `DEV_CORE\API\test_worker_execution.py` couvre succes, echec handler et absence de run.
- `DEV_CORE\API\test_run_pause_resume_cancel.py` couvre pause, annulation et reprise apres redemarrage.

### Transactional outbox

`DEV_CORE\Database\devcore_db\outbox.py` ajoute une outbox transactionnelle pour publier les effets apres commit.

- Table `outbox_messages` : `id`, `topic`, `payload`, `idempotency_key`, `status`, `attempts`, `created_at`, `available_at`, `processed_at`.
- `OutboxRepository.enqueue(...)` ajoute un message dans la meme transaction que la mutation metier.
- `OutboxRepository.claim_pending(limit=...)` recupere les messages `pending` dans l'ordre de creation.
- `IdempotentConsumer` ignore les messages dont `idempotency_key` a deja ete traitee.
- `DEV_CORE\Database\test_outbox_idempotency.py` couvre le schema, l'enqueue/claim et la consommation idempotente.
- `BackoffPolicy` applique un backoff exponentiel borne pour les retries outbox.
- `OutboxRepository.mark_failed(...)` replanifie un message ou le passe en `dead_letter` apres `max_attempts`.
- `Worker(..., timeout_seconds=...)` convertit un depassement de temps en transition `timeout`.
- `DEV_CORE\Database\test_outbox_retry_dlq.py` couvre backoff, retry, dead-letter et timeout worker.

### Observability

`DEV_CORE\API\devcore_api\observability.py` centralise l'instrumentation API/worker.

- `configure_observability(app, recorder=...)` ajoute un middleware HTTP avec propagation `X-Trace-Id`.
- `DEV_CORE\API\devcore_api\correlation.py` standardise `trace_id`, `run_id`, `task_id`, `project_id`.
- Le middleware enregistre un span `http.request` avec `trace_id`, `run_id`, `task_id`, `project_id`, `method`, `path`, `status_code`.
- `Worker(..., span_recorder=...)` enregistre un span `worker.run` avec `trace_id`, `run_id`, `task_id`, `project_id`.
- `InMemorySpanRecorder` fournit un backend de test deterministic; un exporteur OpenTelemetry reel peut s'y brancher ensuite.
- `DEV_CORE\API\test_observability_instrumentation.py` verrouille l'instrumentation HTTP et worker.
- `DEV_CORE\API\test_correlation_context.py` verrouille la normalisation et propagation des identifiants standards.

### Prometheus and Grafana

`DEV_CORE\API\devcore_api\metrics.py` expose les métriques Prometheus.

- `configure_metrics(app, registry=...)` ajoute `/api/v1/metrics`.
- `devcore_http_requests_total` compte les requetes HTTP par `method`, `path`, `status_code`.
- `devcore_worker_runs_total` compte les executions worker par resultat.
- `DEV_CORE\Metrics\grafana\devcore-api-worker.json` versionne le dashboard Grafana API/worker.
- `DEV_CORE\API\test_prometheus_metrics.py` verrouille l'endpoint Prometheus et le dashboard Grafana.

### Web frontend

`DEV_CORE\Web` initialise le frontend moderne DEV_CORE.

- Stack : Next.js, React, TypeScript.
- Style cible : Dark Tech pour dashboard interne.
- Tokens CSS : couleurs sémantiques, espacements 4/8/12/16/24/32/48, rayons et polices Inter / JetBrains Mono.
- Shell initial : `src\app\layout.tsx`, `src\app\page.tsx`, `src\app\globals.css`.
- Accessibilité initiale : `lang="fr"`, landmark `<main>`, focus visible, contraste dark AA.
- `DEV_CORE\Web\test_frontend_scaffold.py` verrouille package, tokens et shell accessible.
- Composants dashboard : `ProjectSummary`, `TaskList`, `RunTimeline`, `HealthPanel`.
- Les composants utilisent des landmarks/labels ARIA explicites pour les domaines projets, tâches, runs et health.
- `DEV_CORE\Web\test_dashboard_components.py` verrouille la composition des composants core.
- `DEV_CORE\Web\src\lib\apiClient.ts` encapsule le client OpenAPI TypeScript généré.
- `DEV_CORE\Web\src\hooks\useDevCoreEvents.ts` consomme les événements SSE via `EventSource`.
- `DEV_CORE\Web\test_api_client_sse.py` verrouille l'intégration client OpenAPI et SSE.
- `DEV_CORE\Web\src\components\UiStates.tsx` fournit `LoadingState`, `EmptyState`, `ErrorState` et `RetryButton`.
- `DEV_CORE\Web\src\hooks\useApiResource.ts` gère `loading`, `empty`, `error`, `retry`, `AbortController` et reprise sur événement `online`.
- `DEV_CORE\Web\test_ui_states_network_recovery.py` verrouille les états UI et la reprise réseau.
- Responsive : breakpoints `768px` et `480px`, grille mono-colonne mobile et cartes compactes.
- WCAG AA : focus visible, zones interactives `44px`, badges avec texte accessible et indicateur non-couleur.
- `DEV_CORE\Web\test_responsive_accessibility.py` verrouille responsive, focus visible et indices non-couleur.
- `DEV_CORE\Web\playwright.config.ts` définit deux projets : `components` et `e2e`.
- Scripts frontend : `npm run test:components` et `npm run test:e2e`.
- Specs Playwright : `tests\components\dashboard.spec.ts` et `tests\e2e\dashboard.spec.ts`.
- `DEV_CORE\Web\test_playwright_setup.py` verrouille la configuration Playwright versionnée.

### LLMOps / Langfuse

`DEV_CORE\API\devcore_api\llmops.py` ajoute une couche LLMOps compatible Langfuse.

- `LangfuseEvent.from_generation(...)` relie generation LLM, modele, usage, cout et `CorrelationContext`.
- `as_langfuse_payload()` produit un payload compatible Langfuse : `traceId`, `model`, `usage`, `metadata`.
- `LlmOpsClient.capture(...)` envoie via transport injecte si `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY` sont configures.
- Sans configuration Langfuse, les evenements sont buffers localement et ne bloquent pas l'execution.
- `DEV_CORE\API\test_llmops_langfuse.py` couvre payload, buffering et transport.

### Evaluation datasets

`DEV_CORE\API\devcore_api\evals.py` ajoute les primitives d'evaluation routage/contexte.

- `load_eval_dataset(path)` charge un dataset versionne `version=1`.
- `evaluate_cases(...)` calcule `route_accuracy` et `context_recall`.
- `DEV_CORE\Evals\routing_context_dataset.json` versionne les premiers cas de routage/contexte.
- `DEV_CORE\API\test_eval_datasets.py` verrouille chargement, validite JSON et scoring.

### SLO, alerts and cost budgets

`DEV_CORE\Config\slo_policy.json` definit les objectifs de service, alertes et budgets cout.

- SLO : disponibilite API, succes worker, accuracy routage, recall contexte.
- Alertes : latence p95, taux d'echec worker, messages dead-letter.
- Budgets : cout quotidien, mensuel et par run.
- `DEV_CORE\API\devcore_api\slo.py` evalue un snapshot de metriques contre la politique.
- `DEV_CORE\API\test_slo_budget_policy.py` verrouille la politique et les breaches latence/cout.
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

### Endday non bloquant pour agents

- `endday.ps1` utilise un lock runtime `DEV_CORE_DATA\Runtime\endday.lock` pour eviter deux clotures concurrentes.
- `-SkipBackup` active automatiquement `AgentMode`, sauf si `-Full` est passe explicitement.
- `AgentMode` garde une cloture courte et bornee : extraction de lecons, metriques et next actions.
- Les operations longues (`qdrant_sync`, `obsidian_sync`, rotation memoire, pricing sync, rapport token, task scan/sync final) sont reservees au endday complet planifie.
- Chaque etape lancee par `endday.ps1` passe par `Invoke-EnddayStep` avec timeout.
- Mesure locale du 2026-07-12 : `endday.ps1 -SkipBackup -StepTimeoutSeconds 20` termine en `21.4 s`.

### Context Service

`context_service.ps1` demarre le Context Engine v1 avec `-Action ScoreSources`.

Le contrat retourne :

- `schema_version` : version du contrat, actuellement `1`.
- `query` et `task_type` : demande courante.
- `include_threshold` : seuil d'inclusion.
- `sources[]` : sources triees par `score`, avec `tier`, `type`, `path`, `relevance`, `freshness`, `authority` et `included`.

Le score combine pertinence, fraicheur et autorite de source. `memory_hierarchy.ps1 -Action Query` affiche les sources incluses dans un bloc `CONTEXT SOURCE SCORES` avant les contenus L3/L2/L1/L0.

## Changelog v9

### 2026-07-13 — v10.0 Repowise Dashboard Windows Loopback Fix

- ✅ **Dashboard Repowise non vide** : correction du cas Windows où l'UI Repowise se charge mais affiche `0 repositories registered` parce que `localhost:7337` est résolu vers IPv6 (`::1`) alors que l'API écoute en IPv4 (`127.0.0.1`).
- ✅ **Proxy local IPv6 -> IPv4** : ajout de `repowise_ipv6_proxy.py` et `ensure_repowise_ipv6_proxy.ps1` pour rendre `http://localhost:7337` fonctionnel.
- ✅ **Patch cache UI Repowise** : `ensure_repowise_web_proxy.ps1` remplace les rewrites Next.js `localhost:7337` par `127.0.0.1:7337` sans ajouter de BOM.
- ✅ **Démarrage durable** : `launch.ps1` démarre Repowise avec `--host 127.0.0.1 --port 7337 --ui-port 3101` et applique les correctifs UI/proxy.

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

