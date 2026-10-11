# Recherche mémoire — raccordement des embeddings

Sources de recette, non activées. Profil individuel : recherche globale
reste fermée, contexte enregistré et droits projet inchangés.

## Chemin

Cockpit compatibilité → EmbeddingService → Router20130/v1/embeddings,
modèle gemini-embedding-001, dimensions768. Un seul embedding par query,
transmis aux collections Qdrant demandées en parallèle. Aucun vecteur nul
384 artificiel. Collections autorisées : decisions, lessons, patterns,
codebase (noms hérités, existence/contenu non qualifiés).

Query non vide <=8192 octets UTF-8, limit entier1..20, collections1..4
uniques dans la liste autorisée, refus avant appel amont. Contrat moteur
version gemini-embedding-001:768:v1 ; input moteur <=32768 octets.
Vecteur768 de nombres finis non booléens, norme finie non nulle. Modèle
retourné s'il est présent doit correspondre ; un seul résultat index0.

## Bornes et dégradation

Embedding : corps raw <=128 Kio, encoding identity, fermeture succès/refus/
annulation. Qdrant : <=1 Mio par collection, hits liste <=limit, diagnostics
fixes sans message privé. Pas de redirections ; client possédé trust_env=False.
Deadline coopérative5 s pour embedding et collections, timeout réseau3 s.
Parser JSON/allocations et chargement local restent synchrones : pas de borne
RSS ou murale stricte annoncée.

Résultat API : search_mode vector ou unavailable, degraded booléen,
métadonnées modèle/dimension/version seulement après embedding validé ;
statut/raison par collection. Embedding indisponible/invalide : aucun appel
Qdrant, zéro résultat, statut explicite ; échec collection : hits vides et
reason mémoire indisponible. Aucune recherche lexicale de remplacement
implémentée, pas de résultat vectoriel artificiel. Annulation externe propagée.

## Limites

Pas de fournisseur authentifié ni de corpus sémantique réel testé. Dimension,
modèle et provenance des vecteurs stockés restent à réconcilier avant activation.
RRF, lexical, projet/principal et pertinence sémantique restent ouverts.
Le contrat de transport des hits est désormais validé, voir sources v104. Nouvel appel d'embedding peut consommer des tokens
à chaque query ; cache/gain/cost non mesurés, aucun appel réel en recette finale.

Recette HTTPX MockTransport avec AsyncByteStream, API legacy et refus du profil
individuel ; racines temporaires avant imports. Le lanceur réel du test de
démarrage individuel est désormais substitué, ancien patch uvicorn.run
étant devenu inefficace après introduction de run_managed.

## Simulateur Qdrant local — sources v103

Le serveur Python se présente comme simulateur DevCore, sans usurper une
version Qdrant. Collections Cosine, dimensions1..4096 ; vecteurs liste de
nombres finis non booléens, norme finie/non nulle. Normalisation avant
produit pour limiter les débordements. Requête/batch invalide400 ; collection
inconnue404, sans création par GET ou upsert ; ancien vecteur invalide503
sur toute la recherche, aucun hit artificiel. Reconfiguration non vide refusée.
Filtres/options inconnus refusés : aucune prétention d'ACL par filtre.
Scroll sans vecteur, mais pagination non implémentée : refus si limit tronque
la collection ou si offset est demandé, plutôt qu'une fin de parcours fictive.

Import/GET/recherche ne sauvegardent pas. JSON corrompu ou schéma incompatible
conservé, service indisponible et mutations interdites. Chaque mutation
valide un candidat puis écrit un temporaire, flush/fsync et replace ; état
mémorisé publié après succès seulement. Verrou RLock dans le processus :
aucune garantie entre processus, aucune qualification non bloquante.
Chargement/copie/calcul/JSON/I/O synchrones ; HTTP lecture de corps sans
deadline globale, snapshot et nombre de points non bornés. Ce simulateur
reste insuffisant pour une plateforme multiutilisateur professionnelle.

38 tests de contrat simulateur, pipeline Cockpit et embedding moteur passent
sur racines temporaires ; HTTP local sur port éphémère uniquement, fournisseurs
substitués. Sources non activées. Provenance sémantique des vecteurs, vrai
Qdrant, projet/principal et corpus réel restent ouverts.

## Résultats de recherche Cockpit — sources v104

Le décodage refuse les doublons de clés JSON, NaN/Infinity et profondeur>64
avant publication. Scan coopératif par64 K caractères ; parse/UTF-8 restent
synchrones. Racine objet, statut ok si présent, result liste bornée par limit.
Identifiant entier non booléen uint64 ou texte UTF-8 non vide<=128 octets,
sans contrôle ASCII ; identifiants uniques dans chaque collection. Scores
Cosine finis non booléens dans[-1,1], ordre décroissant (égalités acceptées).
Aucune compatibilité revendiquée avec collections Dot/Euclid.

Payload objet ou null/absent normalisé en{} ; valeurs finies et UTF-8 valide,
<=64 Kio sérialisés par hit, <=4096 nœuds cumulés par collection. Parcours
coopératif chaque64 nœuds ; borne du corps HTTP1 Mio conservée. Un seul hit
invalide refuse toute la collection : diagnostic fixe, aucun détail du
payload amont ; autres collections valides conservées avec degraded=true.
Sortie limitée à id/score/payload, pas de vecteur/debug/attribut inconnu.
Annulation du scan/parcours propagée ; aucun worker détaché.

60 tests ciblés réussis sur racines temporaires :22 nouveaux cas, dont20
réponses incorrectes avec seconde collection valide, projection valide et
annulation. Aucun réseau fournisseur réel ni index actif. Ce contrat ne
valide ni projet/principal, ni fraîcheur/provenance ou pertinence d'un hit ;
payload reste du contenu non fiable. Profil individuel toujours fermé à
la recherche mémoire globale. Sources non activées ; gain tokens non mesuré.
