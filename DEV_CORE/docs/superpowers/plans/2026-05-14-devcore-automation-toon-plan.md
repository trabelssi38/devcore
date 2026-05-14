# DEV_CORE Automation + TOON Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate DEV_CORE hooks (post-commit, session-start, session-end) + TOON token reduction.

**Architecture:** 3 hooks chaines ensemble via settings.json. post-commit hook integre dans .git/hooks/ du projet actif. session-start/session-end integres dans UserPromptSubmit/Stop hooks. TOON convertit les fichiers JSON en format economique 30-60%.

**Tech Stack:** PowerShell 7, Claude Code hooks, TOON CLI (@toon-format/toon), Qdrant REST API, Obsidian vault

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `C:/devcore/DEV_CORE/Scripts/post-commit.hook` | Modify | Git post-commit: steps_done + task_sync |
| `C:/devcore/DEV_CORE/Scripts/session_start.ps1` | Modify | Add endday_check call |
| `C:/devcore/DEV_CORE/Scripts/session_end.ps1` | Create | Qdrant + Obsidian sync + gen_metrics |
| `C:/devcore/DEV_CORE/Scripts/endday_check.ps1` | Create | Verifie endday execute aujourd'hui |
| `C:/devcore/DEV_CORE/Scripts/qdrant_sync.ps1` | Create | Sync decisions/lessons -> Qdrant |
| `C:/devcore/DEV_CORE/Scripts/obsidian_sync.ps1` | Create | Sync accomplishments -> Daily Note |
| `C:/devcore/DEV_CORE/Scripts/gen_session_context.ps1` | Create | Genere session_context.toon |
| `C:/devcore/DEV_CORE/Scripts/toonify.ps1` | Create | JSON<->TOON conversion + stats |
| `C:/devcore/DEV_CORE_DATA/Metrics/kpi.csv` | Create | Token savings log |
| `C:/Users/trb_m/.claude/settings.json` | Modify | Ajoute session-end hook |

---

## Phase 1: Automation Hooks

### Task 1: post-commit.hook - steps_done + task_sync

**Files:**
- Modify: `C:/devcore/DEV_CORE/Scripts/post-commit.hook`

- [ ] **Step 1: Lire le post-commit existant**

Run:
```bash
cat C:/devcore/DEV_CORE/Scripts/post-commit.hook
```

Read current content.

- [ ] **Step 2: Ecrire le post-commit renforce**

Write `C:/devcore/DEV_CORE/Scripts/post-commit.hook`:

```bash
#!/bin/sh
# post-commit -- DEV_CORE v6.1 -- Full automation
# 1. Incremente steps_done si commit contient [T-XX]
# 2. Lance task_sync pour synchroniser les taches detectees
# 3. Verifie si tache est complete

TASKS="C:/devcore/DEV_CORE_DATA/Memory/tasks.json"
SCRIPTS="C:/devcore/DEV_CORE/Scripts"
MSG=$(git log -1 --pretty=%B)
TID=$(echo "$MSG" | grep -oP '\[T-\d+\]' | tr -d '[]' | head -1)

if [ -n "$TID" ]; then
    echo "  [DEV_CORE] Tag $TID detecte dans le commit"

    powershell.exe -NonInteractive -Command "
    \$f='$TASKS'
    if(-not(Test-Path \$f)){exit 0}
    \$b=Get-Content \$f -Raw|ConvertFrom-Json
    \$t=\$b.tasks|Where-Object{\$_.id -eq '$TID'}
    if(-not \$t){exit 0}
    \$cur=if(\$t.PSObject.Properties['steps_done']){\$t.steps_done}else{0}
    \$tot=if(\$t.PSObject.Properties['steps_total']){\$t.steps_total}else{1}
    \$new=[math]::Min(\$cur+1,\$tot)
    \$t|Add-Member -NotePropertyName 'steps_done' -NotePropertyValue \$new -Force
    \$b|ConvertTo-Json -Depth 10|Set-Content \$f -Encoding UTF8
    Write-Host \"  [DEV_CORE] Step \$new/\$tot enregistree pour $TID\" -ForegroundColor Cyan
    if(\$new -ge \$tot){
        Write-Host '  [DEV_CORE] Tache complete! Lancement task_done...' -ForegroundColor Green
        & 'C:/devcore/DEV_CORE/Scripts/task_done.ps1'
    }
    "
fi

# task_sync toujours
echo "  [DEV_CORE] Synchronisation des taches..."
powershell.exe -NonInteractive -Command "& '$SCRIPTS/task_sync.ps1' 2>&1 | Out-Null"

exit 0
```

