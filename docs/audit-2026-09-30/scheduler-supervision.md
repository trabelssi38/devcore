# Supervision du scheduler : protocole de lancement local

La source supprime la détection WMIC par sous-chaîne et le succès annoncé dès
Popen. Le watcher réserve une tentative dans le budget local commun : trois
tentatives/dix minutes, backoff 5/10/20 secondes, réservation exclusive 60 s.
Les erreurs de réservation ou les états incohérents refusent le lancement.

Le daemon garde `Scheduler/scheduler.instance.guard` pendant sa vie, y compris
sync, initialization et sommeil. Ce fichier persistant ne doit pas être supprimé
ou remplacé. Le guard de cycle `scheduler.lock.guard` reste distinct. Toutes les
anciennes instances doivent être arrêtées et les nouveaux participants utiliser
le protocole avant activation. Un guard occupé/inaccessible bloque un doublon ;
il ne prouve pas à lui seul que le scheduler fonctionne.

Le watcher lance son enfant avec les racines explicites et un nonce de lancement
dans son environnement, sans variables globales de machine. Attente par défaut
cinq secondes, maximum trente ; comptée avant Popen, sans préemption d'un appel
OS bloqué. L'enfant publie un signal atomique après initialisation de l'historique
et chargement d'un registre validé, sous guard de cycle. Signal renouvelé à chaque
cycle valide, invalidé en cas d'exception de cycle ; durée de fraîcheur trente
secondes. Un long job peut donc rendre le signal expiré sans être mort.

Validation de l'enfant connu : handle Popen encore vivant, nonce, PID, Python,
racine locale, types stricts et fraîcheur ; heure de création et image exécutable
du PID vérifiées sur un handle Windows, empêchant d'accepter un PID réutilisé.
Sous Windows, le Python venv peut être un lanceur ; le signal accepte le PID de
l'interpréteur si son parent déclaré est ce lanceur. Lecture maximale 4096 octets.
Après timeout, l'enfant connu est conservé sans relance aveugle, ni arrêt d'un
job dont les effets peuvent déjà avoir commencé. Après sa mort, le budget limite
les prochaines tentatives. Aucun « ServiceAutoHealed » global n'est déduit.

## Reconnaissance d'une instance existante

Un nouveau watcher peut reconnaître un signal protocole 2 frais : guard confirmé
occupé avant/après lecture, PID encore vivant, heure de création/image Windows
correspondant au signal, même image Python que le watcher, même Python venv,
script et racines locale/données/plateforme. Aucun lancement ni consommation du
budget dans ce cas. Erreur d'ouverture du guard distinguée d'une contention OS :
elle ne permet pas cette reconnaissance. Protocole 1 et accès OS refusé échouent
sans adoption. Le signal reste dans un magasin local supposé digne de confiance.

Identité consultée sans énumérer les processus ni WMIC, avec les API Microsoft
[GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)
et [QueryFullProcessImageNameW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew).
Liveness vérifiée au même handle avec une attente de zéro milliseconde ; ce sont
des snapshots de contrôle, pas une garantie permanente après leur retour.

## Arrêt coopératif du scheduler Windows

Le CLI `DEV_CORE/Scheduler/stop_scheduler.py` exige `--local-root`, `--data-root`
et `--platform-root`. Il vérifie le guard occupé, l'identité OS et le profil du
daemon avant de publier une demande atomique liée à son nonce/PID/heure de
création. Un signal devenu ancien pendant un job long peut servir à demander
l'arrêt si son identité/profil sont toujours vérifiés ; il ne permet pas une
adoption comme service prêt. Profil étranger ou identité inaccessible : refus.

La réponse `stop_requested`, `stopped_confirmed=false` confirme uniquement la
publication. Le daemon finit la commande en cours, persiste son résultat et son
état, puis sort sans commencer le job suivant. Au repos il consulte la demande
toutes les 200 ms environ ; cette cadence ne borne pas les appels OS ni un job
en cours. Il libère son propre bail et nettoie ses propres signaux à la sortie.
Aucun kill, annulation, retry ni mutation d'un bail étranger n'est demandé.

Recette : commande simulée avec deux jobs dus et persistence réelle, demandes
invalides/anciennes/profil étranger, arrêt d'un daemon réel sur registre vide.
Avec `--wait-seconds N` (0..30), le CLI attend la libération du guard et le
nettoyage de la demande de son nonce. `shutdown_completed=true` décrit cette
fin de protocole ; `stopped_confirmed=false` reste explicite car la mort OS du
processus n'est pas certifiée indépendamment. Délai expiré : code 2 et demande
conservée, sans kill. Erreur/refus : code 1.

