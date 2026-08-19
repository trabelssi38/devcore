# Changelog - DEV_CORE

All notable changes to the **DEV_CORE** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to Semantic Versioning.

## [10.3.12] - 2026-08-19

### Added
- **Module d'Auto-Configuration Portable et Dynamique (`devcore_engine.installers.claude_installer`)** :
  - **Auto-installation Unifiée** : Commande universelle `python -m devcore_engine setup [--target all|claude|desktop] [--verify] [--dry-run]` pour initialiser et synchroniser les configurations AI clients sans intervention manuelle.
  - **Intégration Claude Desktop GUI** : Configuration automatique du fichier `%APPDATA%\Claude\claude_desktop_config.json` pour déclarer le serveur MCP Repowise tout en préservant intactes les préférences utilisateur existantes et en créant une sauvegarde `.bak`.
  - **Intégration Claude Code CLI / Extension** : Mise à jour dynamique de `~/.claude/settings.json` avec les hooks natifs du cycle de vie (`session start`, `post_tool`, `session end`) et le serveur MCP Repowise.
  - **Clients Universels** : Support étendu pour Codex (`.codex/config.toml`), Gemini et Antigravity (`~/.gemini/settings.json`).
  - **Détection Dynamique de Projet (CWD & Git)** : Résolution automatique du projet cible depuis le répertoire de travail courant (`.devcore/project.json` ou racine Git), permettant d'exécuter le setup depuis n'importe quel dépôt secondaire.
  - **Support `utf-8-sig` & Normalisation Windows** : Gestion transparente des BOM UTF-8 générés par PowerShell et sécurisation des remplacements de chemins Windows (`re.sub` avec lambda) pour éliminer les erreurs de template d'échappement.

### Changed
- **Scripts de Déploiement** : Intégration de l'auto-configuration dans `setup.ps1` et inclusion de `claude_desktop_config.json` dans `ensure_repowise_mcp.ps1`.
- **Détection de Session** : Amélioration de `SessionManager.get_active_project()` pour auto-détecter dynamiquement le projet actif courant dès l'ouverture d'un sous-dossier ou dépôt.

## [10.3.11] - 2026-08-13

### Fixed
- **Correction des Erreurs de Syntaxe PowerShell et Résolution des Chemins** :
  - **Nettoyage des Blocs de Code Orphelins** : Suppression d'un bloc de code corrompu (`} else { ... }`) dans `launch_all.ps1`, `install_universal_hooks.ps1`, `ensure_repowise_watch.ps1` et `setup.ps1` provoquant un crash de syntaxe (`UnexpectedToken`).
  - **Résolution de Conflit de Casse Variable** : Renommage de `$SETTINGS` en `$SETTINGS_PATH` dans `install_hooks.ps1` et `download/install_hooks.ps1` pour éliminer le conflit de casse PowerShell avec la variable `$settings`, évitant ainsi la corruption de l'écriture du fichier de configuration Claude.
  - **Restauration de devcore_engine** : Récupération des fichiers de l'engine supprimés localement afin de rendre le diagnostic et les services opérationnels.

### Changed
- **Migration vers l'Engine Python pour Claude** : Mise à jour de `install_hooks.ps1` et de sa copie d'archive pour utiliser nativement `devcore_engine` (commandes Python directes pour `session start`, `post_tool` et `session end`) à la place des scripts d'enveloppe `.ps1`.

## [10.3.10] - 2026-08-13

