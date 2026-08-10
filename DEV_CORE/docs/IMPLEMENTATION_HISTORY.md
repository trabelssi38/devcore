# DEV_CORE Implementation History

Chronologie consolidee des implementations et plans. Source principale : historique Git tagge `[T-XX]`, documentation existante et fichiers de contrats.

## Lecture rapide

| Periode / tranche | Theme | Resultat |
|---|---|---|
| Mai 2026 | Migration single client, tasks, hooks, cockpit initial | Base DEV_CORE autonome avec tasks, dashboard, Qdrant, Obsidian, Hermes |
| T-100 a T-118 | Stabilisation v10, diagnostic, services memoire/contexte | Gateway de diagnostic, task service, memory service, dashboard stable |
| T-119 a T-138 | Observabilite, event bus, plugins, skills, CI | Metrics, event bus, knowledge graph, auto skills, plugin SDK, verify gate |
| T-139 a T-154 | Securite dashboard, API dashboard, CI portable | CORS/CSRF/body limits, local auth, stable dashboard API, non-blocking endday |
| T-155 a T-177 | API/DB/workers/LLMOps/evals/SLO | FastAPI v1, contrats domaine, SQLAlchemy/Alembic, run state machine, observabilite |
| T-178 a T-185 | Frontend dashboard moderne | Next scaffold, OpenAPI client, SSE, states, responsive/accessibility, Playwright |
| T-186 a T-193 | Hermes/Repowise/plugins v2 | Runtime daemon restaure, Repowise loopback, manifest v2, health isolation |
| T-194 a T-208 | Workspace, integrations, docs operateur/API | Identity, memberships, quota, audit logs, GitHub webhook, schedules, docs API |
| T-209 a T-222 | Release hardening, CI bornes, routing IA | Load/failure tests, SBOM, release package, runbook, routing profiles, capability registry |
| T-223 a T-293+ | Modularisation Python v10 & Supervision Headroom | Refactoring modulaire CCN 1.0, grille 330px/1fr/555px, détails Supervision Headroom persistants, badges de session libres (OK/ALERTE), isolation diagnostics de santé |
| T-344 a T-347 | Watchdog 100% Silencieux & Scanner Git Multi-Projets (v10.3.0) | SystemWatcher native auto-heal, scanner git multi-dépôts (job_tracker, devcore), auto-détection du projet dans hooks git, exécution 100% invisible sans popup de console |
| T-356 | Correctifs Cockpit Modèles & Isolement Projets/Tâches (v10.3.2) | Correction détection projets sans trb_m/dossiers OS, scrollbar répartition modèles, fidélité historique tâches/modèles de sessions |

## Mai 2026 - fondations

### Single Client et Tasks

- Remplacement des missions multi-agent par des tasks `[T-XX]`.
- Archivage des anciens scripts `mission_*`.
- `tasks.json` devient la source de verite par projet.
- Les modes `reasoning`, `coding`, `bulk` remplacent les handoffs entre agents.

### Hooks et autonomie

- `session_start`, `post-commit`, `session_end` installes pour scanner, synchroniser, incrementer les steps et generer le contexte.
- `qdrant_sync.ps1`, `obsidian_sync.ps1`, `lesson_extractor.ps1` structurent la memoire.
- Integration TOON pour compacter certains artefacts.

### Cockpit et API locale

- `gen_dashboard.ps1` genere `Dashboard\index.html`.
- `dashboard_api.py` sert le cockpit et les mutations locales.
- Ajout du refresh dynamique pour eviter le reload complet de la page.

## T-100 a T-118 - stabilisation core v10

| Task | Implementation | Impact |
|---|---|---|
| T-100/T-102/T-103 | Diagnostic gateway, dry-run gate | Separations check, fix, gate release |
| T-104 a T-112 | Task service et memory service | Mutations centralisees, adapters minces |
| T-113 | Dashboard API stable | `GET /api/dashboard`, payload stable |
| T-114 | Model pricing registry/report | Cout par modele, aliases, detection timeline |
| T-115 a T-117 | Context scoring/offload/composition | Justification des sources et visibilite cockpit |
| T-118 | Roadmap sprint | Planification suivante |

