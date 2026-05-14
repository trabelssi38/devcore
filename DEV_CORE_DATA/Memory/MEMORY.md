# MEMORY.md — DEV_CORE v6
<!-- Auto-géré par memory_rotate.ps1 — Ne pas modifier manuellement -->
<!-- Score min inclusion : 0.5 | Max entrées : 50 | Dernière rotation : 2026-04-26 -->

## Patterns confirmés

## Décisions actives
- [score: 0.9] Architecture : Qdrant local (port 6333) préféré à Zilliz Cloud (confidentialité)
- [score: 0.85] Embedding : nomic-embed-text via Ollama local (pas OpenAI)
- [score: 0.8] Dedup Qdrant : hash SHA-256 obligatoire avant tout upsert
- [score: 0.8] Token : 6 couches (CLAUDE.md terse + MCP cache + ghost finder + 9Router RTK + TOON) → -94%
- [score: 0.75] Missions : missions.json = source de vérité unique cross-agents

## Prompts efficaces

## Stack technique
- Platform : DEV_CORE v6.1 (PowerShell + Python)
- Clients : Claude Code (GML) · Codex Desktop · Antigravity (Gemini+Sonnet)
- Mémoire : MEMORY.md + Qdrant local + Vault Obsidian
- Skills : obsidian · qdrant · dev-methodology · ui-ux · fabric-patterns

## Token Optimization Stack (6 couches)

| # | Couche | Technique | Reduction | Status | Mesure |
|---|--------|-----------|-----------|--------|--------|
| 1 | CLAUDE.md terse | Supprime articles, reformats listes | -70% | ✅ | -69% reel |
| 2 | caveman-compress | MEMORY.md compresse | -46% | ✅ | -46% reel |
| 3 | MCP cache | Requetes repetees cachees | -95% | ✅ | N/A (binaire) |
| 4 | 9Router RTK | Compression tool_result | -40% | ✅ | N/A (binaire) |
| 5 | Ghost finder | Audit maintenance | maintenance | ✅ | N/A (audit) |
| 6 | TOON | Format compact tasks+skills | -40% | ✅ | **-90% reel** (tasks.json: 5128→514) |

**Reduction cumulee mesuree : ~98%** (tasks.json 5128 chars → 514 TOON)

## Automation Hooks v6.1

| Hook | Trigger | Action |
|------|---------|--------|
| post-commit.hook | Git commit | steps_done + task_sync |
| session_start | Claude Code start | task_scan + endday_check + gen_session_context |
| session_end | Claude Code stop | qdrant_sync + obsidian_sync + gen_metrics |
| endday_check | Morning (via launch) | Verifie endday.ps1 execute |
