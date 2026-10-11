# Deux chemins LLM — 4 octobre 2026

Instruction utilisateur : conserver le fournisseur et le modèle natifs ; Gemini
seulement pour des tâches auxiliaires explicitement choisies.

## Contrat livré

| Usage | Entrée | Amont |
|---|---|---|
| OpenAI / Codex API | 8787 `/v1/responses` | `https://api.openai.com` |
| Claude | 8787 `/v1/messages` | `https://api.anthropic.com` |
| Gemini natif / Cloud Code Assist | 8787, protocole natif reconnu | Google natif, modèle conservé |
| Auxiliaire | 8789 `/v1/chat/completions` | Router 20130, puis Google |
| Embeddings | 20130 `/v1/embeddings` | `gemini-embedding-001` |

`Scripts/headroom_routes.py` est la source de vérité du lancement. Deux processus,
backend direct, model_router désactivé, paramètres explicites, settings isolés,
stateless et compression structurelle sans perte ; Kompress et outils CCR injectés
désactivés. Les headers permettant de modifier l'upstream et les écritures admin
sont refusés. 8789 ne publie ni Responses, ni Messages, ni embeddings, ni les
endpoints Google natifs. 8787 refuse les alias DevCore et les options de repli.

Router : uniquement `devcore-writing`, `devcore-documentation`, `devcore-summary`,
`devcore-bulk`. Un mode seul, les anciens alias coding/reasoning et les noms natifs
sont refusés avant lecture du contexte protocolaire ou réseau. Le registre de
capacités ne remplace plus le modèle de cette route. Les profils Python/PowerShell
coding/reasoning/plan gardent le modèle de l'application ; bulk est auxiliaire.
Les candidats de l'ancien registre restent des métadonnées, sans pouvoir de routage.

Secours : `fallback_providers: ["cerebras", "nvidia"]` autorise explicitement les
providers listés, dans cet ordre fixe de préférence. Par défaut aucun secours.
Flux/embeddings refusent ce paramètre non vide : aucun repli de streaming qualifié.
Les paramètres internes sont supprimés avant envoi au fournisseur. L'URL Google
compatible est corrigée : `/v1beta/openai`, sans suffixe `/v1` supplémentaire.
Google documente cette base : https://ai.google.dev/gemini-api/docs/openai.

Le contrat EmbeddingService expose directement 20130 et produit maintenant
`input` au format compatible OpenAI ; l'ancien champ REST Google `contents`
est retiré de cette fabrique. Aucun appel d'embedding authentifié rejoué.

8788 est facultatif et auxiliaire seulement : alias explicite, cible 8789 ;
superviseur ne le démarre plus pour Claude. La traduction reste limitée au texte ;
Claude natif utilise directement 8787 et conserve son protocole/outillage.

`init_agent_env.ps1` affiche les paramètres ou lance UNE application avec un
environnement enfant. Aucun changement User/Machine/parent. `-Scope User` retiré.
PowerShell 7 requis pour ArgumentList et le contrôle HTTP sans génération.
Codex Desktop n'est pas automatiquement redirigé par ces variables : son fournisseur
actuel reste openai, sans preuve de passage par Headroom. Aucun changement du modèle
ou de la configuration Codex effectué. L'authentification abonnement et Antigravity
réel restent à qualifier ; les endpoints natifs non reconnus sont refusés.

## Métriques et limites