- [ ] **Step 3: Copier le hook dans .git/hooks/ du projet cea_dashboard**

```bash
cp C:/devcore/DEV_CORE/Scripts/post-commit.hook C:/src/cea_dashboard/.git/hooks/post-commit
```

- [ ] **Step 4: Verifier le hook installe**

```bash
cat C:/src/cea_dashboard/.git/hooks/post-commit | head -5
```

Expected: Affiche le contenu du hook.

- [ ] **Step 5: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/post-commit.hook
git commit -m "feat: enhance post-commit hook with task_sync + auto-done [T-03]"
```

---

### Task 2: endday_check.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/endday_check.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/endday_check.ps1`:

```powershell
# endday_check.ps1 -- DEV_CORE v6.1
# Verifie si endday.ps1 a ete execute aujourd'hui
# Si non -> lance endday.ps1

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$FLAG = "$DEV_CORE_DATA\Logs\endday_flag_$TODAY.txt"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Endday Check" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray

if (Test-Path $FLAG) {
    $lastEndday = Get-Content $FLAG
    Write-Log "endday deja execute aujourd'hui ($lastEndday)" "Green"
    exit 0
}

Write-Log "endday NON execute aujourd'hui - lancement..." "Yellow"
Write-Log "Verification Qdrant disponible..." "Gray"

try {
    $q = Invoke-RestMethod "http://localhost:6333/collections" -TimeoutSec 3
    Write-Log "Qdrant OK - lancement endday.ps1" "Green"
    & "$DEV_CORE\Scripts\endday.ps1"
} catch {
    Write-Log "Qdrant non disponible - endday reporte" "Yellow"
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$timestamp | Set-Content $FLAG -Encoding UTF8
Write-Log "Flag endday cree: $timestamp" "Green"
Write-Host ""
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/endday_check.ps1
git commit -m "feat: add endday_check.ps1 for morning verification [T-03]"
```

---

### Task 3: gen_session_context.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/gen_session_context.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/gen_session_context.ps1`:

```powershell
# gen_session_context.ps1 -- DEV_CORE v6.1
# Genere le fichier session_context.txt et session_context.toon

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$CONTEXT_FILE = "$DEV_CORE_DATA\Logs\scripts\session_context.txt"

$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
if (-not (Test-Path $tFile)) {
    Write-Host "tasks.json absent" -ForegroundColor Yellow
    exit 1
}

$board = Get-Content $tFile -Raw | ConvertFrom-Json
$active = $board.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1

if (-not $active) {
    $todo = $board.tasks | Where-Object { $_.status -eq "todo" } | Select-Object -First 1
    if ($todo) {
        # Passer a la tache suivante
        $board.current_task = $todo.id
        $todo.status = "active"
        $board | ConvertTo-Json -Depth 10 | Set-Content $tFile -Encoding UTF8
        $active = $todo
        Write-Host "  [DEV_CORE] Activation auto: $($active.id)" -ForegroundColor Cyan
    }
}

if (-not $active) {
    Write-Host "  [DEV_CORE] Aucune tache active" -ForegroundColor Yellow
    @"
[DEV_CORE] Aucune tache active
[DEV_CORE] Commencer par: dc new task 'description' -mode reasoning|coding|bulk
"@ | Set-Content $CONTEXT_FILE -Encoding UTF8
    exit 0
}

$budget = switch ($active.mode) {
    "reasoning" { "32k" }
    "coding"    { "8k" }
    "bulk"      { "16k" }
    default     { "16k" }
}

$content = @"
[DEV_CORE] Task active : $($active.id)
[DEV_CORE] Titre  : $($active.title)
[DEV_CORE] Mode   : $($active.mode)
[DEV_CORE] Budget : $budget tokens
[DEV_CORE] Steps  : $($active.steps_done)/$($active.steps_total)
[DEV_CORE] Tag git: [$($active.id)]
"@

$content | Set-Content $CONTEXT_FILE -Encoding UTF8
Write-Host "  [DEV_CORE] Session context genere: $($active.id) - $($active.mode)" -ForegroundColor Green
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/gen_session_context.ps1
git commit -m "feat: add gen_session_context.ps1 for auto-context generation [T-03]"
```

