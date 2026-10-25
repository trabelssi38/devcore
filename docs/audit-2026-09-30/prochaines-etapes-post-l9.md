# Suivi des étapes après la qualification L9

Date de suivi : 2026-10-18

La qualification locale L9 et le cutover PostgreSQL sont terminés. Le service
`DevCoreIndividual` actif est v254 ; le pilote LAN et sa reprise après
redémarrage ont été vérifiés depuis le second poste le 16 octobre. La checklist
post-L9 complète reste ouverte pour l'observabilité distante et les autres
chantiers hors de la pile globale. La phase « pile globale » est qualifiée.

## 1. Gel et traitement des écritures historiques — terminé pour le profil local

Objectif : préserver une copie cohérente de l'historique, arrêter les écrivains
historiques, puis basculer explicitement vers la source de vérité retenue.

Préconditions :

- inventorier les écrivains et leurs processus sur les deux postes connus ;
- notifier et arrêter les sessions/runs avec la procédure de drain coopératif ;
- produire une sauvegarde horodatée et ses empreintes ;
- valider la réconciliation sur copie, y compris les 268 866 arêtes orphelines,
  les deux projets `needs_review` et les 460 identifiants textuels ;
- obtenir un rapport sans écrivain actif avant toute bascule.

La fenêtre du 14 octobre a produit une capture stable et une restauration de
contrôle. Les arêtes orphelines sont conservées en quarantaine sur copie, les
références de projets réparées, et l'ancienne base corrompue supprimée sur
instruction explicite. Les neuf tâches apparues après le premier import ont
été ajoutées à PostgreSQL le 15 octobre et vérifiées sous RLS. PostgreSQL
reste la seule source transactionnelle active ; Dropbox conserve les documents
historiques et aucune bascule de Dropbox n'est nécessaire pour ce profil.

## 2. Déploiement équipe PostgreSQL réel — terminé pour le profil local

Objectif : installer un cluster PostgreSQL local dédié au profil équipe et
déployer le schéma v2 avec le rôle applicatif sans `BYPASSRLS`.

Ordre d'exécution :

1. installer PostgreSQL et choisir les chemins de données hors Dropbox ;
2. créer la base, le rôle propriétaire de migration et le rôle applicatif ;
3. appliquer le schéma et les politiques RLS ;
4. importer un snapshot gelé en mode dry-run, puis vérifier comptes, projets,
   tâches, versions, runs, événements et audit ;
5. exécuter les tests de concurrence et d'isolation par projet ;
6. basculer l'API vers PostgreSQL uniquement après validation des rapports.

Le cluster local `devcore_qualification_team_20261013`, son rôle applicatif,
le schéma/RLS, l'API et le service SCM v250 ont été qualifiés. Preuves :
`postgresql-cutover-qualification-2026-10-13.json`,
`global-cutover-execution-2026-10-13.json` et
`post-cutover-observation-2026-10-14.json`.

## 3. Activation réseau du pilote qualifiée ; OTLP/Langfuse distant non activé

Objectif : ouvrir l'accès réseau après qualification des identités et de
l'isolation, puis activer l'observabilité distante de façon bornée.

Garde réseau :

- conserver le pilote sur localhost tant que l'authentification multi-utilisateur,
  les ACL par projet et la récupération après panne ne sont pas validées ;
- documenter l'adresse d'écoute, le pare-feu, les origines CORS et les ports ;
- vérifier qu'aucun service de développement n'est exposé par inadvertance.

OTLP/Langfuse :

- configurer un endpoint de recette avec authentification et délai borné ;
- valider redaction, attribution projet/tâche, taille maximale et drainage au
  shutdown ;
- mesurer les files, les pertes acceptées et le comportement lorsque le réseau
  distant est indisponible ;
- l'export Langfuse distant est désactivé par D-009 ; les événements restent
  dans le buffer local borné.
- le pilote v254 écoute uniquement sur `172.16.210.32:20129` en HTTPS, avec
  pare-feu limité au LAN privé et au second poste `10.40.100.2/32`. L'accès
  distant de ce poste et la reprise après redémarrage ont passé les contrôles
  du 16 octobre ; l'ingestion distante n'est pas activée.

## 4. Remise en service coordonnée de la pile globale — reprise Windows vérifiée

Objectif : réactiver le mode global et ses dépendances historiques après la
qualification L9, sans considérer le seul service `DevCoreIndividual` comme
une qualification de la plateforme complète.

