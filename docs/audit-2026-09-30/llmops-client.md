# Client LLMOps : bornes et limites

Le client reste un adaptateur à transport injecté, sans export HTTP par défaut.
CaptureResult : sent (callback revenu normalement, pas preuve d'ingestion),
buffered, dropped (tampon plein), invalid (schéma refusé).

Tampon par client : défaut 256 événements et 1 Mio de JSON sérialisé cumulé,
événement au plus 4096 octets. Conserve les premiers événements, refuse les
nouveaux si plein, compte les pertes. Pas de flush/retry implicite ; état
volatile. buffered_events retourne une copie ; accès et compteurs protégés
par lock, callback exécuté hors lock. Ce plafond n'est pas une borne de RSS.

Événement : schéma exact, identifiants ASCII 1..128 (lettres/chiffres/_.:/-),
tokens entiers non booléens 0..2^63-1, total cohérent, coût fini 0..10^9 USD.
Champs disponibles seulement : nom, modèle, corrélation et usage déclarés par
l'appelant ; aucun prompt/output/header arbitraire. Les identifiants restent
de confiance : ce contrôle ne reconnaît pas un secret placé dans un ID valide.
Aucune qualification automatique de tokens observés versus estimés.

Exceptions ordinaires du transport contenues sans conserver leur texte ;
événement retenu si possible, transport_errors compté. Pas de retry automatique.
Annulation/KeyboardInterrupt/SystemExit restent propagés. Compteurs plafonnés
à 2^63-1. snapshot agrégé sans événements/secrets ni erreurs brutes.

16 tests réussis : compatibilité, limites de count/bytes, schémas invalides,
erreur réseau simulée et 128 captures concurrentes avec capacité huit.
Transport synchrone potentiellement bloquant ; worker/file durable, persistance, flush et vraie ingestion restent
à implémenter/qualifier ; transport OTLP séparé décrit ci-dessous. Aucun appelant de production raccordé dans les sources
inspectées, hors tests ; aucune activation ou donnée active modifiée.


## Export OTLP asynchrone explicite

OtlpExporter séparé, aucun changement de configuration/envoi automatique.
Endpoint complet HTTPS /api/public/otel/v1/traces (Langfuse) ou /v1/traces
(collector), credentials explicitement fournis, Basic Auth et header ingestion
v4. HTTP seulement sur IP loopback avec allow_local_http=True. URL avec
userinfo/query/fragment/ancien ingestion refusée, trust_env=False, TLS par
défaut vérifié, aucune redirection ni retry.

Une requête en cours par instance/boucle, sinon busy sans attente ; payload
8 Kio, réponse JSON 8 Kio, deadline totale 2 s (configurable >0..10).
Réponse compressée refusée, HTTP autre que 200 refusé, objet malformé/inconnu
refusé. accepted, accepted_warning et partial_rejected distincts ; timeout,
transport_error, invalid_response, oversized_response explicites. Un timeout
peut survenir après réception serveur : pas de conclusion de non-ingestion.
Annulation externe propagée, créneau libéré ; aclose refuse de couper un export
en cours, puis ferme explicitement le client une fois libre.

Spans : UUID/hex trace non nul requis, span ID neuf, timestamps Unix nanosecondes
explicitement fournis par l'appelant, pas de durée inventée. Modèle et
corrélation conservés ; usage/coût en attributs devcore.* caller_declared,
aucun input/output/prompt exporté. Pas de preuve automatique de mesure réelle
ni de mapping UI de coûts/tokens ; IDs restent de confiance.

32 tests réussis sur vraies connexions HTTP loopback et clés factices : ACK,
partial/warning, refus HTTP/redirect/volume/JSON/compression, délai, busy,
annulation/fermeture et invalidité avant envoi. Aucun vrai Langfuse contacté.
Transport non raccordé aux appels modèle ; UI Langfuse, certificats/credentials
opérationnels, propagation, durabilité et quota global restent à qualifier.

Sources officielles consultées le 4 octobre 2026 :
- [Langfuse OTLP](https://langfuse.com/integrations/native/opentelemetry) : HTTP JSON, endpoint et header v4.
- [Guide](https://langfuse.com/docs/observability/get-started) : exemple HTTP JSON.
- [Spécification OTLP](https://opentelemetry.io/docs/specs/otlp/) : ACK/partial success, limites de réponse.
- [API publique](https://langfuse.com/docs/api-and-data-platform/features/public-api) : ancien ingestion déprécié, OTLP recommandé.


## File OTLP volatile par boucle

OtlpWorker possède exclusivement son exporter : démarrage explicite,
submit synchrone sans attente réseau, capacité 256 événements/1 Mio par défaut
(en cours inclus). Budget en octets sérialisés, pas en mémoire totale ni tokens.
Validation avant admission ; saturation dropped, invalidité invalid ; aucune
reprise automatique. File FIFO avec compteur fixe des ACK, warnings, échecs,
refus et abandons ; aucun contenu ni texte d’erreur dans snapshot.

aclose arrête les admissions et draine ; si son attente expire ou si l’appelant
est annulé, la tâche suivie continue. Réappeler aclose pour vérifier la fin,
avant de terminer la boucle. Une destruction de boucle/processus peut perdre
la file : pas de durabilité garantie. Exporter fermé après drainage.

39 tests OTLP/client/observabilité réussis : réseau retardé, limites événements
et octets, fermeture expirée et annulée, refus partiels/HTTP, poursuite après
exception. Clés factices et serveurs loopback ; aucune preuve de stockage
Langfuse réel. Raccordement workflow, TLS/identités opérationnels, persistance,
quotas interprocessus et activation restent ouverts.


## Observation explicite d’une génération asynchrone

GenerationObserver.run(operation, event_from_result=adapter) appelle exactement
une fois l’opération asynchrone et retourne le même objet résultat. L’adaptateur
synchrone de confiance construit un LangfuseEvent à partir du résultat : modèle,
usage/coût et corrélation doivent être disponibles, sans valeur par défaut
inventée. Son coût doit rester borné ; aucun réseau dans cet adaptateur.
L’observateur n’effectue aucun routage, mapping de modèle, retry ni chargement
d’environnement. Son worker doit être démarré sur cette boucle par l’application.

Début/fin Unix ns entourent l’appel (temps observé par l’application, pas une
mesure du temps interne du fournisseur). Horloge invalide/rétrograde, événement
invalide, saturation ou panne ordinaire de l’adaptateur n’altèrent pas le résultat.
Compteurs bornés queued/refused/invalid/errors, sans contenu. Exceptions et
annulations de l’opération propagées ; aucune génération réussie inventée
pour un échec ou un flux partiellement consommé. Pas de collecte de prompts.

Le propriétaire appelle worker.aclose et en vérifie le résultat avant arrêt de
la boucle. Exemple de raccordement explicite :

```python
worker.start()
observer = GenerationObserver(worker)
result = await observer.run(call_provider, event_from_result=adapt_result)
closed = await worker.aclose()
# closed=False : drainage encore suivi, conserver la boucle et attendre la fin.
```

48 tests réussis incluant réponse avant ACK retardé, saturation, conservation
modèle/usage/timestamps, erreurs et annulations propagées, erreurs de télémétrie
contenues. Un adaptateur de fournisseur réel reste à raccorder : le runner Codex
manuel écrit uniquement des instructions et ne fournit aucun usage à exporter.
Aucun service actif ni fournisseur contacté ; Langfuse réel et gains ouverts.


## Branchement au Router auxiliaire non-streaming

Le POST /v1/chat/completions peut recevoir sur app.state deux dépendances
explicites : generation_observer et generation_event_factory(request, response).
Sans les deux, parcours existant. Politique de routage validée avant ce branchement ;
natifs refusés, flux et embeddings hors de cette observation. Pas de configuration
globale ni de démarrage implicite : propriétaire responsable de start/aclose.

event_from_chat_response(response, correlation=..., cost_usd=...) exige HTTP 200,
route auxiliary et modèle résolu cohérent avec celui de la réponse s’il est présent.
JSON de réponse limité à 64 Kio ; prompt_tokens, completion_tokens, total_tokens
entiers explicites et cohérents. Aucune estimation à partir du texte ; coût et
corrélation fournis explicitement par l’application. Aucun recours au projet actif
ni aux statistiques historiques du Router. Usage/cost restent caller_declared,
identité/corrélation ne constituent pas une authentification.

Sur réponse volumineuse/invalide/usage absent, l’observateur compte l’erreur puis
retourne les mêmes octets/statut/headers sans retry. Adaptateur synchrone borné,
sans réseau. Ce branchement entoure call_with_fallback en entier : sa durée inclut
les attentes/retries internes existants ; une trace de réussite finale ne décrit
pas les tentatives échouées ou leurs éventuels tokens. Les estimations historiques
de providers.py subsistent séparément : ne pas les qualifier de mesure fournisseur.

Recette : véritable requête ASGI vers le Router, opération fournisseur substituée
par fixture, vrai récepteur OTLP loopback retardé. Aucun Gemini/Langfuse réel ni
activation : fournisseur réel, prix, identités, propagation workflow, flux et
persistance restent à qualifier.


## Cycle de vie du Router

FastAPI utilise observation_lifespan ; par défaut aucune dépendance créée.
L’application peut définir app.state.observation_factory(app) avant démarrage,
qui retourne (GenerationObserver(worker_neuf), event_factory(request, response)).
Factory synchrone de confiance, bornée, sans réseau, responsable de ne pas
allouer de ressources avant une éventuelle exception interne. Endpoint/clé,
prix et principal restent explicites, pas de variables globales d’activation.

Au startup, refus de dépendances déjà installées ou de worker actif/exporter
busy/fermé ; start puis installation sur app.state. Callback invalide : échec
de startup et fermeture du client possédé. Chaque lifespan doit construire
un worker neuf ; celui fermé au passage précédent ne peut pas être réutilisé.

Au shutdown, aclose refuse les admissions et attend le drainage. Son timeout
est seulement un budget d’attente répété ; pas un succès, une annulation ou
un retry d’export. Une course entre expiration et fin de tâche relit le résultat
de fermeture. Si fermeture définitivement refusée, erreur de lifespan explicite.
Après succès, seules les références possédées sont retirées de app.state.
Les autres dépendances restent préservées ; exceptions du corps propagées après
drainage, sans nettoyage pouvant masquer une erreur de startup.

La file reste volatile. Jusqu’à 256 événements et timeout de transport 2 s peuvent
allonger l’arrêt ; pas de délai global garanti. Kill/processus ou annulation
externe du lifespan peut interrompre cette attente ; ne pas annoncer un arrêt
réussi. Le worker suivi et les références sont conservés si fermeture échoue,
pour diagnostic. Aucun mécanisme de persistance ni supervision externe ajouté.

Recette inclut protocoles startup/shutdown ASGI via TestClient du Router, cycles
successifs et drainage sur vrai récepteur loopback. Ne constitue pas une
qualification du service Windows actif ou d’un véritable Langfuse.


## Usage non-streaming déclaré par fournisseur

providers.py utilise désormais reported_usage pour Gemini et les replis
autorisés non-streaming. prompt_tokens et completion_tokens explicites, entiers
non booléens, non négatifs, somme <2^63 ; total_tokens s’il est présent doit
être entier et égal à cette somme. Embeddings : prompt_tokens requis,
completion_tokens absent vaut zéro (aucune complétion), total cohérent.
Un zéro déclaré reste zéro : ni taille du prompt ni contenu de réponse ne
remplacent les valeurs. Usage incomplet/invalide : aucune écriture de tokens.
Header X-DevCore-Usage-Source = provider_reported ou unavailable, sans modifier
les octets ni le statut de la réponse. ACK fournisseur n’est pas une preuve
indépendante de facturation ; pas de calcul de prix ajouté.

Les estimations utilisées avant appel pour admission RPM/TPM restent présentes.
Les streams et anciens fichiers de statistiques peuvent encore mélanger des
estimations/historique ; aucune requalification ni migration silencieuse de
leurs totaux. Une absence d’usage n’est ni un zéro de consommation ni un gain.
Attribution via projet actif historique encore ouverte ; ces compteurs ne sont
pas une comptabilité utilisateur authentifiée ou un bilan complet des retries.


## Usage des flux SSE

SseUsage observe les événements data complets, LF/CRLF, lignes multiples et
fragments réseau y compris UTF-8. Tampons de ligne et événement séparés limités
à 64 Kio ; dépassement ou JSON invalide désactive l’observation et libère les
tampons, sans modifier le flux transmis. Un seul couple de compteurs retenu,
pas de texte de complétion accumulé. Usage explicite validé, zéros conservés,
aucune estimation du prompt ou de la sortie. Usage comptabilisé une fois à
EOF normal avec marqueur DONE complet ; absence d’usage, flux incomplet, erreur
ou annulation ne vaut pas consommation nulle et ne produit pas de compteurs.

Octets transmis tels quels avant observation. Après émission d’un morceau,
erreur amont propagée sans reprise susceptible de dupliquer le texte. Avant
émission, les trois tentatives historiques restent possibles ; succès seulement
après consommation normale du flux. Pas de fallback streaming ajouté.

Ce parseur cible les flux chat LF/CRLF du Router, pas tous les transports SSE
(CR seul non qualifié). Pas de mesure/cache/coût/retries perdus inventés, pas
d’export OTLP streaming ajouté. Attribution historique projet actif et stockage
JSON subsistent ; anciens totaux ne deviennent pas mesures fournisseur.


## Admission locale Gemini non-streaming

SlidingWindowRateLimiter est déplacé dans rate_limit.py. wait_if_needed conserve
son nom de compatibilité mais ne contient aucun await interne/verrou/sleep.
Une seule boucle propriétaire, horloge monotone, admission atomique sans attente.
RPM 8 et capacité de tokens 200000 par défaut, fenêtrage 60 s ; refus explicite
RateLimitRefusal, HTTP 429 et Retry-After 1..61 s dans call_with_fallback, sans
nouvel appel réseau, retry ou repli sur ce refus local.

Les estimations sont réservées à l’admission et le total déclaré ultérieurement
est ajouté conservativement : possible double compte dans la fenêtre, pas de
promesse de plafond de facturation réel. Réservations <=max_rpm (1..4096),
compteurs déclarés groupés par seconde avec expiration arrondie vers le haut
(<1 s de marge), <=61 groupes et valeurs plafonnées à capacité+1. Aucun texte
conservé. Comptes invalides/horloge invalide ou boucle étrangère refusés.

Portée : appels Gemini non-streaming qui utilisaient déjà le limiteur. Streams
et replis directs ne sont pas couverts par cette admission ; pas de limite
interprocessus ou équité par utilisateur. Pas de pause/état durable. Une nouvelle
boucle doit obtenir une nouvelle instance ; restart processus repart sans état.
Les compteurs de la facturation/statistiques sont séparés de ces réservations.


## Admission partagée des streams Gemini

La route de chat streaming vérifie la politique, la clé puis réserve l’estimation
dans le même limiteur que Gemini non-streaming, avant ouverture du générateur
et des en-têtes SSE. Saturation : 429 JSON/Retry-After, aucun appel amont ni
repli. Clé manquante ou modèle natif refusé ne consomme pas de réservation.

Le générateur reçoit explicitement ce limiteur ; usage validé après DONE/EOF
normal transmet le total déclaré à ses groupes temporels. Usage absent,
incomplet, erreur ou annulation ne produit pas de total inventé. Les appels
directs au générateur sans limiteur restent réservés au propriétaire interne ;
le chemin HTTP public l’injecte. Réservation conservatrice conservée jusqu’à
expiration même en cas de perte de connexion, sans prétendre une consommation.

Les tentatives internes streaming avant émission restent couvertes par une
seule réservation logique ; admission de chaque tentative reste à qualifier.
Scope instance/boucle, pas d’équité utilisateur ni quotas interprocessus ;
replis directs non couverts. Pas de transformation d’usage en coûts ni de
qualification des statistiques historiques ou d’activation des services.


## Admission des retries streaming

La route transmet au générateur le limiteur et la même estimation initiale.
Première tentative déjà réservée avant en-têtes ; chaque nouvelle tentative
avant émission appelle wait_if_needed avant le réseau. Saturation locale
termine le générateur avec une erreur SSE data bornée (<512 octets dans
la recette), type local_rate_limit et retry_after, sans nouvel appel ni repli.
Le statut HTTP déjà envoyé reste 200 : le client doit lire l’erreur du flux.
Le refus initial conserve son HTTP429 JSON avant ouverture.

Backoff amont historique et plafond de trois tentatives conservés ; jamais
de retry après émission de données. Usage réussi enregistré une fois,
pas de tokens inventés pour les tentatives échouées. Le message public
d’épuisement des retries ne contient plus le texte de la dernière exception.
Logs historiques internes encore distincts, redaction globale à qualifier.

Calls directs sans limiteur restent un chemin interne de test/propriétaire ;
route HTTP toujours injectée. Admission locale conservatrice, pas de quota
authentifié par utilisateur/interprocessus, persistance ou budget de dépense.


## Admission indépendante des replis auxiliaires

providers.py possède désormais fallback_limiters pour cerebras et nvidia-nim,
chacun avec la politique locale bornée par défaut (8 RPM/200000 tokens de
capacité conservatrice). Ces valeurs sont une politique DevCore, pas une
affirmation des quotas commerciaux de ces fournisseurs. _try_provider_request
réserve l’estimation avant réseau et enregistre le total explicite valide
avant la comptabilité historique. Zéros/usage absent restent distincts.

Refus local = HTTP429/Retry-After terminal : aucune tentative réseau ou
continuation vers un autre repli. Une panne amont normale peut poursuivre
uniquement les providers demandés dans fallback_providers, chacun après
sa propre admission. Sans autorisation, ni réservation ni appel de repli.
Aucun modèle natif ajouté ou changé ; replis réservés à la route auxiliaire.

Les trois états Gemini/Cerebras/NVIDIA sont indépendants par instance/boucle,
non durables et conservateurs. Pas d’équité utilisateur/quotas interprocessus
ni plafond financier réel ; identités, historique et attribution projet actif
encore ouverts. Réservations d’une tentative échouée gardées jusqu’à expiry
sans inventer son usage fournisseur.


## Diagnostics d’erreurs explicites du Router

Les print d’échec providers.py/stream_parser.py ne reprennent plus le corps
d’une erreur fournisseur ni le texte brut d’une exception. Fournisseur,
statut HTTP et numéro de tentative conservés ; erreurs de persistance/usage
remplacées par messages fixes. Dernière exception streaming non retenue
après traitement pour fabriquer le message public. Aucune nouvelle tentative
ni modification de réponse réussie introduite par cette réduction des logs.

Recette avec marqueurs privés dans RuntimeError et réponse HTTP500, sur
Gemini/Cerebras/NVIDIA et stream avant émission : absence stdout/stderr
et message public, nombre de tentatives conservé. Exceptions après émission
restent propagées pour signaler un flux rompu ; tracebacks du framework/serveur
peuvent encore les afficher. Redaction globale, fichiers historiques/alertes,
identités/corrélation, erreurs d’autres composants et configuration du logger
à qualifier séparément. Pas de certification de confidentialité end-to-end.


## Deadline asynchrone non-streaming

call_with_fallback entoure toute la chaîne avec asyncio.timeout, 120 s par
défaut, paramètre interne explicite >0..120 s (pas une valeur pilotée par le
corps client). Admission, appel Gemini, attentes Retry-After/backoffs et replis
partagent ce budget ; il ne redémarre pas à chaque tentative/provider.
Expiration : réponse504 JSON provider_deadline, sans continuation vers un
provider suivant. Annulation externe propagée, sans confusion avec504.

Le contrôle est coopératif aux await : écritures JSON, time.sleep historique,
parsing/CPU synchrones ne peuvent pas être préemptés par ce timeout. Ne pas
le qualifier de délai mural strict garanti. Les flux conservent leur propre
chemin, durée totale encore ouverte. Timeout ne prouve ni non-réception
amont ni absence de coût ; réservations locales restent jusqu’à expiration,
aucun usage/coût inventé pour une réponse perdue.

Recette avec appels suspendus ou Retry-After3600 et délai .03 s : autre requête
rapide aboutit, chaîne lente504 sans second appel ; annulation externe
propagée. Transports de provider substitués, fournisseur réel non qualifié.


## Budget total coopératif des flux Gemini

stream_generator possède une échéance monotone unique, 120 s par défaut,
paramètre interne >0..120 s. Chaque anext de la source reçoit le temps restant,
comprenant appels, backoffs et attente des prochains morceaux ; aucun nouveau
budget à chaque tentative. Expiration : source fermée avant erreur SSE
provider_deadline, sans retry ni texte privé. HTTP déjà ouvert reste200.

Aucun contexte asyncio.timeout ne traverse un yield : il ne doit pas annuler
le consommateur pendant son send. Après une pause client, le temps écoulé est
vérifié au pull suivant, sans timer qui annule le consommateur durant la pause.
aclosing garantit la fermeture de source à aclose du générateur ; annulation
externe propagée et await amont annulé. Les chunks déjà émis restent conservés.

Budget coopératif : send client bloqué, CPU/I/O synchrones et durée de cleanup
non préemptés ; plafond mural strict sur la requête ASGI non garanti. Amont
de confiance doit respecter annulation/fermeture. Une expiration ne prouve
pas coût nul ; usage d’un flux interrompu non inventé. Pas de watchdog
interprocessus ni changement de supervision/activation ajouté.

Recette : flux suspendu avant/après chunk, backoff500, pause consommateur,
annulation et aclose après chunk ; fermeture amont et absence de statistiques
vérifiées sur contexte substitué. Service Windows/Langfuse réel ouverts.


## Plafond du volume streaming

stream_generator compte les octets de chaque morceau reçu, plafond 16 Mio
par défaut, paramètre interne entier 1..16 Mio (pas de contrôle par requête
client). Si le prochain morceau dépasse le budget restant, il est refusé
en entier ; source amont fermée avant erreur SSE provider_response_too_large
(<256 octets dans la recette), sans retry, sans comptabilité du flux interrompu.
Les morceaux déjà acceptés restent identiques ; aucun découpage/troncature
silencieux du morceau refusé. HTTP déjà ouvert reste200. Une coupure peut
intervenir au milieu d’un événement SSE fragmenté : intégrité du contenu
applicatif au-delà des chunks précédents non garantie, client doit traiter
l’interruption/erreur sans considérer le flux comme réussi.

Le plafond porte désormais sur aiter_raw HTTPX, avec Accept-Encoding identity.
Les réponses compressées sont refusées avant lecture, sans décompression HTTPX
ni retry ; fermeture amont avant erreur SSE provider_response_refused.
Un morceau excessif peut déjà être alloué avant refus : borne stricte de mémoire
transport encore ouverte. Les réponses non-streaming ont le lecteur décrit ci-dessous. Aucun contenu accumulé
par le compteur, même durée coopérative/fermeture que le wrapper existant.


## Lecture bornée des réponses auxiliaires non-streaming

Gemini et les replis autorisés utilisent post_bounded : POST en streaming
HTTPX, redirections désactivées, Accept-Encoding identity. Un statut200
avec Content-Encoding différent de identity est refusé avant lecture.
Content-Length supérieur au plafond est refusé ; sans longueur fiable,
aiter_raw alimente un bytearray de 16 Mio maximum (paramètre interne entier
1..16 Mio). Le morceau excédant le restant est refusé avant ajout.
Les statuts non200 conservent les en-têtes utiles au retry sans lire leur corps.

Le contexte HTTPX ferme la réponse lors du succès, refus ou annulation.
Un refus de transport remonte jusqu'au wrapper : JSON502 provider_response_refused,
sans détail privé, nouvelle tentative ni autre fournisseur. Le délai global
coopératif120 s existant couvre cette lecture. Les chemins natifs et streaming
ne sont pas modifiés par ce lecteur.

Recette avec vrai AsyncClient/MockTransport et AsyncByteStream : borne exacte,
dépassement, longueur annoncée, compression, erreur et annulation ; fermeture
unique et arrêt de la chaîne Gemini/replis. Les autres tests d'orchestration
substituent explicitement le lecteur ; ils ne qualifient pas son transport.
Pas de fournisseur réel ni d'activation. La capacité borne le tampon, pas le RSS :
morceau transport déjà alloué et copie finale bytes possibles ; décodage JSON
et historique synchrones, nettoyage bloqué et mémoire transport restent ouverts.


## Qualification du flux sans compression

Le Router demande identity et désactive les redirections du flux. Un encodage
autre que identity (y compris gzip/br) sur une réponse réussie est un refus
terminal ; aucun octet du corps n'est lu, aucun usage enregistré, aucun retry.
L'erreur SSE bornée intervient après fermeture de la réponse HTTPX ; le statut
HTTP déjà envoyé reste200. Les flux absents/identity transmettent les morceaux
raw inchangés et conservent le parser d'usage explicite.

Cinq cas avec AsyncClient/MockTransport et AsyncByteStream vérifient en-tête,
absence de lecture/décompression, fermeture unique, absence de retry et usage
du succès. Les fixtures de volume/délai/retry/usage suivent désormais le
contrat raw avec en-têtes explicites. Aucun appel réel ni activation ; send,
cleanup, allocation des chunks transport et CPU/I/O synchrones restent ouverts.


## Équité de lecture hors streaming

Un transport déjà tamponné peut produire ses morceaux sans suspension asyncio.
post_bounded cède désormais la boucle avec sleep(0) après64 morceaux ou64 Kio
reçus, puis remet ses compteurs locaux à zéro. Le plafond16 Mio reste identique.
Ce point permet aux autres coroutines et à l'annulation de progresser pendant
la lecture ; il ne borne pas la durée d'un morceau/traitement synchrone,
la copie finale, JSON, send ou cleanup, et n'est pas une mesure de performance.

Quatre recettes de transport tamponné réel HTTPX/MockTransport :128 morceaux
de1 octet ou64 Kio, concurrence avec/sans annulation. Avant correctif, les
quatre échouent : autre coroutine servie après toute la lecture, annulation
trop tardive. Après correctif, autre travail avant fin et fermeture unique
sur annulation, contenu complet inchangé sur succès. Aucun fournisseur réel.


## JSON amont non-streaming borné avant succès

Gemini et les replis autorisés appellent decode_provider_json avant lecture
d'usage et transmission du succès. Octets <=16 Mio, UTF-8 valide, profondeur
<=64 puis objet racine exigés. Le scanner partagé decode_json_async ignore
les délimiteurs dans les chaînes/échappements et cède la boucle après chaque
lot64 K caractères. JSON invalide/trop profond/non objet devient un refus
terminal502 provider_response_refused, sans nouvelle tentative ni repli,
sans copie du contenu privé dans l'erreur et sans statistiques.
Les bytes d'un objet accepté restent inchangés. Usage absent/invalide demeure
unavailable ; pas de validation complète du schéma fournisseur ajoutée.

Recette Gemini/Cerebras : profondeur64/65, chaînes échappées, JSON incorrect,
UTF-8 invalide, racine tableau ; annulation d'un scan volumineux propagée.
Frontière provider substituée, fermeture du lecteur qualifiée séparément.
UTF-8, json.loads, allocation des objets et historique restent synchrones ;
aucune borne RSS ni plafond mural strict annoncé. Non activé.


## Observation SSE coopérative et profondeur JSON

Le flux transmis reste identique ; son observateur utilise feed_async par
lots64 Kio, avec une suspension asyncio entre lots. Chaque événement JSON
utilise le décodeur partagé avec profondeur64 et chaînes/échappements pris
en compte ; les lignes/événements restent plafonnés64 Kio. Un événement trop
profond/invalide désactive et vide l'observation, sans réécriture du flux
déjà transmis ni usage inventé. Une annulation du scanner vide/désactive
également l'observation et propage CancelledError.

Recette : profondeur64/65, chaînes échappées, gros morceau de commentaires
laissant une autre coroutine avancer avant fin, annulation puis absence
de réactivation/comptabilité. Régressions forwarding/usage/délai conservées.
Feed synchrone reste disponible pour petits appels locaux ; le Router utilise
feed_async. Chaque lot et son parse restent synchrones ; pas de borne murale
stricte, RSS transport ni qualification de performance/fournisseur réel.


## Longueurs amont et erreurs de framing

Lecteurs hors streaming et SSE partagent validate_response_headers.
Content-Length absent reste accepté sous la capacité cumulée existante ;
présent, chiffres ASCII seulement après retrait SP/HTAB extérieurs. Valeur
vide/négative ou liste ambiguë refusée. Zéros initiaux normalisés, comparaison
lexicale avec la capacité avant conversion d'un petit entier : pas de
conversion d'une valeur de milliers de chiffres. Longueur supérieure à
la capacité refusée avant lecture.

Morceau dépassant la longueur déclarée refusé entier ; à EOF, longueur
reçue doit correspondre avant usage/succès. En SSE, des morceaux précédents
peuvent déjà avoir été transmis ; erreur provider_response_refused après
fermeture, HTTP déjà ouvert200, pas de retry ni comptabilité. Les
RemoteProtocolError HTTPX deviennent également un refus terminal.
Sans longueur annoncée, absence de détection sémantique d'un contenu tronqué
non-streaming valide JSON ; DONE explicite requis pour l'usage SSE.

Recette20 cas AsyncClient/MockTransport : exact/zéros/absent, énorme/vide/
liste/négatif, déclaration inférieure/supérieure au corps, erreur protocole
après un morceau ; succès inchangé, fermeture unique, zéro retry/usage sur
refus, erreur publique sans détail privé. Transport réel distant non qualifié ;
en-têtes et chunks peuvent déjà être alloués avant validation.


## Publication atomique des statistiques JSON héritées

record_tokens utilise stats_store : snapshot <=1 Mio, <=4096 tâches,
identifiants/modes ASCII1..128, compteurs entiers non négatifs63 bits,
totaux cohérents. Lecture bornée ; magasin invalide préservé sans réinitialiser
les chiffres. Update sous verrou intra-processus acquis sans attente ;
concurrence refusée, aucune boucle de retry/sleep. Fichier temporaire dans
le même dossier, flush/fsync et os.replace ; nettoyage du temporaire sur
échec normal, publication complète pour lecteurs. Alerte exécutée après
commit dans son propre try : son échec ne répète jamais la mise à jour.

Un refus retourne False et émet un diagnostic fixe sans contenu privé.
La réponse fournisseur et son usage explicite restent disponibles ; les
compteurs locaux RPM/TPM continuent à recevoir l'usage. Ce snapshot est
un historique de compatibilité, pas le grand livre durable de facturation.
Un refus peut perdre cet événement historique : pas de queue/reprise ajoutée.
Pas de déduplication des appels réexécutés par un client, ni garantie power-loss.

Recette sur fichiers temporaires : alerte échouée après commit, remplacement
refusé laissant anciens bytes et aucun temporaire, second update exact,
JSON invalide/trop gros/incohérent conservé, concurrent refusé sans attendre
pendant publish suspendu, lecteur voyant ancien snapshot complet, capacité
tâches/overflow préservant le magasin. Le verrou interprocessus décrit ci-dessous complète désormais le verrou thread.
Tous les écrivains doivent utiliser ce protocole ; autres écrivains non qualifiés.
I/O/fsync synchrones, attribution active_project globale, lecture de tâches,
ACL et projection durable restent ouverts. Sources seules, non activé.


## Verrou interprocessus des statistiques

update_stats conserve le verrou thread immédiat et prend un verrou système
sans attente sur stats.json.lock avant lecture et jusqu'après publication.
Windows : msvcrt.LK_NBLCK sur le premier octet ; branche POSIX flock prévue
mais non qualifiée dans cette recette. Fichier latéral stable conservé,
jamais verrou sur le snapshot remplacé et jamais suppression du lockfile :
les écrivains coopérants partagent le même verrou malgré os.replace.
L'OS libère le verrou à la fermeture ou mort du détenteur ; existence du
lockfile n'indique pas un verrou encore détenu. Concurrence refusée sans retry,
événement historique peut être perdu comme indiqué au protocole précédent.

Deux recettes avec sous-processus Python réel : verrou détenu, update refusé
et anciens bytes préservés, sortie normale ou kill du seul helper fixture,
update suivant accepté avec total exact et fichier latéral conservé.
I/O toujours synchrones, writers extérieurs/anciens non coopérants, suppression
malveillante du lockfile, systèmes de fichiers réseau et reprise durable
restent hors qualification. Aucun changement des données ou services actifs.


## Suppression de l'attribution globale implicite

Les routes chat/stream/embeddings auxiliaires n'appellent plus le bootstrap
protocole : aucune lecture de tâche active, injection de rappel dans les
messages, session éphémère ou log de violation. Gemini et replis ne consultent
plus get_active_task_and_mode pour la comptabilité. Sans contexte authentifié,
usage sous bucket unattributed.<catégorie>, catégorie issue de l'alias
auxiliaire/embedding ; X-DevCore-Attribution=unattributed. Ancien en-tête
X-DevCore-Task hors streaming contient ce bucket, pas une tâche métier.
Les anciens snapshots sont conservés, nouvelles données sans attribution
projet/utilisateur. Les seuils de compatibilité sont agrégés par catégorie.

La route SSE fournit sa catégorie au générateur ; appel interne sans
catégorie utilise auxiliary, catégories invalides refusées avant amont.
Fonctions historiques/export de protocole restent disponibles pour compatibilité,
mais ne sont plus appelées par ce chemin HTTP. Fournisseur/modèle, messages
et input ne sont pas changés par un état global. Le factory d'observation
OTLP explicite reste responsable du contexte authentifié de l'application.

Quatre recettes ASGI chat/stream/embedding/Cerebras avec deux contenus alpha/
beta : hooks globaux remplacés par refus immédiat, contenu upstream exact,
en-tête non attribué et statistiques par catégorie. Régressions d'usage
mises à jour pour vérifier ces buckets ; fixture d'admission SSE reçoit
la catégorie explicite. Pas d'identité/ACL implémentée sur Router, aucun
gain de tokens ou isolation complète revendiqué. Sources non activées.
