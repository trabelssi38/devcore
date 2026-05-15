# Decisions — DEV_CORE v6

## Actives
- Use global shared memory (MEMORY.md + Qdrant) cross-agents
- Use skills_registry.json as single source of truth for skills
- Client-agnostic via adapt_client.ps1 + symbolic links
- Task board (tasks.json) comme source de verite unique (Single Client mode)
- Bootstrap declarative (@load, @when, @policy directives)

## Stack validée
- Router Python : scoring multi-critères (task_type + urgency + volume)
- Sessions : DEV_CORE_DATA/Sessions/{handoff_id}/
- Telemetry : JSONL append-only (prepare + outcome events)
- Contracts : JSON Schema validation (jsonschema Draft202012)