Composants à démarrer et vérifier ensemble :

- cockpit global `/index.html` et `/index_terminal.html` ;
- RepoWise (index, serveur local et synchronisation) sur `7337` ;
- Gemini Router sur `20130` ;
- API Gateway sur `20131` ;
- Headroom natif sur `8787` et auxiliaire sur `8789` ;
- Scheduler et ses jobs persistants.

Ordre d'exécution :

1. préparer un lanceur global compatible PostgreSQL, sans initialisation
   SQLite ni relance des anciens services ; enregistrer les PID, ports et
   journaux de chaque composant ;
2. vérifier les endpoints de santé et les identités de route, notamment le
   fournisseur et le modèle réellement utilisés par chaque profil LLM ;
3. vérifier que RepoWise est à jour avec le commit courant avant d'afficher
   ses résultats dans le cockpit ;
4. ouvrir les deux interfaces globales et vérifier leurs API, flux et actions
   sur une copie isolée ;
5. tester l'arrêt, le redémarrage et la reprise du Scheduler et des services
   dépendants ;
6. documenter explicitement les services démarrés automatiquement et ceux
   restant manuels.

Le superviseur candidat a maintenant démarré Router, les deux Headroom,
Gateway et Scheduler PostgreSQL ensemble sur un cluster temporaire isolé.
Leurs PID, ports, sondes et arrêt coordonné sont vérifiés ; le navigateur a
ouvert les deux cockpits et clôturé une tâche fictive. Un second cycle sur
une copie Git propre a inclus RepoWise : index aligné sur le commit servi,
six PID/sondes vérifiés, puis six arrêts coopératifs à code 0. Le dépôt de
travail reste modifié et son propre index n'est pas à jour ; cette première
copie Git épinglée a depuis été remplacée par `ba9f9a9…`.
La tâche Windows `DevCoreGlobal` a été installée avec déclencheur `AtStartup`
et vérifiée en marche avec six composants sains. Sa reprise après redémarrage
Windows a échoué au premier essai du 17 octobre : après le boot de 15:24, la
tâche était `Ready` avec résultat 1 et le manifeste datait d'avant le boot.
Un lancement manuel à 17:25 a rétabli six composants sains, mais ne qualifie
pas le déclencheur automatique. Le lanceur journalise maintenant les phases
d'échec sans secret et cherche RepoWise dans le profil Administrateur même si
`APPDATA` est absent sous S4U. Le second boot de 17:42 a révélé un délai
dépassé pendant le contrôle Git de la source propre ; chaque commande Git
dispose maintenant de trois tentatives bornées à 45 s. Un démarrage manuel
à 18:09 a rétabli les six sondes et cinq ports. Un nouveau redémarrage est
nécessaire pour qualifier `AtStartup`. Le boot de 18:13 a révélé un second
délai fixe, cette fois l'import RepoWise de 10 s dans le superviseur épinglé.
Une copie séparée au commit `525d14a011eacb822ce9005ab670c6250fe83444`
élargit ses délais sans retirer les contrôles ; son index RepoWise est aligné
et la bascule élevée avec retour arrière a réussi. L'action de tâche, le
marqueur, six sondes et cinq listeners ont été contrôlés indépendamment.
Le boot de 21:24 le 17 octobre a passé `global_post_restart_verified` :
déclenchement automatique S4U, six composants sains, cinq listeners au bon
PID, index aligné et route Gemini auxiliaire réelle. Le contrôle indépendant
observe un battement frais après cet appel. Le gate de reprise Windows est clos.
La section « services » du Cockpit équipe lit maintenant les battements et
sondes du superviseur candidat sur copie, refuse un manifeste périmé et
n'affiche que les composants effectivement lancés. Cette supervision est
servie par le Gateway actif sur `127.0.0.1:20131`.
La section « Automation hooks » affiche maintenant les plannings et leur
historique PostgreSQL sous RLS par projet sur la recette ; une session `alpha`
voit ses deux jobs et reçoit 403 pour la projection `beta`. Les commandes des
jobs ne sont pas exposées dans le HTML.

Le lanceur historique `launch_all.ps1` délègue à `launch.ps1`, qui passe par
`PlatformLauncher` et `SystemWatcher` avec `init_db()` SQLite et des relances
automatiques. Son attente de `20129` peut aussi prendre le listener du service
v254 déjà actif pour une preuve de démarrage global. Il refuse maintenant son
lancement lorsque `DevCoreIndividual` est en cours d'exécution. La tâche
`DevCoreGlobal` lance désormais l'orchestration PostgreSQL distincte.

