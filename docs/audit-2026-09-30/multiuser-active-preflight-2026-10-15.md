# Préflight du pilote multiutilisateur sur le profil actif — 15 octobre 2026

## Résultat

Le service `DevCoreIndividual` et `postgresql-x64-17` sont `Running` et en
démarrage automatique. Le service écoute en localhost sur `20129` ;
`/api/status` et `/project` répondent `200`. Une lecture anonyme de
`/api/dashboard/tasks?project=devcore` répond `401`.

Contrôle PostgreSQL en transaction `READ ONLY` avec le rôle applicatif :
quatre comptes actifs, 60 appartenances réparties entre 29 projets, cinq
sessions enregistrées mais aucune encore valide. Trois comptes n'ont pas de
mot de passe enregistré ; le quatrième est l'identité importée. Deux comptes
`codex-smoke-*` possèdent chacun une appartenance au projet `devcore`.

`GET /api/auth/session` sans cookie répond actuellement `500`. Le journal du
service montre `AttributeError: 'NoneType' object has no attribute 'encode'`
dans la version déployée de `postgres_browser_sessions.session_info`. La
source du dépôt contient déjà le contrôle qui lève `AuthenticationRequired`
pour un secret absent. Un test de régression ciblé a été ajouté et passe sous
Python 3.13 (`1 passed`). La release v250 en service reste plus ancienne et
doit être reconstruite et qualifiée avant remplacement.

## Limites et suite

Aucune tâche, appartenance, session ni donnée active n'a été modifiée pendant
ce préflight. Aucun secret de connexion n'a été affiché. Les sondes HTTP
anonymes et les requêtes SQL de lecture ne constituent pas la qualification
à deux utilisateurs. Le pilote doit continuer sur des racines et des données
de test isolées, puis être rejoué avec deux connexions humaines sur la release
corrective installée. Le déploiement nécessite une sauvegarde restaurable et
un retour arrière de service préparé. Les essais d'écriture ne doivent pas
prendre l'historique actif comme fixture.

## Candidate corrective v251 — préparée, non activée

La release v250 a été copiée dans le même runtime, sous
`E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v251`.
Un seul module installé et son wheel correspondant ont reçu le garde de
`session_info`; les empreintes du wheel, du manifeste, de la provenance et du
`RECORD` installé ont été recalculées. Le wheel SHA-256 est
`18ddf3e1ac443577e3f8eabd41acb35cad90a77d6d892e62a975b158760fb979`.

L'attestation `verify_engine_release.py` passe (88 fichiers moteur). Le profil
de service trouve les racines et le magasin d'identité requis. En ASGI isolé,
avec racines temporaires et URL PostgreSQL factice, `/api/status` répond `200`,
`/api/auth/session` sans cookie répond `401` et la lecture anonyme des tâches
répond `401`. La release v250 active n'a pas été arrêtée ni modifiée.

Le shell de travail n'a pas le rôle Windows Administrateur. La bascule avec
sondes et repli automatique est préparée dans
`DEV_CORE/Scripts/cutover_service_v251_elevated.ps1`. La première invocation
par l'opérateur depuis Windows PowerShell 5.1 s'est arrêtée avant toute
modification du service à cause d'une restriction PowerShell 7 inutile. Le
script a été corrigé et sa syntaxe ainsi que ses sondes HTTP ont été vérifiées
sous Windows PowerShell 5.1 (`200` pour le statut actif, `500` pour la route
défectueuse active). Il peut être relancé depuis un PowerShell élevé. Le
résultat et l'état du service devront être vérifiés avant le pilote réel.

La deuxième invocation par l'opérateur a passé l'attestation de la release,
mais la v251 n'a pas ouvert son listener HTTP. Le script v250 appelé pour la
bascule a tenté le retour arrière ; sa propre sonde a échoué pendant le
démarrage, mais la vérification indépendante suivante a confirmé v250
`Running`, son binaire SCM d'origine, le listener `127.0.0.1:20129` et
`/api/status` ainsi que `/project` à `200`. `/api/auth/session` était encore
à `500`, conformément au défaut v250. Aucune preuve de bascule v251 réussie.