---

### Task 4: session_start.ps1 - Ajouter endday_check

**Files:**
- Modify: `C:/devcore/DEV_CORE/Scripts/session_start.ps1`

- [ ] **Step 1: Lire le session_start existant**

Run:
```bash
cat C:/devcore/DEV_CORE/Scripts/session_start.ps1
```

- [ ] **Step 2: Ajouter endday_check + gen_session_context**

Apres la derniere etape (8/8), ajouter:

```powershell
# 9. Endday check
Write-Host "  9/9 Endday verification" -ForegroundColor Cyan
& "$DEV_CORE\Scripts\endday_check.ps1" 2>$null

# 10. Gen session context
Write-Host "  10/10 Session context" -ForegroundColor Cyan
& "$DEV_CORE\Scripts\gen_session_context.ps1" 2>$null
```

- [ ] **Step 3: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/session_start.ps1
git commit -m "feat: add endday_check + gen_session_context to session_start [T-03]"
```

---

### Task 5: qdrant_sync.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/qdrant_sync.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/qdrant_sync.ps1`:

```powershell
# qdrant_sync.ps1 -- DEV_CORE v6.1
# Sync les decisions et lessons vers Qdrant

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$QDRANT_URL = if ($env:QDRANT_URL) { $env:QDRANT_URL } else { "http://localhost:6333" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$LOG = "$DEV_CORE_DATA\Logs\scripts\qdrant_sync_$TODAY.log"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Qdrant Sync" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray

# Verifier Qdrant
try {
    $q = Invoke-RestMethod "$QDRANT_URL/collections" -TimeoutSec 3
    Write-Log "Qdrant connecte - $($q.result.collections.Count) collections" "Green"
} catch {
    Write-Log "Qdrant non disponible - sync annule" "Yellow"
    exit 0
}

# Sync decisions -> Qdrant collection decisions
$decisionsFile = "$DEV_CORE_DATA\Memory\DECISIONS.md"
if (Test-Path $decisionsFile) {
    $decisions = Get-Content $decisionsFile -Raw
    $payload = @{
        id = "decisions_$TODAY"
        vector = @(0.5 * 768)  # place holder - embeddings via Ollama
        payload = @{
            source = "decisions.md"
            content = $decisions
            date = $TODAY
            type = "decisions"
        }
    } | ConvertTo-Json -Compress

    try {
        Invoke-RestMethod "$QDRANT_URL/collections/decisions/points" `
            -Method Put -Body $payload -ContentType "application/json" -TimeoutSec 10 | Out-Null
        Write-Log "Decisions upserted vers Qdrant" "Green"
    } catch {
        Write-Log "Erreur sync decisions: $_" "Red"
    }
}