### Fixed
- **Portabilité Universelle de `session_end.ps1` et de l'Ensemble des Scripts PowerShell/Python** :
  - **Résolution Python Centralisée** : Ajout de la fonction canonique `Get-DevCorePython` dans `platform_version.ps1` et export de `$env:DEVCORE_PYTHON`, éliminant les chemins absolus locaux `C:\Program Files\Python313\python.exe` et supportant dynamiquement Python 3.12, 3.13, 3.14 et les virtualenvs.
  - **Correction des Redirections de Flux** : Remplacement universel de `2>$null` (qui créait un fichier `$null` sur disque sous PowerShell 5.1) par les syntaxes portables `2>&1 | Out-Null` et `2>&1`.
  - **Normalisation des Séparateurs de Chemins** : Remplacement des regex rigides `-match '\\Scripts\\?$'` par `-match '[/\\]Scripts[/\\]?$'` pour supporter les slashes `/` et backslashes `\`.
  - **Suppression des Chemins Utilisateur et Racines Absolus** : Remplacement des occurrences en dur de `trb_m` et `C:\devcore` par `Path.home()`, `$env:USERPROFILE` et l'inclusion dynamique du nom d'utilisateur dans les filtres d'exclusion système.
  - **Supervision & Contrats de Test** : Alignement de `test_task_service.py` et `test_qdrant_vector_contract.py` sur les chemins locaux `get_db_path()` de `devcore.db`.
- **Remplacement de Qdrant par `sqlite-vec` Natively** :
  - **Élimination des Pings et Wait-Loops Qdrant** : Retrait des pings bloquants sur le port `6333` dans `session_start.ps1`, `endday_check.ps1` et `weekly_maintenance.ps1`.
  - **Exécution Directe de la Maintenance** : `endday_check.ps1` lance désormais directement `endday.ps1` en s'appuyant sur l'extension locale de base vectorielle `sqlite-vec` de `devcore.db`.
  - **Indicateurs Cockpit Modernisés** : `dc.py` et `gen_dashboard.py` vérifient et valident le statut vectoriel directement via la présence locale de `devcore.db` et le comptage des points via SQL.
  - **Correction de la Synchronisation des Détails de Tâches (`tasks.py`)** : Restriction de la tentative de désérialisation JSON aux chaînes commençant par `[` ou `{}` dans `_sync_to_legacy_json`. Cela évite que les détails de tâches extraits en texte brut à partir des commits Git ne soient effacés silencieusement lors des synchronisations base de données <-> JSON.

## [10.3.9] - 2026-08-11

### Fixed
- **Masquage des Éxécutables Repowise et Headroom** : Correction de `DETACHED_FLAG` dans `system_watcher.py` pour utiliser exclusivement `CREATE_NO_WINDOW` (`0x08000000`) sans `DETACHED_PROCESS` (`0x00000008`). Cela garantit que les binaires `.exe` comme `headroom.exe` et `repowise.exe` s'exécutent en arrière-plan 100% silencieux sans ouvrir de fenêtres de console visibles.

## [10.3.8] - 2026-08-11

### Fixed
- **Suppression Totale des Fenêtres Pop-up Consoles (`CREATE_NO_WINDOW`)** : Passage universel du drapeau `creationflags=CREATE_NO_WINDOW` (`0x08000000`) sur l'ensemble des sous-processus `subprocess.run` (`dashboard_api.py`, `scheduler_tick.py`, `run_job.py`, `system_watcher.py`, `multi_project_git_scanner.py`, `gen_dashboard.py`, `repowise_update.py`, `utils.py`). Cela élimine définitivement les ouvertures et fermetures intempestives de fenêtres de console PowerShell/cmd lors du suivi du Cockpit (notamment le poll `/api/timestamp` toutes les 2 secondes).

## [10.3.7] - 2026-08-11

### Changed
- **Transition vers le Scheduler Natif (Abandon d'Hermes)** : Désactivation complète du démarrage automatique du démon Hermes dans `launch_all.ps1`.
- **Persistance des Services d'Arrière-Plan** : Intégration de `DETACHED_PROCESS` (`0x00000008`) dans `system_watcher.py` et lancement de `launch.ps1` via WMI (`Invoke-CimMethod`) dans `launch_all.ps1` pour isoler les services de fond de la console d'exécution et garantir leur persistance après la fermeture du terminal.

## [10.3.6] - 2026-08-11

### Fixed
- **Restauration et Durcissement d'Hermes** : Clonage du dépôt officiel `hermes-agent` manquant sous `hermes/`, résolution de l'erreur d'import de `Path` et `RotatingFileHandler` dans `hermes_cron_tick.py`, et installation automatique de la dépendance `croniter` via pip.
- **Regex de Détection de Tâches Git (`multi_project_git_scanner.py`)** : Assouplissement de la regex pour supporter les variantes de tags comme `(Tag T-10)` et `(Tag T-11)` en plus de `[T-10]` et `(T-10)`.
- **Indentation de la Lecture SQLite (`data_loader.py`)** : Correction d'une indentation critique déconnectant la lecture de la base SQLite `devcore.db` lorsque celle-ci réside dans le répertoire local `LOCAL_ROOT`.
- **Robustesse des Wrappers PowerShell (`Scripts/*.ps1` et `Scripts/Auto/*.ps1`)** : Sécurisation de la résolution du chemin `$DEV_CORE` et du `$env:PYTHONPATH` dans `dc.ps1`, `endday.ps1`, `launch.ps1`, `stop.ps1`, `diagnose.ps1`, `task_done.ps1`, `task_next.ps1`, `task_service.ps1`, `integrity_check.ps1` et l'ensemble des 11 scripts récurrents en arrière-plan sous `Scripts/Auto/` via un test dynamique `Test-Path` sur le dossier `devcore_engine` pour éviter l'erreur `ModuleNotFoundError` lorsque `$env:DEVCORE_PLATFORM_ROOT` est mal configuré.
- **Suppression de Tâches Orphelines (`dashboard_api.py`)** : Résolution du bug de suppression de tâches (ex: `T-371` et `T-03`) en remplaçant la colonne incorrecte `project` par `project_id` et en découplant la suppression du fichier `tasks.json` de celle dans SQLite pour autoriser la suppression des tâches présentes uniquement en base de données.

## [10.3.5] - 2026-08-10

### Added
- **Implémentation Complète de l'Architecture Hybride Option B** : Séparation physique totale des sous-répertoires de runtime (`Logs`, `Bus`, `Cache`, `Scheduler`, `Sessions`, `Backups`, `Dashboard`, `Runtime`, `qdrant_storage`, `Temp`, `scratch`) hors de Dropbox vers `%LOCALAPPDATA%\DEV_CORE_LOCAL`.
- **Refonte des Registres de Chemins (`Tools/devcore/paths.py`)** : Définition de `local_root` et mise à jour de `bus_root`, `session_root`, `logs_root` vers `%LOCALAPPDATA%\DEV_CORE_LOCAL`.
- **Alignement du Moteur & Scripts (`system_watcher.py`, `dc.py`, `gen_dashboard.py`, `utils.py`, `html_renderer.py`, `data_loader.py`, `scheduler_tick.py`, `scheduler_history.py`, `event_bus.py`, `agent_runner.py`, `hooks.py`, `tool_handlers.py`)** : Mise à jour universelle de tous les services Python et des 12 scripts d'automatisation PowerShell (`Scripts/Auto/*.ps1`) pour qu'ils s'appuient sur `DEVCORE_LOCAL_ROOT`.

## [10.3.4] - 2026-08-10

### Added
- **Architecture Deux Racines pour DEV_CORE_DATA (`db.py`)** : Introduction de `get_local_data_root()` qui retourne `%LOCALAPPDATA%\DEV_CORE_LOCAL` pour tous les fichiers machine-spécifiques. `get_db_path()` pointe désormais vers cette racine locale, séparant `devcore.db` et les fichiers runtime (Logs, Cache, Scheduler, Bus…) du dossier Dropbox partagé.
- **Fichier `.dropboxignore`** : Création de `DEV_CORE_DATA/.dropboxignore` excluant `devcore.db`, `*.db-wal`, `*.db-shm`, `Logs/`, `Cache/`, `Runtime/`, `Scheduler/`, `Bus/`, `Sessions/`, `Backups/`, `Dashboard/`, `qdrant_storage/`, `Temp/` et `scratch/` de la synchronisation Dropbox (~97% de réduction).
- **Documentation Architecture (`PATHS.md`)** : Refonte avec la distinction claire entre `DEVCORE_DATA_ROOT` (Dropbox, partagé) et `DEVCORE_LOCAL_ROOT` (local machine).

### Fixed
- **Suppression des Copies en Conflit SQLite** : Suppression des 3 fichiers `devcore (Copie en conflit de DESKTOP-*).db` (~72 MB) générés par Dropbox lors d'écritures WAL concurrentes.
- **Migration de `devcore.db`** : Déplacement de `Dropbox/DEV_CORE_DATA/devcore.db` vers `%LOCALAPPDATA%\DEV_CORE_LOCAL\devcore.db` pour éliminer définitivement le risque de corruption SQLite-WAL via Dropbox.
- **Portabilité de `headroom_config.yaml`** : Remplacement des chemins absolus Dropbox pour `cache_dir` et `stats.output` par des variables d'environnement portables `${LOCALAPPDATA}/DEV_CORE_LOCAL/…`.

## [10.3.3] - 2026-08-10

### Fixed
- **Isolation des Identifiants de Tâches par Projet (`tasks.py`)** : Restriction du calcul de l'ID de tâche incrémental au projet concerné (`WHERE project_id = ?`), évitant que les nouveaux projets n'héritent de la numérotation globale (`T-371` etc.).
- **Clé Primaire Composite dans la Base de Données (`db.py`, `data_loader.py`)** : Remplacement de la clé primaire simple sur l'ID de tâche par une clé composite `PRIMARY KEY (id, project_id)` dans SQLite et alignement du `ON CONFLICT` dans le chargeur de données du Cockpit pour éliminer les collisions inter-projets.
- **Référencement du Projet Oracle (`projects.json`)** : Inscription du projet `oracle_legacy_intelligence_platform` et de son chemin local `E:/src_web/oracle_legacy_intelligence_platform` pour rétablir son affichage et ses métriques dans le Cockpit.
- **Nettoyage du Projet Fantôme (`test_proj`)** : Suppression du répertoire de mémoire et de toutes les tâches d'intégration de test dans SQLite.
- **Portabilité des Chemins Python (`settings.json`, `install_universal_hooks.ps1`)** : Remplacement des chemins d'accès absolus locaux vers `python.exe` par la commande portable `python` dans tous les fichiers `settings.json` des clients IA et scripts d'installation.

## [10.3.2] - 2026-08-08

### Added
- **Scrollbar & Affichage Répartition Modèles (`gen_dashboard.py`, `template.html`)** : Ajout d'un conteneur à défilement vertical (`max-height: 220px; overflow-y: auto`) dans le bloc de coût par modèle du Cockpit pour afficher l'ensemble des modèles de toutes les sessions sans tronquage.
- **Support Modèles Antigravity & Pricing Registry (`model_pricing.json`)** : Définition des règles par défaut pour le client `antigravity` (`gemini-3.6-flash`, `claude-sonnet-4.6`) et prise en compte de la clé `models` dans l'afficheur HTML.

### Fixed
- **Exclusion des Dossiers Utilisateur OS (`token_report.py`)** : Ajout d'un système d'exclusion stricte (`SYSTEM_DIR_NAMES`) retirant `trb_m`, `users`, `documents`, `desktop`, `downloads` de la détection de projets pour éliminer les fausses attributions de projet.
- **Rattachement Précis des Tâches et Modèles de Sessions (`token_report.py`)** : Conservation de l'historique et des modèles réels des sessions archivées (`gpt-5.5`, `claude-opus-4.6`, etc.) et limitation du fallback dynamique de tâche active uniquement aux sessions du jour, évitant l'attribution erronée de `T-357` aux sessions passées.

## [10.3.1] - 2026-08-07

### Added
- **Freshness de task_sync dans le Cockpit** : Touch automatique du fichier de log de synchronisation de tâches à chaque passage pour maintenir l'indicateur d'état `task_sync` au vert (OK) en temps réel.

### Fixed
- **Tri Chronologique des Tâches Git dans le Cockpit (`data_loader.py`)** : Ajustement du tri des tâches complétées pour ordonner en premier par date de complétion (`get_task_datetime`) plutôt que par numéro d'ID (`get_task_id_number`). Cela évite que les tâches associées aux commits Git (`T-GIT-*`, ayant un ID numérique équivalent à 0) soient poussées au début de la file et tronquées par la limite d'affichage des 20 dernières tâches.
- **Réactivation du Runner d'Agent Actif (`jobs.devcore.json`)** : Activation automatique par défaut du job récurrent `DEV_CORE Active Agent Task Runner` (`active_agent_task_runner`) pour permettre l'exécution périodique des tâches en arrière-plan.

## [10.3.0] - 2026-08-05

### Added
- **Scanner Git Multi-Projets (`multi_project_git_scanner.py`)** : Module autonome parcourant l'ensemble des dépôts configurés dans `projects.json` (ex: `job_tracker`, `devcore`, `dashboard_recette_br`). Extraction et synchronisation automatique des commits récents des 30 derniers jours dans SQLite `devcore.db` avec mise à jour du Cockpit.
- **Auto-Détection du Projet dans le Hook Post-Commit (`post_commit.py`)** : Résolution dynamique du nom du projet via le dossier Git racine (`git rev-parse --show-toplevel`) pour garantir l'attribution exacte des commits au projet concerné (ex: `job_tracker`) indépendamment du projet actif principal.
- **Automated System Watchdog & Auto-Healer (`system_watcher.py`)** : Module d'auto-guérison native en Python auditant en continu les services de la plateforme (`Dashboard API`, `Gemini Router`, `Headroom Proxy`, `Anthropic Adapter`, `Repowise Server` et `Scheduler Daemon`). Redémarrage automatique et silencieux en arrière-plan en cas de panne avec émission d'événement `ServiceAutoHealed`.
- **Intégration Cron Scheduler & Bootstrap** : Ajout du job récurrent `system_watcher` (`* * * * *`) sous forme de tâche Python directe dans `jobs.devcore.json` et auto-surveillance de la présence du daemon `scheduler_tick.py`.
- **Diagnostic CLI Enrichi** : Ajout du contrôle direct de santé du port 8787 (Headroom Proxy) dans `devcore diagnose`.

### Fixed
- **Élimination des Popups de Fenêtres Console (Zero Popup)** : Lancement direct des sous-processus `repowise.exe` et `headroom.exe` avec le drapeau `CREATE_NO_WINDOW` (`0x08000000`) exclusif (suppression de `DETACHED_PROCESS` en Win32) pour garantir un fonctionnement 100% invisible en arrière-plan.
- **Politique du Planificateur (`jobs.devcore.json`)** : Passage de `"policy": "catch_up"` à `"policy": "skip"` pour `daily_launch` et `daily_endday` afin d'éviter le déclenchement intempestif des scripts de démarrage/extinction lors de la relance du planificateur en cours de journée.
- **Timeout Démarrage Headroom Proxy** : Augmentation du délai d'initialisation à 15 secondes pour autoriser le chargement complet des parsers AST, Tiktoken et LiteLLM avant vérification du port HTTP.
- **PowerShell Launch Fallback** : Correction de la gestion d'exception pour `-WindowStyle Hidden` sur `headroom_start.ps1` afin de supporter l'exécution croisée sous PowerShell 5.1 et PowerShell Core 7.

## [10.2.0] - 2026-08-05

### Added
- **Abstractions AgentRunner & Hermes Process Engine** : Création de la classe de base abstraite `AgentRunner` et des implémentations `HermesRunner` et `LocalProcessRunner` dans `DEV_CORE/devcore_engine/runners/` pour supporter la gestion unifiée d'agents locaux CLI (Hermes / Processus OS).
- **Pipeline de Recherche Mémoire AsyncIO** : Refactorisation asynchrone non-bloquante avec `httpx.AsyncClient` dans `dashboard_api.py` pour accélérer les requêtes mémoire Qdrant et SQLite-vec sans bloquer la boucle d'événements du serveur Cockpit.
- **Affichage des Sous-systèmes & Modale de Télémetrie Tâches (`Inter.`)** : Ajout d'un bouton d'action `Inter.` sur chaque carte tâche du Cockpit ouvrant une fenêtre modale moderne. La modale affiche les sous-systèmes sollicités (Repowise, Mémoire/Qdrant, Vault, Headroom, AgentRunner), les métriques d'économie de tokens via le Prompt Cache et la timeline chronologique des événements.
- **Correspondance Auto des Commits par Titre de Tâche** : Extension de la correspondance Git dans `gen_dashboard.py` pour lier automatiquement les commits aux tâches du système même lorsque les sujets des commits n'incluent pas le tag `[T-XX]`.

### Fixed
- **Support Complet du Mode Terminal Cockpit** : Alignement de `template_terminal.html` avec ajout des classes CSS `.modal-overlay` glassmorphism et gestion de l'affichage adaptatif en mode Terminal.
- **Traces de Débogage Console Browser (`[Cockpit Debug]`)** : Ajout de logs explicites d'ouverture/fermeture et de résolution des données JSON dans la console DevTools du navigateur pour fiabiliser le diagnostic du Cockpit.

## [10.1.0] - 2026-08-05

### Added
- **SQLite Unifié & Processus Python Natifs (`devcore_engine`)** : Migration complète vers une architecture zero-Docker. Consolidation de 100% des données (26 projets, 448 tâches, 18 942 événements, 8 925 nœuds/liens, 124 notes Vault, 13 skills) dans le fichier unique SQLite WAL `devcore.db`.
- **In-process Vector Search (`sqlite-vec`)** : Remplacement de Qdrant Docker par l'extension native de recherche vectorielle `sqlite-vec` (768 dimensions), réduisant la consommation de RAM de 2.8 GB à moins de 250 MB.
- **Auto-démarrage silencieux des démons** : Intégration dans le cycle de vie de la plateforme (`launch.py`) pour démarrer de manière robuste et silencieuse `dashboard_api.py` (Port 20129) et `gemini_router.py` (Port 20130) en arrière-plan sous Windows.
- **Entrée de package directe (`__main__.py`)** : Ajout du fichier pour supporter l'appel standard `python -m devcore_engine launch` ou `dc launch` depuis n'importe quel dossier.
- **Vérifications de non-régression (11/11 OK)** : Mise à jour de la suite d'intégration globale (`verify.ps1`, `test_secret_scan.ps1`, `test_diagnose_gate.ps1`, `test_qdrant_vector_contract.ps1`) pour valider la plateforme sans dépendances Docker.
- **Migration 100% Python de la Suite de Tests** : Remplacement de l'ensemble des 13 scripts de tests PowerShell (`.ps1`) par des modules unitaires Python `unittest` autonomes sous `devcore_engine/tests/` (100% de compatibilité croisée Windows et Ubuntu / Linux).
- **Auto-création de Tâche Pre-Prompt** : Injection d'une routine dans `SessionManager.start_session()` pour auto-créer une tâche de session active si aucun travail n'est démarré lors du premier prompt de l'agent.

### Changed
- **Nettoyage PowerShell (Monolithes)** : Remplacement de 18 anciens scripts PowerShell monolithes (comme `task_service.ps1`, `memory_hierarchy.ps1`, `qdrant_sync.ps1`, etc.) représentant plus de 5 000 lignes de code par des delegators minces appelant `devcore_engine.cli`, faisant de Python l'unique source de vérité.

### Fixed
- **Tri Chronologique du Flux d'Événements** : Normalisation et conversion des timestamps ISO (contenant 'T') dans la table SQLite `bus_events` pour fiabiliser le tri décroissant sur le Cockpit.
- **Tri ID-First des Cartes Projets** : Tri numérique des identifiants (`T-XX`) dans `data_loader.py` pour afficher la dernière tâche réelle sur les cartes projets du Cockpit au lieu d'anciens restes alphabétiques.
- **Casse des Hooks de Session** : Correction de la casse pour la détection de `"session de travail auto"` dans `post_commit.py` pour garantir le renommage automatique de la tâche de session active sur commit Git.


## [10.0.2] - 2026-08-04


### Fixed
- **Collisions d'IDs de tâches dans la base SQLite du Cockpit** : correction du schéma de la table `tasks` dans `migrate_json_to_sqlite.py` en remplaçant la clé primaire simple `id TEXT PRIMARY KEY` par une clé composite `PRIMARY KEY (id, project)`. Cela évite que les tâches ayant le même ID dans des projets différents (comme `T-94`) ne s'écrasent mutuellement et disparaissent du cockpit. Re-migration complète effectuée avec succès.
- **Optimisation et évitement du timeout de `memory_compactor.py` dans `endday.ps1`** : passage du timeout d'étape de 60s à 120s et augmentation de la taille des blocs de compaction (`chunk_size`) de 20 à 40 items pour réduire le nombre de requêtes LLM consécutives et contourner le limiteur de débit du routeur local.
- **Bouton de suppression Cockpit inopérant (SQLite non synchronisé)** : l'API de suppression du cockpit (`delete_task` dans `dashboard_api.py`) effaçait la tâche de `tasks.json` mais ne mettait pas à jour la base de données SQLite. L'affichage lisant SQLite conservait donc la tâche à l'écran. Corrigé en ajoutant une suppression SQLite synchrone.
- **Projet fantôme "app" dans le Cockpit (Sandbox)** : correction de la détection du nom du projet dans `Get-ActiveProject.ps1`. Le script privilégie désormais la lecture du fichier `.devcore/project.json` (qui contient le nom exact du projet) au lieu de se baser uniquement sur le nom du dossier parent. Cela évite que les sessions d'agents exécutées dans des environnements sandboxés (où le dossier courant s'appelle souvent `app`) ne créent un projet fantôme nommé "app". Nettoyage complet effectué en base SQLite et sur disque pour effacer le projet fantôme.


### Added
- **Règle d'auto-démarrage Antigravity** : création d'une règle globale obligatoire `devcore-session-autostart.md` dans le répertoire des configurations globales (`~/.gemini/config/rules/`) pour forcer l'exécution automatique de `session_start.ps1` lors de l'initialisation de chaque session sous Antigravity.

---

## [10.0.1] - 2026-08-02

### Added
- **Auto-création de tâche au démarrage de session** (`session_start.ps1`) : si `tasks.json` ne contient aucune tâche `todo` ou `active`, une tâche `T-XX: Session de travail auto (YYYY-MM-DD)` est créée automatiquement pour garantir qu'Antigravity démarre toujours avec un contexte de tâche.
- **Lock fichier cross-platform dans `gen_dashboard.py`** : nouvelle classe `DashboardLock` utilisant `os.open(O_CREAT|O_EXCL)` (atomique Windows + Linux) pour sérialiser les appels concurrents à la génération du cockpit depuis `task_sync.ps1`, `repowise_update.py`, les hooks post-commit et l'API. Attente jusqu'à 30 s, nettoyage automatique des locks périmés (>120 s). Lock ignoré en mode `--json` pour ne pas bloquer les requêtes API.
- **Régénération du cockpit après scan Repowise** (`repowise_update.py`) : `gen_dashboard.py --skip-token-refresh` est maintenant appelé à la fin du scan Repowise. Les scores de santé (Radar) sont ainsi toujours à jour dans le cockpit sans délai de propagation.

### Changed
- **Hardening JavaScript des boutons d'action du cockpit** (`template.html`) : les appels `fetch` sur `/api/done`, `/api/delete` et `/api/settings` supportent désormais les deux formats de réponse FastAPI (`{success: true}` et `{status: 'success'}`). Parsing de l'erreur via la clé `detail` (format HTTPException FastAPI) pour remplacer le message silencieux `Erreur : undefined`.

### Fixed
- **Cockpit Radar non actualisé après commit** : diagnostiqué — `task_sync.ps1` régénérait le cockpit avant la fin du scan Repowise (processus asynchrone non bloquant). Corrigé via le lock et la régénération explicite dans `repowise_update.py`.
- **Base SQLite `devcore.db` corrompue** : reconstruite proprement via `migrate_json_to_sqlite.py` (401 tâches, 34 métriques token migrées). Suppression des fichiers WAL/SHM corrompus préalablement.
- **Suppression de tâche cockpit inopérante** (`/api/delete`) : corrigée par le hardening JS du format de réponse FastAPI.

---

## [10.0.0] - 2026-08-02


### Added
- **Supervision Headroom UI Status Badges**: Added explicit `OK (Session Libre)`, `ALERTE (Hors Tâche)`, and `OK` status indicators next to active sessions.
- **Dynamic Cockpit Elements**: Automatic indicator arrows (`▶` / `▼`) on Supervision Headroom and other `<details>` elements using CSS-only attribute selectors.
- **Portability & Isolated Querying**: Repowise health card queries now correctly isolate SQLite database statistics per project rather than leaking `devcore` metrics to other paths.

### Changed
- **Modular Python Refactoring**: Decoupled monolithic scripts into clean, single-responsibility Python packages to reduce cyclomatic complexity (CCN) to 1.0:
  - `gen_dashboard.py` split into [DEV_CORE/Scripts/dashboard/](file:///C:/devcore/DEV_CORE/Scripts/dashboard/).
  - `gemini_router.py` split into [DEV_CORE/Scripts/router/](file:///C:/devcore/DEV_CORE/Scripts/router/).
  - `server.py` MCP server split into [DEV_CORE/MCP/devcore-scripts/handlers/](file:///C:/devcore/DEV_CORE/MCP/devcore-scripts/handlers/) and [services/](file:///C:/devcore/DEV_CORE/MCP/devcore-scripts/services/).
- **Nesting Reduction**: Flattened deeply nested logic (nesting levels down to 3.0) in [task_prompt_analyzer.py](file:///C:/devcore/DEV_CORE/Scripts/Auto/task_prompt_analyzer.py).
- **Tuning Grid Layout**: Grid layout updated to `grid-template-columns: 330px 1fr 555px;` in [template.html](file:///C:/devcore/DEV_CORE/Dashboard/template.html) and [template_terminal.html](file:///C:/devcore/DEV_CORE/Dashboard/template_terminal.html).
- **Supervision Headroom Visibility**: Shifted the `#token-activity-report` container outside the tab panels so it is persistently visible regardless of the active tab.

### Fixed
- **NameError Crash in server.py**: Resolved critical `check_port is not defined` crash at startup.
- **NameError Crash in utils.py**: Added missing `import json` inside `load_project_paths()`.
- **Metrics Service Path Mismatch**: Adjusted `get_metrics_service_status()` path to fetch logs directly from `DEV_CORE_DATA/Logs/metrics` instead of checking the empty `Metrics` directory.

---

## [9.9.5] - 2026-07-28

### Added
- **Multi-Project Worktree Support**: Introduced multi-project loading logic in the dashboard to switch context profiles.
- **Identity & Membership**: Added schema definitions and API logic for managing project identities and credentials.

### Changed
- **Docker Compose Orchestration**: Refactored compose service configurations to leverage local volume mounts to dynamically propagate script updates to running container daemons.

---

## [9.9.0] - 2026-07-22

### Added
- **SSE Live Streaming**: Added Server-Sent Events (SSE) support in the FastAPI `dashboard_api` to stream events in real time without refreshing the client browser.
- **Event Bus v1**: Direct integration of real-time append-only event recording.

### Changed
- **Hermes / Repowise Loopback**: Integrated native scheduled cron execution within the Hermes daemon for periodic health evaluations.

---

## [9.8.0] - 2026-07-15

### Added
- **Diagnostics Gateway**: Gateway validation gate (`dc check`, `dc health`) to ensure system pre-conditions are met.
- **Learning Service v1**: Base repository for extracted lessons learned from workspace sessions.
- **Task & Memory Services**: Extracted central state mutations to decoupled service interfaces.

---

## [9.7.0] - 2026-07-10

### Added
- **French Grammar Auto-Correction**: Helper integration to normalize syntax errors inside french language task prompts.
- **Token Pricing Registry**: Dynamic cost tracker for LLM providers.

---

## [9.6.0] - 2026-07-05

### Added
- **Git Hooks Automation**: Automated scripts for `session_start`, `post-commit`, and `session_end`.
- **Qdrant Index Syncing**: Automatic synchronization of semantic code embeddings to Qdrant vector database.