Diagnostic : le préflight de la candidate refusait dix fichiers `.pyc` créés
dans le bundle par l'essai ASGI isolé. Ces dix fichiers hors manifeste ont
été retirés de la seule candidate ; aucun fichier déclaré du bundle n'était
manquant. Le préflight `launch_individual_candidate.py --check` passe à
nouveau sur le profil réel, et le bundle contient maintenant zéro fichier
hors manifeste. Le script de bascule a été renforcé pour exécuter ce
préflight **avant** d'arrêter v250. Sa syntaxe passe sous PowerShell 5.1.

## Bascule v251 et pilote PostgreSQL synthétique — réussis

La troisième invocation élevée a passé le préflight, l'attestation et la
bascule SCM. L'opérateur a reçu `v251_authfix_cutover_verified` ; une sonde
indépendante confirme `DevCoreIndividual` `Running`, démarrage `Auto`, binaire
v251, `/api/status` et `/project` à `200`, `/api/auth/session` sans cookie à
`401`. La lecture anonyme des tâches répond également `401` dans le résultat
de bascule. Aucun retour arrière n'a été nécessaire pour cette invocation.

Un PostgreSQL 17.11 distinct a été initialisé dans une racine temporaire hors
Dropbox, écoutant seulement `127.0.0.1:55435`. Seules des données synthétiques
ont été insérées : deux comptes `alice` et `bob`, deux projets `alpha` et
`beta`, chacun avec sa tâche `T-01`. Via l'API ASGI de la release v251 :

- connexions par mot de passe : `200` pour chaque compte ;
- lectures de leur projet : `200` et une seule tâche `T-01` de leur projet ;
- lectures croisées : `403` dans les deux sens ;
- deux transitions `pause` concurrentes : `200` chacune ;
- répétition avec l'ancienne version : `409` ;
- vérification SQL : les deux tâches sont `paused` en version 2, avec un audit
  et un événement chacune ;
- déconnexion : `200`, puis accès révoqué `401` pour chaque session ; les deux
  sessions sont marquées révoquées en PostgreSQL.

Le serveur PostgreSQL de test a été arrêté ; son port ne présente plus de
listener. Aucun compte ni aucune tâche de la base active n'a servi de fixture.
Le test valide l'adaptateur PostgreSQL et l'isolation dans un processus ASGI ;
il ne prouve pas encore deux navigateurs humains sur l'installation active,
la charge de vingt sessions, CLI/MCP/SSE, ni un accès depuis un autre poste.
Le profil actif ne disposait au préflight que d'un compte avec mot de passe ;
un deuxième utilisateur réel reste à provisionner pour ce parcours final.

## Charge synthétique — gate de réactivité ouverte

Le même PostgreSQL synthétique a été relancé pour mesurer 20 sessions et 200
lectures de tâches, avec 20 refus inter-projets et 20 déconnexions réussies.
Sur l'ASGI en processus, la médiane était 1 271,71 ms et le p95 observé
1 724,58 ms. Une sonde de référence à une session et 20 lectures a donné
84,96 ms de médiane et 195,39 ms de p95 ; à cinq sessions et 50 lectures,
297,42 ms de médiane et 382,11 ms de p95.

Pour écarter un biais propre au client ASGI en processus, un serveur HTTP
Uvicorn isolé a été démarré sur `127.0.0.1:20139`, avec les mêmes comptes et
la même base synthétique. Ses 20 sessions et 200 lectures ont produit une
médiane de 1 277,45 ms et un p95 de 1 585,96 ms ; les 20 refus croisés et
20 déconnexions ont réussi. La cible de la matrice L9 est p95 inférieur à
300 ms sous charge cible : **ce critère n'est pas atteint** dans ce banc.
La cause et l'optimisation restent à qualifier ; les lectures ouvrent au
moins une connexion PostgreSQL pour l'autorisation et une autre pour la
projection. Les deux listeners de test, `20139` et `55435`, ont été arrêtés.
Ces mesures ponctuelles ne sont pas une mesure des performances du service
actif avec des comptes humains.

