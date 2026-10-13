# Migration globale DevCore — état final

Date de qualification : **14 octobre 2026**

## Résultat

La migration globale est qualifiée pour le profil local PostgreSQL.

- `DevCoreIndividual` : `Running`, démarrage automatique
- `postgresql-x64-17` : `Running`
- Release : `devcore-py31316-20261013-postgres-v250`
- Port : `127.0.0.1:20129`
- `/project` : HTTP 200
- `/api/status` : HTTP 200
- Contrôle post-bascule : 3 observations stables
- Non-régression HTTP : 22 tests passés, 0 échec
- Bloqueurs actifs : 0

## Cockpit

Le cockpit individuel est accessible sur :

```text
http://127.0.0.1:20129/project
```

Le profil individuel ferme volontairement les routes globales historiques :

- `/` → HTTP 403
- `/api/dashboard` → HTTP 403
- `/api/dashboard/tasks` sans session → HTTP 401

Cette séparation protège l'isolation par projet. Une session authentifiée est
nécessaire pour consulter les tâches.

## Décisions d'exploitation

- Langfuse distant désactivé conformément à D-009.
- PostgreSQL est la source active du profil équipe ; SQLite reste réservé aux
  imports, copies et fixtures de qualification.
- Les données transactionnelles restent hors Dropbox conformément à D-004.

## Preuves

- `global-migration-status-2026-10-13.json`
- `global-cutover-execution-2026-10-13.json`
- `post-cutover-observation-2026-10-14.json`
- `execution-2026-10-05.md`, passages v363 et v364
