---
name: devcore
description: >-
  DEV_CORE v6.1 Integration for Hermes Agent. Use when working with
  DEV_CORE scripts, tasks, memory management, or development workflows.
  Triggers for: dc commands, tasks.json, Qdrant sync, Obsidian notes,
  launch/endday cycles, task scanning.
---

# DEV_CORE Skill — Hermes Integration

## Overview

DEV_CORE est une plateforme d'orchestration IA pour le développement logiciel.
Cette skill permet à Hermes d'interagir avec DEV_CORE de manière transparente.

## When to Use This Skill

- Lancement de scripts DEV_CORE (launch, endday, task_*, etc.)
- Consultation/modification de tasks.json
- Recherche dans Qdrant (decisions, patterns, lessons)
- Lecture/écriture dans Obsidian vault
- Extraction de leçons depuis les sessions
- Diagnostic du système DEV_CORE

## DEV_CORE Structure

```
C:\devcore\
├── DEV_CORE\                    # Plateforme
│   ├── Scripts\                 # Scripts PowerShell
│   │   ├── dc.ps1              # CLI principale
│   │   ├── launch.ps1          # Démarrage 10h
│   │   ├── endday.ps1          # Clôture 4h
│   │   └── task_*.ps1          # Gestion tâches
│   ├── Skills\                 # Compétences
│   └── Config\                 # Configuration
└── DEV_CORE_DATA\              # Données
    ├── Memory\                 # tasks.json, MEMORY.md
    ├── Vault\                  # Obsidian
    └── qdrant_storage\         # Vector DB
```

## Key Commands

### Tasks Management

| Hermes Tool | Description |
|-------------|-------------|
| `devcore_task_status` | Affiche le board de tâches |
| `devcore_task_scan` | Scan git + specs + prompts |
| `devcore_task_sync` | Sync tâches détectées |
| `devcore_task_done` | Marque tâche complète |

### Daily Cycle

| Hermes Tool | Description |
|-------------|-------------|
| `devcore_launch` | Démarrage quotidien (10h) |
| `devcore_endday` | Clôture + extract lessons |
| `devcore_diagnose` | Diagnostic complet |

### Memory Layers

| Hermes Tool | Description |
|-------------|-------------|
| `qdrant_search` | Recherche sémantique |
| `qdrant_upsert` | Stocke document |
| `obsidian_daily_note_read` | Lit note du jour |
| `obsidian_daily_note_append` | Ajoute à note du jour |

## Cognitive Modes (9Router)

| Mode | Budget | Usage |
|------|--------|-------|
| **reasoning** | 32k | Architecture, spec, decisions |
| **coding** | 8k | Implementation, fix, patch |
| **bulk** | 16k | Tests, docs, migrations |

## Task Format

```json
{
  "id": "T-01",
  "title": "Spec + Plan implementation",
  "mode": "reasoning",
  "status": "active",
  "steps_total": 3,
  "steps_done": 0
}
```

## Commit Tag

Format: `git commit -m "feat: [description] [T-XX]"`

Example: `git commit -m "feat: add MCP server [T-05]"`

## Rules

1. **Memory First**: Interroger Qdrant avant de régénérer (score > 0.75)
2. **Skills First**: Vérifier skills_registry.json
3. **Tag Commits**: Toujours avec [T-XX]
4. **Stay in Scope**: Rester dans le périmètre de la tâche active

## Cron Schedule

| Task | Time | Hermes Cron |
|------|------|-------------|
| daily_launch | 10:00 | `0 10 * * *` |
| daily_endday | 04:00 | `0 4 * * *` |
| weekly_maintenance | Sunday 05:00 | `0 5 * * 0` |

## External Services

| Service | Port | Status Check |
|---------|------|-------------|
| Qdrant | 6333 | `curl http://localhost:6333/collections` |
| Ollama | 11434 | `curl http://localhost:11434/api/version` |

## Quick Reference

```bash
# Lancer un script DEV_CORE via PowerShell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/devcore/DEV_CORE/Scripts/dc.ps1" task status

# Lire tasks.json
Get-Content "C:/devcore/DEV_CORE_DATA/Memory/tasks.json" | ConvertFrom-Json

# Check Qdrant
Invoke-RestMethod "http://localhost:6333/collections"
```

## Dashboard

URL: `file:///C:/devcore/DEV_CORE/Dashboard/index.html`

## Documentation

- Platform: `C:/devcore/DEV_CORE/docs/PLATFORM_DOCUMENTATION.md`
- Router: `C:/devcore/DEV_CORE/Config/ROUTER.md`