Une micro-mesure sur le même PostgreSQL synthétique donne 33,3 ms de médiane
et 141,8 ms de p95 pour ouvrir une nouvelle connexion et exécuter `SELECT 1`,
contre 0,09 ms et 0,18 ms sur une connexion réutilisée. Un prototype borné de
réutilisation des connexions, avec contexte RLS limité à la transaction et
retour sans contexte visible, a ramené le banc ASGI de 20 sessions et
200 lectures à 720,78 ms de médiane et 1 039,87 ms de p95. Le critère de
300 ms reste donc manqué. Ce prototype a été retiré du code courant et n'a
jamais été installé ; la release active demeure v251. Une optimisation plus
complète et son contrôle d'isolation restent à concevoir et qualifier.

## Préparation du deuxième compte réel

L'utilisateur a désigné `mohd` pour le pilote `devcore`. Lecture seule de la
base active via le rôle applicatif : le projet `devcore` existe et aucun compte
`mohd` n'existe encore. Le service `DevCoreIndividual` est `Running`, en
démarrage automatique ; `/api/status` répond `200`. Le répertoire
`E:/DevCoreRuntime/migration` est limité à Administrateur, Administrateurs et
SYSTEM selon `icacls`.

`DEV_CORE/Scripts/provision_postgres_pilot_user.py` a été préparé pour une
exécution locale interactive avec le rôle PostgreSQL `postgres`. Il impose
d'abord un `pg_dump` complet au format custom, non vide, dont l'inventaire est
lisible par `pg_restore`; il affiche son SHA-256. Il demande ensuite le mot de
passe administrateur puis deux saisies identiques du nouveau mot de passe,
enregistre un hash Argon2 et crée `mohd` avec le seul rôle `contributor` sur
`devcore` dans une transaction. Il refuse de modifier un compte existant et
vérifie les lignes après `COMMIT`. Aucune mutation active n'a encore été faite :
le secret PostgreSQL administrateur n'est pas disponible dans cette session.
Le script passe la compilation Python 3.13 et son aide CLI ; son parcours
administrateur complet devra être attesté par l'exécution réelle. Ensuite,
deux connexions humaines et le parcours d'isolation sont encore à réaliser ;
le gate de réactivité à 20 sessions reste ouvert.

## Première tentative de création de `mohd`

L'opérateur a lancé le script. `pg_dump` a réussi et créé
`E:/DevCoreRuntime/migration/before-pilot-user-mohd-20261015-134041.dump`
(11 181 371 octets, SHA-256
`ad4ea426940cb232ceee1709b70614407bfbab872491c6f27c12e19fd9f623a5`).
L'inventaire `pg_restore -l` est lisible. La double saisie du nouveau mot de
passe était différente ou hors de la plage 12–256 caractères : le script s'est
arrêté avant connexion administrateur et avant insertion. Une lecture seule de
la base active confirme que `mohd` est absent. Le script a été réordonné pour
valider la double saisie avant de lancer la sauvegarde et donner un message
distinct pour divergence et longueur. Nouvelle exécution nécessaire ; le dump
existant est conservé.

## Compte `mohd` provisionné et parcours réel préparé

