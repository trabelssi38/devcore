# Import différentiel des neuf tâches historiques

Statut : **exécuté et vérifié** le 15 octobre 2026. Résultat final :
[`post-l9-historical-task-import-2026-10-15.json`](post-l9-historical-task-import-2026-10-15.json).

Le service `DevCoreIndividual` v250 utilise déjà PostgreSQL. La copie SQLite
qualifiée reste une source d'archive. Seules les tâches `devcore` `T-393` à
`T-401` sont absentes de PostgreSQL actif. Le rôle applicatif ne possède pas
`INSERT` sur `tasks` ; l'import exige le rôle de migration PostgreSQL.

## Artefact préparé

- SQL : `E:/DevCoreRuntime/migration/historical-task-delta-20261015.sql`
- SHA-256 : `4351955adbe621ba14a2d4577d83a3d9215ec63035990ccd80fdb9fc76662e68`
- Source épinglée : `E:/DevCoreRuntime/qualification/historical-pilot-final-20261014.db`
- SHA-256 source : `e24133a8b4a15e0a62e83b4018eb6570ad49cbdf0032a355e6a399cacf10a4f4`
- ACL du répertoire SQL : Administrateur, Administrateurs et SYSTEM seulement.

Le SQL ouvre une transaction sérialisable, verrouille `tasks` pendant le bref
import, vérifie l'absence des neuf UUID/identifiants, puis attribue des numéros
strictement supérieurs au maximum courant du projet. Il conserve titre, état,
étapes, métadonnées et horodatages, sans réactiver de run ni restaurer de
worktree non prouvé. Ne pas remplacer `devcore.db` ou réimporter toutes les
tâches : les numéros historiques 393–401 sont déjà occupés dans PostgreSQL.

## Exécution par un administrateur PostgreSQL

Dans une fenêtre sans écriture concurrente de tâches, obtenir d'abord une
sauvegarde PostgreSQL *complète* hors Dropbox :

```powershell
& 'C:/Program Files/PostgreSQL/17/bin/pg_dump.exe' -h 127.0.0.1 -p 5432 `
  -U postgres -W -F c -f 'E:/DevCoreRuntime/migration/before-task-delta-20261015.dump' `
  devcore_qualification_team_20261013
```

Vérifier le code de sortie, la taille non nulle et l'empreinte du dump. Puis
exécuter le SQL épinglé avec arrêt sur la première erreur :

```powershell
& 'C:/Program Files/PostgreSQL/17/bin/psql.exe' -X -v ON_ERROR_STOP=1 `
  -h 127.0.0.1 -p 5432 -U postgres -W `
  -d devcore_qualification_team_20261013 `
  -f 'E:/DevCoreRuntime/migration/historical-task-delta-20261015.sql'
```

Le mot de passe est saisi dans l'invite locale, jamais dans le fichier SQL ou
la ligne de commande. Si une garde échoue, `psql` arrête le fichier ; la
connexion ferme la transaction non validée. Conserver le dump et la sortie de
`psql` comme preuves.

Après `COMMIT`, lire les neuf `legacy_id`, leurs UUID et leurs nouveaux numéros
sous le contexte RLS `devcore`, puis vérifier les endpoints `/project` et
`/api/status` et le nombre de tâches du projet. En cas d'anomalie, ne pas
répéter l'import ; utiliser le dump et un plan de restauration distinct.

## Résultat de la fenêtre

L'administrateur a transmis une sortie `psql` complète : neuf lignes insérées,
numéros 478 à 486 et `COMMIT`. La lecture indépendante avec le rôle applicatif
voit 398 tâches `devcore`, dont les neuf UUID attendus ; les neuf numéros sont
distincts et leurs états sont `done`. Un autre projet ne voit aucun de ces UUID
sous RLS. Le dump de 11 180 780 octets existe, son SHA-256 est consigné dans le
rapport et `pg_restore --list` retourne 0. Cette vérification n'est pas une
restauration complète du dump. Les services restent `Running` et les deux
sondes HTTP répondent 200.
