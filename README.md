# DEV_CORE v10 - README

**Single Client Mode** — Plateforme d'orchestration IA pour le développement logiciel

Version : 10.0.0
Updated : 2026-07-09
Mode : Single Client (pas de handoffs multi-agents)

---

## 🚀 Installation & Lancement

La plateforme s'exécute dans un environnement conteneurisé à l'aide de Docker Compose pour orchestrer l'ensemble des services système.

### Prérequis
- **Docker Desktop** (avec support WSL 2 sous Windows)
- **PowerShell 7.0+** (recommandé pour l'exécution locale de la CLI `dc`)
- Une clé API Google Gemini et/ou Anthropic (définie dans le fichier `.env` ou via l'interface de configuration du Cockpit)

### Étape 1 : Cloner et Configurer l'environnement
1. Clonez ce dépôt sous `C:\devcore`.
2. Créez votre fichier `.env` à la racine à partir du modèle :
   ```bash
   cp .env.example .env
   ```
3. Remplissez vos clés d'API dans `.env` (notamment `GEMINI_API_KEY` et/ou `ANTHROPIC_API_KEY`).

### Étape 2 : Démarrer l'infrastructure multi-services
Lancez l'orchestration Docker Compose pour construire et démarrer l'ensemble des conteneurs en tâche de fond :
```bash
docker-compose up -d --build
```
*Cette commande démarre PostgreSQL (5432), Qdrant (6333), Gemini Router (20130), Dashboard API (20129), le Scheduler natif v10, l'API devcore (20131), l'interface Web (30000) et les serveurs MCP.*

### Étape 3 : Configurer la CLI locale (Hôte Windows)
Pour utiliser le raccourci `dc` directement depuis votre console hôte Windows PowerShell :
```powershell
cd C:\devcore\DEV_CORE\Scripts
.\setup.ps1
```
*Note : Cela installe l'alias permanent `dc` pointant vers `dc.ps1`.*

### Étape 4 : Lancer le cycle et valider l'installation
```powershell
# Initialiser le cycle quotidien
dc launch

# Exécuter les diagnostics de santé et de conformité
dc check
dc health
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

## 🎯 Modes Cognitifs & Gemini Router

La plateforme utilise un routeur intelligent (**Gemini Router**) qui intercepte les requêtes LLM locales (port `20130`), analyse l'intention cognitive et redirige l'exécution vers le modèle optimal selon le mode requis :

| Mode | Usage | Budget Contexte | Modèle Google Gemini Cible |
|------|-------|-----------------|-----------------------------|
| **reasoning** | Architecture, spécifications, décisions critiques | 32k tokens | Gemini 2.5 Pro |
| **coding** | Implémentation de code, cycle TDD, génération de patches | 8k tokens | Gemini 2.5 Pro |
| **bulk** | Génération de masse, documentation, écriture de tests unitaires | 16k tokens | Gemini 2.5 Flash |

Le routeur communique directement avec l'API Google Gemini sans intermédiaire externe.

---

## 📁 Structure du Projet

```text
C:\devcore\
├── DEV_CORE\                   # Code source de la plateforme
│   ├── API\                    # Moteur de base de données PostgreSQL & API FastAPI
│   ├── Bus\                    # Bus d'événements interne
│   ├── Config\                 # Fichiers de configuration (settings, active client, API keys)
│   ├── Dashboard\              # Fichiers HTML/CSS/JS (Cockpit index.html & Terminal index_terminal.html)
│   ├── Database\               # Modèles de base de données SQLAlchemy & Migrations
│   ├── docker\                 # Dockerfiles de l'environnement Python/Node
│   ├── docs\                   # Fiches d'architecture (ADR, Sprints, UI plans)
│   ├── MCP\                    # Serveurs MCP (Qdrant & DevCore Scripts)
│   ├── Scheduler\              # Tâches d'arrière-plan du planificateur natif
│   ├── Scripts\                # Scripts Powerhell principaux (dc.ps1, launch.ps1, etc.)
│   ├── Skills\                 # Compétences packagées pour les agents autonomes
│   ├── Web\                    # Interface web frontend (Next.js)
│   └── ...
├── DEV_CORE_DATA\              # Volume persistant de données (exclus de Git)
│   ├── Database\               # SQLite (legacy) & stockage de fichiers DB
│   ├── Memory\                 # Tâches (tasks.json), index (MEMORY.md)
│   ├── Logs\                   # Journaux d'exécution
│   ├── Obsidian\               # Vault Obsidian des notes de l'agent
│   ├── qdrant_storage\         # Vecteurs de la base de données Qdrant
│   └── Sessions\               # Historique de sessions
├── docker-compose.yml          # Fichier d'orchestration multi-services
└── README.md                   # Ce fichier
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
- `dc verify --ci` — Agrège les gates CI et préserve tout code d'échec
- `dc verify --ci --json` — Rapport CI structuré pour les pipelines

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
- **Mode Cockpit** (Design graphique moderne) : `http://127.0.0.1:20129/`
- **Mode Terminal** (CRT-scanline rétro-futuriste vert/cyan) : `http://127.0.0.1:20129/index_terminal.html`

*(Alternatives locales hors-ligne : [index.html](file:///C:/devcore/DEV_CORE/Dashboard/index.html) et [index_terminal.html](file:///C:/devcore/DEV_CORE/Dashboard/index_terminal.html))*

### Fonctionnalités Clés :
- **Basculement instantané** : Bouton `⌨ TERMINAL` dans le Cockpit et `⊞ COCKPIT` sur la topbar du Terminal.
- **Filtrage par Projet** : En cliquant sur une ligne projet (colonne 1), le dashboard filtre instantanément les tâches du pipeline et met à jour le **Rapport de Consommation** pour n'afficher que les tokens et les coûts de modèles spécifiques à ce projet.
- **Rapport de Consommation & Headroom** : Section interactive avec sauvegarde automatique de l'état ouvert/fermé dans le `localStorage` lors des cycles de rafraîchissement.
- **Services & Infrastructure** : Monitoring en temps réel avec intégration du **DEV_CORE Scheduler natif v10** (remplaçant Hermes autonome), du **Repowise Engine (MCP)** au sommet de la pile de surveillance, ainsi que de Gemini Router, Dashboard API Server, Headroom Proxy et Qdrant Vector DB.
- **Configuration Unifiée** : Paramètres de configuration (client actif, taux de rafraîchissement, clés API Gemini et Anthropic, activation des services) synchronisés entre les deux templates.
- **Pipeline de tâches globale** (T-01 → T-04) avec options de filtrage par date (tous, 1j, 7j, 30j).

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
2. exécute un refresh docs `repowise update --docs --no-workspace`, ou `--full --docs` si le wiki est vide, quand le commit HEAD diffère du dernier wiki généré, avec throttle `REPOWISE_DOCS_REFRESH_MINUTES`;
3. lance `repowise watch --no-workspace`;
4. écrit ses logs dans `DEV_CORE_DATA\Logs\scripts\repowise_watch\`.

Le worker charge aussi `DEV_CORE\Config\gemini_api_key.txt` comme fallback Gemini, comme `gemini_router.py`. Si aucun provider Repowise/API key non interactif n'est disponible, il journalise `provider_missing`, continue le watch index-only et retentera au prochain lancement.

Le démarrage est idempotent : relancer `dc launch` ne crée pas de doublons.

### Dashboard Repowise

`launch.ps1` maintient aussi le dashboard Repowise local :

- API Repowise : `http://127.0.0.1:7337`
- UI Repowise : `http://127.0.0.1:3101`
- Fallback navigateur : `http://localhost:7337` est supporté via `repowise_ipv6_proxy.py` (`::1:7337` -> `127.0.0.1:7337`)

Pourquoi : sous Windows, `localhost` peut être résolu en IPv6 (`::1`) alors que Repowise écoute en IPv4 (`127.0.0.1`). DEV_CORE corrige ce cas avec :

- `ensure_repowise_web_proxy.ps1` : patche le cache UI Repowise pour utiliser `127.0.0.1:7337`.
- `ensure_repowise_ipv6_proxy.ps1` : démarre un proxy local IPv6 vers IPv4 pour les navigateurs qui gardent `localhost:7337` en cache.

Diagnostic rapide :

```powershell
Invoke-WebRequest http://127.0.0.1:3101/api/repos
Invoke-WebRequest http://localhost:7337/api/repos
```

---

## 🛠️ Skills

**Core skills actifs** :
- `qdrant` — Mémoire vectorielle
- `obsidian` — Vault management
- `fabric-patterns` — Patterns IA
- `dev-methodology` — Méthodologie dev

**Total installés** : 159 skills

### Auto-Skills

Auto-Skills transforme les evenements repetes du bus local en candidats `SKILL.md` controles :
- `dc skills detect` cree des candidats dans `DEV_CORE_DATA\Skills\Candidates`.
- `dc skills lint <name>` applique le gate statique.
- `dc skills eval <name>` verifie les preuves Event Bus.
- `dc skills promote <name>` active explicitement une skill verifiee.
- `dc skills reject <name>` conserve la trace et desactive le candidat.

Documentation : `C:\devcore\DEV_CORE\docs\AUTO_SKILLS.md`

### Plugin SDK

Le SDK plugin installe des manifests `plugin.json` bornes par scope dans `DEV_CORE_DATA\Plugins`.
Plugins internes versionnes :
- `DEV_CORE\Plugins\python-fastapi\plugin.json`
- `DEV_CORE\Plugins\web-react\plugin.json`
- `DEV_CORE\Plugins\android-gradle\plugin.json`

Commandes : `dc plugin list|health|install|diagnose|check|disable [--json]`

`dc plugin check <id>` execute les `capabilities.health_checks` du manifest installe et retourne les sorties, codes de retour, timeouts et echecs requis.

---

## 📖 Documentation complète

Voir : `C:\devcore\DEV_CORE\docs\PLATFORM_DOCUMENTATION.md`

---

## 🔄 Changelog v10+

### 2026-07-26 — v10.1 Dual Cockpit/Terminal Layouts & Interactive Filtering

- ✅ **Système de double template** : Interface Cockpit moderne et interface Terminal rétro-futuriste (style CRT scanline vert/cyan phosphoreux) avec bouton de basculement instantané `⌨ TERMINAL` / `⊞ COCKPIT`.
- ✅ **Filtrage interactif par Projet** : Possibilité de cliquer sur n'importe quel projet pour filtrer immédiatement les tâches actives et adapter dynamiquement le rapport de jetons (coûts et volume par modèle de l'API Gemini/Claude/GPT).
- ✅ **Persistance d'état du rapport de consommation** : L'état d'ouverture/fermeture du bloc détails de consommation de jetons est sauvegardé dans le stockage local (`localStorage`) pour persister lors des rafraîchissements partiels dynamiques (AJAX toutes les 15s) et rechargements de page.
- ✅ **Configuration unifiée** : Synchronisation complète du formulaire de configuration (taux de rafraîchissement, clés d'API, démarrage des services) entre les deux templates.
- ✅ **Intégration du DEV_CORE Scheduler natif** : Remplacement de l'ancien démon autonome Hermes par le planificateur natif de la v10 et affichage dans la topbar sous le statut `SCHEDULER ACTIVE`.
- ✅ **Nettoyage et stabilisation du dépôt** : Suppression des répertoires corrompus ou temporaires (comme `C`), retrait du fichier auto-généré dynamique `index_terminal.html` du suivi Git et inclusion dans `.gitignore` pour un dépôt propre.

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

### 2026-07-26 — v10.1 UTF-8 BOM Compatibility & Robust Sticky Token Report

- ✅ **Compatibilité UTF-8 BOM dans token_report.py** : Correction de la lecture des fichiers `tasks.json` et `model_pricing.json` pour utiliser l'encodage `utf-8-sig` au lieu de `utf-8` brut. Cela permet de lire sans erreur les fichiers contenant une signature BOM (Byte Order Mark) et d'associer correctement toutes les tâches à leurs projets respectifs dans `token_metrics_summary.json` (résolvant le problème de disparition des badges de tokens/coûts des tâches).
- ✅ **Fix de la fonction updateContainerHTML (morphDOM)** : Correction d'une régression majeure où le rafraîchissement dynamique écrasait et supprimait par erreur les attributs HTML (`id`, `class`, `style`) des conteneurs cibles. La fonction copie désormais les attributs de l'ancien conteneur vers le nouveau avant d'effectuer la comparaison morphique DOM, préservant ainsi la scrollbar des tâches (`.scroll-area`) et les identifiants d'API.
- ✅ **Rapport de Consommation & Supervision Headroom Toujours Visibles** : Restauration de la structure du layout tout en appliquant un comportement de type *sticky footer* en CSS Flexbox (`min-height: 0` sur `#tasks-pipeline` et `flex-shrink: 0` sur `#token-activity-report`). Le rapport de consommation de tokens reste ainsi ancré en permanence au bas de la colonne et entièrement visible dans le viewport (première vue), tandis que la liste des tâches défile de manière indépendante.

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