Le moteur de runs possède un adaptateur PostgreSQL, une déduplication des effets
par projet et un contrôle de schéma/RLS au démarrage. Le DDL correspondant est
appliqué à la base active et ce moteur est chargé par le Gateway global.
Le schéma cible et les chemins de tâches/runs ont passé une recette sur un
cluster PostgreSQL temporaire isolé : versions, audit, événements, RLS,
idempotence et routes HTTP principales. Les flux et les dépendances de la pile
ont ensuite été exercés ensemble sous le superviseur.
Les lectures Gateway de contexte enregistré et d'audit paginé ont aussi passé
sur ce cluster, avec refus 403 interprojet, 400 sur curseur invalide et 413 sur
budget insuffisant. Les flux et les cockpits ont ensuite passé une recette
isolée ; la reprise automatique après redémarrage est maintenant vérifiée.
Un flux de notification par projet fondé sur les événements PostgreSQL a
passé une recette isolée avec reprise par curseur et refus interprojet. Les
templates demandent ce flux avec projet explicite. Le rendu `/api/dashboard`
authentifié et les pages `/cockpit` et `/cockpit/terminal` ont ensuite passé
une recette HTTP sur le cluster PostgreSQL isolé : 401 anonyme, 200 pour le
projet autorisé, 403 interprojet. La projection borne les tâches, runs et
événements, échappe les valeurs SQL et affiche explicitement les sections non
raccordées. Les anciennes pages statiques et leurs données multiprojets ne
sont pas servies par ces routes. Les actions de clôture et de suppression
avec cookie, CSRF et version ont ensuite passé un parcours HTTP sur la recette
PostgreSQL. Le contrôle dans le navigateur des deux vues et d'une clôture
fictive a suivi ; les autres sections et les métriques restent à raccorder.
Le service individuel actif reste v254, et le Gateway global est séparé.

Les dix sections du snapshot Cockpit sont raccordées au projet ; les cinq
dernières sources ont été requalifiées par les deux comptes réels après boot.
OpenAI et Anthropic ne sont pas prévus dans ce déploiement : leurs appels réels
sont sans objet pour la clôture. Le contrat de routage natif reste vérifié sur
simulation ; une qualification fournisseur réelle sera nécessaire seulement
si leur usage est activé plus tard.
Le daemon Scheduler historique
initialise SQLite et JSON. Un ordonnanceur PostgreSQL distinct et sa migration
RLS ont passé une recette isolée (dispatch unique, concurrence, arrêt/reprise)
et le daemon est lancé dans la pile active. Les jobs historiques archivés ne
sont pas réactivés implicitement. La sauvegarde complète de la base active et
le DDL atomique ont été appliqués avec succès ; le schéma actif est prêt. Les six
processus globaux tournent sous la tâche de démarrage `DevCoreGlobal`, avec deux
utilisateurs réels vérifiés avant et après ce redémarrage. La reprise après
Windows est vérifiée ; les fournisseurs natifs ne sont pas des gates de ce
déploiement.
Le contrôle Gemini auxiliaire a réussi avec le fournisseur réel
`google-gemini`, l'alias `devcore-summary` et le modèle retourné
`gemini-2.5-flash`, HTTP 200. Après sauvegarde complète vérifiée, le DDL
Cockpit a ajouté les droits `SELECT` et les protections RLS par projet de
`plugins`, `memory_entries` et `budgets` ; l'audit actif ne trouve plus de
manque. La projection réelle a passé sa recette sur PostgreSQL isolé.
La copie Git Cockpit est maintenant servie par la tâche Windows ; les deux
comptes réels ont passé quatre vues Cockpit et l'isolation HTTP sur cette
version avant redémarrage ; leur requalification HTTP après la reprise
automatique a réussi : quatre vues Cockpit à 200, projet croisé à 403 et
sessions révoquées après déconnexion.
Les deux dernières sections Cockpit disposent maintenant d'un candidat de
lecture par projet. L'audit intégral établit l'identité des tables historiques
PostgreSQL avec la candidate graphe scindée : 2 272 nœuds et 696 267 arêtes.
La projection stockée rend 681 642 arêtes `devcore` lisibles et conserve 14 625
arêtes traversant une frontière de projet en quarantaine invisible sous RLS.
L'usage Gemini futur sera enregistré uniquement après un appel authentifié
portant un projet ; les sondes techniques passées restent non attribuées. Les
deux DDL ont réussi une recette PostgreSQL isolée, et le candidat Git propre
`af3b646…` a été servi avec les deux utilisateurs réels et un appel Gemini
attribué au projet. Son premier boot a échoué sur l'import préalable RepoWise
de 90 secondes ; la pile a été relancée manuellement, ce qui ne valide pas
`AtStartup`. Un correctif propre `ba9f9a9…` supprime ce contrôle redondant,
conserve la sonde HTTP réelle et possède 833 pages RepoWise indexées.
Les deux DDL sont appliqués à la
base active avec sauvegardes complètes vérifiées. Le préflight indépendant
confirme 2 272 nœuds, 696 267 arêtes dont 14 625 en quarantaine, et le schéma
d'usage Gemini par projet prêt sous RLS. La tâche globale sert maintenant
`ba9f9a9…` automatiquement après le boot du 18 octobre : six composants sains,
cinq listeners aux bons PID, index RepoWise de 833 pages aligné, Gemini réel
HTTP 200 et battement frais. `majdi` et `mohd` ont chacun passé quatre vues
Cockpit, dashboard et tâches à 200, refus interprojet à 403 et révocation des
sessions après logout sur ce même boot. La ligne d'usage Gemini attribuée à
`devcore` persiste après redémarrage. La phase « pile globale » est close.

