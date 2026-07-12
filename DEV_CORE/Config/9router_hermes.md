# Gemini Router Config — Hermes Agent Integration
# DEV_CORE v10 — Mode-aware routing for Hermes

## Overview

Hermes utilise le point d'entrée OpenAI-compatible du Gemini Router local.
Quand Hermes traite une requête DEV_CORE, il conserve le mode de tâche côté DEV_CORE et envoie les appels LLM vers `http://127.0.0.1:20130/v1`.

## Model Tiers

```
Tier 1 (reasoning) — Complex reasoning, architecture, decisions
├── claude-opus-4-7
├── claude-sonnet-4-6
├── anthropic/claude-sonnet-4-20250514
└── o3 (si disponible)

Tier 2 (coding) — Implementation, fixes, patches
├── claude-sonnet-4-6
├── codex (OpenAI)
├── anthropic/claude-haiku-4-5
└── sonnet-4-6

Tier 3 (bulk) — Tests, docs, migrations
├── claude-haiku-4-5
├── gemini-2.0-flash
├── qwen-2.5-coder
└── glm-coder
```

## Hermes Configuration

Hermes ne supporte pas nativement le routing multi-modèle.
Solution: Hermes exécute les tâches selon le mode detectado.

### Mode Detection from Task

```python
# Dans MCP tools — la tache inclut le mode
{
    "id": "T-01",
    "title": "Spec + Plan implementation",
    "mode": "reasoning",  # <- Hermes lit ce champ
    "status": "active",
    ...
}
```

### Routing Strategy

Hermes route via Gemini Router. Le routeur mappe les aliases OpenAI/DEV_CORE vers les modèles Gemini.

```yaml
# Windows Hermes v0.18+ : %LOCALAPPDATA%\hermes\config.yaml
model:
  provider: "custom"
  base_url: "http://127.0.0.1:20130/v1"
  default: "devcore-always-on"
  reasoning_model: "devcore-always-on"
  coding_model: "gpt-4o"
  bulk_model: "gpt-4o-mini"
```

### Tool Invocation per Mode

| Mode | Provider | Model | Budget |
|------|----------|-------|--------|
| reasoning | Gemini Router | devcore-always-on -> gemini-2.5-pro | 32k |
| coding | Gemini Router | gpt-4o -> gemini-2.5-pro | 8k |
| bulk | Gemini Router | gpt-4o-mini -> gemini-2.5-flash | 16k |

## Integration Points

### 1. MCP devcore-scripts

Les tools DEV_CORE retournent le mode de la tâche active:

```
devcore_task_status -> {"mode": "reasoning", ...}
devcore_task_next -> {"mode": "coding", ...}
```

Hermes lit `mode` et ajuste son comportement:
- reasoning: prompt plus détaillé, exploration
- coding: exécution directe, focus implémentation
- bulk: batch processing, parallélisation

### 2. Hermes Context

Le fichier `hermes_context.md` inclut:

```markdown
## Current Task Mode

Lire `C:\DEV_CORE_DATA\Memory\tasks.json`
Champ `current_task` -> champ `mode`

- mode=reasoning: Tier 1 models, 32k budget
- mode=coding: Tier 2 models, 8k budget
- mode=bulk: Tier 3 models, 16k budget
```

### 3. Scheduled Tasks (Cron)

Les cron tasks Hermes peuvent spécifier le mode:

```yaml
# hermes_cron.yaml
cron_tasks:
  - id: "daily_launch"
    mode: "reasoning"  # <- Hermes utilise reasoning pour analyse
    command: ...
  - id: "weekly_maintenance"
    mode: "bulk"  # <- Hermes utilise bulk pour cleanup
    command: ...
```

## Usage in Hermes

Quand Hermes traite une requête:

1. Lire `tasks.json` via MCP -> obtenir `mode` actuel
2. Adapter le prompt selon le mode:
   - reasoning: "Analyse en profondeur, explore alternatives"
   - coding: "Implémente directement, concis"
   - bulk: "Traite en masse, efficient"
3. Choisir le modèle selon le tier correspondant
4. Executer avec le budget approprié

## Skills per Mode

| Mode | Skills à charger |
|------|-----------------|
| reasoning | dev-methodology, fabric-patterns, qdrant |
| coding | dev-methodology, python_api, web_ui, android_release |
| bulk | fabric-patterns |

## Fallback Chain

Si Tier N échoue -> Tier N+1:

```
reasoning: opus -> sonnet -> haiku
coding: sonnet -> haiku -> flash
bulk: haiku -> flash -> qwen
```

## Files

- `ROUTER.md` — Config 9Router complete
- `hermes_context.md` — Contexte Hermes + mode
- `9router_hermes.md` — Cette config
