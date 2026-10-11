# Inspection des occurrences scheduler non résolues

`DEV_CORE/Scheduler/inspect_claims.py` inspecte une base explicitement choisie,
sans charger les racines DevCore ni initialiser une base. Il ne relance aucun job,
ne supprime aucun claim et ne modifie aucun statut.

Exemple sur une base de recette ou un snapshot validé :

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe' -I `
  DEV_CORE/Scheduler/inspect_claims.py `
  --database 'C:/recette/scheduler.db' --limit 50 --after-id 0
```

Seules les lignes `running` et `error` sont retournées, par ID croissant.
Si `has_more` vaut true, utiliser `next_after_id` pour la page suivante. Chaque
page est un snapshot de lecture ; des changements concurrents peuvent intervenir
entre les pages. Les statuts `ok` et `skipped` ne figurent pas dans ce diagnostic.

La limite accepte 1 à 100 lignes. Les champs texte sont coupés côté SQLite et
`truncated_fields` indique ceux qui sont incomplets. Le curseur repose sur l'ID,
pas sur le texte potentiellement tronqué. Les erreurs peuvent contenir des données
sensibles : limiter l'accès au rapport et vérifier avant de le partager.

Lecture SQLite `mode=ro` et `query_only`, attente de verrou limitée à une seconde,
contrôle de durée du travail SQL à deux secondes par progress handler. Ce contrôle
ne préempte pas un appel système bloqué. Base absente, format/schéma invalide ou
verrou refusé : erreur JSON sur stderr et code 1 ; jamais un résultat vide de repli.
Les erreurs d'arguments sont celles d'argparse (code 2).

Seul le mode journal DELETE du scheduler est pris en charge. WAL est refusé avant
connexion : SQLite peut créer des fichiers partagés même en lecture seule. Ne pas
changer le mode journal pendant l'inspection. Ne pas copier naïvement une base
active : le snapshot doit être produit par une procédure de sauvegarde cohérente.

## Avant une résolution

- Vérifier l'identité et la fin du processus concerné : `running` ne prouve pas
  qu'il est orphelin. L'âge du claim seul ne suffit pas.
- Vérifier les effets externes de l'occurrence : une commande peut avoir réussi
  alors que son résultat n'a pas pu être enregistré.
- Conserver la preuve de la décision de résolution et l'identité de l'opérateur.

## Résolution locale explicite

`resolve_claim.py` accepte uniquement `confirm-success` (effets vérifiés, statut
`ok`) ou `skip` (décision explicite de ne pas exécuter cette occurrence, statut
`skipped`). Aucun retry ou effacement. Exemple sur une base de recette :

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe' -I `
  DEV_CORE/Scheduler/resolve_claim.py --database 'C:/recette/scheduler.db' `
  --claim-id 1 --expected-status running --action confirm-success `
  --evidence 'Référence de la preuve des effets vérifiés'
