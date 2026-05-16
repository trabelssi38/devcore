# DEV_CORE v6 — README

**Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel

Version : 6.3  
Updated : 2026-05-16  
Mode : Single Client (pas de handoffs multi-agents)

---

## 🚀 Quick Start

```powershell
# 1. Installation
cd C:\devcore\DEV_CORE\Scripts
.\setup.ps1

# 2. Démarrer les services
docker run -d -p 6333:6333 qdrant/qdrant
ollama serve
ollama pull nomic-embed-text

# 3. Lancer DEV_CORE
dc launch

# 4. Vérifier
dc check
```

---

## 📋 Workflow Tasks

```powershell
# Créer une tâche
dc new task "Implémenter API REST" -reasoning

# Charger la tâche active
dc next task

# Travailler...
git commit -m "feat: add REST endpoints [T-01]"

# Valider la tâche
dc task done

# Voir le statut
dc task status
```

---

## 🎯 Modes cognitifs (9Router)

| Mode | Usage | Budget | Modèles |
|------|-------|--------|---------|
| **reasoning** | Architecture, spec, décisions | 32k | Opus, o3 |
| **coding** | Implémentation, TDD, patches | 8k | Sonnet, Codex |
| **bulk** | Génération masse, docs, tests | 16k | Haiku, Flash |

Le mode est détecté automatiquement par 9Router selon les mots-clés.

---

## 📁 Structure

```
C:\devcore\
├── DEV_CORE\              # Plateforme (scripts, skills, config)
└── DEV_CORE_DATA\         # Données (mémoire, logs, vault)
```

---

## 🔧 Commandes principales

### Tâches
- `dc next task` — Charge prochaine tâche
- `dc task done` — Valide + sync mémoire
- `dc task status` — Dashboard tâches
- `dc new task [titre] -[mode]` — Crée une tâche

### Cycle
- `dc launch` — Démarrage journée
- `dc endday` — Clôture + sync
- `dc check` — Diagnostic complet

### Projet
- `dc new project [nom] -stack [x]` — Init projet
- `dc link project [nom]` — Lier projet existant

---

## 📊 Dashboard

Ouvrir dans un navigateur :
```
file:///C:/devcore/DEV_CORE/Dashboard/index.html
```

Auto-refresh 30s — Affiche :
- Multi-projets : Cards récapitulatives par projet
- Worktrees : Tags [worktree] dans la pipeline
- Infrastructure Temps Réel : Monitoring ports (Qdrant, Ollama, Hermes)
- Automation Hooks : Horodatage réel des dernières exécutions
- Pipeline tasks globale (T-01 → T-04)

---

## 🧠 Mémoire

### Architecture
```
MEMORY.md (index)
    ↓
Qdrant (3 collections: decisions/patterns/lessons)
    ↓
Obsidian Vault (notes structurées)
```

### Workflow
1. Consulter Qdrant (score > 0.75 = réutiliser)
2. Créer nouvelle décision/pattern/lesson
3. Embedder via nomic-embed-text
4. Stocker dans Qdrant + Obsidian + MEMORY.md

---

## 🛠️ Skills

**Core skills actifs** :
- `qdrant` — Mémoire vectorielle
- `obsidian` — Vault management
- `graphify` — Graphes de connaissances
- `fabric-patterns` — Patterns IA
- `dev-methodology` — Méthodologie dev

**Total installés** : 159 skills

---

## 📖 Documentation complète

Voir : `C:\devcore\DEV_CORE\docs\PLATFORM_DOCUMENTATION.md`

---

## 🔄 Changelog v6

### 2026-05-11 — Single Client Migration

- ✅ Missions → Tasks (workflow simplifié)
- ✅ Scripts `mission_*.ps1` archivés
- ✅ `tasks.json` avec modes (reasoning/coding/bulk)
- ✅ Tags git `[T-XX]` au lieu de `[M-XX]`
- ✅ Structure déplacée : `C:\devcore\`
- ✅ Variables d'env mises à jour
- ✅ Documentation complète

### 2026-05-16 — v6.3 Multi-Project & Worktree Support

- ✅ **Multi-Projet** : Dashboard dynamique agrégeant tous les projets de `DEV_CORE_DATA\Memory\`.
- ✅ **Worktree Isolation** : Support natif de `git worktree` via `Get-ActiveProject.ps1`.
- ✅ **Dynamic Monitoring** : Dashboard auto-généré avec état réel des ports et timestamps de logs.
- ✅ **Tags Worktree** : Métadonnée `"worktree"` injectée dans les tâches pour le tracking multi-branche.

**Avant** : Multi-client (claude → codex → antigravity)  
**Après** : Single client (claude + 9Router)  
**Gain** : Simplicité, pas de handoffs, routing automatique

---

## 🆘 Support

- **Diagnostic** : `dc check`
- **Logs** : `C:\devcore\DEV_CORE_DATA\Logs\`
- **Dashboard** : `C:\devcore\DEV_CORE\Dashboard\index.html`
- **Issues** : GitHub repo