`--pause` écrit aussi `Scheduler/scheduler.paused.json` après vérification du
daemon. Le watcher refuse alors lancement/readiness, et un nouveau daemon
refuse la synchronisation du registre sous son guard de vie. Un marqueur invalide
ou inaccessible bloque les relances. Reprise explicite avec les mêmes trois
racines et `--resume` : exige le guard libre et un marqueur borné correspondant
au profil ; retire la pause sans lancer de processus. Un job en cours peut
continuer au-delà du délai d'attente. Une erreur après publication de la pause
la conserve ; diagnostiquer puis reprendre explicitement.

`Scripts/stop.ps1 -SchedulerOnly -WaitSeconds 30` emploie ce protocole et exige
DEVCORE_LOCAL_ROOT/DEVCORE_DATA_ROOT explicites. Sans `-SchedulerOnly`, clôture
de session et anciennes actions réseau n'interviennent qu'après fin du protocole.
Refus ou timeout conserve les autres services. Recherche des processus scheduler
par nom/ligne de commande et kill forcé supprimés. Les actions réseau héritées
restent par port, sans qualification de propriété ; leur supervision globale
et l'arrêt des anciens daemons Hermes ne sont pas couverts par ce protocole.

Magasin local protégé,
intégration au lanceur/service, délais d'exploitation et activation restent à
qualifier. Une erreur de publication du registre conserve l'historique SQLite
pour réconciliation ; elle ne transforme pas l'arrêt en preuve de succès métier.

## Suspension des relances de SystemWatcher

Le watcher est appelé par audits successifs. Le CLI local
`Scheduler/service_control.py --action pause|resume` exige les trois racines
explicites et une racine locale existante. Il partage un guard OS persistant
`Runtime/services.launch.guard` avec les entrées de lancement du watcher.
Un lancement/contrôle de préparation déjà sous ce guard doit finir avant qu'une
pause puisse être acceptée. Contention ou erreur OS : refus immédiat, pas de
kill ni attente bloquante. Les audits concurrents peuvent donc décliner un
contrôle pendant qu'un autre prépare un service ; ils ne consomment pas alors
le budget de redémarrage. Le guard n'est jamais remplacé ni supprimé.

La pause publie atomiquement `Runtime/services.paused.json`. Présence, corruption
ou accès refusé bloque les relances ; la décision est revérifiée sous le guard.
Une nouvelle instance de watcher la respecte. Un audit commencé après pause
répond PAUSED, sans sondes/scan Git/Docker ; un audit déjà engagé peut finir ses
observations, mais ses prochains lancements participent au guard. Les processus
déjà démarrés ne sont ni arrêtés ni contenus par ce contrôle.

L'arrêt complet `stop.ps1` exige cette pause avant le protocole scheduler, puis
la clôture de session et les actions réseau. Refus du guard : services conservés.
Un échec ultérieur conserve la pause : reprise explicite par le même CLI avec
`--action resume` et le profil correspondant. Cette reprise retire seulement
la pause globale ; la pause scheduler exige toujours son propre `--resume`.
`-SchedulerOnly` conserve son périmètre scheduler et n'écrit pas la pause globale.

Limites : protocole réservé aux watchers mis à jour, magasin local supposé
protégé, aucun contrôle des lanceurs externes/anciennes instances, pas de preuve
d'arrêt global des services. Arrêt par port hérité et identité/descendants des
services restent à qualifier avant activation.

## Arrêt coopératif des serveurs Python gérés

`Scripts/service_runtime.py` encadre Uvicorn pour dashboard 20129, router 20130
et Headroom natif/auxiliaire 8787/8789. Avec trois racines explicites et localhost,
le serveur publie son propre PID réel, création/image Windows, profil et nonce
dans `Runtime/service-<nom>.identity.json`, sous guard OS durant sa vie. Ce signal
atteste une identité participante, sans attester que le port est prêt. Le watcher
transmet les racines dans l'environnement de chaque enfant ; pas de changement
global de fournisseur/modèle. Sans aucune racine explicite, le lanceur autonome
reste non enregistré ; une configuration partielle/incompatible est refusée.

`Scripts/stop_service.py --service <nom> --local-root ... --data-root ...
--platform-root ... --wait-seconds N` vérifie profil, nonce, création/image du
processus vivant et guard occupé avant demande atomique. Le moniteur du serveur
ignore les demandes malformées/étrangères ; une demande correspondante met
Server.should_exit à vrai, permettant la fermeture Uvicorn et ses requêtes en
cours. Nettoyage seulement des signaux de son nonce. Délai du demandeur expiré :
code 2 et demande conservée, aucun kill. Fin du protocole (signaux nettoyés et
guard libre) distincte d'une certification indépendante de mort OS.