`postgresql-x64-17` et `DevCoreIndividual` démarrent automatiquement comme
services Windows. `DevCoreGlobal` démarre automatiquement sous la tâche
`AtStartup/S4U` et supervise Router, les deux Headroom, Gateway, Scheduler et
RepoWise. Les scripts d'audit et les opérations de maintenance restent manuels.
Le démarrage de
`DevCoreIndividual` seul n'active pas la pile globale.


## Contrôle de suivi — 14 octobre 2026

Le contrôle post-bascule a été rejoué sur le poste : `DevCoreIndividual` et
`postgresql-x64-17` sont `Running`, le démarrage du service est automatique et
les sondes `/project` et `/api/status` restent à HTTP 200. Le listener actif du
profil individuel est `127.0.0.1:20129`; les ports globaux `7337`, `8787`,
`8789`, `20130` et `20131` ne sont pas démarrés. Ce résultat confirme le
profil local PostgreSQL et ne clôt pas l'ouverture réseau ni la remise en
service de la pile globale.

Le 15 octobre, le pilote SQLite a également été rejoué avec la release
`l9-runfix` propre : cinq sessions isolées et deux runs concurrents passent.
Deux tests Windows ciblés valident le confinement de l'arbre de processus et
le refus lorsque ce confinement échoue. Cette qualification est sur copie.

La prochaine action autorisée est une surveillance périodique documentée du
profil local. Toute activation du réseau externe, du Scheduler ou des cockpits
globaux doit rester une fenêtre séparée avec preuve de gel, smoke, reprise et
retour arrière.


## Résultat des gates — 14 octobre 2026 (mise à jour après fenêtre de gel)

Le rapport détaillé est [`post-l9-gates-2026-10-14.json`](post-l9-gates-2026-10-14.json).

- **Gel historique : capture et restauration clôturées.** L'utilisateur a
  confirmé l'arrêt de l'autre poste, l'état Dropbox « À jour » et la fenêtre de
  maintenance. La capture est stable et restaurée sur copie ; elle exclut une
  ancienne base corrompue et conserve 268 912 violations FK historiques dans
  le manifeste. La réparation sur copie produit zéro FK résiduelle et conserve
  les arêtes non résolues en quarantaine. La base corrompue explicitement
  désignée a été supprimée ; `devcore.db` reste intacte. La bascule de source
  n'est pas une opération prévue : PostgreSQL v250 est déjà la source active.
  Le contrôle d'empreinte de conservation a été corrigé et validé sur la
  candidate v4. Les neuf tâches historiques manquantes ont été importées dans
  PostgreSQL le 15 octobre, avec numéros 478–486 et contrôle RLS. Voir
  [`post-l9-historical-task-import-2026-10-15.json`](post-l9-historical-task-import-2026-10-15.json).
- **Réseau : qualifié en localhost uniquement.** Le contrat de bind, le Gateway
  et un smoke éphémère de l'API sur `20131` passent sur copies temporaires.
  L'ouverture externe reste fermée selon D-002.
