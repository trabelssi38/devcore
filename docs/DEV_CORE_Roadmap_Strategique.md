# DEV_CORE v10+ -- Roadmap Strategique Raffinee

Date : 2026-07-08
Statut : draft stratégique
Mode cible : single client, orchestration locale, mémoire hiérarchique, services observables

## Vision

Faire évoluer DEV_CORE d'une collection de scripts PowerShell vers une plateforme
d'orchestration IA locale, modulaire, observable et auto-améliorante.

Le changement clé n'est pas "ajouter plus d'automatisation". Le changement clé est
de rendre chaque automatisation sûre, mesurable, testable et réversible.

## Diagnostic

### Forces actuelles

- Cycle quotidien déjà automatisé : `launch`, `dc next task`, `endday`.
- Architecture mémoire L0-L3 déjà définie : persona, scenarios, Qdrant, SQLite/FTS.
- Routage par mode déjà cadré : `reasoning`, `coding`, `bulk`, `lookup`.
- Dashboard et API locale déjà présents.
- Hooks et scripts de task management déjà structurants.

### Risques à traiter avant toute extension

- Secrets et clés API encore présents dans des fichiers de configuration ou fallbacks.
- `Invoke-Expression` encore utilisé dans le routage CLI.
- Documentation hétérogène : README v9, documentation plateforme v7, roadmap v10+.
- Frontières de services encore implicites : scripts, API, dashboard et mémoire partagent
  trop de conventions non contractualisées.
- Mesures existantes mais pas encore assez reliées aux décisions : coût, tokens, cache,
  temps, succès, rollback.

### Implication stratégique

Les phases "Knowledge Graph", "Learning Engine", "Self Healing" et "Auto Evolution"
ne doivent pas commencer comme produits séparés. Elles doivent émerger à partir d'un
noyau v10 stable : configuration propre, contrats locaux, événements traçables,
métriques fiables.

---

# Objectif v10 : Stabiliser le noyau

Horizon : 2 à 4 semaines
But : rendre DEV_CORE sûr, diagnostiquable et prêt pour une architecture service.

## P0 -- Sécurité et exécution

- Retirer toutes les clés API hardcodées.
- Remplacer les fallback secrets par variables d'environnement ou vault local ignoré par Git.
- Supprimer `Invoke-Expression` du CLI.
- Valider les arguments de commandes avant dispatch.
- Ajouter un check de secrets dans le diagnostic et/ou release gate.

## P0 -- Configuration

- Définir une source de vérité claire :
  - `DEV_CORE\Config` pour la configuration versionnée.
  - `.env` ou variables d'environnement pour les secrets.
  - `DEV_CORE_DATA` pour l'état runtime.
- Documenter les variables obligatoires et optionnelles.
- Remplacer les chemins hardcodés par `$env:DEVCORE_PLATFORM_ROOT` avec fallback
  `C:\devcore\DEV_CORE`.

## P0 -- Observabilité minimale

- Standardiser les logs script : composant, action, statut, durée, task id.
- Normaliser les codes de sortie.
- Ajouter `diagnose.ps1` comme gate de release locale.
- Produire un rapport court "health" : services, ports, secrets, Qdrant, dashboard,
  router, task board, mémoire.

## P1 -- Packaging et tests

- Ajouter ou compléter `requirements.txt` / `pyproject.toml` pour les modules Python.
- Ajouter des tests de smoke pour :
  - `dc.ps1` dispatch.
  - task lifecycle.
  - `launch.ps1`.
  - `endday.ps1` avec mode dry-run.
  - dashboard API.
- Créer un mode `-DryRun` pour les scripts sensibles.

## Gate v10.0

- Aucun secret versionné connu.
- Aucun `Invoke-Expression` dans le chemin principal.
- `diagnose.ps1` passe sans erreur critique.
- Documentation README + plateforme + AGENTS synchronisée sur v10.
- Démarrage DEV_CORE < 5 s hors démarrage Docker/Qdrant.
- Rapport health généré en moins de 2 s.