`stop.ps1` supprime Get-NetTCPConnection/Stop-Process de l'arrêt réseau. Les quatre
serveurs sont sollicités individuellement via ce protocole ; identité absente,
profil étranger, accès refusé ou délai dépassé conserve le processus et marque
l'arrêt incomplet (code 1). RepoWise et ancien adaptateur 8788 restent explicitement
conservés : leur arrêt n'est pas qualifié. Un code 0 concerne les quatre protocoles
gérés, pas la disparition de tous les processus DevCore. Anciennes instances
non enregistrées : aucun arrêt/adoption implicite, activation à préparer.

Recette : serveur Uvicorn minimal sur port éphémère et racines temporaires,
nonce étranger ignoré puis fermeture et guard libéré ; refus d'identités/profils
et états invalides ; orchestration PowerShell simulée sans kill ni découverte de
ports. Pas de test d'arrêt des véritables API/routages actifs. Requêtes longues,
WebSocket/drainage, hooks propres à chaque service, descendants, Linux, magasin
NTFS/compte de service et activation restent ouverts. Script/profil sont déclarés
par le participant et le lien guard/receipt suppose un magasin local protégé ;
ce n'est pas une authentification administrative résistante à un signal forgé.

## Drainage HTTP et hook de fermeture

Le profil géré impose `timeout_graceful_shutdown=None` : une valeur de timeout
Uvicorn qui annulerait les tâches actives est refusée avant enregistrement.
Le délai de stop_service borne l'observation du demandeur, sans interrompre
la réponse ni certifier la fin du serveur. Une tâche/hook bloqué peut garder
indéfiniment le service en drainage ; une procédure opérationnelle distincte
reste à définir pour ce cas, sans annoncer un temps maximal de fermeture.

Recette réelle sur ports éphémères : réponse HTTP retardée et réponse streaming
à deux morceaux terminées intégralement avec statut 200 après expiration de
l'attente d'arrêt ; absence d'annulation et signaux présents pendant traitement,
puis nettoyage/guard libéré. Hook lifespan retardé vérifié séparément : signaux
conservés jusqu'à sa confirmation de fermeture. Ces tests concernent une app
ASGI minimale, pas les effets métier ou hooks des véritables services.

WebSocket non qualifié : websockets absent de la recette Python 3.13. Erreurs
du hook, déconnexions client, effets métier, charge et véritables appels fournisseurs
restent ouverts ; fin du protocole ne constitue pas leur preuve de succès.

## Résultat de fermeture et échec des hooks

La disparition des signaux n'est plus suffisante pour confirmer le succès.
Avant leur nettoyage, le serveur publie atomiquement, sous guard, un résultat
`Runtime/service-<nom>.result.json` lié au nonce, PID/création/image et profil.
Classification : ok, lifespan_error, not_started, forced_exit ou server_error.
Aucun texte d'exception ou secret n'est stocké. Échec de publication : signaux
conservés et erreur propagée ; pas de confirmation par absence supposée.

L'observateur exige ce résultat correspondant et le guard libre. Résultat ok :
shutdown_completed=true ; résultat d'échec : shutdown_finished=true,
shutdown_completed=false, status=shutdown_failed, code CLI 3. Délai dépassé :
code 2 ; refus/profil ou résultat invalides : code 1. Sans attente, code 0 confirme
seulement l'acceptation de demande. stop.ps1 conserve un statut incomplet pour
l'échec, sans prétendre que le processus est encore vivant ni forcer son arrêt.

Recette Uvicorn réelle : lifespan.shutdown.failed et exception du hook produisent
lifespan_error, malgré le retour normal de Server.run ; échec disque du résultat
ne nettoie pas les signaux ; résultats étrangers/invalides refusés. Les données
business et exceptions propres aux requêtes ne sont pas attestées par ce résultat.
Un seul résultat récent est conservé par service et peut être remplacé par une
fermeture ultérieure : journal historique/authentifié, lecteur de diagnostic,
activation et hooks des véritables services restent à qualifier.

## Diagnostic local en lecture seule

`Scripts/inspect_service_shutdown.py --local-root ... --data-root ...
--platform-root ... --service router` consulte uniquement les trois preuves
connues : identité, demande et dernier résultat. Chaque lecture est bornée à
4096 octets ; fichiers non réguliers/reparse points directs refusés, schéma et
profil contrôlés. Réponse structurée filtrée : aucun contenu brut, message
d'exception, image du processus ou nonce exposé ; référence d'instance par hash
pour distinguer preuve correspondante, autre instance et résultat historique.