- **Observabilité : contrat local qualifié.** 182 tests Scheduler/OTLP/LLMOps
  passent avec un avertissement de dépréciation tiers. Langfuse distant reste
  désactivé selon D-009.
- **Pile globale : qualifiée sur copies, non activée.** Router, Headroom, Gateway,
  Scheduler, les deux cockpits et RepoWise passent leurs contrôles sur copies
  temporaires. La reprise Windows du profil individuel passe également (`Running`,
  démarrage automatique, cockpit HTTP 200). Les listeners et jobs globaux restent
  arrêtés en opération conformément au profil local.

Le gel, la restauration sur copie et l'import des neuf tâches historiques sont
terminés. L'ouverture réseau reste fermée selon D-002.
La pile globale est qualifiée sur copie, mais son activation reste désactivée.

## Préflight et exécution du gel historique — 14 octobre 2026

Le préflight en lecture seule est consigné dans [`historical-freeze-preflight-2026-10-14.json`](historical-freeze-preflight-2026-10-14.json). Aucun processus DevCore historique n'a été observé sur ce poste et le service actif a été identifié séparément. La fenêtre confirmée a produit la capture locale `E:/DevCoreRuntime/qualification/historical-freeze-20261014-130504` et la restauration de contrôle locale `E:/DevCoreRuntime/qualification/historical-restore-20261014`. Ces dossiers de recette ne sont pas publiés avec la documentation. Aucune source active n'a été supprimée ni remplacée.

## État et décision

Conclusion : le cutover local PostgreSQL et le service individuel sont
`cutover_verified`. La checklist post-L9 complète reste partiellement ouverte
pour l'accès réseau, l'activation distante et la pile globale complète.
Le rapport final de l'import est
[`post-l9-historical-task-import-2026-10-15.json`](post-l9-historical-task-import-2026-10-15.json).
Le compte Windows
`Administrateur` reste l'identité du pilote ; il ne constitue pas un compte de
service restreint.

## Qualification complémentaire — 15 octobre 2026

Le défaut de la release v250 qui retournait HTTP 500 pour `GET /api/auth/session`
sans cookie a été corrigé dans une release v251 attestée. La bascule SCM est
vérifiée ; le service v251 est `Running` en démarrage automatique, `/api/status`
et `/project` répondent 200, et la session anonyme répond 401. Un premier essai
de bascule a échoué à cause de caches Python introduits dans le bundle de la
candidate et s'est replié sur v250 ; le bundle a été nettoyé et le préflight
a été ajouté avant arrêt du service. Voir
[`multiuser-active-preflight-2026-10-15.md`](multiuser-active-preflight-2026-10-15.md).

Un pilote PostgreSQL 17.11 sur racines temporaires avec deux comptes, deux
projets et deux tâches synthétiques de même numéro valide les connexions,
lectures propres 200, refus croisés 403, deux mutations simultanées 200,
conflit de version 409, audits/événements et révocation 401. Le serveur de
test est arrêté. Le parcours HTTP réel sur le service actif avec `majdi` et
`mohd` a ensuite réussi : chacun lit `devcore` (200), `mohd` est refusé sur
`scripts` (403), la session `majdi/devcore` reste limitée à son projet (403),
et une session `majdi/scripts` distincte lit `scripts` (200). Les trois
sessions ont été révoquées et la base ne montre aucune session valide restante.
La recette en deux navigateurs est distincte de cette preuve HTTP ; elle a
ensuite été confirmée par l'utilisateur pour les étapes 2 à 6 du protocole.

La gate de réactivité a d'abord échoué : sur PostgreSQL synthétique, 20 sessions
et 200 lectures via un serveur HTTP local ont donné un p95 de 1 585,96 ms,
au-dessus de l'objectif initial de 300 ms. L'isolation et la révocation ont
tenu pendant cet essai. Une candidate v252 avec pool borné et autorisation
plus projection sur une seule connexion a ensuite atteint 231,63 ms de p95
sur 20 sessions et 200 lectures via Uvicorn isolé, avec isolation et nettoyage
RLS vérifiés. La copie propre v252 est désormais active et répond aux contrôles
SCM et HTTP anonymes. La mesure sur le service actif avec les deux comptes
réels a ensuite confirmé le résultat : 20 sessions et 200 lectures, médiane
139,25 ms, p95 205,81 ms, maximum 238,71 ms, refus inter-projets 403 et
vingt déconnexions vérifiées. L'objectif p95 < 300 ms est atteint ; la gate
de réactivité du pilote localhost est close. La recette interactive dans deux
navigateurs est close sur attestation utilisateur des étapes 2 à 6.
L'ouverture réseau et la pile globale restent des gates distincts. Le parcours
et les preuves du pilote sont consignés dans
[`pilote-deux-navigateurs-reels-2026-10-15.md`](pilote-deux-navigateurs-reels-2026-10-15.md).

