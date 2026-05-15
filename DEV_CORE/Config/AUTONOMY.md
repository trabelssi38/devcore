# AUTONOMY.md -- DEV_CORE v6.2

## Cycle de vie 100% automatique

```
SESSION START (hook)
  |
  v
session_start.ps1
  |-- launch.ps1 (8 checks bootstrap)
  |-- Watchdog Qdrant (auto-start docker)
  |-- task_next.ps1 (charge/active la tache)
  |-- task_scan + task_sync (background job)
  |-- endday_check.ps1
  |-- gen_session_context.ps1
  |
  v
TRAVAIL (IA code + commits)
  |
  |-- post_tool_hook (AfterTool/PostToolUse)
  |     |-- Detecte commits [T-XX] dans git
  |     |-- Auto-increment steps_done
  |     |-- Integrity check steps
  |     |-- Auto-backup tasks.json
  |     |-- Si steps_done >= steps_total -> task_done.ps1
  |
  |-- post-commit.hook (git)
  |     |-- Detecte [T-XX] dans le message
  |     |-- steps_done++ 
  |     |-- Si complete -> task_done.ps1
  |
  v
TASK DONE (auto ou dc task done)
  |-- lesson_extractor.ps1
  |-- qdrant_sync.ps1
  |-- obsidian_sync.ps1
  |-- memory_rotate.ps1
  |-- Notification Windows
  |-- AUTO -> task_next.ps1 (charge la suivante)
  |
  v
SESSION END (hook)
  |-- qdrant_sync.ps1
  |-- obsidian_sync.ps1
  |-- gen_metrics.ps1
  |-- endday_check.ps1
  |
  v
WEEKLY (dimanche 23h, scheduled task)
  |-- Memory audit
  |-- Qdrant dedup
  |-- Skills prune
  |-- Cache flush
  |-- Rapport HTML
  |-- Backup MEMORY.md
```

## Déclencheurs

| Événement | Client Claude | Client Gemini | Mécanisme |
|-----------|--------------|---------------|-----------|
| Début session | UserPromptSubmit | BeforeAgent | Hook settings.json |
| Après outil | PostToolUse(Bash) | AfterTool | Hook settings.json |
| Fin session | Stop | SessionEnd | Hook settings.json |
| Après commit | post-commit | post-commit | Git hook .git/hooks/ |
| Maintenance | — | — | Windows Scheduled Task |

## Commandes manuelles restantes (optionnelles)

Ces commandes existent pour les cas d'override humain, mais ne sont **jamais nécessaires** en fonctionnement normal :

| Commande | Usage |
|----------|-------|
| `dc step done [N]` | Forcer la progression d'une step |
| `dc task pause` | Mettre en pause sans valider |
| `dc task skip` | Passer une tâche bloquée |
| `dc check --fix` | Auto-réparer si quelque chose casse |

## Self-healing

`dc check --fix` corrige automatiquement :
- Variables d'environnement manquantes
- Dossiers absents
- Hooks clients non installés
- Incohérence steps_done vs steps réelles
- Tasks 'done' avec steps incomplètes
- Qdrant arrêté (docker start)
- Git post-commit hook manquant