`--verify-live` ajoute une consultation OS de l'identité du PID enregistré.
Accès refusé/disparition indistinguables signalés unavailable, jamais interprétés
comme preuve de mort. Pas de sonde de port, de guard ouvert, de SQLite, de retry,
de création de répertoire, de nettoyage ni de demande d'arrêt. Bytecode désactivé
à l'entrée du CLI. Code 0 indique diagnostic produit, y compris preuves absentes
ou résultat d'échec valide ; code 1 indique preuve/racine invalide ou inaccessible.
Il ne confirme ni readiness, ni fin d'arrêt, ni succès métier.

Les trois lectures et le snapshot OS ne forment pas une transaction :
consistent_snapshot=false et guard_checked=false restent explicites. Contrôle
des fichiers au moment de lecture seulement, pas protection contre remplacement
concurrent par un utilisateur ayant les mêmes droits. Parents/jonctions, magasin
NTFS et console authentifiée restent à qualifier ; ce lecteur local n'apporte
aucune authentification administrative. Dernier résultat seulement, pas historique.

## Fermeture WebSocket sur recette isolée

Le support `websockets>=17.2,<18.0` est déclaré dans pyproject et websockets 17.2
verrouillé avec hashes dans le lock Windows Python 3.13. Vérification de version
et API depuis [PyPI officiel](https://pypi.org/project/websockets/) ; résolution uv
sur copie du lock, aucun changement des versions existantes. Dépendance installée
uniquement dans un overlay temporaire CPython 3.13 Windows, Uvicorn 0.54.0.
Les runtimes/release actifs restent inchangés ; reconstruction et activation ouvertes.

Deux scénarios WebSocket réels sur port éphémère : echo avant demande d'arrêt,
fermeture avec code 1012 côté client et événement disconnect 1012 côté ASGI,
hook lifespan terminé et résultat terminal ok. Variante de traitement après
disconnect retardée : le client est déjà fermé, mais le serveur conserve son
identité/demande au-delà du délai d'observation, puis finit après libération de
la fixture. Aucune annulation forcée ni reconnexion/rejeu automatique ajouté.

Qualification limitée au transport et cycle de vie d'une app ASGI minimale.
Acheminement intégral des messages en cours, reprise de conversation fournisseur,
authentification OpenAI/Claude et véritables proxy Headroom restent à qualifier.
Les tests ASGI de politiques natif/auxiliaire sont aussi rejoués ; ils ne prouvent
pas un aller-retour WebSocket authentifié auprès d'un fournisseur.

## Limites encore ouvertes

- Le lien entre détenteur du guard et signal dépend de participants respectant
  le protocole et d'un magasin protégé. Les métadonnées de script/racines sont
  déclarées par le daemon ; elles ne sont pas extraites de sa ligne de commande
  ni de son environnement par le noyau. Pas de résistance à un signal forgé par
  un utilisateur ayant les mêmes droits. ACL/compte de service encore ouverts.
- Le signal atteste la préparation du cycle, pas la réussite de toutes les tâches
  ni une identité administrative authentifiée. Les fichiers/permissions locales
  doivent être dignes de confiance ; le PID parent déclaré n'est pas une preuve
  indépendante du noyau. Compte de service et ACL opérationnels ouverts.
- Le watchdog n'a pas encore de Job Object contenant son daemon/arbre complet ;
  arrêt opérationnel, fermeture du watcher, retard et charge restent à qualifier.
- Les sources ne sont pas activées et les releases figées ne sont pas reconstruites.
- Un démarrage direct génère son nonce local si aucune valeur n'est fournie,
  publie le même signal et peut être reconnu par un nouveau watcher. Les racines
  du signal viennent des chemins résolus du daemon, sans dépendre de variables
  obligatoirement présentes ni modifier l'environnement global. Une valeur de
  nonce explicitement invalide est refusée avant synchronisation du registre.
  Une sortie normale ou exception propageant hors du cycle invalide le signal
  de ce nonce ; après arrêt forcé, identité OS/guard restent les critères de refus.

Recette : racines temporaires, définitions statiques `[]`, aucun job ni donnée
active. Le daemon réel et ses descendants de recette sont arrêtés par le test ;
libération du guard et refus de l'ancien signal après sa mort vérifiés.


### Signaux JSON malformés

Le lecteur borné convertit le dépassement de profondeur JSON en ValueError.
Le monitor conserve sa surveillance après JSON invalide, UTF-8 invalide,
nesting excessif ou volume excessif ; une demande valide ultérieure fonctionne.
Au nettoyage, un signal illisible est conservé sans masquer le résultat terminal
publié. Sa présence empêche toujours de certifier la fermeture via request_stop.
54 tests runtime/drainage/diagnostic réussis sur fixtures (4 octobre).
Stockage local de confiance, ACL et courses de remplacement restent à qualifier.
