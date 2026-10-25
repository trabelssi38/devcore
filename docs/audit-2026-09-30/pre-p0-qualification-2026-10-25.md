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

À 18:18 `Africa/Tunis`, le lanceur utilisé par `DevCoreGlobal` a été remplacé
après vérification SHA-256 de l'ancien fichier ; la copie de retour est
`E:/DevCoreRuntime/qualification/pre-p0-launcher-backup-20261025.py`.
`--budget-status` sur le profil actif retourne `failures=[]` et
`exhausted=false`. La tâche reste `Running`, le superviseur PID 3628 et ses
six enfants restent `ready` ; aucune relance ou panne n'a éprouvé le garde en
production. Le contrôle `--budget-status` ne crée pas le fichier d'état : il
sera créé lors d'un premier résultat de lancement. Le tick de cinq minutes
reste sans fin, mais le wrapper refusera le quatrième lancement après trois
échecs rapides. Les deux schedules quotidiens restent désactivés.

## Phase 6 — pilote agent

Le choix utilisateur du 25 octobre limite l'agent au projet `devcore` et
exige une approbation humaine avant une modification des fichiers. Le nouveau
pilote `devcore_agent_pilot.py` est un point d'entrée séparé, sans connexion
à `task_sync` ni à un schedule. Il n'accepte que le checkout dédié
`E:/DevCoreRuntime/qualification/devcore-agent-pilot` propre. `codex exec`
est lancé avec `--sandbox read-only` et produit un diff ; le contrôleur
vérifie le fichier existant sous `DEV_CORE/`, la base Git et construit un patch
à partir d'un remplacement de texte exact fourni par l'agent. Il
conserve une proposition avec son SHA-256. Une seconde commande interactive
montre le patch et exige `APPLY <sha256>` avant `git apply --index` ; l'audit
consigne identité locale, empreinte et application. Les limites sont trois
propositions par jour, quinze minutes par invocation, un fichier, 8 000 octets
par extrait et 128 000 octets de patch. Une sortie sans changement est refusée.

Cette version est un **prototype qualifié en isolation**, pas encore une mise
en service autonome : aucun déclenchement sur tâche, aucun compte `majdi`
authentifié pour l'approbation et aucun essai d'arrêt/reprise n'est revendiqué.
Trois essais réels de proposition Codex en lecture seule ont été refusés avant
création d'un patch approuvable : le premier et le second par la validation
`git apply --index` sur CRLF, le troisième par un diff mal formé. Le correctif
suivant remplace le diff libre par un remplacement d'extrait exact et construit
le diff localement ; il passe les tests isolés mais n'a pas encore eu de nouvel
essai réel, le quota quotidien de trois propositions étant atteint.
L'approbation est interactive dans un terminal local. Les tests utilisent un
dépôt Git et des racines DEVCORE temporaires ; ils ne touchent pas aux données
actives.

## Stabilité

Au contrôle du 25 octobre vers 14:39 `Africa/Tunis`, le superviseur PID 3628
créé le 24 octobre à 12:23 reste `ready`, six enfants vivants avec ce parent,
et cinq sondes HTTP répondent 200. Le journal Windows donne 315 événements
322 depuis le nouveau cycle : le tick a été ignoré quand la tâche tournait.
À 18:25 `Africa/Tunis`, le même superviseur et les six mêmes enfants sont
encore présents (dates de création du 24 octobre, parents contrôlés par CIM),
le manifeste a un heartbeat récent et les cinq chemins exacts de sonde
(`20130/healthz`, `8787/healthz`, `8789/healthz`,
`20131/api/v1/health`, `7337/health`) répondent 200. Depuis le premier
`ready`, le canal TaskScheduler contient 360 événements 322 pour
`DevCoreGlobal` et aucun autre événement de cette tâche ; le journal de
lanceur n'a pas de nouvelle sortie en échec après celle du 24 octobre à
11:20 UTC. Cela représente environ 30 heures, sans prouver chaque intervalle
de disponibilité.
Ce contrôle ponctuel ne démontre pas la disponibilité continue. Les 48 heures
depuis le premier `ready` ne peuvent être vérifiées avant le 26 octobre à
12:24:27 `Africa/Tunis`, puis doivent être confrontées aux journaux et incidents.