## T-119 a T-138 - observabilite, plugins, CI

| Task | Implementation | Impact |
|---|---|---|
| T-119 | Metrics service | Snapshots et metriques runtime |
| T-120 | Event bus v1 | Evenements append-only |
| T-121 | Knowledge graph v1 | Relations entre entites DEV_CORE |
| T-122 a T-124 | Repowise/wiki/model key fixes | Indexation docs plus robuste |
| T-125 | Learning service v1 | Base d'apprentissage/corrections |
| T-126 a T-130 | Skills registry, auto skills, plugin SDK | Extensibilite locale |
| T-131 a T-133 | Plugin checks/status dashboard | Health checks cockpit |
| T-134 | Retrait Graphify | Reduction dependance obsolete |
| T-135 | Roadmap plateforme | Plan sprint documente |
| T-136/T-137 | CI verify gate et exit codes | Tests bloquants fiables |
| T-138 | Platform version et headers | Version centralisee |

## T-139 a T-154 - securite dashboard et CI portable

| Task | Implementation | Impact |
|---|---|---|
| T-139/T-141 | CI portable + benchmarks | Gates reproductibles |
| T-140 | Qdrant embedding dimension contract | Dimension 768 verrouillee |
| T-142 | Bind loopback par defaut | Surface reseau reduite |
| T-143 | Dashboard token auth | Auth locale cockpit |
| T-144 a T-147 | Mutations off GET, CORS/CSRF/body limits, paths confine | Securite API dashboard |
| T-148/T-149 | Dashboard read model + pagination | Lecture plus scalable |
| T-150/T-151/T-152 | Reads sans PowerShell, cache HTTP, SSE deltas | Performance dashboard |
| T-153 | Latency budget dashboard | Non-regression perf |
| T-154 | Endday non bloquant | Fin de session agent-safe |

## T-155 a T-177 - API, DB, execution durable

| Task | Implementation | Impact |
|---|---|---|
| T-155 a T-160 | FastAPI gateway, ports, contracts, task list port, OpenAPI/client, versioning | API v1 stable |
| T-161 a T-166 | Postgres schema, SQLAlchemy/Alembic, repositories, import reconciliation, dual read, backup/restore | Base DB transitionnelle |
| T-167 a T-171 | Run state machine, worker durable, outbox, retry/DLQ, pause/cancel/resume | Execution durable |
| T-172 a T-177 | Observability, correlation IDs, Prometheus/Grafana, LLMOps, eval datasets, SLO/cost budgets | Exploitabilite et mesure |

## T-178 a T-185 - frontend dashboard

| Task | Implementation | Impact |
|---|---|---|
| T-178/T-179 | Next/React scaffold et composants dashboard | Frontend moderne amorce |
| T-180 | OpenAPI client + SSE | Client typé et flux live |
| T-181/T-182 | Agent skills spec + UI/UX skill adapte | Qualite skills et design |
| T-183/T-184 | Loading/empty/error + responsive/WCAG states | UX robuste |
| T-185 | Playwright components/e2e | Verifications navigateur |

## T-186 a T-193 - Hermes, Repowise et plugins v2

| Task | Implementation | Impact |
|---|---|---|
| T-186 | Hermes daemon runtime restaure | Cron et daemon utilisables |
| T-187 | Repowise dashboard loopback/IPv6/proxy | UI Repowise fiable sous Windows |
| T-188/T-193 | Manifest v2 et migration plugins | Contrats plugins versionnes |
| T-189 a T-192 | Permission scopes, health isolation, package integrity, atomic install rollback | Securite et rollback plugins |

## T-194 a T-208 - workspaces, integrations, documentation

| Task | Implementation | Impact |
|---|---|---|
| T-194 a T-197 | Workspace identity, membership, isolation, quotas | Base multi-tenant |
| T-198/T-199 | Dashboard refresh/token cache hardening | Cockpit plus robuste |
| T-200 | Qdrant startup hardening | Launch plus fiable |
| T-201/T-202 | Audit log exports + tenant isolation matrix | Compliance/test isolation |
| T-203/T-205 | GitHub webhook + notifications webhook plugin | Integrations externes |
| T-204/T-206/T-207 | Schedules, workflow templates, onboarding recovery | Automatisation operateur |
| T-208 | API reference + operator guide | Documentation publique |

