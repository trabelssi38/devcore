# DEV_CORE v10 - README

**Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel

Version : 10.0.0
Updated : 2026-07-09
Mode : Single Client (pas de handoffs multi-agents)

---

## 🚀 Quick Start

```powershell
# 1. Installation
cd C:\devcore\DEV_CORE\Scripts
.\setup.ps1

# 2. Démarrer les services
docker run -d -p 6333:6333 qdrant/qdrant

# 3. Lancer DEV_CORE
dc launch

# 4. Vérifier
dc check
dc health
dc check --gate
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

## 🎯 Modes cognitifs

| Mode | Usage | Budget | Modèles |
|------|-------|--------|---------|
| **reasoning** | Architecture, spec, décisions | 32k | Gemini 2.5 Pro |
| **coding** | Implémentation, TDD, patches | 8k | Gemini 2.5 Pro |
| **bulk** | Génération masse, docs, tests | 16k | Gemini 2.5 Flash |

Le mode est géré par Gemini Router pour le choix du modèle optimal.

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
- `dc check --gate` — Diagnostic release gate avec code de sortie
- `dc check --fix --dry-run` — Simulation des réparations sans écriture
- `dc health` — Rapport court services, secrets, mémoire et task board
- `dc health --json` — Rapport health exploitable par scripts

### Projet
- `dc new project [nom] -stack [x]` — Init projet
- `dc link project [nom]` — Lier projet existant

### Repowise
- `DEV_CORE\Scripts\ensure_repowise_mcp.ps1` — Configure Repowise MCP pour Codex, Claude Code, Gemini/Antigravity et opencode
- `DEV_CORE\Scripts\ensure_repowise_watch.ps1` — Lance le scan continu Repowise des projets déclarés
- `DEV_CORE\Scripts\ensure_repowise_watch.ps1 -StatusOnly` — Affiche les watchers actifs
- `DEV_CORE\Scripts\ensure_repowise_watch.ps1 -Stop` — Arrête les watchers

---

## 📊 Dashboard

Ouvrir dans un navigateur (Recommandé pour éviter les restrictions CORS) :
```
http://127.0.0.1:20129/
```
*(Alternative locale hors-ligne : `file:///C:/devcore/DEV_CORE/Dashboard/index.html`)*

Auto-refresh 15s — Affiche :
- Multi-projets : Cards récapitulatives par projet
- Worktrees : Tags [worktree] dans la pipeline
- Infrastructure Temps Réel : Monitoring ports (Qdrant, Gemini Router, API Dashboard, Headroom)
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
3. Embedder via text-embedding-3-small
4. Stocker dans Qdrant + Obsidian + MEMORY.md

---

## 🧭 Repowise

DEV_CORE configure Repowise automatiquement au lancement pour exposer le MCP et maintenir l'index de code à jour.

### MCP multi-client

`launch.ps1` exécute `ensure_repowise_mcp.ps1`, qui écrit une entrée `repowise` dans les configurations de :
- Codex global et projet
- Claude Code
- Gemini / Antigravity
- opencode
- `.mcp.json` projet

Les clients déjà ouverts doivent être redémarrés pour charger le MCP.

### Scan continu

`launch.ps1` exécute aussi `ensure_repowise_watch.ps1`, qui démarre un watcher par projet déclaré dans `DEV_CORE\Config\projects.json`.

Avant chaque scan, DEV_CORE exécute `ensure_repowise_web_languages.ps1`. Ce script enrichit la registry locale Repowise pour tous les repos scannés avec ce binaire :
- HTML / web markup : `.html`, `.htm`, `.vue`, `.svelte`, `.astro`
- CSS / stylesheets : `.css`, `.scss`, `.sass`, `.less`, `.pcss`, `.postcss`
- PowerShell : `.ps1`, `.psm1`, `.psd1`

