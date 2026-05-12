# Guide de Migration DEV_CORE v6

**De** : `C:\DEV_CORE` + `C:\DEV_CORE_DATA`  
**Vers** : `C:\devcore\DEV_CORE` + `C:\devcore\DEV_CORE_DATA`

**Date** : 2026-05-12
**Changements** : Detection automatique des taches (v6.1)

---

## Changements majeurs

### 1. Structure des dossiers

**Avant** :
```
C:\DEV_CORE\
C:\DEV_CORE_DATA\
```

**Après** :
```
C:\devcore\
  ├── DEV_CORE\
  └── DEV_CORE_DATA\
```

### 2. Workflow

**Avant** : Missions (M-01, M-02...) avec handoffs multi-agents
**Après** : Tasks (T-01, T-02...) single client + 9Router

### 3. Fichiers

| Avant | Après | Action |
|-------|-------|--------|
| `missions.json` | `tasks.json` | Archivé → `.archived` |
| `mission_*.ps1` | `task_*.ps1` | Déplacé → `archived/` |
| Tag git `[M-XX]` | Tag git `[T-XX]` | Nouveau format |
| `MISSIONS_JSON` | `TASKS_JSON` | PATHS.md mis à jour |

---

## Procédure de migration

### Étape 1 : Sauvegarder

```powershell
# Backup complet
xcopy C:\DEV_CORE C:\DEV_CORE_BACKUP\ /E /I /H
xcopy C:\DEV_CORE_DATA C:\DEV_CORE_DATA_BACKUP\ /E /I /H
```

### Étape 2 : Déplacer

```powershell
# Créer structure
mkdir C:\devcore

# Déplacer
mv C:\DEV_CORE C:\devcore\DEV_CORE
mv C:\DEV_CORE_DATA C:\devcore\DEV_CORE_DATA
```

### Étape 3 : Mettre à jour variables d'environnement

```powershell
# Méthode 1 : Via setup.ps1
cd C:\devcore\DEV_CORE\Scripts
.\setup.ps1

# Méthode 2 : Manuellement
[System.Environment]::SetEnvironmentVariable("DEVCORE_PLATFORM_ROOT", "C:\devcore\DEV_CORE", "User")
[System.Environment]::SetEnvironmentVariable("DEVCORE_DATA_ROOT", "C:\devcore\DEV_CORE_DATA", "User")
```

### Étape 4 : Vérifier

```powershell
# Vérifier variables
$env:DEVCORE_PLATFORM_ROOT
$env:DEVCORE_DATA_ROOT

# Diagnostic complet
dc check

# Test
dc launch
```

### Étape 5 : Migrer missions → tasks

```powershell
# Archiver missions.json
mv C:\devcore\DEV_CORE_DATA\Memory\missions.json C:\devcore\DEV_CORE_DATA\Memory\missions.json.archived

# Créer tasks.json (fait automatiquement par task_next.ps1)
dc new task "Migration complete" -reasoning
```

---

## Fichiers modifiés automatiquement

Ces fichiers ont été mis à jour pour refléter la nouvelle structure :

### Configuration
- ✅ `CLAUDE.md` — Tag `[T-XX]`, plus de références missions
- ✅ `PATHS.md` — Chemins mis à jour
- ✅ `DECISIONS.md` — Tasks board au lieu de mission board
- ✅ `GLOBAL_STATE.md` — Single client mode
- ✅ `MEMORY.md` — Tasks au lieu de missions

### Scripts
- ✅ `launch.ps1` — Lit `tasks.json` au lieu de `missions.json`
- ✅ `dc.ps1` — Alias missions redirigent vers tasks
- ✅ `post-commit.hook` — Chemin mis à jour

### Dashboard
- ✅ `index.html` — Affiche tasks au lieu de missions

---

## Compatibilité

### Alias conservés

Les anciens alias missions sont redirigés vers tasks :

```powershell
dc next mission  → dc next task
dc mission done  → dc task done
dc mission status → dc task status
```

### Scripts archivés

Les scripts missions sont conservés dans `Scripts/archived/` :
- `mission_add.ps1`
- `mission_done.ps1`
- `mission_next.ps1`
- `mission_pause.ps1`
- `mission_skip.ps1`
- `mission_status.ps1`

