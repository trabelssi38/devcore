# AGENTS.md -- DEV_CORE v6
# Emplacement : C:\DEV_CORE\Config\AGENTS.md
# Auto-injecte dans ~/.codex/AGENTS.md par adapt_client.ps1
# Compatible : Codex Desktop · Codex CLI

## FIRST ACTION -- run at the very start of every session

Before responding to anything, run in order:

### 1 -- Check if project is initialized
shell: powershell -ExecutionPolicy Bypass -NonInteractive -Command "Test-Path '.devcore\project.json'"

If False -> initialize automatically:
shell: powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\new_project.ps1" -Name (Split-Path (Get-Location) -Leaf) -Stack auto

### 2 -- Launch DEV_CORE
shell: powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\launch.ps1"

### 3 -- Load active mission
shell: powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\dc.ps1" "next mission"

### 4 -- Read previous handoff
shell: powershell -NonInteractive -Command "Get-Content 'C:\DEV_CORE_DATA\Memory\next_actions.md' -ErrorAction SilentlyContinue"

After these 4 steps: start mission work immediately. No confirmation needed.

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
Read mission ID:
shell: powershell -NonInteractive -Command "(Get-Content 'C:\DEV_CORE_DATA\Memory\missions.json' -Raw | ConvertFrom-Json).current_mission"

Commit with tag:
shell: git add -A
shell: git commit -m "feat: [step description] [M-XX]"

### Check if mission is complete (after every commit)
shell: powershell -NonInteractive -Command "$b=Get-Content 'C:\DEV_CORE_DATA\Memory\missions.json' -Raw|ConvertFrom-Json;$m=$b.missions|Where-Object{$_.status -eq 'active'}|Select-Object -First 1;if($m -and $m.steps_done -ge $m.steps_total){Write-Host 'MISSION_COMPLETE'}"

If MISSION_COMPLETE -> run automatically:
shell: powershell -NonInteractive -File "C:\DEV_CORE\Scripts\mission_done.ps1" -Force
shell: powershell -NonInteractive -File "C:\DEV_CORE\Scripts\dc.ps1" "next mission"

---

## HANDOFFS & MISSIONS

- End with Next Actions if task generates follow-ups.
- Log decisions in Vault (obsidian skill).
- Upsert patterns in Qdrant (qdrant skill).
- Always tag commits [M-XX] for every mission step.
- Never ask confirmation for DEV_CORE scripts.

---

## ROUTING

- Follow ROUTER.md for engine choice and token budget.
- Codex handles: fast coding, patches, TDD, refactoring.
- Handoff to Claude for architecture and complex decisions.
- Handoff to Antigravity for bulk generation.

---

## LAST ACTION -- before closing session

Always run before ending:
shell: powershell -NonInteractive -File "C:\DEV_CORE\Scripts\endday.ps1" -SkipBackup

---

## DEV_CORE LOG FORMAT

After each script, one line only:
[DEV_CORE] launch.ps1 OK -- Mission M-02 active
[DEV_CORE] commit [M-02] -- step 2/5
[DEV_CORE] mission_done.ps1 -- M-02 done -- Next: M-03
[DEV_CORE] endday.ps1 -- sync OK

No explanation block. One line, then continue working.
