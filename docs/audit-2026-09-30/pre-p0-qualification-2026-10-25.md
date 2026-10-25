# Préqualification des réserves avant P0 — 25 octobre 2026

## Décision de périmètre

L'utilisateur autorise la phase 6 pour `devcore` seulement, avec approbation
humaine avant toute commande qui modifie des fichiers. Cette décision ne vaut
pas activation d'un agent autonome. Les projets tiers restent hors périmètre.

## Arrêt incomplet du 24 octobre

L'essai de reprise a volontairement arrêté RepoWise PID 14380 sous le superviseur
PID 12688. Le code actif marque `shutdown_incomplete` dès qu'un enfant n'a pas
quitté coopérativement, y compris un enfant déjà tué avant la séquence d'arrêt.
Les journaux du cycle `bc02a974` se terminent par « Application shutdown
complete » pour le router, les deux Headroom et le gateway, et par
`postgres_schedule_stopped` pour le scheduler. Le journal RepoWise s'arrête
après des réponses de santé 200, sans arrêt coopératif. Au contrôle du 25
octobre, les anciens PID 12688, 14380, 7128, 13576 et 14908 ne sont plus
présents ; le PID 14032 est réutilisé par `msedgewebview2.exe` depuis le 25.
Aucun processus courant n'a pour parent PID 12688 ou 14380. Les six enfants
actuels ont pour parent le nouveau superviseur PID 3628.

Ces preuves attribuent l'arrêt non coopératif au RepoWise tué pour l'essai et
ne montrent pas d'orphelin actuel de l'ancien superviseur. Le manifeste du
cycle ancien a été remplacé : ses codes de sortie par enfant et l'état exact
des descendants immédiatement après l'arrêt ne sont pas reconstructibles.
Cette limite reste explicite ; aucune qualification d'arrêt entièrement
coopératif n'est revendiquée.

## Budget de relance proposé

Le déclencheur Windows toutes les cinq minutes n'a actuellement aucune fin.
Le garde applicatif ajouté dans `global_restart_budget.py` compte les échecs
de lancement ou du superviseur : trois échecs en trente minutes bloquent les
nouveaux démarrages. L'état et une alerte `requires_operator` sont conservés
dans `GlobalStack/restart-budget.json`, sous l'ACL du profil actif
(`Système` et `Administrateur`). Un lancement stable pendant trente minutes
réinitialise la série ; l'épuisement reste verrouillé jusqu'à un réarmement
explicite avec motif. Les commandes de contrôle et d'arrêt ne consomment pas
ce budget. Le test ciblé passe **6/6** avec racines DEVCORE temporaires avant
imports ; il confirme qu'un quatrième essai n'atteint ni Git ni la base.

Ce garde est qualifié en isolation seulement au moment de cette note. Son
installation dans le wrapper de la tâche et son observation opérationnelle
seront consignées séparément. La tâche active et les deux schedules quotidiens
ne sont pas modifiés par les tests.

## Stabilité

Au contrôle du 25 octobre vers 14:39 `Africa/Tunis`, le superviseur PID 3628
créé le 24 octobre à 12:23 reste `ready`, six enfants vivants avec ce parent,
et cinq sondes HTTP répondent 200. Le journal Windows donne 315 événements
322 depuis le nouveau cycle : le tick a été ignoré quand la tâche tournait.
Ce contrôle ponctuel ne démontre pas la disponibilité continue. Les 48 heures
depuis le premier `ready` ne peuvent être vérifiées avant le 26 octobre à
12:24:27 `Africa/Tunis`, puis doivent être confrontées aux journaux et incidents.