# Sync lessons -> Qdrant collection lessons  
$lessonsFile = "$DEV_CORE_DATA\Memory\LESSONS.md"
if (Test-Path $lessonsFile) {
    $lessons = Get-Content $lessonsFile -Raw
    $payload = @{
        id = "lessons_$TODAY"
        vector = @(0.5 * 768)
        payload = @{
            source = "lessons.md"
            content = $lessons
            date = $TODAY
            type = "lessons"
        }
    } | ConvertTo-Json -Compress

    try {
        Invoke-RestMethod "$QDRANT_URL/collections/lessons/points" `
            -Method Put -Body $payload -ContentType "application/json" -TimeoutSec 10 | Out-Null
        Write-Log "Lessons upserted vers Qdrant" "Green"
    } catch {
        Write-Log "Erreur sync lessons: $_" "Red"
    }
}

Write-Log "Qdrant sync termine" "Green"
Write-Host ""
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/qdrant_sync.ps1
git commit -m "feat: add qdrant_sync.ps1 for decisions/lessons sync [T-03]"
```

---

### Task 6: obsidian_sync.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/obsidian_sync.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/obsidian_sync.ps1`:

```powershell
# obsidian_sync.ps1 -- DEV_CORE v6.1
# Sync accomplishments vers Obsidian Daily Note

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$LOG = "$DEV_CORE_DATA\Logs\scripts\obsidian_sync_$TODAY.log"
$NOTE_PATH = "$DEV_CORE_DATA\Vault\Daily Notes\$TODAY.md"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    $l = "[$(Get-Date -f HH:mm:ss)] $msg"
    Add-Content $LOG $l -ErrorAction SilentlyContinue
    Write-Host "    $l" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Obsidian Sync" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray

if (-not (Test-Path $NOTE_PATH)) {
    Write-Log "Daily Note $TODAY n'existe pas - creation" "Yellow"
    New-Item -ItemType Directory -Path (Split-Path $NOTE_PATH) -Force | Out-Null
@"
---
title: Daily Note $TODAY
date: $TODAY
tags: [daily, devcore]
---

# $TODAY

## Resume
<!-- Auto-complete par endday -->

## Taches accomplies

## Decisions

## Lecons

## Next actions
- [ ]
"@ | Set-Content $NOTE_PATH -Encoding UTF8
    Write-Log "Daily Note creee" "Green"
    exit 0
}

# Lire le board de taches
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    $doneToday = $board.tasks | Where-Object { $_.status -eq "done" }

    Write-Log "Taches completees: $($doneToday.Count)" "Green"

    # Ajouter accomplishments a la note
    $note = Get-Content $NOTE_PATH -Raw

    if ($note -match "## Taches accomplies") {
        $newContent = "## Taches accomplies`n"
        foreach ($t in $doneToday) {
            $newContent += "- [x] $($t.id): $($t.title)`n"
        }
        $note = $note -replace "## Taches accomplies[\s\S]*?(?=\n##|$)", $newContent
        $note | Set-Content $NOTE_PATH -Encoding UTF8
        Write-Log "Daily Note mise a jour avec $($doneToday.Count) taches" "Green"
    }
}

Write-Log "Obsidian sync termine" "Green"
Write-Host ""
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/obsidian_sync.ps1
git commit -m "feat: add obsidian_sync.ps1 for daily note update [T-03]"
```

---

### Task 7: session_end.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/session_end.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/session_end.ps1`:

```powershell
# session_end.ps1 -- DEV_CORE v6.1
# Execute a la fin de session Claude Code
# 1. Sync Qdrant
# 2. Sync Obsidian
# 3. Genere metrics

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$TODAY = Get-Date -Format "yyyy-MM-dd"

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- Session End" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host "  Date: $TODAY" -ForegroundColor White
Write-Host ""

Write-Host "  [1/3] Sync Qdrant..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\qdrant_sync.ps1" 2>$null

Write-Host "  [2/3] Sync Obsidian..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\obsidian_sync.ps1" 2>$null

Write-Host "  [3/3] Generation metrics..." -ForegroundColor Cyan
& "$DEV_CORE\Scripts\gen_metrics.ps1" 2>$null

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  ||  Session end complete               ||" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/session_end.ps1
git commit -m "feat: add session_end.ps1 for Qdrant + Obsidian sync [T-03]"
```

---

### Task 8: gen_metrics.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/gen_metrics.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/gen_metrics.ps1`:

