# DEV_CORE v7 — README

**Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel

Version : 7.3.0  
Updated : 2026-05-24  
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

## 🔄 Changelog v7

### 2026-05-24 — v7.3 Detached Daemon & Resilient API

- ✅ **Lancement autonome via WMI** : Remplacement de l'instable `Start-Process` dans `hermes-daemon.ps1` par la création de processus détachés à l'aide de la méthode WMI `Win32_Process.Create` de façon à ce que le démon de tick survive à la fermeture du terminal parent.
- ✅ **Prise en charge de flux stdout nuls/fermés** : Robustesse accrue du script `hermes_cron_tick.py` (le gestionnaire de logs `StreamHandler` n'est configuré que si `sys.stdout` n'est pas `None`, et l'action de vidage de flux `flush()` est désormais protégée par un `try...except OSError`).
- ✅ **Résilience de dashboard_api.py** : Ajout d'une capture propre du signal `ConnectionError` (ConnectionAborted, Reset, Broken Pipe) lors de l'envoi de la régénération d'index afin d'éviter tout crash secondaire ou affichage de tracebacks inutiles.
- ✅ **Nettoyage des étapes de tâches Git autonomes** : Retrait de l'étape générique redondante *"Execution et implémentation"* des tâches créées via `post-commit.hook`. Les tâches basées sur des commits Git n'ont plus d'étapes superflues, rendant leur affichage sur le Cockpit beaucoup plus épuré.

### 2026-05-22 — v7.2 Dynamic Partial Refresh & Live Cockpit API

- ✅ **Remplacement du Meta-Refresh par AJAX** : Retrait du tag HTML meta-refresh obsolète qui causait une réactualisation totale de la page toutes les 30 secondes, entraînant la perte du défilement et de l'état d'ouverture des accordéons.
- ✅ **Nouvel Endpoint `/api/refresh`** : Ajout d'une route `GET /api/refresh` dans le serveur API local `dashboard_api.py` qui compile et retourne de manière dynamique le dernier contenu HTML généré.
- ✅ **Algorithme de DOM Diffing Partiel** : Implémentation d'une logique JavaScript robuste de comparaison et de mise à jour partielle intelligente dans `template.html`. Met à jour uniquement le contenu dynamique modifié tout en conservant l'état d'interaction de l'utilisateur (scroll, expansions).
- ✅ **Indicateur de Synchronisation (#sync-indicator)** : Ajout d'un voyant LED interactif dans le header du dashboard indiquant l'état en temps réel du rafraîchissement (Violet clignotant = rafraîchissement en cours, Vert = synchronisé, Rouge = erreur de communication avec le serveur).

### 2026-05-21 — v7.1 Robustesse du Cockpit & Simulation des Métriques de Cache

- ✅ **Résolution des Projets Fantômes** : Déploiement d'une liste noire insensible à la casse de dossiers système Windows (`Documents`, `Desktop`, `Downloads`, `OneDrive`, etc.) dans `Get-ActiveProject.ps1` et `task_prompt_analyzer.py` pour éviter le chargement de projets fantômes lorsque les tâches d'arrière-plan s'exécutent depuis le répertoire utilisateur.
- ✅ **Métriques de prompt caching (85%)** : Clarification de l'estimation de tokens hors-ligne dans `token_report.py` (comme l'API de Gemini ne logge pas son statut de cache réel dans le fichier local `overview.txt`, le script applique un taux d'efficacité empirique constant de 85% correspondant à la rétention moyenne de contexte).

### 2026-05-20 — v7.0 Auto-Apprentissage & Intelligence Sémantique

- ✅ **Intelligence Sémantique** : Intégration de l'impératif et du présent conjugués en français pour la détection autonome d'intentions de tâches (ex : `corrige`, `crée`, `ajoute`).
- ✅ **Analyseur de Prompts Actif** : Remplacement du scan sémantique historique par un analyseur dynamique (`task_prompt_analyzer.py`) scannant en temps réel les journaux de sessions d'Antigravity (`C:\Users\trb_m\.gemini\antigravity\brain`).
- ✅ **Nettoyage des Titres** : Élimination automatique des balises XML et des métadonnées système (`</USER_REQUEST>`, etc.) des titres de tâches capturés pour un rendu ultra-propre dans le cockpit.
- ✅ **Registre Sémantique Dynamique** : Création de `intent_patterns.json` pour externaliser les verbes cibles et découpler la logique du code.
- ✅ **Moteur d'Auto-Apprentissage (`intent_learner.py`)** : Déploiement d'un moteur d'arrière-plan autonome qui extrait le premier mot des tâches validées de `tasks.json`, génère ses déclinaisons sémantiques françaises, et enrichit le registre dynamique sans intervention humaine.
- ✅ **Intégration au Cycle de Vie** : Hook de l'apprentissage automatique dans la phase 5/8 du script `endday.ps1` et du wrapper Powershell de scan.

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
- ✅ **Cockpit Single View** : Interface 100vh compacte en 3 colonnes avec défilements indépendants.
- ✅ **Filtres Historiques & Tri Dynamique** : Filtrage temporel JS (All, 1j, 7j, 30j) des tâches closes et tri intelligent (les Worktrees et Tâches récents s'affichent en premier).
- ✅ **Clarté UX & Détails fluides** : Élimination des caractères spéciaux, suppression des fonds opaques verts pour les tâches, et affichage étendu sur une ligne des étapes (`steps-container`).
- ✅ **Correction des Hooks Antigravity** : Correction du script `install_universal_hooks.ps1` pour installer correctement les déclencheurs dans le dossier utilisateur d'Antigravity (`.gemini\antigravity`) au lieu de `.antigravity`.
- ✅ **Cycle des Tâches 100% Autonome** : Amélioration de `session_start.ps1` pour lier automatiquement un projet (`dc link project`) et créer la première tâche (`dc new task`) si aucun tableau de bord n'existe encore. Plus de blocage manuel pour l'initialisation.

### 2026-05-18 — v6.5 Cockpit API Operations & Task Synchronization

- ✅ **Boutons d'Actions Intégrés** : Ajout de boutons interactifs ("Clôturer" et "Supprimer") directement sur les tâches dans le Cockpit HTML.
- ✅ **Dashboard local API Server** : Implémentation d'un serveur API local Python (`dashboard_api.py`) sur le port 20129 pour traiter en temps réel la complétion et la suppression des tâches, avec démarrage automatique via le script `gen_dashboard.ps1`.
- ✅ **Nettoyage des Tâches devcore** : Nettoyage des anciennes tâches obsolètes `T-09` à `T-18` et renumérotation des nouvelles tâches avec synchronisation `.json` et `.toon`.
- ✅ **Synchronisation job_tracker** : Indexation et validation de l'historique des commits des 17 et 18 mai n'ayant pas de tags de tâches (`T-04` à `T-06`), avec validation visuelle autonome via un sous-agent de navigation (complétion de 100%).

### 2026-05-17 — v6.4 Dashboard Real-Time Fixes & Sorting

- ✅ **Tri Dynamique de l'Activité** : Tri automatique des projets du Cockpit par date de tâche la plus récente, mettant le projet actif et ses modifications récentes en premier lieu.
- ✅ **Robustesse des Chemins des Hooks** : Correction des chemins relatifs de `gen_dashboard.ps1` via `$PSScriptRoot` dans les scripts de transition de tâche (`task_done`, `task_step_done`, `task_pause`, `task_edit`) pour garantir un rafraîchissement immédiat et sans erreur du tableau de bord.

**Avant** : Multi-client (claude → codex → antigravity)  
**Après** : Single client (claude + 9Router)  
**Gain** : Simplicité, pas de handoffs, routing automatique

---

## 🆘 Support

- **Diagnostic** : `dc check`
- **Logs** : `C:\devcore\DEV_CORE_DATA\Logs\`
- **Dashboard** : `C:\devcore\DEV_CORE\Dashboard\index.html`
- **Issues** : GitHub repo