## T-209 a T-222 - release, support, routing IA

| Task | Implementation | Impact |
|---|---|---|
| T-209/T-210 | Load contracts + failure drills | Tests locaux de resilience |
| T-211 | SBOM + security review gate | Release securisee |
| T-212/T-213 | Backup/rollback plan + packaging reproducible | Release reproducible |
| T-214 | Routing profile layer + Hermes hardening + cockpit status fix | Routage mode/profil et monitoring correct |
| T-215 | Incident runbook support criteria | Support exploitable |
| T-216 a T-220 | CI timeouts, deps, generated docs, bounded verify | Gates bornes et moins fragiles |
| T-221 | Sync worktree | Consolidation artefacts |
| T-222 | AI Capability Registry | Abstraction model/agent declarative |

## T-252 a T-255 - Sprints 18, 08a, 08b, 09 & 10 (Roadmap unifiee DEV_CORE v10)

| Task | Implementation | Impact |
|---|---|---|
| T-252 (Sprint 18) | Continuous Integration & Autonomy Validation (WS-G) | Verification automatique CI, gates d'autonomie et hooks de securite |
| T-249 (Sprint 08a) | Quick wins cockpit & Data hygiene (WS-K) | Reduction du payload dashboard de 18.8 MB a ~0.9 MB (-95%), delta hash SHA-256 SSE, rotation logs > 30j et .repowiseignore |
| T-253 (Sprint 08b) | Migration etat JSON vers SQLite WAL (WS-K) | Base SQLite `devcore.db` centralisee, requetes SQL en 1.99 ms, endpoints REST pagines |
| T-254 (Sprint 09) | Dashboard, MCP & Services Containers (WS-L) | Stream SSE granulaire par section (`?section=tasks|events|tokens`), tools MCP `mcp-devcore` (13 tools) et `mcp-qdrant` (6 tools) 100% Python-natifs |
| T-255 (Sprint 10) | Skills/UI/Motion standards (WS-M) | Publications `MOTION_STANDARDS.md` & `ACCESSIBILITY_CHECKLIST.md`, skills `dashboard-ui-craft` & `motion-review`, audit statique `audit_ui_motion.py` (95 findings priorises) |
| T-257 (Sprint 11) | UI gates et corrections prioritaires (WS-M) | Script CI gate bloquant `check_ui_gates.py`, correction des P0 `transition: all`, reduced-motion (P0 = 0) |
| T-260 (Sprint 12) | Performance profiling et candidats Rust (WS-N) | Profiling empirique (`profile_performance.py`), budgets SLA/SLO (`PERFORMANCE_BUDGETS.md`), matrice de decision (statu quo Python confirme) |
| T-262 (Sprint 14 & 15) | Go daemon ADR & Hardening v10 Container-First (WS-O) | Décision ADR Go Daemon (`ADR_GO_DAEMON_EVALUATION.md`), guides `MIGRATION_V9_V10.md` & `CONTAINER_OPERATOR_GUIDE.md`, suite E2E `test_container_e2e.py` (5/5 PASS 100% HEALTHY) |

## Plateforme Unifiee DEV_CORE v10 -- Release Stable

1. Tous les Sprints de la feuille de route DEV_CORE v10 (18, 08a, 08b, 09, 10, 11, 12, 14 et 15) sont acheves et deployes.
2. Conteneurisation Docker Compose complete avec bascule SQLite WAL et APIs REST < 2ms.
3. Suite de tests E2E et diagnostics d'autonomie validés.

## Maintenance & Correctifs Cockpit & Event Bus (Juillet 2026)