La seconde invocation du script a créé une sauvegarde complète
`E:/DevCoreRuntime/migration/before-pilot-user-mohd-20261015-134316.dump`
(11 181 371 octets, SHA-256
`cecbdfd5790d8a2071ec22dab959a1a384a02e518cbd71931185cf4fe39df75f`),
puis a retourné `pilot_user_provisioned`. Lecture indépendante avec le rôle
applicatif : `mohd` est actif, possède un hash de mot de passe et une seule
adhésion `devcore/contributor`; aucune session valide `mohd` n'existe encore.
`majdi` est actif, possède aussi un hash et l'adhésion `devcore/contributor`.
La sauvegarde est présente et son empreinte recalculée correspond à celle de
l'opérateur. `DevCoreIndividual` est `Running` et `/api/status` répond `200`.

`DEV_CORE/Scripts/verify_two_real_pilot_users.py` prépare la vérification HTTP
réelle via deux sessions isolées : connexions `majdi` et `mohd`, lectures
`devcore`, refus de `scripts` pour `mohd`, lecture autorisée de `scripts` pour
`majdi`, déconnexions et refus après déconnexion. Les mots de passe sont saisis
localement sans argument ni journal. Ce parcours n'est pas encore exécuté,
car ses deux secrets ne sont pas disponibles dans cette session. La syntaxe
Python 3.13 du script a été contrôlée ; son résultat opérationnel reste à
établir.

## Préparation de la réinitialisation du mot de passe `majdi`

L'opérateur a indiqué avoir oublié le mot de passe `majdi`. Lecture seule de
la base active : compte `active`, hash présent, 29 adhésions de projet et
aucune session valide. Le script local
`DEV_CORE/Scripts/reset_majdi_postgres_password.py` a été préparé. Il valide
deux saisies du nouveau secret avant la sauvegarde complète PostgreSQL,
contrôle l'inventaire du dump, remplace le hash Argon2 de `majdi` et révoque
ses sessions dans une transaction. Il ne modifie ni l'état du compte ni ses
adhésions ; après `COMMIT`, il vérifie le hash, le nombre d'adhésions et
l'absence de session valide. Le mot de passe PostgreSQL administrateur et le
nouveau mot de passe seront saisis localement. La syntaxe Python 3.13 et le
refus d'une double saisie divergente avant `pg_dump` ont été vérifiés avec des
racines temporaires. Aucune réinitialisation active n'a encore été effectuée.

## Premier parcours réel : erreur d'attente dans le vérificateur

L'opérateur a exécuté `verify_two_real_pilot_users.py` avec les secrets locaux
de `majdi` et `mohd`. Les connexions et lectures `devcore` ont passé les
assertions, et la session `mohd/devcore` a été refusée sur `scripts` (`403`).
La dernière assertion attendait à tort `200` sur `scripts` avec la session
`majdi/devcore` ; l'API a répondu `403`. Le code de session stocke un seul
projet dans ses métadonnées et refuse un projet différent même si l'utilisateur
possède une autre adhésion. Ce résultat est conforme au contrat ; le défaut
était dans le vérificateur. Son bloc de nettoyage s'est exécuté : lecture SQL
indépendante, zéro session valide pour les deux comptes, cinq sessions
`majdi` et deux `mohd` révoquées au total. Un dump
`before-password-reset-majdi-20261015-135340.dump` est présent ; la sortie du
script de reset n'a pas encore été transmise, donc son résultat exact n'est pas
attesté ici. La connexion HTTP de `majdi` avec le secret saisi a toutefois
réussi.

Le vérificateur a été corrigé : il attend `403` pour la session
`majdi/devcore` sur `scripts`, et ouvre une session distincte `majdi/scripts`
pour attendre `200`. Son flux complet a été vérifié avec un transport HTTP
simulé et des racines temporaires (trois sessions créées et révoquées) ; la
syntaxe Python 3.13 passe. Le parcours réel complet doit être relancé.

## Parcours HTTP réel à deux comptes : réussi

