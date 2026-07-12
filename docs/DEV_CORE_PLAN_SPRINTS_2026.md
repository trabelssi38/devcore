# DEV_CORE — Plan de transformation par sprints

Version : 1.0  
Date : 2026-07-11  
Statut : approuvé pour planification  
Horizon : 12 sprints de 2 semaines, soit environ 24 semaines  
Capacité de référence : 1 développeur principal, 18 à 22 points par sprint

## 1. Vision

Transformer DEV_CORE d'un cockpit d'automatisation local performant en une plateforme
local-first moderne, sécurisée, observable et évolutive, utilisable d'abord par un
développeur, puis par une équipe, sans réécriture prématurée en microservices.

La cible initiale est un monolithe modulaire avec workers isolés. Une distribution en
plusieurs services ne sera envisagée qu'après mesure d'un besoin réel de charge,
d'isolation ou de disponibilité.

## 2. Résultats attendus

- Une API versionnée constitue l'unique porte d'entrée des mutations métier.
- PostgreSQL devient la source de vérité transactionnelle.
- Qdrant reste un index sémantique reconstructible.
- Obsidian devient une projection documentaire, pas un stockage transactionnel.
- Les exécutions sont persistées, annulables, rejouables et idempotentes.
- Le dashboard répond rapidement sans lancer de sous-processus à chaque lecture.
- Chaque action sensible est authentifiée, autorisée et auditée.
- Les traces, métriques, coûts et évaluations sont corrélés à un run et une tâche.
- Le frontend utilise des contrats typés et reçoit les changements incrémentalement.
- Les plugins sont déclaratifs, permissionnés et isolés du noyau.

## 3. Baseline mesurée

| Signal | Baseline | Cible v1 |
|---|---:|---:|
| `/api/status` p50 | 1,9 ms | < 20 ms |
| `/api/dashboard` | 47,55 s | p95 < 500 ms |
| Payload dashboard | ~7,9 Mo | < 500 Ko initial, < 20 Ko par delta |
| `launch.ps1` | ~35 s | < 10 s hors dépendances externes |
| `endday.ps1 -SkipBackup` | 159–334 s | < 30 s en mode agent, tâches longues réservées au endday planifié |
| Santé statique moyenne | 8,14/10 | >= 8,5/10 |
| Hotspots critiques | 3 principaux | 0 fichier < 5/10 |
| Tests Python observés | 10/10 | couverture cœur >= 80 % |
| Skills actifs | 11 | registre et runtime toujours cohérents |

Problèmes bloquants constatés :

- mutations HTTP non authentifiées et certaines mutations exposées en GET ;
- CORS permissif et écoute réseau non restreinte ;
- chemins de fichiers insuffisamment confinés ;
- gates qui affichent des échecs mais retournent parfois un code de succès ;
- état partagé entre JSON, scripts, dashboard et mémoire sans transaction globale ;
- mismatch Qdrant entre embeddings 3072 dimensions et collections 768 dimensions ;
- génération synchrone et volumineuse du dashboard ;
- versions et contextes runtime susceptibles de diverger.

## 4. Principes non négociables

1. Sécurité avant nouvelles fonctions autonomes.
2. Contrats et tests avant migration de stockage.
3. Une seule source de vérité par domaine.
4. Toute mutation est idempotente ou porte une clé d'idempotence.
5. Tout traitement long s'exécute hors du thread HTTP.
6. Les événements sont versionnés et append-only.
7. Qdrant et Obsidian doivent pouvoir être reconstruits depuis les données canoniques.
8. Aucun plugin ne reçoit plus de permissions que son manifeste n'en déclare.
9. Aucun sprint ne se ferme avec un gate rouge ou neutralisé.
10. Kubernetes, Temporal et les microservices restent différés sans seuil mesuré.

## 5. Architecture cible

```text
CLI / Web UI / Hooks / Webhooks
              |
              v
        API Gateway v1
              |
   +----------+-----------+----------------+
   |          |           |                |
 Task      Context      Memory         Automation
 Service   Service      Service          Service
   |          |           |                |
   +----------+-----------+----------------+
              |
        PostgreSQL + Outbox
              |
      Workers d'exécution isolés
              |
   +----------+-----------+----------------+
   |                      |                |
 Qdrant              Object storage    Obsidian
 (index)               (artefacts)     (projection)

 Toutes les couches -> OpenTelemetry -> dashboards / alertes / LLMOps
```

