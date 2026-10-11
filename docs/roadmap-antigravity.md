# Feuille de route Antigravity — DevCore

Date de référence : 2026-10-10
Dépôt : `E:\src_python\devcore`
Statut : pilote local en cours, non qualifié pour la production.

Ce document sert de brief d'exécution à Antigravity. Il complète le plan et le
registre des décisions ; il ne les remplace pas.

## 1. Lecture obligatoire avant toute modification

Lire dans cet ordre :

1. `AGENTS.md`.
2. `docs/project-context/devcore.md` et `docs/project-context/decisions.md`,
   préférablement avec `DEV_CORE/Scripts/resume_project_context.py`.
3. `plans/2026-10-01-devcore-local-multiutilisateur.md`.
4. `docs/audit-2026-09-30/rapport.md`.
5. `docs/audit-2026-09-30/execution-2026-10-05.md`.
6. Le journal spécialisé du lot choisi, sans charger tous les journaux.

Le code, les tests actuels et l'état Git priment sur une note ancienne. Une
proposition du plan n'est pas une qualification opérationnelle.

## 2. Objectif produit

DevCore doit permettre à plusieurs utilisateurs locaux de travailler chacun
dans leurs projets sans traverser les frontières de données ou de droits. La
cible comprend une API commune, PostgreSQL local, des droits par projet, des
workers durables, une outbox, un Cockpit cohérent et des métriques attribuées.

Un projet délimite données et permissions. Un run est une tentative
d'exécution persistante. Un workspace est un répertoire de travail et ne vaut
pas une sandbox de sécurité.

## 3. État établi au 2026-10-10

| Lot | État | Éléments établis sur fixtures |
| --- | --- | --- |
| L0 | Avancé | Inventaire, sauvegarde/restauration sur copies, environnement Python verrouillé et mesures ponctuelles. |
| L1 | Avancé | Isolation `project_id`, mutations SQLite transactionnelles, versions, dépendances et import JSON prévalidé sur copie. |
| L2 | Partiel | API, contrats, MCP stdio et adaptateurs présents ; unification complète des interfaces ouverte. |
| L4 | Partiel | Argon2id, sessions cookies/CSRF, rôles et audit testés localement. |
| L6 | Avancé | Publication atomique, snapshots, cache, SSE et protections clients Cockpit couverts par tests. |
| L7 | Partiel | Fiche et décisions bornées en UTF-8 ; injection automatique à qualifier. |
| L8-L9 | Partiel | Métriques locales, scheduler, arrêt/reprise et rapports sur fixtures ; activation et charge réelle ouvertes. |

Le passage d'audit v209 expose des digests SHA-256 source/candidate pour les
tâches et le graphe d'une migration SQLite candidate. Il ne qualifie ni
PostgreSQL, ni la bascule, ni les propriétés JSON hors schéma.

Restent ouverts : PostgreSQL et la bascule, charge et multi-processus,
activation de services réels, navigateur/réseau, autorisation de toutes les
ressources, attribution authentifiée des usages et gains de tokens. RepoWise
a un index ancien, un embedder mock et une recherche sémantique inactive :
confronter chaque résultat au code courant.

## 4. Décisions à appliquer

| Décision | Directive |
| --- | --- |
| D-002 | Déployer sur ce poste et lier les services à localhost avant toute ouverture réseau. |
| D-003 | PostgreSQL est la cible via une API commune ; SQLite sert aux correctifs/imports. Une seule source active par instance. |
| D-004 | Garder les données transactionnelles hors Dropbox. Tester sur copies et racines temporaires. |
| D-006 | Mesurer tokens et qualité avec tâches comparables ; aucun gain sans preuve. |
| D-007 | 8787 conserve fournisseur/modèle ; 8789 passe par Gemini Router 20130 ; embeddings directs et refus des modèles natifs par le Router. |

D-005, DBOS derrière `WorkflowEngine`, reste une proposition : aucune décision
définitive avant un prototype concluant de panne et de reprise. D-001 est
remplacée et ne guide plus l'implémentation.

## 5. Configuration et règles de travail

- Python de recette : `E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe` (Python 3.13.3 vérifié).
- Définir `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` vers des répertoires
  temporaires avant imports ou sous-processus.
- Ne jamais utiliser comme fixture les données actives, Dropbox ou l'index
  RepoWise réel.
- Préserver toutes les modifications Git, y compris les fichiers non suivis.
  Aucun `reset`, `checkout` global ou nettoyage destructif.

Configurations de référence :

- `DEV_CORE/Config/network.json` : interfaces et ports.
- `DEV_CORE/Config/routing_profiles.json` : routage LLM.
- `DEV_CORE/Config/headroom_config.yaml` : métriques et limites.
- `DEV_CORE/Config/local-team.env.example` : environnement local exemple.
- `DEV_CORE/Config/mcp-individual.example.toml` et
  `mcp-individual-tasks.example.toml` : profils MCP individuels.
- `DEV_CORE/Scheduler/jobs.devcore.json` : scheduler.
- `DEV_CORE/pyproject.toml`, `requirements-ci.txt` et les verrous Python :
  dépendances et recette.

Ports de référence : 20129 (Cockpit/compatibilité), 20131 (API), 8787 (route
native), 8789 (route auxiliaire vers Gemini Router 20130). Vérifier les ports
juste avant démarrage : la configuration ne prouve pas qu'un service est actif.

## 6. Séquence de travail

### Phase A — stabiliser le terrain