| Domaine | Correctif | Impact |
|---|---|---|
| Synchronisation Tâches Cockpit | Auto-sync `sync_tasks_from_memory(conn)` dans `gen_dashboard.py` | Résolution du bug où les nouvelles tâches (`T-103` à `T-106`) n'étaient pas affichées en raison du décalage entre `tasks.json` et SQLite `devcore.db` |
| Filtrage des états tâches | Inclusion des statuts `done`, `skipped` et `failed` dans la vue accomplie | Les tâches ignorées ou échouées s'affichent désormais de manière exhaustive |
| Catégorisation Event Bus | Badges de périmètre : `task_id` (cyan), `project` (violet) et `system` (gris neutre) | Suppression des étiquettes `devcore` trompeuses sur les métriques d'infrastructure |
| Daemon Hermes & Cron | Verrouillage `fcntl` (Linux) / `msvcrt` (Windows) & résolution dynamique `DEVCORE_PLATFORM_ROOT` | Compatibilité conteneur-first et environnement Linux / Windows native |

## Maintenance & Correctifs Cockpit & Clients IA (Août 2026)

| Domaine | Correctif | Impact |
|---|---|---|
| Détection des services en conteneur | Bypass du mapping `127.0.0.1` pour les hôtes de conteneurs dans `gen_dashboard.py` (comme `gemini-router`) | Le statut de Gemini Router dans le Cockpit s'affiche désormais correctement au vert (`True`) au lieu de rester au rouge (HS). |
| Enregistrement des compétences Antigravity | Ajout de la mise à jour automatique de `.antigravity-install-manifest.json` dans `adapt_client.ps1` | Les compétences liées au projet (notamment `devcore-automation`) sont automatiquement activées sous Antigravity, permettant le suivi automatique du protocole DevCore. |
| Statut Core API | Configuration de la variable `API_HOST=api` pour le service `dashboard-api` dans `docker-compose.yml` | La vérification de port pour le service Core API réussit désormais, affichant le service en ligne dans le Cockpit. |

## Refactoring Modulaire v10 & Supervision Cockpit (Août 2026)

| Domaine | Implémentation | Impact |
|---|---|---|
| Refactoring Modulaire | Découplage de `gen_dashboard.py`, `gemini_router.py` et `server.py` (MCP) en sous-packages | Réduction de la complexité cyclomatique (CCN) à 1.0. Architecture propre orientée responsabilité unique. |
| Aplatissement d'Imbrication | Réduction des imbrications complexes de blocs dans `task_prompt_analyzer.py` (de 13 à 3) | Lisibilité accrue, maintenance facilitée et élimination de la duplication de code. |
| Supervision Headroom | Extraction du bloc du cockpit hors des onglets et verrouillage de la persistance de l'état ouvert/fermé | Supervision toujours visible au bas de la colonne 2, sans perte d'état lors des transitions d'onglets. |
| Grille Cockpit | Quadrillage figé de la mise en page à `grid-template-columns: 330px 1fr 555px;` | Rendu optimisé des colonnes de données sur les écrans modernes. |
| Télémétrie & Logs de Métriques | Redirection de la lecture des logs vers le dossier correct `DEV_CORE_DATA/Logs/metrics` | Le graphique et l'activité du service de métriques se chargent et se mettent à jour automatiquement. |
| Diagnostic Santé Repowise | Isolation de la base de données SQLite de diagnostic par projet | Résolution des métriques dupliquées. Chaque projet affiche désormais son score global et son compte de fichiers propre. |
| Badges de Session | Ajout d'indicateurs `OK`, `OK (Session Libre)` et `ALERTE (Hors Tâche)` sur les sessions actives | Permet aux opérateurs d'identifier immédiatement les sessions orphelines et les fuites de tokens. |

## Correctifs Cockpit, Repowise & Robustesse (Août 2026 — 2026-08-02)