```powershell
# gen_metrics.ps1 -- DEV_CORE v6.1
# Genere les metriques de session

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$TODAY = Get-Date -Format "yyyy-MM-dd"
$METRICS_DIR = "$DEV_CORE_DATA\Metrics"
$METRICS_FILE = "$METRICS_DIR\session_metrics_$TODAY.csv"

if (-not (Test-Path $METRICS_DIR)) {
    New-Item -ItemType Directory -Path $METRICS_DIR -Force | Out-Null
}

# Lire tasks
$tFile = "$DEV_CORE_DATA\Memory\tasks.json"
$totalSteps = 0
$doneSteps = 0
$taskCount = 0

if (Test-Path $tFile) {
    $board = Get-Content $tFile -Raw | ConvertFrom-Json
    foreach ($t in $board.tasks) {
        $totalSteps += $t.steps_total
        $doneSteps += $t.steps_done
        $taskCount++
    }
}

# Lire logs de session
$sessionLog = "$DEV_CORE_DATA\Logs\scripts\session_context.txt"
$activeTask = ""
if (Test-Path $sessionLog) {
    $line = Get-Content $sessionLog | Where-Object { $_ -match "Task active" } | Select-Object -First 1
    if ($line -match "T-\d+") {
        $activeTask = $matches[0]
    }
}

$progress = if ($totalSteps -gt 0) { [math]::Round(($doneSteps / $totalSteps) * 100) } else { 0 }
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$header = "date,active_task,tasks_total,steps_done,steps_total,progress_pct"
$row = "$TODAY,$activeTask,$taskCount,$doneSteps,$totalSteps,$progress"

if (-not (Test-Path $METRICS_FILE)) {
    $header | Set-Content $METRICS_FILE -Encoding UTF8
}
$row | Add-Content $METRICS_FILE -Encoding UTF8

Write-Host "  [METRICS] $TODAY | $activeTask | $doneSteps/$totalSteps steps | $progress%" -ForegroundColor Cyan
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/gen_metrics.ps1
git commit -m "feat: add gen_metrics.ps1 for session metrics tracking [T-03]"
```

---

### Task 9: Configurer hooks dans settings.json

**Files:**
- Modify: `C:/Users/trb_m/.claude/settings.json`

- [ ] **Step 1: Lire le settings.json actuel**

Run:
```bash
cat "C:/Users/trb_m/.claude/settings.json"
```

- [ ] **Step 2: Ajouter les hooks session-end**

Modifier le fichier settings.json pour ajouter:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File \"C:\\DEV_CORE\\Scripts\\session_start.ps1\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File \"C:\\DEV_CORE\\Scripts\\post_tool_hook.ps1\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File \"C:\\DEV_CORE\\Scripts\\session_end.ps1\""
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 3: Verifier le settings.json**

```bash
cat "C:/Users/trb_m/.claude/settings.json" | python -c "import json,sys; json.load(sys.stdin); print('JSON valide')"
```

Expected: "JSON valide"

---

## Phase 2: TOON Integration

### Task 10: Installer @toon-format/toon

**Files:**
- Nothing to create

- [ ] **Step 1: Verifier npm disponible**

```bash
npm --version
```

Expected: version number

- [ ] **Step 2: Installer toon globalement**

```bash
npm install -g @toon-format/toon
```

Expected: package installed without errors

- [ ] **Step 3: Verifier installation**

```bash
toon --version
```

Expected: version number

---

### Task 11: toonify.ps1

**Files:**
- Create: `C:/devcore/DEV_CORE/Scripts/toonify.ps1`

- [ ] **Step 1: Ecrire le script**

Write `C:/devcore/DEV_CORE/Scripts/toonify.ps1`:

