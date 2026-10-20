# Jobs projet — candidat de phase 3

Trois fonctions utiles des anciens jobs disposent d'un nouveau chemin dans
le profil équipe. Elles ne chargent ni `jobs.devcore.json`, ni Hermes, ni le
board SQLite/JSON. Chaque soumission est limitée à un projet Git actif et
enregistré, sous un principal `task.mutate` ou, pour l'échéance quotidienne,
sous la planification que ce principal a inscrite. Les essais n'utilisent que
des bases et dépôts temporaires.

## Scan Git

`POST /api/v1/automation/jobs/git-scan` accepte un projet et un SHA complet
facultatif. Le service vérifie la racine Git enregistrée, l'atteignabilité du
commit et les identifiants de tâches du projet sous RLS. Il soumet un run
durable à commande argv gérée, avec une clé par révision. Le processus lit au
plus cent commits, compare les tags `[T-...]` à la capture des identifiants et
rend les tags manquants et les tâches sans tag récent. Il ne modifie aucune
tâche. Une révision rejouée renvoie le même run ; une autre révision attend la
fin du run déjà actif pour ce projet.

Un événement `git_commit` réussi sur la route de phase 2 tente aussi la
soumission du scan et de l'indexation RepoWise. La réponse distingue le
résultat du hook des admissions des deux jobs ; un échec d'admission y reste
explicite. Un événement de commit n'est pas une clôture de tâche.

## Bilan quotidien

`POST /api/v1/automation/jobs/daily-metrics` inscrit explicitement un projet,
une zone IANA et une heure locale ; `DELETE` le désactive. Le dispatcher
PostgreSQL lit au moment de l'échéance les tâches créées et terminées et les
runs réussis/échoués du **jour local précédent**. Il fige ces quatre comptes
dans une commande gérée, sans transmettre le DSN au processus enfant. Le
résultat figure dans le run et `schedule_history` contient la soumission et
l'état terminal. Un passage qui chevauche un run du même calendrier avance à
l'échéance suivante avec une trace `skipped`, sans seconde exécution. Les
échecs et une interruption épuisant ses tentatives produisent respectivement
`failed` et `timed_out` dans l'historique. Aucun `MEMORY.md`, note partagée ou
fichier Dropbox n'est écrit.

## RepoWise

`POST /api/v1/automation/jobs/repowise` soumet un run par dépôt/révision,
avec un intervalle minimal de 24 h entre deux réussites sur la même révision.
Le wrapper refuse un dépôt sale ou dont `HEAD` a changé, appelle `repowise
status --format json --no-workspace`, lance au besoin `update --index-only
--no-docs --no-workspace`, puis vérifie que le commit indexé correspond.
L'actualisation est forcée après le seuil de 24 h. Le résultat expose le
nombre d'omissions quand RepoWise le fournit, sinon `coverage_known=false` ;
une simple empreinte alignée ne prouve donc pas une couverture exhaustive.
La qualification exécute le wrapper et le run avec un faux exécutable et un
dépôt temporaire. L'index réel n'est jamais une fixture de test.

## Traces, contrôle et limites

Les runs sont `execution_ready=true`, à durée bornée, et portent acteur,
projet, type de job et clé d'idempotence. `events` reçoit la soumission et
le résultat terminal des jobs Git/RepoWise dans la même transaction que le
run. `schedule_history` reçoit le résultat terminal des runs planifiés.
Les chemins d'annulation et de reprise après expiration du heartbeat sont
également raccordés. L'environnement des processus retire
`DEVCORE_DATABASE_URL` ; aucun secret PostgreSQL n'est mis dans les commandes.

La [politique de sauvegarde candidate](team-backup-maintenance-policy-2026-10-19.md)
décrit le périmètre, la rétention, l'empreinte et la restauration de contrôle.
La maintenance historique et sa purge ne sont pas activées. Le DDL des hooks
de phase 1, les nouvelles routes et planifications, les nouveaux scripts et
les déclencheurs Git ne sont pas encore déployés sur `DevCoreGlobal`. Les
profils réels, le binaire RepoWise réel, les ACL et l'essai de restauration
restent à qualifier à la bascule de phase 5. Le Cockpit ne projette pas encore
ces traces : c'est l'objet de la phase 4.
