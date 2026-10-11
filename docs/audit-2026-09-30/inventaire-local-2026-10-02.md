# Inventaire local DevCore — 2 octobre 2026

Relevé ponctuel en lecture seule vers 11 h (Europe/Paris). Les nombres peuvent évoluer pendant l'exécution des services. Aucun secret, contenu de configuration, note, événement ou tâche n'est reproduit ici. Les chemins sous le profil Windows sont abrégés par `%USERPROFILE%`.

## Frontières de stockage

| Rôle | Chemin observé | État |
|---|---|---|
| Code et configuration | `E:/src_python/devcore/DEV_CORE` | Dépôt Git avec modifications en cours ; `Config/projects.json`, `Config/network.json`, `Config/security.json` et `Scheduler/jobs.devcore.json` existent. Leurs valeurs sensibles ne figurent pas dans ce manifeste. |
| État local actif | `%USERPROFILE%/AppData/Local/DEV_CORE_LOCAL` | Existe, hors Dropbox. `devcore.db` : 176 041 984 octets ; pas de fichier WAL visible au relevé. |
| Planificateur local | `%USERPROFILE%/AppData/Local/DEV_CORE_LOCAL/Scheduler` | `scheduler.db` : 22 061 056 octets ; `jobs.json` présent. Deux anciennes copies SQLite nommées « Copie en conflit » sont présentes, non fusionnées. |
| Documents partagés | `%USERPROFILE%/Dropbox/DEV_CORE_DATA` | Existe ; 120 fichiers `.json` et 13 copies conflictuelles recensés. `Memory` : 89 fichiers ; `Vault` : 157 ; `Bus` : 8 ; `Logs` : 347. Ces nombres ne prouvent pas qu'un autre poste écrit actuellement. |
| Autre SQLite partagé | `%USERPROFILE%/Dropbox/DEV_CORE_DATA/Memory/conversations.db` | 40 960 octets ; son rôle et ses écrivains restent à qualifier avant bascule. |
| Index RepoWise du dépôt | `E:/src_python/devcore/.repowise` | 536 fichiers, environ 68,4 Mo ; `wiki.db`, `omissions/omissions.db`, `sessions/sessions.db` présents. |
| État RepoWise utilisateur | `%USERPROFILE%/.repowise` | 3 458 fichiers, environ 130,9 Mo. Chemin trouvé, propriétaire et politique de sauvegarde à confirmer. |
| Ancienne copie locale | `%USERPROFILE%/AppData/Local/DEV_CORE_LOCAL/devcore-before-t532-correction-20260928-0907.db` | 96 198 656 octets ; conservation à décider après vérification des sauvegardes. |

Le dossier local contient aussi `Bus/events` (27 fichiers), `Bus/processed` (728), `Bus/processing` (0), `Logs` (853) et `Sessions` (0) au relevé. Le dossier `Metrics` n'existait pas encore. Le contenu des 27 événements en attente n'a pas été interprété dans cet inventaire.

## Services et planification

- Processus identifiés sans lire leurs arguments sensibles : `scheduler_tick.py` (PID 9052, ensemble résident 20,1 Mo), `dashboard_api.py` (PID 19052, 18,8 Mo), RepoWise (PID 752, 251,1 Mo). Les PID, mémoire et temps CPU sont instantanés ; aucune mesure de pic ni de charge au repos n'a été faite.
- Ports localhost joignables au relevé : 20129, 20130 et 7337. Le port 20131 ne répondait pas ; ceci ne prouve pas l'absence d'une API configurée ailleurs. `Config/network.json` déclare des hôtes `127.0.0.1` pour 20129, 20130, 8787 et 7337. Le port 8787 n'a pas été sondé lors de ce relevé.
- `Scheduler/jobs.json` local contenait huit tâches activées : `daily_launch`, `daily_endday`, `weekly_maintenance`, `periodic_task_scan`, `periodic_task_sync_dashboard`, `event_watcher`, `active_agent_task_runner`, `system_watcher`. Le dernier statut du scan périodique était `error` ; les autres étaient `ok`. Le registre statique du dépôt désactive désormais les quatre premières tâches sans contexte sûr (`daily_launch`, `daily_endday`, `weekly_maintenance`, `periodic_task_scan`), mais le processus actif n'a pas encore resynchronisé son état dynamique. Les commandes de ces quatre tâches échouent désormais sans projet ou option explicite avant leurs anciennes mutations.

## Outils trouvés

Python 3.14.3, Git 2.54.0.windows.1, `docker`, `wsl` et `repowise` sont trouvés dans le PATH. `psql` et `pg_ctl` n'y sont pas. Le service Windows `com.docker.service` était arrêté au relevé ; la présence des exécutables ne prouve pas qu'un moteur fonctionne. Aucune installation PostgreSQL locale n'est confirmée.

## Points à résoudre avant la bascule

1. Identifier les autres postes et processus qui écrivent encore dans `DEV_CORE_DATA`, y compris `conversations.db` ; établir une fenêtre de gel et réconcilier les 13 copies conflictuelles sans choisir une copie par sa seule date.
2. Vérifier les 27 événements locaux en attente et les deux copies conflictuelles du planificateur ; ne pas les réinjecter automatiquement.
3. Mesurer la mémoire au pic, le CPU au repos, les latences et la taille des index sur un protocole reproductible ; le relevé ponctuel ci-dessus ne constitue pas un benchmark.
4. Documenter la resynchronisation contrôlée du planificateur, les dépendances verrouillées et la restauration applicative complète avant l'installation PostgreSQL et l'ouverture réseau.