## 6. Jalons

| Jalon | Sprints | Résultat |
|---|---|---|
| Foundation Secure | 0–2 | gates fiables, périmètre sécurisé, dashboard rapide |
| Platform Core | 3–6 | API contractuelle, PostgreSQL, runs durables, observabilité |
| Team Beta | 7–9 | frontend moderne, plugins isolés, RBAC et workspaces |
| Product v1 | 10–11 | intégrations, reprise, charge et release professionnelle |

---

# Sprint 0 — Vérité opérationnelle et CI

Objectif : rendre les signaux de santé fiables avant toute migration.

## Backlog

- [x] `S0-01` — Créer `dc verify --ci` avec sortie JSON et code non nul fiable. `5 pts`
- [x] `S0-02` — Corriger les tests qui affichent FAIL mais retournent `0`. `3 pts`
- [x] `S0-03` — Unifier la version plateforme affichée par scripts et documentation. `2 pts`
- [x] `S0-04` — Ajouter une CI : lint, tests Python/PowerShell, secret scan, contrats. `5 pts`
- [x] `S0-05` — Corriger ou migrer la dimension Qdrant 768/3072. `5 pts`
- [x] `S0-06` — Ajouter les benchmarks de référence au pipeline. `2 pts`

## Gate de sortie

- Toute assertion échouée rend la CI rouge.
- Qdrant accepte un upsert puis une recherche avec le modèle d'embedding configuré.
- Version, task active et contexte de session sont cohérents.
- Les benchmarks sont archivés comme artefacts CI.

## KPI

- Faux succès de gate : 0.
- Tests critiques exécutés en CI : 100 %.
- Collections Qdrant incompatibles : 0.

---

# Sprint 1 — Frontière de sécurité

Objectif : rendre l'exposition locale sûre avant d'étendre l'API.

## Backlog

- [x] `S1-01` — Écouter sur `127.0.0.1` par défaut et rendre le bind explicite. `2 pts`
- [x] `S1-02` — Ajouter authentification locale et rotation des tokens. `5 pts`
- [x] `S1-03` — Remplacer les mutations GET par POST/PATCH/DELETE. `3 pts`
- [x] `S1-04` — Introduire CORS allowlist, CSRF et limites de taille. `3 pts`
- [x] `S1-05` — Canonicaliser les chemins et imposer les racines autorisées. `5 pts`
- [x] `S1-06` — Séparer secrets, configuration versionnée et état runtime. `4 pts`

## Gate de sortie

- Aucun endpoint de mutation n'est accessible anonymement.
- Aucun outil MCP fichier ne peut sortir de sa racine autorisée.
- Tests négatifs : traversal, CORS, CSRF, token expiré, payload trop grand.
- Les secrets ne sont jamais retournés par `/api/settings`.

## KPI

- Mutations anonymes : 0.
- Chemins non confinés : 0.
- Findings secrets critiques : 0.

---

# Sprint 2 — Dashboard rapide et modèle de lecture

Objectif : supprimer la génération synchrone massive du dashboard.

## Backlog

- [x] `S2-01` — Construire un read model incrémental depuis les événements. `5 pts`
- [x] `S2-02` — Découper `/api/dashboard` en ressources paginées. `4 pts`
- [x] `S2-03` — Retirer les appels PowerShell des requêtes de lecture. `4 pts`
- [x] `S2-04` — Ajouter ETag, cache conditionnel et compression HTTP. `3 pts`
- [x] `S2-05` — Publier les deltas par SSE. `4 pts`
- [x] `S2-06` — Ajouter un test de non-régression payload/latence. `2 pts`

## Gate de sortie

- Aucun endpoint GET ne lance de sous-processus.
- `/api/dashboard` p95 < 500 ms sur la machine de référence.
- Payload initial < 500 Ko ; delta SSE < 20 Ko.
- Une régénération échouée ne rend pas le dashboard indisponible.

## KPI

- Réduction de latence : > 95 %.
- Réduction du payload : > 90 %.
- Timeout dashboard : 0 sur 1 000 lectures locales.

---

# Sprint 3 — Gateway FastAPI et contrats de domaine

