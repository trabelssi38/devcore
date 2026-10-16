# Propositions détaillées — migration globale DevCore

Généré le 2026-10-12T13:30:24.288065+00:00. Statut : **proposal_only** ; bascule autorisée : **non**.

## Ordre proposé

| Phase | Action | Critère de sortie |
|---|---|---|
| P0 — Qualification post-L9 | qualifier PostgreSQL équipe et les piles globales RepoWise, Headroom, Gemini Router, Gateway, Scheduler, réseau et OTLP/Langfuse avant la migration de production | tous les endpoints, schémas, identifiants et retours arrière sont testés sur une copie hors production |
| P1 — Gel et nouvelle capture | arrêter tous les écrivains, confirmer l'arrêt de l'autre poste, attendre la stabilité Dropbox, capturer des copies SQLite sans WAL et leurs empreintes | empreintes et comptes figés ; toute mutation invalide la fenêtre |
| P2 — Clôture des décisions | approuver les racines des projets, les valeurs gagnantes par champ, les projets provisoires et la politique de quarantaine du graphe | aucun élément de revue non classé |
| P3 — Répétition indépendante | restaurer la candidate dans un environnement indépendant et exécuter les contrôles API, recherche, impact, scheduler, réseau et OTLP | intégrité et FK correctes et répétition du retour arrière réussie |
| P4 — Bascule de production | publier une génération immuable, maintenir le scheduler arrêté, basculer les lecteurs puis réactiver les écrivains dans une fenêtre observée | smoke tests réussis et responsable du retour arrière présent |

## Projets et tâches

Trois projets ont un identifiant commun mais des racines ou horodatages différents. Les 33 tâches `xtream_universal_manager` nécessitent la validation de la racine `C:\src\xtream_universal_manager`; les 13 tâches `scripts` nécessitent un projet provisoire approuvé.

Les conflits matériels concernent 134 tâches : worktree=119, metadata=11, status=6, steps_done=8, title=1. Répartition : dashboard_recette_br=116, job_tracker=12, cea_dashboard=4, conso_api_madania=1, devcore=1.

Règle proposée : arbitrage champ par champ, conservation des deux valeurs sources et de la preuve ; aucune victoire globale d’une base.

## Graphe

Sur la copie actuelle, 174681 arêtes sont réparables par règle déterministe et 94185 restent en quarantaine. Les relations sans preuve restent hors projection FK. La déduplication ne doit intervenir qu’après remappage et doit conserver `source_rows` et l’empreinte de la source.

## Scheduler et pile post-L9

La migration de production est proposée après la qualification PostgreSQL équipe et des services globaux RepoWise, Headroom, Gemini Router, Gateway, Scheduler, réseau et OTLP/Langfuse. Avant cela, seules les répétitions sur copies sont autorisées. Le scheduler reste arrêté pendant la bascule et l’observation initiale.

## Approbations nécessaires

- project ownership and roots
- task field conflict winners
- quarantine retention policy
- PostgreSQL/global stack readiness
- cutover and rollback window

## Blocages actuels

- candidate_historical_fk_empty
- project_review_empty
- quarantine_empty
- unresolved_task_conflicts_empty
- consumer_contract_reviewed