Supervision bornée : magasin local `DEVCORE_LOCAL_ROOT/Runtime/service_restarts.sqlite3`,
réservation atomique par hôte/port, bail 60 s, au plus trois lancements sur dix
minutes et délais minimaux 5/10/20 s. Échec de réservation = aucun lancement.
Budget conservé même en cas de succès pour borner les services qui oscillent.
Bail expiré récupérable, ancien propriétaire incapable de libérer un nouveau bail.
L'attente de démarrage utilise un délai total monotone <=30 s. Le contrôle HTTP
Headroom est un enfant stdlib avec réponse <=32 KiB, sans proxy/redirection,
arrêté par le parent après 3 s. Contrôle réussi sur les deux Headroom actifs.
**62 tests réussis en 8,48 s** sur le budget, le lancement historique et le contrat.
Le polling générique reste fondé sur le port. Pour Headroom, la qualification
complète est désormais exigée avant retour positif ou événement ServiceAutoHealed
(status READY, verification route_contract). Un port occupé par un mauvais profil
n'est pas redémarré automatiquement. **65 tests réussis en 10,96 s** après ce
correctif ; délai de sonde ajusté au temps de démarrage restant.
Contrôle final du délai ajouté : aucune réussite constatée à son expiration
ou après ne publie de reprise. **67 tests réussis en 9,54 s** avec deux cas
de dépassement simulés, sur racines temporaires.
Le processus directement lancé doit aussi rester vivant jusqu'à validation.
Sortie prématurée, même code zéro : échec journalisé, bail libéré, budget conservé.
**71 tests réussis en 11,43 s** ; quatre cas supplémentaires simulés.
Un wrapper qui délègue puis termine n'est pas un lancement direct qualifié.
Budget incohérent : réservation refusée explicitement et état conservé,
sans remise à zéro automatique. Horloge non finie/invalide rejetée avant écriture.
**84 tests réussis en 16,52 s**, dont treize cas de cohérence supplémentaires.
Scheduler, identité du processus, compte de service et magasin
privé restent hors de cette qualification. Aucun redémarrage réel provoqué.

Le lanceur et le superviseur utilisent maintenant le même contrat pur
`devcore_engine/infra/llm_route_contract.py`. Une identité/route annoncée ne suffit
pas : status ready, port, toutes les options de profil et leurs types sont
comparés. Model_router doit rester null, upstream natif exact, auxiliaire vers
20130 et protections actives. Le contrôle PowerShell compare également le profil
complet et a réussi sur les services actifs. **132 tests réussis en 22,50 s**,
dont 48 contrôles du contrat. Ce JSON ne constitue pas une attestation cryptographique
du processus ; identité OS, daemon scheduler et arrêt des descendants restent
à qualifier. Le budget local et le bail de lancement sont décrits ci-dessus.

Compacteur mémoire raccordé à 8789 avec `devcore-summary`, `task_type=summary`
et aucun secours par défaut ; l'ancien override DEVCORE_ROUTER_URL est ignoré.
Proxy HTTP hérité et redirections désactivés, réponse limitée à 1 MiB. En cas
d'échec/invalidation, les lignes originales sont conservées par cette fonction.
La publication globale de LESSONS.md reste historique et n'est pas qualifiée
pour des écritures concurrentes ; aucun compactage des données actives exécuté.
Trois lanceurs d'application testés par un vrai processus enfant : variables
de la route sélectionnée uniquement et arguments/chemins avec espaces préservés.
Ce test ne prouve pas que Codex Desktop honore OPENAI_BASE_URL. Suite totale :
**84 tests réussis en 18,59 s**, CI distante non exécutée.

Lecture HTTP bornée : 16 MiB et délai total de 30 secondes, sans remise à zéro
par fragment. Expiration 408 avant appel amont, déconnexion sans envoi, annulation
propagée. Une requête lente laisse passer les autres. Le délai ne borne pas la
génération du fournisseur ni le flux de réponse. Les fragments de réponse sont
relayés immédiatement. `/healthz` retourne 503 jusqu'à `app.state.ready=True`
après le démarrage Headroom ; l'identité seule ne suffit plus à qualifier la route.

Suite étendue : **59 tests réussis en 11,97 s** sous Python 3.13, comprenant sept
contrôles ASGI de durée, concurrence, fragments, taille, déconnexion, annulation
et readiness. Pas de listener réel ni fixture active ; un avertissement, zéro skip.
La sonde précédente Headroom installée n'a pas été répétée pour cette extension.

