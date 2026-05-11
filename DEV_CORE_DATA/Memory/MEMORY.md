# MEMORY.md — DEV_CORE v6
<!-- Auto-géré par memory_rotate.ps1 — Ne pas modifier manuellement -->
<!-- Score min inclusion : 0.5 | Max entrées : 50 | Dernière rotation : 2026-04-26 -->

## Patterns confirmés

## Décisions actives
- [score: 0.9] Architecture : Qdrant local (port 6333) préféré à Zilliz Cloud (confidentialité)
- [score: 0.85] Embedding : nomic-embed-text via Ollama local (pas OpenAI)
- [score: 0.8] Dedup Qdrant : hash SHA-256 obligatoire avant tout upsert
- [score: 0.8] Token : CLAUDE.md terse + MCP cache + ghost finder (3 couches)
- [score: 0.75] Missions : missions.json = source de vérité unique cross-agents

## Prompts efficaces

## Stack technique
- Platform : DEV_CORE v6 (PowerShell + Python)
- Clients : Claude Code (GML) · Codex Desktop · Antigravity (Gemini+Sonnet)
- Mémoire : MEMORY.md + Qdrant local + Vault Obsidian
- Skills : obsidian · qdrant · dev-methodology · ui-ux · fabric-patterns