Livrable : DEV_CORE v10.0 Stable.

---

# Objectif v10.1 : Contractualiser les services

Horizon : 1 mois
But : transformer les scripts existants en modules à interfaces stables sans réécrire
toute la plateforme.

## Services cibles

| Service | Responsabilité | Interface minimale |
|---|---|---|
| Gateway | Point d'entrée CLI/API | commandes typées, validation arguments |
| Task Service | `tasks.json`, steps, status, scan | CRUD tâches, transitions validées |
| Memory Service | L0-L3, Qdrant, SQLite, Obsidian | query, upsert, sync, health |
| Context Service | session context, task context, compression | build context, score, offload |
| Router Service | mode, budget, modèle, retries | route request, explain decision |
| Metrics Service | tokens, coût, durée, cache, succès | record event, aggregate report |
| Dashboard API | état lisible par UI | endpoints read-only + refresh |
| Automation Service | launch/endday/hooks/scheduled tasks | run job, dry-run, status |

## Architecture cible

```text
CLI / Dashboard / Hooks
        |
        v
     Gateway
        |
        +-- Task Service
        +-- Memory Service
        +-- Context Service
        +-- Router Service
        +-- Metrics Service
        +-- Automation Service
        +-- Dashboard API
```

## Règles de conception

- Un service possède ses fichiers d'état ou expose une API claire pour y accéder.
- Le dashboard lit via API, il ne reconstruit pas la logique métier.
- Les scripts PowerShell restent supportés, mais deviennent des adaptateurs.
- Chaque service expose `health`, `status`, `dry-run` quand pertinent.

## Gate v10.1

- Les commandes principales passent par Gateway ou adaptateur validé.
- Les mutations de tâches sont centralisées dans Task Service.
- Dashboard API ne dépend plus de parsing fragile de fichiers multiples.
- Les services critiques publient un état exploitable par `diagnose.ps1`.

Livrable : Service Layer v1.

---

# Objectif v10.2 : Context Engine

Horizon : 3 à 5 semaines
But : construire automatiquement un contexte LLM utile, court et traçable.

## Entrées

- Tâche active et mode cognitif.
- Derniers commits et fichiers modifiés.
- Scénario mémoire L2.
- Résultats Qdrant L1 avec scores.
- Fallback SQLite/FTS L0 si Qdrant ne répond pas ou score insuffisant.
- Décisions et lessons pertinentes.
- État services et erreurs récentes.

## Sorties

- `session_context.txt` structuré et borné.
- Contexte compressé/offloadé si trop volumineux.
- Justification des sources incluses.
- Score de pertinence et score de fraîcheur.

## Règles

- Score Qdrant > 0.75 : réutiliser, ne pas régénérer.
- Score 0.50-0.75 : utiliser comme base et enrichir.
- Score < 0.50 : fallback FTS5 ou recherche source.
- Tout bloc > 10k caractères doit être offloadé via Canvas.

## Gate v10.2

- Construction contexte < 500 ms sur projet courant hors appels réseau.
- Réduction tokens > 40 % vs contexte brut.
- Chaque contexte indique ses sources et scores.
- Le dashboard affiche la composition du contexte courant.

Livrable : Context Engine v1.

---

# Objectif v11 : Event Bus et Knowledge Graph

Horizon : 2 à 3 mois
But : découpler les modules et rendre les dépendances exploitables.

## Event Bus

Événements initiaux :

- `TaskCreated`
- `TaskStarted`
- `TaskStepCompleted`
- `TaskCompleted`
- `CommitCreated`
- `MemoryUpdated`
- `ContextBuilt`
- `RouteSelected`
- `MetricRecorded`
- `DashboardRefreshed`
- `HealthCheckFailed`

Règles :

- Les événements sont append-only.
- Chaque événement porte `id`, `timestamp`, `source`, `task_id`, `payload`, `schema_version`.
- Les scripts peuvent publier des événements sans connaître les consommateurs.
- Les consommateurs doivent être idempotents.