---

## Rollback (si nécessaire)

```powershell
# 1. Restaurer structure
mv C:\devcore\DEV_CORE C:\DEV_CORE
mv C:\devcore\DEV_CORE_DATA C:\DEV_CORE_DATA

# 2. Restaurer variables
[System.Environment]::SetEnvironmentVariable("DEVCORE_PLATFORM_ROOT", "C:\DEV_CORE", "User")
[System.Environment]::SetEnvironmentVariable("DEVCORE_DATA_ROOT", "C:\DEV_CORE_DATA", "User")

# 3. Restaurer missions.json
mv C:\DEV_CORE_DATA\Memory\missions.json.archived C:\DEV_CORE_DATA\Memory\missions.json

# 4. Relancer setup
cd C:\DEV_CORE\Scripts
.\setup.ps1
```

---

## Vérification post-migration

### Checklist

- [ ] Variables d'environnement correctes
- [ ] `dc check` passe sans erreur
- [ ] `dc launch` fonctionne
- [ ] `tasks.json` existe et est valide
- [ ] Dashboard accessible
- [ ] Qdrant accessible (port 6333)
- [ ] Ollama accessible (port 11434)
- [ ] Skills symlinks corrects

### Commandes de test

```powershell
# Variables
$env:DEVCORE_PLATFORM_ROOT
$env:DEVCORE_DATA_ROOT

# Fichiers clés
Test-Path C:\devcore\DEV_CORE_DATA\Memory\tasks.json
Test-Path C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt

# Services
curl http://localhost:6333/collections
curl http://localhost:11434/api/version

# Dashboard
start C:\devcore\DEV_CORE\Dashboard\index.html
```

---

## Nouvelles fonctionnalites v6.1

### Detection automatique des taches

```powershell
# Scanner toutes les sources
dc task scan

# Synchroniser dans tasks.json
dc task sync
```

Les scripts Auto crees :
- `task_git_scanner.ps1` — Detecte tags [T-XX] dans commits
- `task_spec_parser.ps1` — Parse fichiers spec markdown
- `task_prompt_analyzer.ps1` — Analyse sessions recentes
- `task_scan.ps1` — Orchestre les 3 scanners
- `task_sync.ps1` — Syncronise les suggestions

### Integration launch

`launch.ps1` inclut maintenant 8 etapes (au lieu de 7) avec detection automatique.

---

## Nouvelles fonctionnalites v6.1

### Detection automatique des taches

```powershell
# Scanner toutes les sources
dc task scan

# Synchroniser dans tasks.json
dc task sync
```

Les scripts Auto crees :
- `task_git_scanner.ps1` — Detecte tags [T-XX] dans commits
- `task_spec_parser.ps1` — Parse fichiers spec markdown
- `task_prompt_analyzer.ps1` — Analyse sessions recentes
- `task_scan.ps1` — Orchestre les 3 scanners
- `task_sync.ps1` — Syncronise les suggestions

### Integration launch

`launch.ps1` inclut maintenant 8 etapes (au lieu de 7) avec detection automatique.

---

## Problèmes connus

### 1. setup.ps1 recrée C:\DEV_CORE_DATA

**Cause** : Variables d'env pas encore définies lors du premier setup

**Solution** : Définir manuellement les variables avant de relancer setup.ps1

### 2. Alias dc non reconnu

**Cause** : Profil PowerShell pas rechargé

**Solution** :
```powershell
. $PROFILE
# ou
Set-Alias dc 'C:\devcore\DEV_CORE\Scripts\dc.ps1'
```

### 3. Skills symlinks cassés

**Cause** : Chemins absolus dans les symlinks

**Solution** :
```powershell
cd C:\devcore\DEV_CORE\Scripts
.\adapt_client.ps1 -Client claude
```

---

## Support

- **Diagnostic** : `dc check`
- **Logs** : `C:\devcore\DEV_CORE_DATA\Logs\`
- **Documentation** : `C:\devcore\DEV_CORE\docs\PLATFORM_DOCUMENTATION.md`