La relance du vérificateur corrigé a retourné
`two_real_users_http_verified`. Avec trois sessions isolées et deux secrets
saisis localement : `majdi/devcore` et `mohd/devcore` lisent chacun leurs
tâches (`200`), `mohd/devcore` est refusé sur `scripts` (`403`), la session
`majdi/devcore` reste limitée à son projet (`403` sur `scripts`), et une session
distincte `majdi/scripts` lit ce projet (`200`). Le script a confirmé les
déconnexions. Lecture SQL indépendante après l'essai : zéro session encore
valide pour les deux comptes ; les adhésions `majdi/devcore`, `majdi/scripts`
et `mohd/devcore` sont conformes. Le service répond toujours `200` sur
`/api/status`. Ce résultat qualifie le chemin HTTP réel et ses droits sur ce
poste, sans constituer une recette de deux navigateurs ni une mesure de charge.

## Candidate v252 pour la réactivité PostgreSQL

Sur le PostgreSQL 17.11 synthétique déjà isolé hors Dropbox, un banc de
20 travailleurs et 200 lectures distingue le coût des connexions : avec
`pg8000`, deux connexions par lecture donnent médiane 1 070,36 ms / p95
1 912,41 ms ; une connexion par lecture donne 525,01 / 1 159,03 ms.
L'ouverture seule d'une connexion concurrente donne 441,43 / 1 159,45 ms.
Des connexions réutilisées par travailleur avec contexte RLS limité à la
transaction donnent 7,22 / 144,79 ms sur les requêtes SQL. La comparaison
avec `psycopg` installé seulement dans une racine temporaire confirme la
direction, mais aucun nouveau pilote n'a été ajouté à la release active.

Le code source regroupe l'autorisation du cookie et la projection des tâches
sur une seule connexion `pg8000` réutilisée, avec un pool borné à 20 et un
`rollback` à chaque retour. Le chemin de lecture existant pour les autres
routes et les jetons Bearer demeure distinct. Les tests ciblés de l'identité
et du Dashboard passent (33/33). Sur une base synthétique, la lecture alpha
voit sa tâche ; sans projet, la même connexion ne voit aucune tâche ; le
contexte beta voit sa tâche, puis un nouveau prêt sans projet revient à zéro.

En ASGI sur le code source : isolation `200/403/200`, 20 sessions et
200 lectures après amorçage, médiane 45,82 ms / p95 80,68 ms. Sur Uvicorn
isolé avec le même code : médiane 157,02 ms / p95 236,41 ms. Les 20 premières
lectures d'un pool froid en ASGI donnent médiane 44,77 ms / p95 207,80 ms.

Une release candidate **v252** séparée a été construite par
`DEV_CORE/Scripts/build_v252_perf_candidate.py` à
`E:/DevCoreRuntime/qualification/service-profile-v250-postgres/runtime/releases/devcore-py31316-20261015-postgres-v252`.
Elle contient le Dashboard modifié dans son bundle et une modification limitée
du module installé de session PostgreSQL ainsi que de son wheel/RECORD. Le
manifeste du bundle a l'empreinte
`778be9545d285710212c55a804a14385fe796bd640a5fc6f8887b29b389e400b`,
le wheel `beb938d6932fca5b1cd7f99d814379fef9216129ab83dad6fea7104153eb3b84`
et le manifeste moteur
`e236d8a86ccd7a05b2297fa3bb2c4c70ef9e30ce73bc8dea94dc07253fd7558c`.
L'attestation moteur (88 fichiers), la vérification du bundle et le préflight
du lanceur passent. Sur **le bundle v252 lui-même** via Uvicorn isolé :
isolation `200/403/200`, médiane 155,72 ms / p95 231,63 ms pour
20 sessions et 200 lectures ; sans contexte RLS, zéro tâche avant et après
un prêt sur beta. Statut et shell HTTP `200`, sessions/tâches anonymes `401`.
Les sessions synthétiques ont été supprimées et les listeners de test arrêtés.