## Knowledge Graph

Noeuds :

- projets
- tâches
- commits
- fichiers
- services
- décisions
- bugs
- lessons
- skills
- métriques

Relations :

- tâche -> commit
- commit -> fichier
- fichier -> service
- décision -> service
- lesson -> bug
- skill -> tâche
- métrique -> exécution

Fonctionnalités :

- impact analysis avant refactor.
- historique des décisions par service.
- recherche sémantique enrichie par relations.
- vue dashboard des dépendances critiques.

## Gate v11.0

- Event log durable et requêtable.
- 80 % des actions critiques publient un événement.
- Graphe généré automatiquement depuis tasks, commits, docs et events.
- Impact analysis disponible pour un fichier ou service.

Livrable : DEV_CORE v11 Platform Graph.

---

# Objectif v11.1 : Learning Engine

Horizon : 1 à 2 mois après v11
But : transformer les métriques en décisions opérationnelles.

## Métriques à capturer

- Durée par commande.
- Coût et tokens par tâche.
- Taux de cache.
- Nombre de corrections après première réponse.
- Tests passants / échoués.
- Rollbacks ou revert.
- Réutilisation mémoire.
- Choix de mode et modèle.

## Décisions apprises

- Quel mode utiliser pour un type de tâche.
- Quel contexte inclure ou exclure.
- Quel prompt ou skill produit moins de corrections.
- Quels scripts sont instables ou trop coûteux.

## Garde-fous

- Le moteur recommande avant d'agir.
- Toute modification de code reste sur branche.
- Le merge reste humain.
- Les règles apprises ont une date, une source et un score de confiance.

## Gate v11.1

- Rapport hebdomadaire : coûts, gains, erreurs, recommandations.
- Suggestions de routage mesurées contre baseline.
- Score de confiance visible pour chaque recommandation.

Livrable : Learning Engine v1.

---

# Objectif v11.2 : Plugin System

Horizon : 1 à 2 mois
But : permettre l'extension sans modifier le noyau.

## SDK Plugin

Chaque plugin peut fournir :

- commandes CLI.
- hooks.
- skills.
- health checks.
- métriques.
- widgets dashboard.
- templates de tâches.

## Plugins prioritaires

1. Python / FastAPI.
2. Web / React / Next.js.
3. Android / Gradle.
4. Docker.
5. GitHub.
6. Kubernetes / cloud plus tard.

## Gate v11.2

- Un plugin peut être installé, listé, désactivé et diagnostiqué.
- Les plugins ne peuvent pas écrire hors de leur scope sans permission explicite.
- Au moins 3 plugins internes migrés depuis les skills existantes.

Livrable : Plugin SDK v1.

---

# Objectif v12 : Self Healing et Auto Evolution

Horizon : après stabilisation v11
But : automatiser les réparations simples et proposer les évolutions complexes.

## Self Healing

Détections :

- ports occupés.
- services arrêtés.
- Qdrant indisponible.
- mémoire corrompue.
- embeddings manquants.
- clés absentes ou expirées.
- logs trop volumineux.
- dashboard non joignable.

Réparations autorisées :

- redémarrage service local.
- nettoyage logs selon politique de rétention.
- reconstruction index mémoire.
- relance dashboard API.
- génération rapport incident.

Réparations interdites sans validation :

- suppression de données utilisateur.
- rotation de secrets.
- migration de schéma irréversible.
- merge ou push automatique.

## Auto Evolution

Boucle :

```text
Observation -> Analyse -> Proposition -> Branche -> Tests -> Rapport -> Validation humaine -> Merge
```

Capacités :

- détecter zones peu maintenables.
- proposer refactors atomiques.
- générer une PR draft.
- mesurer gain avant/après.
- documenter la décision.

## Gate v12.0

