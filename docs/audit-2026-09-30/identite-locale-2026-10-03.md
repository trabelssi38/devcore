# Profil d'identité individuel — recette locale

État : implémenté et testé sur fixtures ; aucun service actif basculé.
Ce parcours couvre les clients Bearer et une page de tâches avec connexion par
identifiant/mot de passe. Le rôle administrateur d'instance a un canal de
[recette en console](administration-locale-2026-10-03.md) ; son exploitation et
l'adaptateur PostgreSQL restent ouverts en L3/L4. Le stockage SQLite séparé sert à qualifier
les règles et la révocation, sans migrer la base métier active.

## Droits qualifiés

| Rôle dans le projet | `task.read` | `task.mutate` | `context.read` |
| --- | --- | --- | --- |
| lecteur (`reader`) | oui | non | oui |
| contributeur (`contributor`) | oui | oui | oui |
| responsable (`owner`) | oui | oui | oui |

Le jeton possède une liste explicite de projets et d'actions. L'émission refuse
un périmètre qui dépasse les droits actuels ; chaque requête revérifie compte,
expiration, révocation, portée du jeton et appartenance au projet. Une promotion
ne donne pas de nouvelles actions à un ancien jeton ; une rétrogradation ou
suppression d'appartenance retire les droits concernés à la requête suivante.

Les jetons aléatoires de 32 octets sont enregistrés par empreinte SHA-256, avec
identifiant, émission et expiration. Durée par défaut : une heure, minimum une
minute, maximum un jour. Le provisionnement local explicite peut révoquer un
jeton ou désactiver un compte. Aucun jeton commun ni compte implicite n'est créé
par le profil individuel.

## Recette et activation ultérieure

Ne pas charger cette configuration sur l'instance courante avant la bascule.
Les tests créent et approvisionnent les magasins dans des racines temporaires.
Pour préparer un magasin de recette **explicitement choisi**, la CLI est :

```powershell
$taskPython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$taskStore = '<racine-absolue-locale-de-recette>/Security/individual_identity.db'
$taskSecret = '<répertoire-absolu-local-existant>/alice-token.json'
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore init
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore add-user --user alice
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore grant --user alice --project alpha --role reader
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore issue-token --user alice --project alpha --action task.read --output $taskSecret
```

Les projets/données métier de recette doivent aussi exister. Le fichier du
secret est créé exclusivement : aucun écrasement, aucun jeton sur stdout. Sous
Windows, les ACL du répertoire et du compte de service restent à qualifier ;
`mode=0600` n'est pas une validation des permissions Windows. Conserver magasin
et secrets hors Git et Dropbox.

Le profil HTTP se sélectionne avant le lancement/import :
`DEVCORE_DASHBOARD_AUTH_PROFILE=individual` et
`DEVCORE_IDENTITY_STORE=<chemin absolu du magasin>`. Le profil par défaut reste
`legacy` pendant la migration. L'exemple `Config/local-team.env.example` ne
modifie pas l'environnement des services existants.

## Surface HTTP de ce profil

- `/api/status` reste public et ne retourne aucune donnée projet.
- `GET /api/dashboard/tasks?project=...` exige `task.read`.
- `POST /api/done` et `DELETE /api/delete` exigent `task.mutate`, un projet
  explicite et une version attendue positive. Le contrôle de version reste dans
  la transaction du service métier.
- HTML historique, projections globales, paramètres, SSE, recherche et routes non qualifiées
  sont fermés avec 403 ; ils ne sont pas filtrés par une simple heuristique.
- Les requêtes Bearer de tâches avec Origin restent refusées. Le backend de
  sessions décrit ci-dessous permet les cookies avec une origine contrôlée
  et un nonce CSRF ; aucun jeton n'est injecté dans HTML.
- Magasin absent/incompatible : 503, aucune création ni repli vers le jeton
  commun. Jeton invalide/expiré/révoqué : 401 ; droit absent : 403.
- Requêtes mutantes limitées en octets déclarés et reçus, y compris sans
  Content-Length. Recherche d'identité exécutée dans un thread : le test d'une
  recherche retardée vérifie que `/api/status` continue de répondre.

## Backend de sessions ajouté le 3 octobre

Migration explicite v1→v2 du magasin de recette :

```powershell
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore upgrade-sessions
```

HTTP ne migre jamais le magasin. `POST /api/auth/session`, avec Bearer
individuel, JSON `{project: ...}` et Origin concordant, crée une session liée
à ce projet et au jeton source. Le cookie `devcore_session` est HttpOnly,
SameSite=Strict, sans Domain et avec Secure sous HTTPS. HTTP est accepté
uniquement en loopback. Sa durée maximale est de trente minutes, bornée aussi
par l'expiration du jeton source. L'échange remplace et révoque le cookie
précédent présenté ; une valeur précédente malformée n'empêche pas une nouvelle
authentification valide.