Objectif : créer un monolithe modulaire à interfaces stables.

## Backlog

- [x] `S3-01` — Introduire FastAPI, Pydantic et une API `/api/v1`. `5 pts`
- [x] `S3-02` — Définir les contrats Task, Run, Event, Plugin et Health. `5 pts`
- [x] `S3-03` — Encapsuler les services existants derrière des ports Python. `5 pts`
- [x] `S3-04` — Transformer PowerShell en adaptateurs de compatibilité. `3 pts`
- [x] `S3-05` — Générer OpenAPI et un client TypeScript. `3 pts`
- [x] `S3-06` — Ajouter contract tests et politique de versioning. `1 pt`

## Gate de sortie

- Les mutations principales passent par `/api/v1`.
- Les scripts ne modifient plus directement l'état d'un autre domaine.
- Les erreurs suivent un schéma stable avec `code`, `message`, `details`, `trace_id`.
- Un changement incompatible est détecté par contract test.

## KPI

- Couverture des commandes principales par API : >= 80 %.
- Contrats documentés : 100 % des endpoints v1.

---

# Sprint 4 — PostgreSQL comme source de vérité

Objectif : remplacer les fichiers JSON concurrents par un stockage transactionnel.

## Backlog

- [x] `S4-01` — Concevoir le schéma projects/tasks/runs/events/plugins/audit. `4 pts`
- [x] `S4-02` — Ajouter SQLAlchemy, Alembic et configuration locale. `4 pts`
- [x] `S4-03` — Implémenter repositories et transactions. `5 pts`
- [x] `S4-04` — Importer les données existantes avec rapport de réconciliation. `4 pts`
- [x] `S4-05` — Mettre en place dual-read contrôlé puis cutover. `3 pts`
- [x] `S4-06` — Ajouter backup, restore et test de migration descendante. `2 pts`

## Gate de sortie

- PostgreSQL est la source canonique des tâches et runs.
- L'import est idempotent et ne perd aucune tâche.
- Les fichiers JSON deviennent export ou compatibilité en lecture seule.
- Backup restauré automatiquement dans un environnement vierge.

## KPI

- Écritures concurrentes perdues : 0.
- Écart de réconciliation : 0.
- Migration reproductible : 100 %.

---

# Sprint 5 — Exécution durable et workers

Objectif : rendre les runs persistants, reprenables et contrôlables.

## Backlog

- [x] `S5-01` — Définir la machine d'état Run et ses transitions. `4 pts`
- [x] `S5-02` — Extraire un worker d'exécution hors du processus HTTP. `5 pts`
- [x] `S5-03` — Ajouter outbox transactionnelle et consommateurs idempotents. `5 pts`
- [x] `S5-04` — Implémenter timeout, retry/backoff et dead-letter queue. `4 pts`
- [x] `S5-05` — Ajouter pause, annulation et reprise après redémarrage. `4 pts`

## Gate de sortie

- Un redémarrage pendant un run ne perd ni état ni artefact.
- Une commande rejouée avec la même clé ne s'exécute qu'une fois.
- Les erreurs permanentes arrivent en DLQ avec diagnostic.
- Les timeouts terminent réellement les processus enfants.

## KPI

- Runs perdus après crash : 0.
- Exécutions dupliquées : 0 dans les tests de reprise.
- Temps de reprise local : < 30 s.

---

# Sprint 6 — Observabilité et LLMOps

Objectif : corréler comportement, coût, qualité et incidents.

## Backlog

- [x] `S6-01` — Instrumenter API, services et workers avec OpenTelemetry. `5 pts`
- [x] `S6-02` — Standardiser `trace_id`, `run_id`, `task_id`, `project_id`. `3 pts`
- [x] `S6-03` — Exposer métriques Prometheus et dashboards Grafana. `4 pts`
- [x] `S6-04` — Brancher une couche LLMOps compatible Langfuse. `4 pts`
- [x] `S6-05` — Créer datasets et évaluations de routage/contexte. `4 pts`
- [x] `S6-06` — Définir SLO, alertes et budgets de coût. `2 pts`

## Gate de sortie

- Une requête est traçable du HTTP jusqu'au worker et au modèle.
- Tokens, coût, latence et résultat sont reliés au même run.
- Les données sensibles sont redacted avant export.
- Une régression de coût ou qualité est visible dans la CI ou le dashboard.