### Préflight du gate LAN après le pilote

Le préflight du 15 octobre identifie PostgreSQL à l'écoute sur toutes les
interfaces au port 5432, alors que DevCore reste limité à localhost. Les règles
`pg_hba.conf` n'autorisent que le bouclage local, mais le pare-feu privé du
poste est désactivé. Le durcissement d'écoute PostgreSQL a ensuite été exécuté
et vérifié indépendamment : seuls `::1` et `127.0.0.1` écoutent sur 5432.
Le réseau DevCore n'a pas été ouvert.
La qualification LAN complète reste ouverte (TLS, pare-feu, origines
autorisées et essai depuis un second poste). Voir
[`lan-readiness-preflight-2026-10-15.md`](lan-readiness-preflight-2026-10-15.md).
Le contrôle complémentaire identifie Windows 10 Pro 22H2 build 19045.5487 et
aucun correctif visible par `Get-HotFix` après février 2025 ; l'inscription ESU
n'est pas établie. À la demande explicite de l'utilisateur, la preuve ESU et
le changement des mots de passe du pilote ne sont plus des critères de cette
migration. Un outil de réinitialisation reste disponible si nécessaire.

La release v253 LAN est construite et attestée. Un cycle HTTPS géré a passé
les contrôles d'origine, de cookie `Secure`, de lecture, de révocation et
d'arrêt sur des données temporaires et une interface virtuelle. Le certificat
du poste est créé sous ACL privée ; la bascule élevée avec retour arrière est
préparée. Le service actif reste v252 sur localhost. La confiance du second
poste, l'application du pare-feu, la bascule SCM et le test LAN réel restent à
effectuer.
Le vérificateur second poste est préparé avec saisie locale masquée des deux
secrets et contrôle des ports internes ; il n'a pas encore été exécuté.

**Mise à jour du 16 octobre :** ces phrases décrivent le préflight initial.
Le service actif est maintenant v253 en HTTPS sur `172.16.210.32:20129`.
La règle Private du LAN et une seconde règle limitée à `10.40.100.2/32` sont
actives. Le vérificateur a réussi depuis le second poste avec les deux comptes,
refus interprojets, révocations et six ports internes inaccessibles. Le gate
LAN du pilote est clos ; la reprise après redémarrage et la pile globale
restent à qualifier séparément.
Le premier essai de reprise après redémarrage a échoué : v253 s'est arrêté
après trois tentatives. Le service a été relancé manuellement. Les délais de
30 s de l'attestation et de la disponibilité ont expiré au démarrage à froid ;
une release v254 attestée avec bornes de 120 s et repli préparé attend la
bascule élevée puis un nouveau test de redémarrage.
La bascule élevée v254 a réussi avec service `Running/Auto`, HTTPS 200/200/401
et règles LAN inchangées. Une nouvelle référence de boot est enregistrée ; le
contrôle distant post-bascule a réussi sur le second poste : TLS, deux comptes,
refus interprojets, révocations et six ports internes inaccessibles. La reprise
automatique sur le prochain boot reste ouverte ; exécuter le vérificateur v254
avant toute relance manuelle, puis refaire le contrôle du second poste.
Le redémarrage du 16 octobre à `02:21:47.5000000Z` a passé le vérificateur
v254 : services `Running/Auto`, listener LAN et pare-feu attendus, PostgreSQL
sur loopback et HTTPS 200/200/401. Le SCM confirme v254 `Running/Auto` sur ce
boot. Il reste à refaire le contrôle depuis le second poste après ce boot.
Le contrôle a ensuite réussi depuis le second poste sur ce boot : TLS, accès
des deux comptes, refus interprojets, révocation des sessions et six ports
internes inaccessibles. Le gate de reprise LAN du pilote v254 est clos. La
remise en service opérationnelle de la pile globale a ensuite été clôturée le
18 octobre ; voir la section 4 et le journal d'exécution.