`GET /api/auth/session` permet de reprendre utilisateur, projet, expiration,
nonce CSRF et actions actuellement autorisées. Ces actions résultent du contrôle
commun du jeton et de l'appartenance ; leur affichage ne remplace jamais les
contrôles sur une mutation. La session brute reste uniquement dans le cookie HttpOnly et son
empreinte en base. Le nonce est un HMAC lié au secret de cette session ; les
mutations et `DELETE /api/auth/session` exigent un Origin concordant et ce nonce
dans `X-CSRF-Token`. La déconnexion révoque aussi le cookie côté serveur, ce qui
refuse son rejeu. Les données/session retournées portent Cache-Control=no-store.

Chaque accès revérifie également l'état du compte, le jeton source et les droits
courants. Révocation du jeton ou rétrogradation s'appliquent à la requête suivante.
Tests avec deux clients HTTP à cookies indépendants : droits croisés, CSRF
absent/étranger, origine étrangère, rotation, déconnexion/rejeu, durée bornée et
Secure sous HTTPS. Ces clients ne vérifient pas le comportement d'un navigateur
réel vis-à-vis de SameSite/HttpOnly. La recette navigateur ajoutée ensuite est
décrite ci-dessous ; elle ne qualifie pas les scénarios cross-site ou HTTPS.