- Self healing couvre au moins 5 incidents fréquents.
- Auto evolution ne modifie jamais `main` directement.
- Chaque proposition contient risque, rollback, tests et gain attendu.
- Le dashboard affiche les propositions ouvertes et leur statut.

Livrable : DEV_CORE v12 Cognitive Platform.

---

# KPIs consolidés

## Performance

- Démarrage DEV_CORE < 5 s hors dépendances externes.
- Construction contexte < 500 ms.
- Recherche mémoire < 150 ms pour requêtes courantes.
- Dashboard API répond < 200 ms sur endpoints status.

## Qualité

- Secrets versionnés connus : 0.
- `Invoke-Expression` dans chemin principal : 0.
- Réutilisation mémoire > 70 %.
- Réduction tokens > 40 %.
- Réduction corrections après première réponse > 50 %.
- Tests smoke critiques passants : 100 %.

## Plateforme

- Composants critiques observables : 100 %.
- Actions critiques tracées par événement : 80 % v11, 100 % v12.
- Services découplés par interface : 80 % v11, 95 % v12.
- Incidents fréquents auto-diagnostiqués : 5 minimum v12.

---

# Ordre d'exécution recommandé

1. Sécurité : secrets, `Invoke-Expression`, config.
2. Diagnostic : health report fiable, codes de sortie, logs standardisés.
3. Tests smoke : task lifecycle, launch, endday, dashboard API.
4. Gateway : dispatch typé et validation arguments.
5. Task Service : centraliser mutations `tasks.json`.
6. Memory Service : encapsuler Qdrant, scenarios, FTS fallback.
7. Context Engine : sources, scores, compression, offload.
8. Metrics Service : événements, coût, tokens, durée, succès.
9. Event Bus : append-only, schemas, consommateurs idempotents.
10. Knowledge Graph : relations tâches/commits/fichiers/décisions.
11. Learning Engine : recommandations mesurées.
12. Plugin SDK : extensions hors noyau.
13. Self Healing : réparations locales sûres.
14. Auto Evolution : PR draft avec validation humaine.

---

# Backlog initial

## Sprint 1 -- Sécurité et confiance

- [x] Supprimer les clés hardcodées et fallbacks secrets.
- [x] Ajouter `.env.example` sans secret.
- [x] Ajouter check secrets dans `diagnose.ps1`.
- [x] Remplacer `Invoke-Expression` dans `dc.ps1`.
- [x] Ajouter tests smoke CLI.

## Sprint 2 -- Diagnostic et docs

- [x] Normaliser logs et codes de sortie.
- [x] Ajouter health report.
- [x] Mettre README, PLATFORM_DOCUMENTATION, AGENTS et roadmap au même niveau v10.
- [x] Ajouter mode `-DryRun` aux scripts sensibles.

## Sprint 3 -- Service Layer minimal

- [x] Introduire Gateway.
- [x] Extraire Task Service.
  - [x] v1 : `Path`, `Read`, `Add` et adaptateur `task_add.ps1`.
  - [x] v2 : `Next` et adaptateur `task_next.ps1`.
  - [x] v3 : `Complete` et adaptateur `task_done.ps1`.
  - [x] v4 : `Step` et adaptateur `task_step_done.ps1`.
  - [x] v5 : `Edit` et adaptateur `task_edit.ps1`.
  - [x] v6 : `Pause`, `Skip` et adaptateurs `task_pause.ps1` / `task_skip.ps1`.
  - [x] v7 : `Sync`, `task_sync.ps1` et synchronisations secondaires.
- [x] Encapsuler accès mémoire dans Memory Service.
- [x] Faire lire le dashboard via API stable.

## Sprint 4 -- Context Engine v1

- [x] Scorer les sources de contexte.
- [x] Ajouter justification des sources.
- [x] Offloader les blocs volumineux.
- [x] Afficher composition du contexte dans dashboard.

## Sprint 5 -- Metrics Service v1

Objectif : centraliser les mesures opérationnelles dans un service append-only avant de construire l'Event Bus.

