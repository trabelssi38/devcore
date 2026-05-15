---
name: devcore-automation
description: >-
  CHARGER EN PREMIER a chaque session. Definit les regles d'execution autonome
  de DEV_CORE v6.2 : initialisation projet, lancement taches, commits, step tracking,
  fin de session. L'agent execute les scripts ps1 sans attendre d'instruction
  humaine. Triggers automatiques sur detection de conditions precisees.
compatibility: Claude Code · Codex Desktop · Gemini CLI · Antigravity
priority: 100
---

# Skill -- DEV_CORE Automation v6.2
# Ce skill remplace toute intervention humaine sur les scripts DEV_CORE.
# L'agent lit, decide et execute. Pas de confirmation demandee.

## REGLE ABSOLUE
Tu executes les scripts DEV_CORE de facon autonome.
Tu n'attends pas de confirmation humaine pour les actions DEV_CORE.
Tu informes apres execution, pas avant.

---

## TRIGGER 1 -- Debut de session (TOUJOURS)

A chaque ouverture de session, executer dans l'ordre :

```
1. Verifier CWD et projet actif
2. Lancer launch.ps1 si pas lance aujourd'hui
3. Lancer dc next task
4. Lire next_actions.md (handoff precedent)
5. Afficher la tache et commencer
```

**Commandes exactes :**
```powershell
# Claude Code
Bash("powershell -ExecutionPolicy Bypass -NonInteractive -File `"C:\devcore\DEV_CORE\Scripts\launch.ps1`"")
Bash("powershell -ExecutionPolicy Bypass -NonInteractive -File `"C:\devcore\DEV_CORE\Scripts\dc.ps1`" `"next task`"")

# Codex / Gemini
shell("powershell -ExecutionPolicy Bypass -NonInteractive -File \"C:\\devcore\\DEV_CORE\\Scripts\\launch.ps1\"")
shell("powershell -ExecutionPolicy Bypass -NonInteractive -File \"C:\\devcore\\DEV_CORE\\Scripts\\dc.ps1\" \"next task\"")
```

---

## TRIGGER 2 -- Nouveau projet detecte

**Condition :** pas de `.devcore\project.json` dans le repertoire courant.

**Action automatique :**
```powershell
$projectName = Split-Path (Get-Location) -Leaf
$stack = "generic"
if (Test-Path "*.py" -or Test-Path "requirements.txt" -or Test-Path "pyproject.toml") { $stack = "python" }
if (Test-Path "package.json") { $stack = "web" }
if (Test-Path "build.gradle" -or Test-Path "*.gradle") { $stack = "android" }

powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\new_project.ps1" -Name $projectName -Stack $stack
```

Apres initialisation, reprendre depuis le TRIGGER 1.

---

## TRIGGER 3 -- Apres chaque etape validee

**Condition :** une etape de la tache est terminee (tests passants, code fonctionne).

**Action automatique :**
```bash
# Toujours commiter avec le tag de tache
git add -A
git commit -m "feat: [description courte] [T-XX]"
# XX = ID de la tache courante depuis tasks.json
# Le post-commit hook auto-incremente steps_done
```

**Lire l'ID de tache depuis tasks.json :**
```powershell
$b = Get-Content "C:\devcore\DEV_CORE_DATA\Memory\tasks.json" -Raw | ConvertFrom-Json
$taskId = ($b.tasks | Where-Object { $_.status -eq "active" } | Select-Object -First 1).id
# Utiliser $taskId dans le commit message
```

**Ou marquer une step manuellement :**
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\task_step_done.ps1"
# Auto-selectionne la prochaine step non-faite
```

---

## TRIGGER 4 -- Tache complete

**Condition :** Le post-commit hook et post_tool_hook detectent automatiquement quand steps_done >= steps_total.

**Si detection automatique echoue :**
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\task_done.ps1" -Force
```

**Auto-chainage :** task_done.ps1 charge automatiquement la tache suivante via task_next.ps1. Pas besoin de relancer `dc next task`.

---

## TRIGGER 5 -- Fin de session

**Condition :** l'agent a termine son travail (tache done ou fin de journee).

**Action automatique :**
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup
```

`-SkipBackup` si la session a ete courte (< 2h). Sans flag si session complete.

---

## TRIGGER 6 -- Nouveau projet avec git init

Si le projet n'a pas de depot git :
```bash
git init
git add -A
git commit -m "chore: init projet [T-00]"
# Le hook post-commit est installe automatiquement par session_start.ps1
```

---

## Format de communication a l'humain

Apres chaque action automatique, une ligne de log :
```
[DEV_CORE] launch.ps1 execute -- Task T-02 active
[DEV_CORE] Commit [T-02] -- step 2/5 enregistree
[DEV_CORE] task_done.ps1 -- T-02 done -- Auto-chainage T-03
[DEV_CORE] endday.ps1 -- lecons extraites -- Qdrant sync -- backup OK
```

Pas de bloc d'explication. Une ligne, puis continuer le travail.

---

## Lecture tasks.json -- helper

```python
import json, pathlib

def get_active_task():
    p = pathlib.Path(r"C:\devcore\DEV_CORE_DATA\Memory\tasks.json")
    if not p.exists():
        return None
    board = json.loads(p.read_text(encoding="utf-8"))
    return next((t for t in board["tasks"] if t["status"] == "active"), None)

def get_task_id():
    t = get_active_task()
    return t["id"] if t else "T-00"
```

---

## Ce que l'agent NE fait PAS

- Ne demande pas "voulez-vous que je lance launch.ps1 ?" -- il le lance
- Ne dit pas "je vais maintenant executer..." -- il execute puis informe
- Ne saute pas un trigger parce que "ca semble deja fait" -- verifier tasks.json
- Ne commite pas sans tag [T-XX]
- Ne termine pas une session sans endday.ps1
