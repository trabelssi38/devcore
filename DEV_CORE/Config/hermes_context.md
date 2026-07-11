# DEV_CORE v6.1 — Context for Hermes Agent

## Project Overview

DEV_CORE est une plateforme d'orchestration IA pour le développement logiciel.
- **Mode**: Single Client (pas de handoffs multi-agents)
- **Version**: 6.1
- **Objectif**: Mémoriser, réutiliser, automatiser

## Directory Structure

```
C:\devcore\
├── DEV_CORE\                    # Plateforme (code, scripts, skills)
│   ├── Scripts\                 # Scripts PowerShell
│   │   ├── dc.ps1              # CLI principale
│   │   ├── launch.ps1          # Démarrage journée
│   │   ├── endday.ps1          # Clôture + sync
│   │   ├── task_*.ps1          # Gestion tâches
│   │   └── Auto\               # Scripts automatiques
│   ├── Skills\                 # Compétences réutilisables
│   │   ├── qdrant\             # Mémoire vectorielle
│   │   ├── obsidian\           # Vault management
│   │   ├── fabric-patterns\    # Patterns IA
│   │   └── dev-methodology\     # Méthodologie
│   ├── Config\                 # Configuration
│   │   ├── CLAUDE.md           # Instructions agent
│   │   ├── ROUTER.md           # Détection modes
│   │   └── PATHS.md            # Chemins de référence
│   └── Dashboard\              # Dashboard HTML
│
└── DEV_CORE_DATA\              # Données persistantes
    ├── Memory\                 # Mémoire partagée
    │   ├── tasks.json          # Board de tâches
    │   ├── MEMORY.md           # Index central
    │   ├── DECISIONS.md        # Décisions actives
    │   └── *_queue.jsonl       # Queues temporaires
    ├── Obsidian\              # Vault Obsidian
    ├── Logs\                  # Logs système
    ├── Sessions\              # Sessions de travail
    └── qdrant_storage\        # Données Qdrant
```

## Key Commands

| Command | Description |
|---------|-------------|
| `dc launch` | Démarrage journée (10h) |
| `dc task scan` | Scan git + specs + prompts |
| `dc task sync` | Sync tâches détectées |
| `dc task done` | Marque tâche complète |
| `dc endday` | Clôture quotidienne (4h) |
| `dc weekly` | Maintenance hebdomadaire (dimanche 5h) |

## Cognitive Modes (9Router — Hermes Compatible)

### Mode Detection

Hermes lit le mode actif depuis `tasks.json`:
```json
{
  "current_task": "T-01",
  "tasks": [{
    "id": "T-01",
    "mode": "reasoning",  // <- Mode detecté
    ...
  }]
}
```

### Routing Rules

| Mode | Model (Anthropic) | Budget | When |
|------|----------|--------|------|
| **reasoning** | `claude-opus-4-7` | 32k | Architecture, spec, decisions, debug cause inconnue |
| **coding** | `claude-sonnet-4-6` | 8k | Implementation, fix, refactoring, TDD |
| **bulk** | `claude-haiku-4-5` | 16k | Tests en masse, docs, migrations, batch |

### Provider Selection

Hermes ajuste le provider selon le mode:
```yaml
model:
  provider: "openai"
  base_url: "https://api.anthropic.com/v1"
  reasoning_model: "anthropic/claude-opus-4-7"
  coding_model: "anthropic/claude-sonnet-4-6"
  bulk_model: "anthropic/claude-haiku-4-5"
```

### Skills Charged per Mode

| Mode | Skills |
|------|--------|
| reasoning | dev-methodology, fabric-patterns, qdrant |
| coding | dev-methodology, python_api, web_ui, android_release |
| bulk | fabric-patterns |

### Fallback

Si un modele echoue: reasoning -> coding -> bulk
- `claude-opus-4-7` -> `claude-sonnet-4-6` -> `claude-haiku-4-5`
- Même base_url Anthropic donc transparent pour Hermes

### Integration Files

- `C:/devcore/DEV_CORE/Config/ROUTER.md` — Spec complete 9Router
- `C:/devcore/DEV_CORE/Config/9router_hermes.md` — Config Hermes

## Task Format

```json
{
  "id": "T-01",
  "title": "Spec + Plan implementation",
  "mode": "reasoning",
  "status": "active",
  "steps_total": 3,
  "steps_done": 0,
  "depends_on": null
}
```

## Commit Tag Format

```
git commit -m "feat: [description] [T-XX]"
```

Example: `git commit -m "feat: add MCP server [T-05]"`

## Memory Layers

1. **Qdrant** (port 6333) - Base vectorielle
   - Collections: decisions, patterns, lessons, codebase

2. **MEMORY.md** - Index central
   - Patterns, stack, configurations

3. **Obsidian Vault** - Notes structurées
   - Daily Notes, Decisions, Lessons

## External Services

| Service | Port | Purpose |
|---------|------|---------|
| Qdrant | 6333 | Vector database |
| Ollama | 11434 | Embeddings (nomic-embed-text) |

## Rules

1. **Memory First**: Interroger Qdrant avant de régénérer (score > 0.75)
2. **Skills First**: Vérifier skills_registry.json avant tâche non triviale
3. **Tag Commits**: Toujours taguer avec [T-XX]
4. **Stay in Scope**: Rester dans le périmètre de la tâche active

## Skills Available

- `qdrant` — Mémoire vectorielle
- `obsidian` — Vault management
- `fabric-patterns` — Patterns IA réutilisables
- `dev-methodology` — Méthodologie dev
- `python_api` — APIs Python
- `web_ui` — Interface web
- `android_release` — Android

## Cron Schedule

| Task | Time | Description |
|------|------|-------------|
| daily_launch | 10:00 | Démarrage journée |
| daily_endday | 04:00 | Clôture + sync |
| weekly_maintenance | Sunday 05:00 | Maintenance |

## Dashboard

URL: `file:///C:/devcore/DEV_CORE/Dashboard/index.html`

## Documentation

- Platform: `C:/devcore/DEV_CORE/docs/PLATFORM_DOCUMENTATION.md`
- Migration: `C:/devcore/DEV_CORE/docs/MIGRATION_GUIDE.md`
- Router: `C:/devcore/DEV_CORE/Config/ROUTER.md`
