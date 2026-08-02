# DEV_CORE Architecture Decisions

Journal consolide des decisions structurantes. Cette page ne remplace pas les notes Obsidian/Qdrant, mais fournit un index stable lisible depuis le depot.

## ADR-001 - Single Client Mode

**Statut** : accepte

DEV_CORE utilise un seul client actif au lieu de handoffs multi-agents. Les differences de comportement passent par des modes (`reasoning`, `coding`, `bulk`) et par le routage runtime.

**Raisons**

- Evite les pertes de contexte entre agents.
- Simplifie les hooks, commits et attribution des taches.
- Permet de garder un seul cockpit et un seul board de taches par projet.

**Consequences**

- Les workflows ne doivent pas dependre d'un agent nomme.
- Le routage doit porter les intentions et contraintes.
- Les capacites agent/modele sont externalisees dans le AI Capability Registry.

## ADR-002 - Tasks comme unite de travail

**Statut** : accepte

Les anciens concepts de missions ont ete remplaces par des tasks `[T-XX]`.

**Sources**

- `DEV_CORE_DATA\Memory\<project>\tasks.json`
- `Scripts\task_service.ps1`
- Hook Git `post-commit`

**Consequences**

- Chaque commit doit porter `[T-XX]`.
- `steps_done` et `status` sont mis a jour par le hook.
- Les scripts `task_add`, `task_next`, `task_done`, `task_step_done`, `task_sync` sont des adapters autour de `task_service.ps1`.

## ADR-003 - Memoire hierarchique L0-L3

**Statut** : accepte

La memoire est lue dans l'ordre :

- L3 persona toujours pertinente.
- L2 scenarios par type de tache.
- L1 Qdrant pour recherche semantique.
- L0 SQLite/FTS fallback.

**Consequences**

- Les contenus volumineux ne doivent pas etre injectes bruts.
- Les resultats avec score eleve doivent etre reutilises.
- Les scripts de memoire doivent rester idempotents.

## ADR-004 - Dashboard par read model et payload stable

**Statut** : accepte

Le cockpit ne doit pas dependre uniquement d'un HTML complet regenere. Il expose un payload JSON stable, des sections HTML et un read model incremental.

**Sources**

- `Scripts\gen_dashboard.ps1`
- `Scripts\dashboard_api.py`
- `Scripts\dashboard_read_model.ps1`
- `DEV_CORE_DATA\Dashboard\dashboard_payload.json`

**Consequences**

- Les mutations doivent passer par endpoints controles.
- Les donnees runtime restent dans `DEV_CORE_DATA`.
- Les tests de contrat dashboard verrouillent schema, securite et rendu critique.

## ADR-005 - Services centraux avant scripts directs

**Statut** : accepte

Les mutations recurrentes doivent passer par un service central :

- taches : `task_service.ps1`
- memoire : `memory_service.ps1`
- contexte : `context_service.ps1`
- plugins : `plugin_service.ps1`
- metrics : `metrics_service.ps1`
- event bus : `event_bus.ps1`

**Consequences**

- Les scripts historiques deviennent adapters.
- Les tests ciblent le service central.
- Les corrections de bugs se font en un endroit.

## ADR-006 - API v1 et contrats versionnes

**Statut** : accepte

Les integrations externes passent par FastAPI et OpenAPI versionne.

**Sources**

- `API\devcore_api`
- `Schemas\openapi-v1.json`
- `API\clients\typescript\devcore-api-client.ts`

**Consequences**

- Toute rupture de schema impose une nouvelle version.
- Les clients generes ne sont pas edites a la main.
- Les tests API valident contrats et versioning.

## ADR-007 - DB progressive avec dual-read

**Statut** : accepte

DEV_CORE conserve les JSON historiques tout en introduisant une couche SQL/repository.

**Sources**

- `Database\postgres_schema_v1.sql`
- `Database\devcore_db`
- `API\test_dual_read_cutover.py`

**Consequences**

- Les migrations doivent etre reversibles ou documentees.
- Les repositories doivent etre testes sans casser la source JSON.
- Le cutover doit pouvoir tourner en mode JSON, SQL ou dual.

## ADR-008 - Event bus et execution durable

**Statut** : accepte

Les evenements et runs doivent etre tracables, idempotents et recuperables.

**Sources**

- `event_bus.ps1`
- outbox DB
- run state machine
- retry/DLQ

**Consequences**

- Les consumers doivent etre idempotents.
- Les transitions de run sont explicites.
- Les erreurs persistantes vont en dead-letter.

## ADR-009 - Plugins manifest v2

**Statut** : accepte

Les plugins internes declarent leurs capabilities dans un manifest versionne.

**Sources**

- `Plugins\manifest_v2.schema.json`
- `Plugins\manifest_v2.py`
- `plugin_service.ps1`