1. Capturer `git status --short` et limiter chaque intervention à son
   périmètre.
2. Créer une racine de recette temporaire et consigner son manifeste.
3. Relire le test et le journal spécialisés du lot choisi.
4. Définir les critères d'acceptation avant le code.
5. Ajouter un test de régression utile, modifier le minimum, puis exécuter la
   recette ciblée sous Python 3.13.
6. Consigner preuve, limites et travail restant dans le journal.

### Phase B — finir L1 et L2

- Migrer les lecteurs restants de `active_project`, les JSON partagés et les
  tâches sans manifeste de projet.
- Rendre obligatoire `RequestContext(user_id, project_id, session_id, run_id,
  trace_id)` dans les chemins métier restants.
- Terminer version optimiste, atomicité et adaptateurs historiques.
- Généraliser `TaskRepository`, `UnitOfWork`, `IdentityProvider`,
  `WorkflowEngine`, `Runner`, `ModelGateway` et `KnowledgeProvider`.
- Router CLI et MCP vers l'API, sans accès direct client à la base serveur.
- Unifier statuts, pagination, erreurs et catalogue de routes.

### Phase C — qualifier L3 : PostgreSQL

- Qualifier PostgreSQL Windows sur une base temporaire hors Dropbox.
- Créer migrations pour utilisateurs, memberships, sessions, tâches, runs,
  événements, audit, outbox, artefacts, mémoire et budgets.
- Faire l'import à blanc SQLite/JSON avec correspondances, divergences,
  digests et réconciliation des ambiguïtés.
- Tester transactions, contraintes, pool, verrouillage optimiste et RLS avec
  le rôle applicatif.
- Neutraliser les imports automatiques historiques après bascule validée.

### Phase D — finir L4 : identité et droits

- Finaliser expiration/révocation de sessions et récupération administrateur.
- Autoriser côté serveur tâches, runs, artefacts, exports, logs, mémoire, SSE
  et MCP pour chaque projet et rôle.
- Retirer jeton HTML commun et routes anonymes de données.
- Qualifier cookies HttpOnly/SameSite, CSRF, Origin/CORS, jetons CLI/MCP
  révocables et secrets Windows protégés.

### Phase E — qualifier L5 : exécution durable

- Prototyper DBOS ou un moteur alternatif avec trois étapes et arrêt forcé.
- Documenter la décision seulement après preuve de reprise sans cloud requis.
- Ajouter admission idempotente, `run_id`, outbox, transitions atomiques,
  heartbeat, reprise et annulation confirmée.
- Imposer quotas, backpressure, délais de l'arbre Windows, workspaces par run,
  limites de ressources et identité non administratrice.
- Remplacer Hermes simulé ou signaler explicitement l'indisponibilité backend.

### Phase F — terminer L6 : Cockpit et événements

- Outbox durable, publication idempotente, consommateurs reprenables et
  rétention.
- Projections reconstruites depuis événements SQL.
- SSE avec curseur durable, `Last-Event-ID`, heartbeats et resynchronisation.
- Qualifier autorisation par projet, corruption, permissions, navigateur réel,
  multi-workers et charge.
- Déporter les opérations lourdes de la boucle async et réduire les templates
  dupliqués.

### Phase G — L7, L8 et L9

- Démontrer qu'un nouvel agent reçoit et respecte fiche et décisions.
- Finaliser métriques authentifiées, OTLP, supervision et budgets par projet.
- Mesurer tokens et qualité selon le protocole, sur tâches comparables.
- Préparer fenêtre de gel, migration sur copie, restauration et reprise après
  panne.
- Proposer l'activation locale seulement après les phases précédentes.

## 7. Critères de blocage

Ne pas activer et documenter le problème si une écriture traverse les projets,
si une commande fonctionne sans contexte, si une route contourne les droits,
si un run réattribué peut être validé par un ancien worker, si une migration
choisit silencieusement des données ambiguës, ou si un secret apparaît dans
Git, HTML, logs ou métriques.

## 8. Livrable attendu par ticket

Chaque ticket Antigravity doit fournir : lot, objectif, fichiers modifiés,
décisions appliquées, racines temporaires, commande de test, résultat exact,
limites restantes et mise à jour des documents de suivi. Ne cocher un point du
plan qu'après une preuve reproductible.

## 9. Prompt de démarrage pour Antigravity

> Tu travailles dans `E:\src_python\devcore`. Lis `AGENTS.md`, le contexte
> projet, les décisions, le plan et le rapport d'audit avant toute modification.
> Préserve l'état Git complet : aucun reset, checkout global ou suppression de
> fichiers. Choisis un seul lot L0-L9 et annonce ses critères d'acceptation.
> Utilise Python `E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`
> avec `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires définis avant
> imports ou sous-processus. N'utilise ni données actives, ni Dropbox, ni index
> RepoWise réel. Exécute les tests ciblés, consigne commandes, résultats et
> limites dans le journal, puis mets à jour plan, fiche ou décisions si la
> preuve le justifie. N'affirme jamais qu'un service est actif sans preuve
> actuelle.

## Sources

- `docs/project-context/devcore.md`
- `docs/project-context/decisions.md`
- `plans/2026-10-01-devcore-local-multiutilisateur.md`
- `docs/audit-2026-09-30/rapport.md`
- `docs/audit-2026-09-30/execution-2026-10-05.md`
- `docs/audit-2026-09-30/protocole-tokens-codex.md`