## KPI

- Runs critiques tracés : 100 %.
- Spans orphelins : < 1 %.
- Coût non attribué : < 1 %.

---

# Sprint 7 — Frontend moderne

Objectif : remplacer le HTML généré par une application maintenable et accessible.

## Backlog

- [ ] `S7-01` — Initialiser React/Next.js, TypeScript et design tokens. `4 pts`
- [ ] `S7-02` — Implémenter projets, tâches, runs et health. `5 pts`
- [ ] `S7-03` — Consommer le client OpenAPI et les événements SSE. `4 pts`
- [ ] `S7-04` — Ajouter états loading/empty/error et reprise réseau. `3 pts`
- [ ] `S7-05` — Rendre l'interface responsive et WCAG AA. `3 pts`
- [ ] `S7-06` — Ajouter tests composants et E2E Playwright. `3 pts`

## Gate de sortie

- Aucun HTML métier n'est produit par PowerShell.
- Les mutations affichent leur résultat réel et leur trace ID.
- Les principales tâches utilisateur passent les tests E2E.
- Lighthouse performance/accessibilité >= 90 sur le parcours principal.

## KPI

- JavaScript initial compressé : < 250 Ko.
- Interaction principale p95 : < 200 ms hors traitement backend.
- Parcours E2E critiques : 100 % verts.

---

# Sprint 8 — Plugins permissionnés et sandbox

Objectif : permettre l'extension sans donner un accès implicite à toute la machine.

## Backlog

- [ ] `S8-01` — Définir Manifest v2 et compatibilité de version. `3 pts`
- [ ] `S8-02` — Ajouter scopes filesystem/network/secrets/process. `5 pts`
- [ ] `S8-03` — Exécuter les plugins dans un processus isolé. `5 pts`
- [ ] `S8-04` — Ajouter signature, provenance et checksum des packages. `3 pts`
- [ ] `S8-05` — Ajouter installation atomique, rollback et migrations. `3 pts`
- [ ] `S8-06` — Migrer les trois plugins internes et tester les permissions. `3 pts`

## Gate de sortie

- Un plugin non autorisé ne peut ni sortir de son workspace ni lire un secret.
- Un plugin en échec ne fait pas tomber l'API.
- Toute installation et élévation de permission est auditée.
- Le rollback restaure la dernière version fonctionnelle.

## KPI

- Violations de scope dans les tests : 0.
- Plugins internes conformes Manifest v2 : 100 %.

---

# Sprint 9 — Workspaces, utilisateurs et RBAC

Objectif : passer du cockpit personnel à une bêta utilisable en équipe.

## Backlog

- [ ] `S9-01` — Introduire users, organizations et workspaces. `5 pts`
- [ ] `S9-02` — Implémenter rôles owner/admin/developer/viewer. `4 pts`
- [ ] `S9-03` — Isoler données, secrets, artefacts et index par workspace. `5 pts`
- [ ] `S9-04` — Ajouter quotas de runs, modèles et stockage. `3 pts`
- [ ] `S9-05` — Construire audit log consultable et exportable. `3 pts`
- [ ] `S9-06` — Ajouter tests systématiques d'isolation tenant. `2 pts`

## Gate de sortie

- Aucun identifiant d'un workspace ne permet d'accéder à un autre.
- Toutes les mutations sont attribuées à un principal.
- Les quotas produisent une erreur explicite et ne corrompent pas les runs.
- Les tests d'isolation couvrent API, DB, Qdrant et artefacts.

## KPI

- Fuite inter-workspace : 0.
- Mutations sans audit : 0.
- Endpoints protégés par RBAC : 100 %.

---

# Sprint 10 — Intégrations et expérience produit

Objectif : connecter DEV_CORE au cycle d'ingénierie réel.

## Backlog

- [ ] `S10-01` — Ajouter intégration GitHub App/webhooks. `5 pts`
- [ ] `S10-02` — Ajouter schedules persistants avec historique. `4 pts`
- [ ] `S10-03` — Ajouter notifications Slack ou Teams via plugin. `3 pts`
- [ ] `S10-04` — Créer templates de workflows versionnés. `4 pts`
- [ ] `S10-05` — Construire onboarding, diagnostic et recovery guidés. `3 pts`
- [ ] `S10-06` — Publier documentation API et guide opérateur. `3 pts`