Chaque worker :
1. exécute un `repowise update --index-only --no-docs --no-workspace`;
2. lance `repowise watch --no-workspace`;
3. écrit ses logs dans `DEV_CORE_DATA\Logs\scripts\repowise_watch\`.

Le démarrage est idempotent : relancer `dc launch` ne crée pas de doublons.

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

## 🔄 Changelog v10+

### 2026-07-09 — v10.0 Core Stabilization

- ✅ **CLI durci** : suppression de `Invoke-Expression` du dispatcher principal `dc.ps1` et dispatch par commandes validées.
- ✅ **Secrets gate** : `.env.example`, scanner `secret_scan.ps1` et intégration dans `diagnose.ps1`.
- ✅ **Health report** : `dc health` et `dc health --json` couvrent chemins, services, secrets, task board et mémoire.
- ✅ **Release gate locale** : `dc check --gate` retourne un code non nul sur erreur critique.
- ✅ **Dry-run diagnostic** : `dc check --fix --dry-run` affiche les réparations sans les exécuter.
- ✅ **Token reports multi-clients** : détection automatique Codex, Claude Code, Antigravity, Gemini et opencode.

## 🔄 Changelog v9

### 2026-07-08 — v9.2 Repowise MCP & Continuous Watch

- ✅ **MCP Repowise multi-client** : configuration automatique pour Codex, Claude Code, Gemini/Antigravity, opencode et `.mcp.json`.
- ✅ **Watch continu des projets DEV_CORE** : démarrage idempotent de `repowise watch` pour chaque projet déclaré.
- ✅ **Registre projets** : ajout de `DEV_CORE\Config\projects.json`, maintenu par `new_project.ps1`.
- ✅ **Contrôle opérationnel** : scripts `ensure_repowise_watch.ps1` et `repowise_watch_worker.ps1` avec logs et statut.

### 2026-07-06 — v9.1 Ollama & 9Router Removal & Direct Gemini Routing

- ✅ **Désactivation de 9Router & Ollama** : Suppression totale des dépendances et du processus 9Router (Port 20128) ainsi que d'Ollama (Port 11434) de l'orchestration, du diagnostic sémantique et du tableau de bord.
- ✅ **Completions et Embeddings en direct via Gemini** : Configuration par défaut de Gemini Router (`gemini_router.py` sur le port **`20130`**) pour appeler l'API Google Gemini directement.
- ✅ **Correction de la collision de headers** : Résolution du bogue `WebException` sous PowerShell 5.1 lors des requêtes d'embeddings en éliminant la déclaration redondante du header `Content-Type`.

### 2026-07-01 — v9.0 Port Separation, CORS Resolution & HTTP Cockpit Server

- ✅ **Résolution du conflit de port 20129** : Séparation définitive des ports de communication. Le serveur de routage intelligent `gemini_router.py` a été déplacé sur le port **`20130`** (avec mise à jour de toutes ses dépendances, notamment `headroom_start.ps1`, `qdrant_sync.ps1`, `memory_hierarchy.ps1`), libérant ainsi le port **`20129`** pour le serveur API Dashboard (`dashboard_api.py`).
- ✅ **Boutons d'Actions & Bégaiement CORS** : Remplacement des appels AJAX vers `localhost` par `127.0.0.1` pour contourner les comportements capricieux de résolution IPv6 sous Windows.
- ✅ **Cockpit disponible en HTTP** : Mise à jour de `dashboard_api.py` pour servir directement la page HTML du Cockpit sur l'URL racine `GET /`. Cela permet de charger le Cockpit via `http://127.0.0.1:20129/` au lieu du protocole local `file://`, évitant ainsi le blocage des requêtes AJAX dynamiques par les politiques de sécurité (CORS) des navigateurs modernes.
- ✅ **Nettoyage automatique** : Ajustement de `launch.ps1` pour purger automatiquement les anciens processus orphelins (notamment sur le port `8787` pour Headroom Proxy) lors du démarrage de la plateforme.

### 2026-05-24 — v9.0 Detached Daemon & Resilient API

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
**Après** : Single client (claude + Gemini Router)
**Gain** : Simplicité, pas de handoffs, routing direct Gemini

---

## 🆘 Support

- **Diagnostic** : `dc check`
- **Gate release** : `dc check --gate`
- **Dry-run diagnostic** : `dc check --fix --dry-run`
- **Health** : `dc health`
- **Logs** : `C:\devcore\DEV_CORE_DATA\Logs\`
- **Dashboard** : `C:\devcore\DEV_CORE\Dashboard\index.html`
- **Issues** : GitHub repo