```

Conditions : toutes les anciennes instances arrêtées, tous les participants
utilisent le nouveau guard OS ; base nommée `scheduler.db` et verrou standard
`scheduler.lock` dans le même dossier. Un scheduler utilisant un autre verrou
n'est pas couvert. Le bail doit être expiré/absent et le guard disponible ; ne
pas effacer le bail ou le guard pour forcer le passage. La disparition du bail
seule ne prouve pas l'arrêt d'un ancien worker ne respectant pas ce protocole.

Le statut attendu protège contre une nouvelle résolution après modification.
La justification (1 à 4096 octets UTF-8) est enregistrée avec l'ID du claim, sa
clé, les statuts avant/après, la date UTC, le compte local déclaré et le PID.
Audit et statut sont publiés dans une transaction unique ; une erreur annule
les deux. Les détails d'exécution initiaux sont conservés. Aucun changement de
jobs.json : le prochain cycle pourra avancer une occurrence désormais terminée.

La reprise d'un résultat `ok`/`skipped` déjà enregistré restaure `last_run_at`,
`last_status` et `last_error` avant de calculer la prochaine échéance. Un succès
compte une fois si son marqueur `last_run_at` n'était pas déjà publié ; un skip
ne compte pas comme succès. Compteur, marqueur et prochaine échéance sont
publiés ensemble dans le JSON atomique. Si cette publication échoue, la reprise
repart du registre persistant sans répéter la commande. Cela couvre un résultat
SQLite publié suivi d'un échec JSON ; ce n'est pas une transaction commune des
deux magasins ni une garantie d'exécution unique d'effets externes.

## Bornes de planification par intervalle

Les intervalles acceptés sont des minutes entières de 1 à 525600 (365 jours).
Le modèle refuse une expression invalide avant l'exécution, même si le registre
contient déjà une échéance. Un modèle modifié en mémoire est également revérifié
au calcul. Les intervalles supérieurs à cette borne doivent être revus avant
activation ; aucun ajustement automatique n'est appliqué aux données existantes.

`skip` avance directement au premier slot strictement futur, avec calcul
arithmétique depuis le dernier slot. `run_once` sélectionne le plus récent slot
manqué dans la fenêtre historique de 30 jours, sans troncature à 1000 slots.
`catch_up` choisit le premier de cette même fenêtre. Quand le dernier slot est
antérieur à la fenêtre, l'ancrage reste sa borne de 30 jours, comme auparavant.
Le calcul ne parcourt plus toutes les minutes du retard. La liste de consultation
`get_missed_interval_slots` conserve son plafond historique de 1000 éléments et
ne sert plus à déterminer l'échéance des intervalles.

Cela ne qualifie pas les politiques cron ni toutes les ambiguïtés DST : la
sémantique locale des durées est conservée. Date hors plage, timezone invalide
ou autre erreur de calcul restent des échecs, sans succès implicite. Quotas de
rattrapage, admission multiutilisateur et durée du cycle complet restent ouverts.

## Validation du registre

Types de planning limités à cron/interval/once ; politiques limitées à
skip/run_once/catch_up. Expression bornée à 256 caractères, syntaxe cron
contrôlée avec le croniter installé, date once ISO parsable. Une dépendance
croniter absente est une erreur, sans planning vide de repli. Timezone explicite
valide, dates d'état ISO parsables (128 caractères maximum) et compteur entier
positif ou nul exigés. Une définition statique invalide refuse la synchronisation
et conserve le registre précédent ; une entrée dynamique invalide refuse le
cycle avant toute commande. Aucun nettoyage automatique de l'ancien état.

Pour les anciennes dates sans timezone, la comparaison les interprète en UTC,
comme le contrat existant. Leur représentation utilisée dans la clé d'occurrence
reste conservée ; une date avec offset conserve également sa représentation.
Changer la timezone de comparaison ne doit pas transformer un claim déjà
enregistré en nouvelle occurrence. L'unicité ne canonicalise pas toutes les
écritures ISO équivalentes : migration globale des clés non réalisée.

La recherche cron reçoit une limite explicite de huit années entre occurrences.
Un calendrier sans occurrence dans cet horizon peut donc être refusé au calcul ;
aucun dépassement silencieux ni résultat vide de succès. Cela borne l'horizon de
recherche, pas un temps mural absolu. La validation syntaxique ne prouve pas que
tout calendrier a une occurrence ni ne qualifie tous les scénarios DST.
Le cron `run_once` recherche directement la dernière occurrence, inclusive à
l'instant courant et strictement après le dernier slot/la borne des 30 jours.
Il ne dépend plus de la liste historique tronquée à 1000 éléments. Sans occurrence
dans cette fenêtre, il choisit un slot futur depuis le plus tardif de now/last_run,
sans retourner une ancienne occurrence antérieure à la fenêtre. Un calendrier
avec année future explicite peut ne pas avoir d'occurrence précédente : l'absence
de résultat dans l'horizon arrière conduit alors à la recherche future bornée.
Cela ne constitue pas une qualification générale DST, ni des effets externes.

## Limites de l'administration locale

Le compte local est une métadonnée issue de getpass, pas une identité API
authentifiée ni une attestation SID Windows. Cet outil de maintenance dépend
des permissions locales de l'opérateur ; il ne constitue pas l'administration
multiutilisateur qualifiée. Les preuves externes ne sont pas vérifiées par le
programme. L'audit SQLite n'est pas un registre inviolable. Base absente, WAL,
bail invalide/actif, guard occupé, claim absent/changé ou échec SQL : refus.

Une transaction commune historique/registre, l'identité administrative forte et
la qualification opérationnelle restent ouvertes. Aucun achèvement automatique
n'est autorisé par le simple résultat de l'inspecteur. Les releases figées ne
sont pas reconstruites par ces ajouts.