Chaque instance expose `/metrics` et `/devcore/routes` indépendamment ; la seconde
vue contient au plus 256 métadonnées de requêtes, sans prompts ni secrets : route,
requested_model, resolved_model, provider, task_type, status. Pour le natif, la
résolution reflète le modèle conservé par le proxy, pas une attestation du modèle
servi en interne par le fournisseur. Router émet les mêmes dimensions en headers
et logs de résolution ; son JSON historique devient `gemini_auxiliary_stats.json`.
Les anciens `headroom_stats.json` restent historiques et ne prouvent aucun gain
natif. Flux : headers de résolution avant réponse, pas preuve de succès complet.
Compteurs anciens par tâche/projet actif : attribution multiutilisateur non qualifiée.
WS Responses natif : admission ASGI vérifiée sur chaque frame response.create,
format plat ou response enveloppé, modèle OpenAI explicite obligatoire à chaque
frame. Refus 1008 des alias auxiliaires, modèle absent, JSON invalide/binaire,
frames >16 MiB, autres types et options de substitution dans enveloppe/payload.
Les frames admises restent identiques ; pas de changement de modèle implicite.
18 cas ajoutés, total **77 tests réussis en 12,13 s**. Transport WebSocket réel
avec fournisseur, reprise/reconnexion/cancel et métriques WS non qualifiés.
Compression longue, charge et
gains de tokens à qualité comparable restent ouverts. Aucune dépense API de recette.

## Activation locale réalisée

Après arrêt par l'utilisateur via stop.ps1, les quatre ports ont été vérifiés
libres. Lancement caché autorisé : natif PID 5744, auxiliaire PID 8852, Router
PID 9844. Readiness réelle 200/ready sur 8787/8789 ; Router auxiliaire policy_version2
sur 20130. Tous écoutent 127.0.0.1 ; 8788 reste arrêté. Contrôle de conformité
sans génération réussi : gpt-4o/codex-mini/claude-test refusés HTTP400 sur 8789
et 20130. Ces refus précèdent les lectures/écritures métier et appels fournisseurs.
stop.ps1 inclut maintenant 8789 et cible seulement les connexions Listen.

Logs de cette activation :
`C:/Users/Administrateur/AppData/Local/Temp/devcore-llm-activation-742eb0f85ee5446b9bc34a45d2c5ba34/`.
Appels authentifiés, intégration des applications et économies non qualifiés.
Les résultats ci-dessous décrivent les tests et l'ancien obstacle désormais levé.

Recette locale : **52 tests réussis**, contrôles PowerShell de profils réussis,
et **2 tests réussis avec Headroom 0.34.0 installé** sous Python 3.14. Ces deux
sondes interceptent les requêtes HTTP en mémoire, bloquent les connexions externes
et vérifient URL/provider/modèle sur Responses et Messages. Les 52 autres tests
utilisent Python 3.13 de recette, racines temporaires et clés factices. Une tentative
initiale de sonde a été interrompue sans compter son résultat ; le garde réseau
a ensuite été corrigé pour autoriser le socketpair localhost d'asyncio Windows.
Les passages antérieurs ne sont pas additionnés. CI enrichie, non exécutée à distance.
Snapshot/wheel candidat antérieur inchangé : cette livraison de routage est dans
les sources du dépôt, sans nouvelle qualification de ce bundle.

Les anciens processus ont été identifiés : Headroom 8787 upstream Router, Router
20130 et adaptateur 8788. Leur remplacement a été refusé par le contrôle automatique
(`blocked by policy`), sans motif plus précis. L'ancienne configuration demeure
active à ce moment-là ; cet obstacle a ensuite été levé par l'arrêt utilisateur
et l'activation locale décrite ci-dessus.

Depuis un terminal PowerShell 7, arrêter les anciens services via leur gestionnaire
après vérification des lignes de commande (pas un kill générique de Python). Puis :

```powershell
Set-Location E:/src_python/devcore
& DEV_CORE/Scripts/headroom_start.ps1 -Route native -Check
& DEV_CORE/Scripts/headroom_start.ps1 -Route auxiliary -Check
# Après arrêt des anciennes instances, lancement caché des deux routes :
& DEV_CORE/Scripts/headroom_start.ps1 -Route native
& DEV_CORE/Scripts/headroom_start.ps1 -Route auxiliary
Start-Process -FilePath C:/Python314/python.exe `
  -ArgumentList '"E:/src_python/devcore/DEV_CORE/Scripts/gemini_router.py"' `
  -WindowStyle Hidden
# Garder 8788 arrêté ; facultatif uniquement pour les alias auxiliaires.
& DEV_CORE/Scripts/test_agent_conformity.ps1
```

Le superviseur contrôle maintenant l'identité du service et la route de `/healthz`
après le port. Un ancien listener n'est plus déclaré qualifié. Prévoir ensuite une
requête authentifiée native par application et une requête auxiliaire choisie,
avec preuve du modèle, fournisseur et compteurs ; elles ne sont pas exécutées ici.