| Task | Implémentation | Impact |
|---|---|---|
| T-306 | **Auto-création de tâche** dans `session_start.ps1` : détection absence de tâche `todo`/`active` dans `tasks.json` et création autonome de `T-XX: Session de travail auto (YYYY-MM-DD)` | Antigravity démarre toujours avec une tâche active, plus de session orpheline |
| T-307 | **Hardening JS cockpit** (`template.html`) : support des formats `{success:true}` et `{status:'success'}` dans les callbacks `fetch`, parsing `detail` pour HTTPException FastAPI | Boutons Supprimer/Terminer fonctionnels, messages d'erreur lisibles |
| T-308 | **Diagnostic Radar Repowise non actualisé** : identifié que `task_sync.ps1` régénère le cockpit avant la fin du scan Repowise asynchrone (`Start-Process`) — `TimelineRenderer.ts`, `api.ts`, `server.js` affichaient des scores périmés | Cause racine identifiée et documentée |
| T-309 | **Lock fichier cross-platform** (`DashboardLock` dans `gen_dashboard.py`) + **régénération post-Repowise** (`repowise_update.py`) : `os.open(O_CREAT\|O_EXCL)` garantit l'unicité, attente 30 s, nettoyage périmé 120 s. `gen_dashboard.py --skip-token-refresh` appelé après chaque scan Repowise réussi | Cockpit toujours à jour avec les derniers scores de santé, zéro conflit de génération concurrente |
| T-310 | **Rebuild `devcore.db`** : suppression des fichiers corrompus (WAL/SHM), réexécution `migrate_json_to_sqlite.py` (401 tâches, 34 token metrics) | Base SQLite saine, dashboard API fonctionnel sans warnings |

## Maintenance, Robustesse & Tests Python (Août 2026 — Session Actuelle)

| Task | Implémentation | Impact |
|---|---|---|
| T-319 | **Auto-création post-commit** : Création autonome de tâche pour commit non taggué en l'absence de tâche active | Plus de commits perdus hors du Graphe de Tâches DEV_CORE |
| T-320 | **Tri de tâches ID-first** : Tri numérique des IDs de tâches (`T-X`) et persistance des timestamps `completed_at` | Les cartes projets du Cockpit affichent la dernière tâche chronologique réelle (ex: `T-322`) |
| T-321 | **Event Bus SQLite** : Raccordement de l'affichage du flux du cockpit aux événements SQLite `bus_events` | Les événements récents s'affichent instantanément et fidèlement dans le cockpit |
| T-322 | **Normalisation Datetime** : Uniformisation des formats ISO ('T') et Espace dans la table `bus_events` | Tri chronologique exact des événements système et applicatifs du cockpit |
| T-323 | **Migration 100% Python des Tests** : Remplacement de 13 suites PowerShell par des modules Python `unittest` | Tests 100% portables et compatibles Ubuntu / Linux / Windows / macOS |
| T-324 | **Nettoyage PowerShell (Monolithes)** : Remplacement de 18 scripts `.ps1` par des wrappers Python minces | Suppression de 5 000+ lignes de code PowerShell dupliqué, single source of truth Python |
| T-325 | **Auto-création Pre-Prompt** : Lancement automatique d'une tâche de session si aucune n'est active à l'init | Sessions d'agents 100% couvertes par des tâches dès le premier prompt |
| T-326 | **Casse des Hooks de Session** : Détection insensible à la casse de la tâche de session générique (`post_commit.py`) | Renommage automatique post-commit garanti quel que soit le format du titre |
| T-327 | **Cockpit Sync T-325** : Synchronisation et régénération du Cockpit pour le titre résolu de T-325 | Cohérence parfaite des affichages du Cockpit Dashboard |
| T-355 | **Correctif du Tri des Tâches Git Cockpit** : Tri chronologique des tâches complétées par datetime avant l'ID | Réintégration des tâches `T-GIT-*` issues de commits récents et non taggués, évitant leur disparition due à la troncature. |
| T-356 | **Activation par défaut du Task Runner Hermes** : Passage de `enabled` à `true` pour `active_agent_task_runner` | Permet aux tâches en arrière-plan et aux agents actifs de s'exécuter périodiquement de manière stable. |
| T-357 | **Freshness de task_sync dans le Cockpit** : Touch automatique du fichier de log de synchronisation de tâches à chaque passage | Maintien de l'indicateur d'état `task_sync` au vert (OK) en temps réel. |
| T-358 | **Résolution Dynamique des Chemins & Fix Native Services (v10.4)** | Remplacement des chemins `C:/devcore` en dur dans `html_renderer.py`, `headroom_start.ps1` et `system_watcher.py` par `DATA_ROOT`, `shutil.which` et `sys.prefix`. Restauration au vert (OK) de SQLite Vector DB et Headroom Proxy. |