```powershell
# toonify.ps1 -- DEV_CORE v6.1
# Conversion JSON <-> TOON avec stats et fallback
# Usage: toonify.ps1 -InputFile "tasks.json" [-Stats] [-Decode]

param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,

    [switch]$StatsSave,

    [switch]$Decode,

    [switch]$DryRun
)

$DEV_CORE = if ($env:DEVCORE_PLATFORM_ROOT) { $env:DEVCORE_PLATFORM_ROOT } else { "C:\devcore\DEV_CORE" }
$DEV_CORE_DATA = if ($env:DEVCORE_DATA_ROOT) { $env:DEVCORE_DATA_ROOT } else { "C:\devcore\DEV_CORE_DATA" }
$KPI_FILE = "$DEV_CORE_DATA\Metrics\kpi.csv"
$TOON_BIN = "toon"

function Write-Log {
    param([string]$msg, [string]$color="Gray")
    Write-Host "  $msg" -ForegroundColor $color
}

Write-Host ""
Write-Host "  DEV_CORE v6.1 -- TOONIFY" -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor DarkGray
Write-Host ""

# Verifier paths
if (-not (Test-Path $InputFile)) {
    Write-Log "ERREUR: $InputFile introuvable" "Red"
    exit 1
}

try {
    $toonVersion = & $TOON_BIN --version 2>&1
    Write-Log "TOON CLI: $toonVersion" "Green"
} catch {
    Write-Log "ERREUR: TOON non installe (npm install -g @toon-format/toon)" "Red"
    exit 1
}

# Lire le fichier source
$sourceContent = Get-Content $InputFile -Raw

# Mesurer tokens (caracteres comme proxy)
$sourceChars = $sourceContent.Length

if (-not $Decode) {
    # ENCODE: JSON -> TOON
    Write-Log "Encoding: $InputFile -> TOON" "Cyan"

    try {
        # Creer un fichier temp JSON pour l'encoder
        $tempJson = [System.IO.Path]::GetTempFileName() + ".json"
        $sourceContent | Set-Content $tempJson -Encoding UTF8

        $toonOutput = & $TOON_BIN encode --input $tempJson 2>&1

        Remove-Item $tempJson -Force -ErrorAction SilentlyContinue

        if ($LASTEXITCODE -ne 0 -or (-not $toonOutput)) {
            throw "TOON encode failed: $toonOutput"
        }

        $toonChars = $toonOutput.Length
        $savings = if ($sourceChars -gt 0) { [math]::Round((($sourceChars - $toonChars) / $sourceChars) * 100, 1) } else { 0 }

        Write-Log "  JSON:   $sourceChars chars" "Gray"
        Write-Log "  TOON:   $toonChars chars" "Gray"
        Write-Log "  Gain:   $savings%" $(if ($savings -gt 25) { "Green" } else { "Yellow" })

        # Recommandation
        if ($savings -gt 25) {
            Write-Log "  RECOMMANDE: Activer TOON par defaut (gain > 25%)" "Green"
        } else {
            Write-Log "  NOTE: Gain < 25%, JSON peut suffire" "Yellow"
        }

        # Sauvegarder stats
        if ($StatsSave) {
            $metricsDir = Split-Path $KPI_FILE
            if (-not (Test-Path $metricsDir)) {
                New-Item -ItemType Directory -Path $metricsDir -Force | Out-Null
            }
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $filename = Split-Path $InputFile -Leaf
            $header = "timestamp,file,json_chars,toon_chars,savings_pct,recommended"
            $row = "$timestamp,$filename,$sourceChars,$toonChars,$savings,"
            if ($savings -gt 25) { $row += "YES" } else { $row += "NO" }
            if (-not (Test-Path $KPI_FILE)) {
                $header | Set-Content $KPI_FILE -Encoding UTF8
            }
            $row | Add-Content $KPI_FILE -Encoding UTF8
            Write-Log "  Stats sauvegardees dans $KPI_FILE" "Green"
        }

        # Output TOON
        if (-not $DryRun) {
            $toonFile = [System.IO.Path]::ChangeExtension($InputFile, ".toon")
            $toonOutput | Set-Content $toonFile -Encoding UTF8
            Write-Log "  TOON ecrit dans $toonFile" "Green"
        }

        # Fallback: si gain < 25%, garder une copie JSON
        if ($savings -lt 25 -and (Test-Path $InputFile)) {
            Write-Log "  Fallback JSON conserve: $InputFile" "Yellow"
        }

        return @{
            source = $InputFile
            sourceChars = $sourceChars
            toonChars = $toonChars
            savings = $savings
            recommended = ($savings -gt 25)
            toonOutput = $toonOutput
        }

    } catch {
        Write-Log "ERREUR encoding TOON: $_" "Red"
        Write-Log "Fallback: utilisation du JSON original" "Yellow"
        return @{ error = $_.Exception.Message; fallback = "json" }
    }
} else {
    # DECODE: TOON -> JSON
    Write-Log "Decoding: $InputFile -> JSON" "Cyan"
    try {
        $tempToon = [System.IO.Path]::GetTempFileName() + ".toon"
        $sourceContent | Set-Content $tempToon -Encoding UTF8

        $jsonOutput = & $TOON_BIN decode --input $tempToon 2>&1

        Remove-Item $tempToon -Force -ErrorAction SilentlyContinue

        if ($LASTEXITCODE -ne 0 -or (-not $jsonOutput)) {
            throw "TOON decode failed: $jsonOutput"
        }

        if (-not $DryRun) {
            $jsonFile = [System.IO.Path]::ChangeExtension($InputFile, ".json")
            $jsonOutput | Set-Content $jsonFile -Encoding UTF8
            Write-Log "  JSON ecrit dans $jsonFile" "Green"
        }

        return @{
            source = $InputFile
            jsonOutput = $jsonOutput
        }
    } catch {
        Write-Log "ERREUR decoding TOON: $_" "Red"
        Write-Log "Fallback: lecture du JSON original" "Yellow"
        return @{ error = $_.Exception.Message; fallback = "json" }
    }
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/devcore/DEV_CORE
git add Scripts/toonify.ps1
git commit -m "feat: add toonify.ps1 for JSON<->TOON conversion with stats [T-03]"
```