## Admission HTTP et JSON bornée

Router (chat/embeddings directs) et adaptateur auxiliaire lisent désormais le
corps par chunks : total 16 Mio, deadline globale 30 s non renouvelée. Refus
413/408 avant état/protocole/fournisseur ; déconnexion et annulation externe
ne déclenchent pas de repli. Décodeur partagé avec Headroom HTTP/WS : JSON
UTF8 valide et au plus 64 niveaux, crochets dans les chaînes ignorés.
JSON invalide/profond : HTTP 400, WS 1008 sans transfert de la trame invalide.
Modèles/fournisseurs et contenu JSON admis restent conservés par la garde native.
Le plafond de profondeur est une nouvelle contrainte de compatibilité.
102 tests locaux réussis ; provider authentifié, charge/CPU du parsing,
quotas agrégés, admission des connexions et activation encore ouverts.


## Capacité simultanée des chemins LLM

Headroom natif/auxiliaire, Router et adaptateur : huit requêtes POST ou sessions
WS simultanées par instance ASGI. Refus avant lecture du corps : HTTP 503
service_capacity_exceeded avec Retry-After: 1 ; handshake WS refusé via close
ASGI 1013 (le serveur peut répondre HTTP 403 avant acceptation du handshake).
Pas de file interne ni de nouvelle tentative automatique. GET/sondes et lifespan
ne consomment pas ce budget. Créneau maintenu durant flux et nettoyage ASGI ;
finally le libère en cas d'erreur/annulation. Les instances sont indépendantes.
100 tests réussis, dont huit requêtes bloquées puis neuvième refusée dans les
vraies applications Router/adaptateur, sondes accessibles et admission rétablie.
Ce plafond est local à une instance/boucle ASGI ; plusieurs workers multiplient
la capacité. Pas de quota utilisateur/projet ni de garantie d'équité ou de borne
RSS/CPU ; TCP avant ASGI, parsing synchrone, fournisseur et charge à qualifier.
Services actifs non rechargés.


## Lecture et contrôle de profondeur coopératifs

Le scan JSON HTTP/WS cède la main tous les 64 K caractères, en conservant
profondeur/chaînes/échappements entre blocs. Annulation arrête ce scan dans la
même coroutine, sans worker abandonné. Tampon HTTP bytearray unique, y compris
avec beaucoup de chunks vides/petits ; plus de liste conservant chaque chunk.
Lecture ASGI directe dans le Router/adaptateur : Request.stream masque les
événements vides ; ils sont désormais comptés avec yield tous les 64 événements
pour faire respecter le délai même lorsque receive répond immédiatement.
Headroom applique la même règle. 107 tests réussis : sonde disponible avant
la fin du scan d'un corps de 2 Mio, corps intact, deadline sur flux de chunks
vides, échappement traversant une frontière, annulation et drainage/routage.
UTF8, conversion du tampon et json.loads restent synchrones ; durée/RSS réelle
et charge complète non qualifiées. Aucun changement des limites 16 Mio/30 s/64
niveaux/huit requêtes, ni du routage ; services actifs non rechargés.


## Diagnostic de capacité par instance

GET /devcore/admission expose schema_version=1, scope=asgi_instance, capacity,
active, peak_active, admitted, finished, exceptions, cancelled, rejected_http,
rejected_websocket et counters_saturated. Compteurs plafonnés à 2^63-1, flag
de saturation explicite ; réponse sous 1 Kio, Cache-Control: no-store.
Disponible sans utiliser de créneau, même à saturation, via la garde Headroom
et les middlewares Router/adaptateur. Aucun corps, header, query, prompt, modèle,
identifiant utilisateur/projet ni secret collecté. Pas de lecture DB/disque.
finished indique retour normal ASGI (peut comprendre HTTP 400/500), pas succès
métier/provider. Exceptions et annulations propagées, capacité toujours libérée.
Compteurs locaux volatils depuis la création de la garde, non agrégés entre
workers, non persistés ; diagnostic technique non authentifié pour le pilote
localhost. Il ne certifie ni readiness ni fournisseur/model/tokens.
90 tests réussis ; vraie chaîne LLMOps, authentification et charge restent ouvertes.