## Gate de sortie

- Les webhooks sont signés, idempotents et rejouables.
- Chaque schedule possède prochain run, dernier statut et historique.
- Une installation vierge atteint son premier run sans modification manuelle de fichier.
- Les intégrations peuvent être désactivées sans modifier le noyau.

## KPI

- Webhooks dupliqués produisant deux runs : 0.
- Temps installation -> premier run : < 15 min.

---

# Sprint 11 — Hardening et release v1

Objectif : démontrer que la plateforme peut être exploitée et mise à jour proprement.

## Backlog

- [ ] `S11-01` — Tests de charge API, SSE, workers et DB. `4 pts`
- [ ] `S11-02` — Tests de panne : process kill, DB restart, Qdrant indisponible. `4 pts`
- [ ] `S11-03` — Security review, dépendances et SBOM. `4 pts`
- [ ] `S11-04` — Procédures backup/restore/upgrade/rollback automatisées. `4 pts`
- [ ] `S11-05` — Packaging reproductible et release notes. `3 pts`
- [ ] `S11-06` — Runbook incidents et critères de support. `3 pts`

## Gate de sortie

- Release candidate déployée depuis zéro par une commande documentée.
- Backup restauré et migration rollbackée lors d'un test automatisé.
- Les SLO tiennent pendant le test de charge de référence.
- Aucun finding sécurité critique ou élevé non accepté.

## KPI v1

- Disponibilité locale cible : >= 99,5 %.
- API read p95 : < 200 ms.
- API write p95 hors exécution : < 500 ms.
- Reprise après panne : < 60 s.
- Couverture cœur : >= 80 %.
- Actions sensibles auditées : 100 %.

---

## 7. Definition of Done commune

Une story n'est terminée que si :

- le test a échoué avant l'implémentation quand du code est ajouté ;
- les tests unitaires, intégration et contrats concernés passent ;
- les erreurs et métriques nécessaires sont observables ;
- la documentation et les migrations sont à jour ;
- aucun secret, TODO non tracé ou code mort n'est introduit ;
- les performances ne régressent pas au-delà du budget du sprint ;
- la compatibilité et le rollback ont été considérés ;
- le changement est relié à une tâche DEV_CORE et un commit atomique.

## 8. Revues et cadence

- Planning : premier jour du sprint, capacité maximum 22 points.
- Revue technique : à mi-sprint sur contrats, migration et sécurité.
- Démo : dernier jour avec critères de sortie observables.
- Rétrospective : une action d'amélioration maximum reportée au sprint suivant.
- Release interne : à chaque sprint vert.
- Aucun report implicite : une story incomplète est re-découpée et réestimée.

## 9. Risques et mitigations

| Risque | Mitigation |
|---|---|
| Migration trop large | Strangler pattern, dual-read temporaire, cutover mesuré |
| Multiplication des technologies | Monolithe modulaire ; Redis/NATS/Temporal différés |
| Régression des scripts existants | Adaptateurs PowerShell et contract tests |
| État local historique incohérent | Import idempotent et rapport de réconciliation |
| Coût d'observabilité excessif | Sampling, rétention et redaction configurables |
| Plugin compromis | Scopes, isolation process, provenance et audit |
| Dérive de roadmap | Gate de sprint, KPI mesuré, backlog limité à la capacité |

## 10. Hors périmètre avant la v1

- Kubernetes et multi-région.
- Microservices par domaine.
- Temporal comme dépendance obligatoire.
- Marketplace publique de plugins.
- Auto-évolution avec merge autonome.
- Self-healing qui modifie le code sans validation humaine.
- Workflow canvas généraliste comparable à Dify.

Ces éléments nécessitent une décision d'architecture séparée et des seuils mesurés.

## 11. Premier ordre d'exécution

1. Ouvrir Sprint 0 uniquement.
2. Transformer chaque item `S0-*` en tâche DEV_CORE avec dépendances.
3. Capturer les benchmarks avant la première modification.
4. Fermer Sprint 0 seulement quand `dc verify --ci` est réellement bloquant.
5. Recalibrer les points des sprints 1–3 à partir de la vélocité observée.