- [ ] Introduire `metrics_service.ps1` avec actions `Record`, `Aggregate`, `Status`, `Health`.
- [ ] Écrire les métriques dans `DEV_CORE_DATA\Logs\metrics\metrics-YYYY-MM-DD.jsonl`.
- [ ] Normaliser le schéma `MetricRecorded` :
  - `schema_version`
  - `id`
  - `timestamp`
  - `source`
  - `project`
  - `task_id`
  - `metric_type`
  - `value`
  - `unit`
  - `payload`
- [ ] Ajouter tests smoke pour append JSONL, agrégation et health.
- [ ] Brancher `token_report.py` pour publier tokens, coût, cache et modèles.
- [ ] Brancher `gen_dashboard.ps1` pour publier durée de génération et statut.
- [ ] Brancher `launch.ps1` et `endday.ps1` pour publier durée, succès et erreurs.
- [ ] Afficher dans le dashboard un résumé Metrics Service : événements du jour, erreurs, coût, tokens, durée.

Gate Sprint 5 :

- `metrics_service.ps1 -Action Health` retourne OK avec codes de sortie normalisés.
- Le store JSONL est append-only et supporte plusieurs appels successifs.
- Aucune métrique ne contient de secret ou contenu de prompt brut.
- Les tests smoke Metrics Service passent.

## Sprint 6 -- Event Bus v1

Objectif : transformer les métriques et actions critiques en événements durables, typés et consommables.

- [ ] Introduire `event_bus.ps1` avec actions `Publish`, `Read`, `Tail`, `Health`.
- [ ] Définir le schéma événement append-only :
  - `schema_version`
  - `id`
  - `timestamp`
  - `source`
  - `event_type`
  - `project`
  - `task_id`
  - `correlation_id`
  - `payload`
- [ ] Publier `TaskCreated`, `TaskStarted`, `TaskStepCompleted`, `TaskCompleted`.
- [ ] Publier `CommitCreated` depuis hook post-commit ou scanner git.
- [ ] Publier `ContextBuilt`, `MetricRecorded`, `DashboardRefreshed`, `HealthCheckFailed`.
- [ ] Ajouter idempotence minimale par `id`/`correlation_id`.
- [ ] Ajouter une vue dashboard des événements récents.

Gate Sprint 6 :

- 80 % des actions critiques listées dans la roadmap publient un événement.
- Les consommateurs peuvent relire le log sans modifier l'état.
- Les tests valident publication, lecture, filtrage par type et idempotence.

## Sprint 7 -- Knowledge Graph v1

Objectif : construire les relations exploitables entre tâches, commits, fichiers, services, décisions et métriques.

- [ ] Créer un générateur `knowledge_graph.ps1` ou service Python minimal.
- [ ] Ingérer `tasks.json`, commits Git, events JSONL, metrics JSONL et décisions docs.
- [ ] Produire un graphe local dans `DEV_CORE_DATA\Knowledge\graph.json`.
- [ ] Modéliser les relations initiales :
  - tâche -> commit
  - commit -> fichier
  - fichier -> service
  - métrique -> tâche
  - événement -> tâche
  - décision -> service
- [ ] Ajouter `ImpactAnalysis` pour un fichier ou service.
- [ ] Afficher dans le dashboard les dépendances critiques et le blast radius.

Gate Sprint 7 :

- Un fichier modifié retourne les tâches, commits et services liés.
- Le graphe est régénérable sans état caché.
- Les tests couvrent ingestion tasks, commits et events.

---

# Décisions ouvertes

- Format du bus d'événements : JSONL local, SQLite, ou les deux.
- Frontière entre scripts PowerShell adaptateurs et services Python.
- Politique de rétention des logs, events et métriques.
- Format de schéma pour plugins.
- Niveau de permission requis pour self healing.

La recommandation actuelle : démarrer avec JSONL append-only pour les événements,
SQLite pour les vues requêtables, et services Python uniquement là où PowerShell
devient fragile ou difficile à tester.