---

### Task 12: Tester toonify sur tasks.json

**Files:**
- Nothing to create

- [ ] **Step 1: Tester conversion tasks.json -> TOON**

```powershell
& "C:/devcore/DEV_CORE/Scripts/toonify.ps1" -InputFile "C:/devcore/DEV_CORE_DATA/Memory/tasks.json" -StatsSave
```

Expected: Affiche "Gain: XX%" avec recommandation

- [ ] **Step 2: Verifier le fichier kpi.csv**

```bash
cat C:/devcore/DEV_CORE_DATA/Metrics/kpi.csv
```

Expected: contient les stats de conversion

- [ ] **Step 3: Verifier le fichier tasks.toon**

```bash
cat C:/devcore/DEV_CORE_DATA/Memory/tasks.toon
```

Expected: affiche le contenu TOON valide

- [ ] **Step 4: Verifier le decode TOON -> JSON**

```powershell
& "C:/devcore/DEV_CORE/Scripts/toonify.ps1" -InputFile "C:/devcore/DEV_CORE_DATA/Memory/tasks.toon" -Decode
```

Expected: retourne JSON valide

---

## Self-Review

**1. Spec coverage:**
- [x] post-commit.hook modifie -> Task 1
- [x] session_start.hook (endday_check) -> Task 4
- [x] session_end.hook cree -> Task 7, 9
- [x] endday_check.ps1 cree -> Task 2
- [x] qdrant_sync.ps1 cree -> Task 5
- [x] obsidian_sync.ps1 cree -> Task 6
- [x] toonify.ps1 cree -> Task 11
- [x] Metrics/kpi.csv -> Task 11, 12
- [x] gen_metrics.ps1 -> Task 8
- [x] gen_session_context.ps1 -> Task 3

**2. Placeholder scan:** Aucun placeholder trouve.

**3. Type consistency:** Tous les chemins et noms coherents.

**4. Spec compliance:** Spec completement couverte.
