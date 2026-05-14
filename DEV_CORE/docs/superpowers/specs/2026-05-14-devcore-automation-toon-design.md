# DEV_CORE v6.1 - Automation + TOON Integration

## Status
- **Date**: 2026-05-14
- **Version**: 1.0
- **Author**: DEV_CORE

---

## Overview

Integrer l'automation complete des hooks et l'economie de tokens via TOON.

**Objectives:**
1. Rendre DEV_CORE autonome - sync automatique hooks
2. Reduire tokens 30-60% avec TOON
3. Mesurer et logger les gains

---

## Part 1: Automation Hooks

### Architecture

```
Session Start (hook)
    │
    ├── task_scan.ps1
    ├── endday_check.ps1 (si pas execute veille)
    └── session_context.txt (genere)

Session Active (cron hourly)
    └── task_scan.ps1

Post Commit (hook)
    ├── steps_done += 1 (si [T-XX])
    └── task_sync.ps1

Session End (hook)
    ├── Qdrant sync
    └── Obsidian sync
```

### Hooks Specification

#### 1. post-commit.hook (Modifier)

```bash
# Trigger: apres chaque git commit
# Actions:
#   1. Incremente steps_done si [T-XX] dans message
#   2. Lance task_sync.ps1

#!/bin/sh
TASKS="C:/devcore/DEV_CORE_DATA/Memory/tasks.json"
MSG=$(git log -1 --pretty=%B)
TID=$(echo "$MSG" | grep -oP '\[T-\d+\]')

if [ -n "$TID" ]; then
    powershell.exe -NonInteractive -Command "..."
fi

powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/task_sync.ps1'"
```

#### 2. session_start.hook (Creer)

```bash
# Trigger: au demarrage de session Claude Code
# Actions:
#   1. Lance task_scan.ps1
#   2. Verifie si endday.ps1 execute veille
#   3. Genere session_context.txt

#!/bin/sh
powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/task_scan.ps1'"
powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/endday_check.ps1'"
powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/gen_session_context.ps1'"
```

#### 3. session_end.hook (Creer)

```bash
# Trigger: a la fin de session Claude Code
# Actions:
#   1. Sync Qdrant (decisions + lessons)
#   2. Sync Obsidian (daily note update)
#   3. Genere metrics

#!/bin/sh
powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/qdrant_sync.ps1'"
powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/obsidian_sync.ps1'"
powershell.exe -NonInteractive -Command "& 'C:/devcore/DEV_CORE/Scripts/gen_metrics.ps1'"
```

### Scripts Additionnels

#### endday_check.ps1 (Creer)

```powershell
# Verifie si endday.ps1 a ete execute aujourd'hui
# Si non -> lance endday.ps1

$TODAY = Get-Date -Format "yyyy-MM-dd"
$FLAG = "$DEV_CORE_DATA\Logs\endday_executed_$TODAY.txt"

if (-not (Test-Path $FLAG)) {
    Write-Host "endday.ps1 non execute aujourd'hui - lancement..."
    & "$DEV_CORE\Scripts\endday.ps1"
    "executed" | Set-Content $FLAG
}
```

#### qdrant_sync.ps1 (Creer)

```powershell
# Sync les decisions et lessons vers Qdrant

$DECISIONS = "$DEV_CORE_DATA\Memory\DECISIONS.md"
$LESSONS = "$DEV_CORE_DATA\Memory\LESSONS.md"

# Parse et upsert vers Qdrant
# Collection: decisions, lessons
```

#### obsidian_sync.ps1 (Creer)

```powershell
# Update daily note avec accomplishments

$TODAY = Get-Date -Format "yyyy-MM-dd"
$NOTE = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"

# Ajoute accomplishments, decisions, lessons
```

---

## Part 2: TOON Integration

### Scope

Tous les fichiers de contexte LLM:
- `session_context.txt` -> `session_context.toon`
- `tasks.json` -> `tasks.toon`
- `MEMORY.md` - garder (quasi-TOON)
- `DECISIONS.md` - garder (quasi-TOON)
- Qdrant payloads

### TOON Format Examples

#### session_context.toon

```toon
session:
  active_task: T-02
  mode: coding
  budget: 8k
  project: cea_dashboard
  steps_done: 2
  steps_total: 5
  tag_git: T-02
```

#### tasks.toon

```toon
project: cea_dashboard
current_task: T-02

tasks[4]{id,title,mode,status,steps_done,steps_total}:
  T-01,Spec + Plan implementation,reasoning,done,3,3
  T-02,Implementation TDD,coding,active,2,5
  T-03,Tests bulk + Documentation,bulk,todo,0,2
  T-04,Review finale + Qdrant logging,reasoning,todo,0,2
```

### Implementation

#### toonify.ps1 (Creer)

```powershell
# Convertit JSON -> TOON avec stats
param(
    [string]$InputFile,
    [switch]$Stats,
    [switch]$Decode
)

$json = Get-Content $InputFile -Raw
$toon = & toon encode $json

# Calcul stats
$jsonTokens = ( Measure-Object -InputObject $json -Character).Characters
$toonTokens = ( Measure-Object -InputObject $toon -Character).Characters
$savings = (($jsonTokens - $toonTokens) / $jsonTokens) * 100

if ($Stats) {
    "$InputFile,$jsonTokens,$toonTokens,$savings" | Out-File "$DEV_CORE_DATA\Metrics\kpi.csv" -Append
}

# Log result
if ($savings -gt 25) {
    Write-Host "TOON recommande: $savings% gain" -ForegroundColor Green
}
```

### Fallback Strategy

```powershell
try {
    $data = & toon decode $toon
} catch {
    Write-Warning "TOON decode failed: $_ - using JSON"
    $data = $json | ConvertFrom-Json
}
```

### Seuil d'Activation

- Gain > 25% -> activer TOON par defaut
- Gain < 25% -> garder JSON
- Logging dans `Metrics/kpi.csv`

---

## Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `post-commit.hook` | Modify | P1 |
| `session_start.hook` | Create | P1 |
| `session_end.hook` | Create | P1 |
| `endday_check.ps1` | Create | P1 |
| `qdrant_sync.ps1` | Create | P2 |
| `obsidian_sync.ps1` | Create | P2 |
| `toonify.ps1` | Create | P2 |
| `Metrics/kpi.csv` | Create | P2 |

---

## Implementation Order

1. **Phase 1: Automation Hooks**
   - post-commit.hook (modify)
   - session_start.hook (create)
   - session_end.hook (create)
   - endday_check.ps1 (create)

2. **Phase 2: TOON Integration**
   - Install `@toon-format/toon`
   - toonify.ps1 (create)
   - session context TOON
   - tasks TOON
   - Metrics/kpi.csv

---

## Metrics

| Metric | File | Frequency |
|--------|------|-----------|
| Token savings | kpi.csv | Per conversion |
| Tasks sync | task_sync log | Per commit |
| Qdrant vectors | Qdrant collections | Per session-end |
| Hook executions | hook logs | Per trigger |

---

## Success Criteria

- [ ] 3 hooks operationnels (post-commit, session-start, session-end)
- [ ] endday_check lance endday si pas execute
- [ ] Qdrant sync fonctionne sur session-end
- [ ] TOON conversion avec stats > 25% gain
- [ ] Metrics dans kpi.csv

---

## References

- TOON Spec: https://toonformat.dev/
- NPM: `@toon-format/toon`
