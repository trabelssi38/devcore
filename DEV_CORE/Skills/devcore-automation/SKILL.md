---
name: devcore-automation
description: >-
  CHARGER EN PREMIER a chaque session. Definit les regles d'execution autonome
  de DEV_CORE : initialisation projet, lancement missions, commits, handoff,
  fin de session. L'agent execute les scripts ps1 sans attendre d'instruction
  humaine. Triggers automatiques sur detection de conditions precisees.
compatibility: Claude Code · Codex Desktop · Gemini CLI · Antigravity
priority: 100
---

# Skill -- DEV_CORE Automation
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
3. Lancer dc.ps1 "next mission"
4. Lire next_actions.md (handoff precedent)
5. Afficher la mission et commencer
```

**Commandes exactes :**
```powershell
# Claude Code
Bash("powershell -ExecutionPolicy Bypass -NonInteractive -File `"C:\DEV_CORE\Scripts\launch.ps1`"")
Bash("powershell -ExecutionPolicy Bypass -NonInteractive -File `"C:\DEV_CORE\Scripts\dc.ps1`" `"next mission`"")

# Codex
shell("powershell -ExecutionPolicy Bypass -NonInteractive -File \"C:\\DEV_CORE\\Scripts\\launch.ps1\"")
shell("powershell -ExecutionPolicy Bypass -NonInteractive -File \"C:\\DEV_CORE\\Scripts\\dc.ps1\" \"next mission\"")
```

---

## TRIGGER 2 -- Nouveau projet detecte

**Condition :** pas de `.devcore\project.json` dans le repertoire courant.

**Action automatique :**
```powershell
# Detecter le nom du projet depuis le nom du dossier
$projectName = Split-Path (Get-Location) -Leaf

# Detecter la stack depuis les fichiers presents
$stack = "generic"
if (Test-Path "*.py" -or Test-Path "requirements.txt" -or Test-Path "pyproject.toml") { $stack = "python" }
if (Test-Path "package.json") { $stack = "web" }
if (Test-Path "build.gradle" -or Test-Path "*.gradle") { $stack = "android" }

# Initialiser
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\new_project.ps1" -Name $projectName -Stack $stack
```

Apres initialisation, reprendre depuis le TRIGGER 1.

---

## TRIGGER 3 -- Apres chaque etape validee

**Condition :** une etape de la mission est terminee (tests passants, code fonctionne).

**Action automatique :**
```bash
# Toujours commiter avec le tag de mission
git add -A
git commit -m "feat: [description courte] [M-XX]"
# XX = ID de la mission courante depuis missions.json
```

**Lire l'ID de mission depuis missions.json :**
```powershell
$b = Get-Content "C:\DEV_CORE_DATA\Memory\missions.json" -Raw | ConvertFrom-Json
$missionId = ($b.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1).id
# Utiliser $missionId dans le commit message
```

---

## TRIGGER 4 -- Mission complete

**Condition :** verifier apres chaque commit si toutes les steps sont done.

```powershell
$b = Get-Content "C:\DEV_CORE_DATA\Memory\missions.json" -Raw | ConvertFrom-Json
$active = $b.missions | Where-Object { $_.status -eq "active" } | Select-Object -First 1
$allDone = $active -and ($active.steps_done -ge $active.steps_total)
```

**Si $allDone = true :**
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\mission_done.ps1" -Force
# -Force evite la confirmation interactive
```

Apres mission_done.ps1, verifier s'il y a une prochaine mission :
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\dc.ps1" "next mission"
```

---

## TRIGGER 5 -- Fin de session

**Condition :** l'agent a termine son travail (mission done ou fin de journee).

**Action automatique :**
```powershell
powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\DEV_CORE\Scripts\endday.ps1" -SkipBackup
```

`-SkipBackup` si la session a ete courte (< 2h). Sans flag si session complete.

---

## TRIGGER 6 -- Nouveau projet avec git init

Si le projet n'a pas de depot git :
```bash
git init
git add -A
git commit -m "chore: init projet [M-00]"
# Puis installer le hook post-commit
powershell -ExecutionPolicy Bypass -NonInteractive -Command "
  Copy-Item 'C:\DEV_CORE\Scripts\post-commit.hook' '.git\hooks\post-commit' -Force
"
```

---

## Format de communication a l'humain

Apres chaque action automatique, une ligne de log :
```
[DEV_CORE] launch.ps1 execute -- Mission M-02 active -- Codex
[DEV_CORE] Commit [M-02] -- step 2/5 enregistree
[DEV_CORE] mission_done.ps1 -- M-02 done -- Prochaine : M-03 Antigravity
[DEV_CORE] endday.ps1 -- lecons extraites -- Qdrant sync -- backup OK
```

Pas de bloc d'explication. Une ligne, puis continuer le travail.

---

## Lecture missions.json -- helper

```python
import json, pathlib

def get_active_mission():
    p = pathlib.Path(r"C:\DEV_CORE_DATA\Memory\missions.json")
    if not p.exists():
        return None
    board = json.loads(p.read_text(encoding="utf-8"))
    return next((m for m in board["missions"] if m["status"] == "active"), None)

def get_mission_id():
    m = get_active_mission()
    return m["id"] if m else "M-00"
```

---

## Ce que l'agent NE fait PAS

- Ne demande pas "voulez-vous que je lance launch.ps1 ?" -- il le lance
- Ne dit pas "je vais maintenant executer..." -- il execute puis informe
- Ne saute pas un trigger parce que "ca semble deja fait" -- verifier missions.json
- Ne commite pas sans tag [M-XX]
- Ne termine pas une session sans endday.ps1