Références de conception : [OWASP, CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
et [OWASP, sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
Elles ne constituent pas une certification du déploiement.

## Page individuelle ajoutée ensuite

`GET /project` sert une coquille publique et `GET /project.js` son script ; ces
routes restent fermées dans le profil historique. Aucun utilisateur, projet,
tâche ou secret n'est injecté dans la page. CSP avec scripts et connexions limités
à la même origine, anti-embedding, no-referrer, nosniff et no-store.

La première version demandait projet et Bearer individuel ; la page demande
maintenant identifiant et mot de passe (voir ci-dessous). Un rechargement reprend la session
par cookie ; utilisateur, projet et droits viennent ensuite du serveur. Les
tâches sont paginées par vingt et rendues avec textContent. Le lecteur n'a pas
de boutons de mutation ; une version absente ou hors plage JavaScript les
désactive. Clôture/suppression envoient le projet et la version affichés, avec
nonce CSRF ; un 409 recharge la liste sans rejouer la mutation. Un 403 rafraîchit
les droits ; un 401 efface les données affichées et demande une reconnexion.

Preuves locales : neuf tests Python sessions/HTTP, dix scénarios exécutant le
script livré sous Node avec DOM/HTTP simulés, deux contrats PowerShell. Dans le
navigateur intégré, instance temporaire sur 127.0.0.1:20239 : connexion Alice,
rechargement avec session reprise, conflit de version sans clôture, texte HTML
inerte, rétrogradation en lecture, révocation avec effacement, connexion Bob
sur beta, déconnexion puis rechargement sans session. Capture de recette :
[lecture seule](interface-projet-lecture-2026-10-03.jpg). Le serveur et l'onglet
ont été arrêtés ; les jetons temporaires en clair ont été supprimés.

Cette recette utilise un navigateur avec des comptes successifs. Deux clients
HTTP indépendants restent la preuve de concurrence entre comptes ; deux profils
de navigateur distincts et la protection cross-site complète restent à tester.
Le parcours Bearer reste disponible pour l'échange API, sans champ dédié dans la page.

## Connexion par mot de passe — schéma v3

Le magasin passe explicitement de v2 à v3 avec `upgrade-passwords` ; HTTP ne
migre jamais une base. Les comptes et appartenances restent provisionnés par
le canal local, sans inscription publique. `set-password` et `reset-password`
exigent un terminal interactif et deux saisies masquées concordantes. Le repli
de getpass vers une saisie affichée est refusé. Aucun argument, variable
d'environnement ou fichier de mot de passe n'est proposé par la commande.

```powershell
# $taskPython et $taskStore désignent la recette, pas le magasin actif.
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore upgrade-passwords
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore set-password --user alice
# Récupération par l'opérateur local : remplace le secret et invalide les accès antérieurs.
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore reset-password --user alice
# Un compte désactivé reste désactivé après reset ; réactivation distincte si requise.
& $taskPython DEV_CORE/Scripts/manage_local_identity.py --store $taskStore enable-user --user alice
```

Hachage par `argon2-cffi` 25.1.0 et bindings 26.1.0, Argon2id avec le profil
RFC_9106_LOW_MEMORY explicite : mémoire configurée 65 536 KiB, trois passes,
quatre threads, sel aléatoire. Ce sont les paramètres du hash, pas une mesure
du pic mémoire total ou une garantie de débit. Mot de passe de 15 à 256
caractères, Unicode et espaces conservés, sans troncature ni règle de composition.
Un compte inconnu fait une vérification sur un hash factice et ne crée pas de
ligne ; mauvais secret/compte inconnu/désactivé renvoient la même erreur HTTP.

Après cinq échecs, les nouveaux logins du compte sont refusés pendant soixante
secondes. Compteur/délai persistés ; les autres comptes et sessions déjà admises
ne sont pas bloqués. Deux vérifications simultanées par processus au maximum ;
excès refusé avec 429 et Retry-After, sans attente de place. Vérification et
rehash hors verrou d'écriture, exécutés dans un thread par la route asynchrone.
Un test avec deux vérifications suspendues conserve `/api/status` sous 0,5 s.
Cela ne qualifie pas la résistance à un déni de service réseau distribué.

Après vérification, la transaction relit version/hash du mot de passe, état
du compte et appartenance. Reset/désactivation/retrait de droit survenus pendant
la vérification empêchent l'admission. La source interne à portée projet et la
session sont créées dans la même transaction ; aucun Bearer brut n'est livré.
La page reçoit le cookie HttpOnly et le nonce CSRF comme auparavant. Un reset
révoque toutes les sessions et tous les jetons du seul compte concerné, sans
changer ses rôles ni réactiver un compte désactivé. Les accès déjà admis à une
opération métier restent hors de cette garantie de révocation immédiate.

La dépendance est ajoutée au manifeste Python et au verrou avec hashes, sans
changer les versions déjà verrouillées. Recette Python 3.13 : paquets Argon2
installés uniquement dans `E:/DevCoreRuntime/recipes/devcore-auth-py313-20261003/packages`,
chargés via PYTHONPATH avant les tests/serveur temporaires. Le runtime installé
actif n'a pas été modifié. La CI prévoit désormais la suite d'identité et les
scénarios JavaScript avec Node 24 explicite ; sa réussite distante reste à établir.

Parcours navigateur temporaire : mauvais secret refusé, Alice connectée puis
session reprise, champ du secret vide après l'envoi, reset local invalidant le
cookie, reconnexion avec le nouveau secret, Bob sur beta et logout/rechargement
sans session. [Capture sans secret](connexion-mot-de-passe-2026-10-03.jpg).
La saisie getpass sur une vraie console Windows et les ACL NTFS de l'opérateur
n'ont pas été qualifiées : ce canal de récupération n'est pas déclaré prêt
pour une équipe en exploitation.

Références primaires : [API Argon2](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[paramètres](https://argon2-cffi.readthedocs.io/en/stable/parameters.html),
[OWASP, authentification](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).

## Audit des clôtures et suppressions individuelles

Le profil `individual` transmet désormais un RequestContext construit à partir
du principal admis par le middleware. Les champs actor/user_id/trace_id d'un
JSON et les en-têtes d'identité libres ne définissent jamais l'auteur. Pour un
cookie, seul l'identifiant non secret de la session est conservé ; un Bearer
individuel est enregistré sans son secret ni son identifiant de credential.

TaskService insère dans `audit_log` l'auteur, le projet, l'identité de tâche,
l'action `task.complete` ou `task.delete`, la trace générée côté serveur et les
statuts/versions avant et après. Cette insertion précède le commit de la
mutation ; journal absent ou rejetant l'insertion : la tâche et sa version
sont annulées. Les refus d'accès, conflits et tâches absentes ne produisent
pas d'entrée de succès. Aucun titre, corps de requête, mot de passe, cookie,
nonce CSRF ou jeton n'est sérialisé dans ces détails.

Le contexte du service est fourni par un adaptateur de confiance ; il ne
constitue pas une ACL pour les appels Python directs. Les appels historiques
sans contexte restent compatibles et non audités. L'API v1, les autres
mutations/canaux et les journaux des refus restent à couvrir. Les clients
CLI/MCP individuels utilisent désormais cet audit serveur via HTTP ;
l'administration dispose d'un audit séparé dans son magasin privé.
La [consultation HTTP](consultation-audit-2026-10-03.md) des tâches est qualifiée
sur fixtures, réservée au responsable ; ses lecteurs CLI/MCP/Cockpit restent ouverts.
Ce journal SQLite n'est pas un stockage inviolable par l'opérateur
du poste ; archivage/rétention/protection et adaptateur PostgreSQL restent
à qualifier. Le bus d'événements existant reste publié après commit : la
garantie transactionnelle porte ici sur tâche + audit, pas sur l'outbox L5.

## Limites avant qualification équipe

API v1, CLI/MCP et autres ressources ne consomment pas encore ce fournisseur.
Le profil individuel expose seulement la page de tâches ; les pages globales
restent fermées jusqu'à une projection autorisée. L'auteur est audité pour les
clôtures/suppressions individuelles ; l'audit de chaque mutation reste ouvert.
Les garanties de révocation d'une opération déjà admise puis bloquée ne sont pas
qualifiées ; les essais portent sur la requête suivante. Administration Web/API,
qualification NTFS/console de la récupération et deux navigateurs indépendants, droits sur
workflows/artefacts/export/mémoire/SSE, RLS PostgreSQL et permissions du poste
restent requis. Le profil historique conserve ses limites déjà recensées.