Le script `DEV_CORE/Scripts/cutover_service_v252_elevated.ps1` est prêt : il
contrôle les empreintes et le lanceur avant arrêt de v251, puis vérifie le
service et les réponses anonymes, avec repli vers v251 en cas d'échec. Sa
syntaxe PowerShell 5.1 passe. Le shell de travail n'est pas élevé ; le service
réel est encore `Running` sur v251 et `/api/status` répond `200`. La bascule
v252 et sa mesure sur la base active avec comptes humains restent à faire.
La mesure réelle est préparée dans
`DEV_CORE/Scripts/verify_v252_active_load.py` : garde SCM v252 avant toute
connexion, saisie locale des deux secrets, dix sessions par utilisateur,
20 lectures d'amorçage, 200 lectures mesurées via HTTP, refus inter-projets,
puis révocation et contrôle `401` des vingt sessions. Le script a été vérifié
syntaxiquement et refuse bien le service actif v251 avant de demander un
secret. Son exécution réelle attend la bascule v252. Une particularité de
l'encodage Windows de `sc.exe` a été corrigée dans cette garde.

### Préflight refusé puis candidate propre

Le premier lancement élevé de `cutover_service_v252_elevated.ps1` a été refusé
avant l'arrêt du service : `candidate_preflight_refused`. Le diagnostic direct
du vérificateur a identifié dix fichiers `.pyc` créés par le test Uvicorn isolé
dans le bundle v252, absents de son manifeste. Le service est resté `Running`
sur v251. Aucune donnée active n'a été modifiée.

Une copie `devcore-py31316-20261015-postgres-v252-clean` a été produite à partir
de la candidate attestée en excluant uniquement `__pycache__` et `*.pyc` ;
l'ancienne candidate reste conservée. Le script de bascule pointe maintenant
vers cette copie. L'attestation moteur passe (88 fichiers), le préflight du
lanceur passe sur les racines actives en lecture seule, et les empreintes
wheel/bundle restent respectivement `beb938d6932fca5b1cd7f99d814379fef9216129ab83dad6fea7104153eb3b84`
et `778be9545d285710212c55a804a14385fe796bd640a5fc6f8887b29b389e400b`.
Un lancement non élevé du script a atteint le contrôle d'élévation de la
bascule générique après le préflight, sans toucher au service. L'exécution
élevée et la mesure sur la base active restent à faire.

### Bascule v252 vérifiée sur le service actif

L'utilisateur a exécuté `cutover_service_v252_elevated.ps1` dans PowerShell
élevé. Le préflight et l'attestation du moteur passent, puis la bascule SCM
retourne `cutover_verified` et `v252_perf_candidate_cutover_verified`.
Le chemin du service pointe vers `devcore-py31316-20261015-postgres-v252-clean`.
Une vérification indépendante après la commande confirme `Running`, démarrage
`Auto`, `/api/status` et `/project` HTTP 200, et les routes de session et de
tâches anonymes HTTP 401. La mesure avec les deux comptes réels reste ouverte ;
le champ `operationally_qualified=false` dans le rapport de préflight ne doit
pas être interprété comme une qualification finale.

### Charge avec deux comptes réels vérifiée

L'utilisateur a exécuté `verify_v252_active_load.py` sur le service v252 actif
en saisissant localement les mots de passe de `majdi` et `mohd`. Résultat :
20 sessions, 200 lectures, médiane **139,25 ms**, p95 **205,81 ms** et maximum
238,71 ms. La lecture `mohd` du projet `scripts` est refusée en HTTP 403 ;
les vingt déconnexions sont vérifiées. L'objectif initial de p95 < 300 ms est
atteint sur ce parcours réel. Une vérification indépendante après charge
confirme `DevCoreIndividual` v252 et PostgreSQL `Running`, service en démarrage
automatique, `/api/status` et `/project` HTTP 200 et session anonyme HTTP 401.
La recette interactive dans deux navigateurs et les autres gates post-L9
restent distincts de cette mesure.
