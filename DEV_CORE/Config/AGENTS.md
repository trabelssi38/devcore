# AGENTS.md -- DEV_CORE v6.1
# Emplacement : C:\devcore\DEV_CORE\Config\AGENTS.md
# Auto-injecte dans ~/.codex/AGENTS.md par adapt_client.ps1
# Compatible : Codex Desktop · Codex CLI

## Hermes Agent Integration (v6.1)

Hermes Agent (Nous Research) fonctionne en daemon avec MCP :
- MCP server `devcore-scripts` : launch, endday, task_*, diagnose
- MCP server `qdrant-storage` : collections, search, upsert, delete
- MCP server `obsidian-vault` : daily_note, search, create_note

Hermes orchestre via scheduled tasks Windows :
- `DEV_CORE_Daily_Launch` (10:00)
- `DEV_CORE_Daily_Endday` (04:00)
- `DEV_CORE_Weekly_Maintenance` (Sunday 05:00)

---

## FIRST ACTION -- run at the very start of every session

Before responding to anything, run in order:

### 1 -- Check if project is initialized
shell: powershell -ExecutionPolicy Bypass -NonInteractive -Command "Test-Path '.devcore\project.json'"

If False -> initialize automatically:
shell: powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\new_project.ps1" -Name (Split-Path (Get-Location) -Leaf) -Stack auto

### 2 -- Launch DEV_CORE
shell: powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\launch.ps1"

### 3 -- Load active task
shell: powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\dc.ps1" "next task"

### 4 -- Read session context
shell: powershell -NonInteractive -Command "Get-Content 'C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt' -ErrorAction SilentlyContinue"

After these 4 steps: start task work immediately. No confirmation needed.

---

## RESPONSE MODE

- Concise. Code first. No preamble.
- Lists > prose for structured content.
- 1 question max if clarification needed.
- TDD: write test first, make it pass, then commit.

---

## MEMORY (absolute priority)

- Check MEMORY.md before any potentially known topic.
- Query Qdrant (collections: decisions/lessons/patterns).
- Score > 0.75: use result without regenerating.
- Load only skills relevant to the current task.

---

## SKILLS (mandatory)

- Load devcore-automation first.
- Check skills_registry.json before any non-trivial task.
- If skill available: load it and follow exactly.
- Auto-create skill threshold: 3 similar occurrences.

---

## TOKENS

- Structured summaries > long prose.
- Do not repeat context already provided.
- Default budget: 8k tokens. Alert if likely exceeded.

---

## RULES DURING WORK

### After each validated step (tests passing)
Read task ID:
shell: powershell -NonInteractive -Command "(Get-Content 'C:\devcore\DEV_CORE_DATA\Memory\tasks.json' -Raw | ConvertFrom-Json).current_task"

Commit with tag:
shell: git add -A
shell: git commit -m "feat: [step description] [T-XX]"

### Check if task is complete (after every commit)
shell: powershell -NonInteractive -Command "$b=Get-Content 'C:\devcore\DEV_CORE_DATA\Memory\tasks.json' -Raw|ConvertFrom-Json;$t=$b.tasks|Where-Object{$_.status -eq 'active'}|Select-Object -First 1;if($t -and $t.steps_done -ge $t.steps_total){Write-Host 'TASK_COMPLETE'}"

If TASK_COMPLETE -> run automatically:
shell: powershell -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\task_done.ps1" -Force
shell: powershell -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\dc.ps1" "next task"

---

## TASKS (v6.1)

- Single Client Mode : pas de handoffs multi-agents
- Modes : reasoning (32k), coding (8k), bulk (16k)
- Detection auto via 9Router
- Tags git : [T-XX]
- Auto-detection via task_scan (git+spec+prompts)

---

## ROUTING

- Follow ROUTER.md for engine choice and token budget.
- mode=reasoning -> 9Router routes to Tier 1 automatically.
- mode=coding    -> 9Router routes to Tier 2 automatically.
- mode=bulk      -> 9Router routes to Tier 3 automatically.
- No handoffs. Single client. 9Router handles model selection.

---

## LAST ACTION -- before closing session

Always run before ending:
shell: powershell -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup

---

## DEV_CORE LOG FORMAT

After each script, one line only:
[DEV_CORE] launch.ps1 OK -- Task T-02 active
[DEV_CORE] commit [T-02] -- step 2/5
[DEV_CORE] task_done.ps1 -- T-02 done -- Next: T-03
[DEV_CORE] endday.ps1 -- sync OK

No explanation block. One line, then continue working.
