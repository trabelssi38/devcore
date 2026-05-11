# Design Principles — DEV_CORE v6

## Architecture
- Séparation plateforme (DEV_CORE) / données (DEV_CORE_DATA) / legacy (DEV_CORE_LEGACY)
- Client-agnostic : les skills sont des liens symboliques, pas des copies
- Mission-driven : toute tâche est trackée dans missions.json

## Mémoire
- MEMORY.md : mémoire chaude (top-50 scorés, roté quotidiennement)
- Qdrant : mémoire sémantique (décisions, leçons, patterns, codebase)
- Vault Obsidian : mémoire froide (archivée, structurée)

## Handoff
- Fichier next_actions.md : source de vérité pour le passage de relais
- Généré automatiquement par mission_done.ps1
- Chargé automatiquement par launch.ps1 + adapt_client.ps1