**Consequences**

- Les installs doivent etre atomiques.
- Les health checks sont isoles.
- Les permissions et scopes sont explicites.

## ADR-010 - Gates locaux bornes

**Statut** : accepte

Les tests et gates ne doivent pas bloquer indefiniment.

**Sources**

- `verify.ps1`
- `ci_powershell_tests.ps1`
- `ci_python_tests.ps1`
- `.github\workflows\ci.yml`

**Consequences**

- Chaque check a un timeout.
- Les sorties longues doivent etre tronquees/offloadees.
- Les failures doivent retourner un code non nul.

## ADR-011 - AI Capability Registry

**Statut** : accepte

Les agents/modeles ne sont plus cables dans les workflows. Ils declarent des capacites, et le runtime selectionne le meilleur candidat.

**Sources**

- `Config\ai_capability_registry.json`
- `Scripts\ai_capability_registry.py`
- `Scripts\routing_profile.ps1`
- `Scripts\gemini_router.py`

**Consequences**

- Un workflow exprime des requirements, pas un agent.
- Ajouter/remplacer un modele se fait dans le registry.
- Un candidat non supporte par backend direct doit rester desactive.

## ADR-012 - Secrets et runtime hors plateforme

**Statut** : accepte

La plateforme `DEV_CORE` contient code, schemas, configs non sensibles. Les donnees runtime et secrets vont dans `DEV_CORE_DATA`.

**Consequences**

- Ne pas committer secrets, caches, qdrant storage, dashboards runtime.
- Les scripts doivent confiner les chemins.
- `secret_scan.ps1` et security review doivent rester dans les gates.

## ADR-013 - Container-First Architecture

**Statut** : accepte

DEV_CORE v10 adopte une architecture orientée conteneurs par défaut (container-first) pour uniformiser l'exécution locale et en production. Le code principal est exécuté via Docker Compose, éliminant la dépendance directe à Windows, PowerShell pour la logique métier, et aux tâches planifiées du système hôte.

**Consequences**

- L'environnement de dev utilise le mode Compose avec des *bind mounts* pour le hot-reload.
- Les volumes Docker persistants abritent l'historique des runs, Qdrant et Postgres.
- Les conteneurs s'adressent via les noms de services du Compose au lieu de `localhost`.
- Les scripts PowerShell du host sont réduits à de simples wrappers d'amorçage.

## ADR-014 - Modularisation des scripts Python monolithiques

**Statut** : accepté (Août 2026)

Afin de réduire la complexité cyclomatique (CCN) et d'éliminer la duplication de code, les scripts Python massifs d'orchestration (`gen_dashboard.py`, `gemini_router.py`, `server.py` MCP) ont été découpés en sous-packages modulaires.

**Sources**
- `DEV_CORE/Scripts/dashboard/` (utils, data_loader, html_renderer)
- `DEV_CORE/Scripts/router/` (config, providers, stream_parser)
- `DEV_CORE/MCP/devcore-scripts/handlers/` & `services/`

**Conséquences**
- La complexité cyclomatique de chaque point d'entrée est réduite à 1.0.
- Les responsabilités sont isolées : chargement de données, configuration, et rendu HTML sont séparés.
- Les tests unitaires peuvent cibler des modules spécifiques au lieu de devoir exécuter le script global.

## ADR-015 - Supervision Headroom & Architecture des Métriques de Tokens

**Statut** : accepté (Août 2026)

La supervision des consommations de jetons (Supervision Headroom) est extraite des onglets dynamiques du cockpit pour rester ancrée de manière persistante au bas de la colonne centrale. Les sessions orphelines sont identifiées à l'aide de badges de statut calculés.

**Conséquences**
- Le composant de cockpit `#token-activity-report` est persistant sur toutes les vues.
- L'état de dépliement/repliement de l'élément `<details>` est sauvegardé dans le `localStorage` et restauré de manière transparente à chaque cycle de rafraîchissement (toutes les 15s).
- Les sessions libres sans tâche ID active se voient attribuer des statuts visuels clairs (`OK` ou `ALERTE` si la session dépasse 500k tokens ou $0.50).

## ADR-016 - Isolation des Diagnostics de Santé Repowise par Projet

**Statut** : accepté (Août 2026)

Les diagnostics de santé (Repowise Health) doivent interroger la base de données SQLite de diagnostic propre à chaque projet au lieu de renvoyer par défaut les statistiques du projet principal `devcore`.

**Conséquences**
- La méthode `get_repowise_db_health` valide rigoureusement les chemins des dossiers de projet.
- Si le chemin est vide ou invalide, l'évaluation renvoie `None` au lieu de lire la base locale SQLite courante de `devcore`.
- Chaque carte projet affiche désormais ses scores et son nombre de fichiers de façon parfaitement cloisonnée.

