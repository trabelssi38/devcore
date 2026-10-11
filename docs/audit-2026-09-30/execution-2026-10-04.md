# Journal DevCore - 2026-10-04


## L2/L4/L9 — Qualification HTTP/CLI/MCP du runtime candidat

- Reprise : fiche v29, décisions, journal du runtime, état Git et tests pertinents
  avant modification. DevCore contexte/statut disponibles ; board 384/389
  historique, pas un certificat des lots. RepoWise ne connaît pas les tests
  stdio récents ; index neuf jours, mock/sémantique absente, sources locales
  confrontées. Index réel et données actives non modifiés.
- Runtime E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe,
  Python 3.13.16/SQLite 3.53.1 : **216 tests réussis en 795,61 s**, zéro skip/échec,
  un avertissement connu Starlette/httpx. Neuf fichiers : HTTP audit, sessions
  navigateur et contexte ; MCP contexte/tâches/CLI/suppression/audit et stdio.
  Lecture seule, droits croisés, révocations, versions, réponses bornées et
  invalides, réponse perdue, absence de retry, wheel installé et échanges stdio
  réels couverts selon les assertions de ces fichiers. Cela ne certifie pas
  tous les endpoints historiques ni l'ensemble CI.
- Racines DEVCORE_LOCAL_ROOT/DATA_ROOT temporaires avant lancement/imports ;
  outillage build séparé existant fourni explicitement. Aucun test sur Dropbox,
  données actives ou index réel. Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-runtime-http-mcp-c671f1fcf81b46dd8127fa1faa11c187/tests.txt,
  SHA-256 a73dd37d45a16826c4e615912ca6ac5fc22f062cfada24db6f34dd309b930d44.
- Artefact moteur construit sur copie des sources dirty et conservé :
  E:/DevCoreRuntime/releases/devcore-py31316-20261003/artifacts/wheels/devcore_engine-10.2.0-py3-none-any.whl,
  SHA-256 486dfdf1f19fdecbb2935781fc089c4983caac4e104bec926300f34961e6ec07.
  Manifest avec commit + empreintes des sources, SHA-256
  a0118d1795c295cc4b1a551388864b0695986174a2aa2f79bc67e56052fc40c7.
  Wheel installé --no-deps dans le candidat ; individual --help hors dépôt,
  sans PYTHONPATH charge site-packages et ne crée pas les racines de magasins.
  Ce help n'est pas une opération authentifiée. Les opérations wheel/API réelles
  sont qualifiées dans les fixtures de la suite, sur wheel construit par le test.
- 54 paquets compatibles via uv pip check. Liste et provenance actualisées :
  provenance.json SHA-256
  3e1c4fccaa6e8cd67a511d160f49dd4181e300ad83130176f3dec71968575dfc.
  Le paquet exclut Dashboard/API/MCP serveur : pas une release d'instance complète.
- Qualification applicative partielle du candidat ; runtime actif/configurations
  conservés. Service Windows, autres canaux/mutations auditées, deux profils
  navigateur, charge et bascule/restauration opérationnelles restent ouverts.
  Pas de CI distante globale, pas de gain de tokens ni reprise IA neuve qualifiés.
  Automatisation conservée ; préparation de release complète et qualification
  des autres critères nécessaires avant activation.

- Fiche v30/manifeste actualises : 11 577/12 000 octets UTF-8, aucun
  avertissement, decisions inchangees. card_sha256
  49783be1e365c35770659e746207b35e2c3ac452a6b2dff435b0fa38a812b0c4.


## L2/L9 — Snapshot individuel des scripts serveur et du Cockpit

- Reprise fiche v30 et décisions, Git et journal du passage HTTP/MCP avant
  modification. Mémoire consultée pour les priorités d'isolation ; sources
  dashboard/server et fixtures concernées lues. Ancien index RepoWise inchangé.
- Constructeur build_individual_bundle.py et vérificateur : sept sources
  explicitement autorisées, SHA-256, pas d'identités/données/config/index.
  Liens/jonctions sources, destination interne, écrasement, source mutable,
  fichier absent/oversize et fichier supplémentaire refusés. Staging retenu en
  cas d'échec ; publication seulement après vérification. Manifestes modifiables
  non authentifiés : comparer leur SHA à une provenance fiable.
- Baseline du nouveau fichier : 6 réussites/1,28 s ; final **8 réussites/1,27 s**,
  zéro skip/échec, un avertissement connu Starlette/httpx. Changements concurrents
  et lien simulé ajoutés ; import HTTP du snapshot sur fixture avec génération
  de pycache interdite. Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-bundle-test-c7b7eb54876e43cfa823704c08042fc6/tests-final.txt, SHA-256 4db24201ba6111b5f3365e1bae8d7da429490cc4d66d12391fa93a99e48efcba.
- Snapshot réel publié sous E:/DevCoreRuntime/releases/devcore-py31316-20261003/individual-platform, manifest SHA-256 d38e0c16cf1bb7604811538f015d14bd38c47743b49268e331c81871c6ff9027.
  Construction et vérification CLI réussies. TestClient hors dépôt/sans PYTHONPATH
  charge le wheel moteur depuis site-packages, HTTP 200 page/JS, 403 route globale,
  401 tâches sans credential ; aucune racine de magasin créée. Aucun port/service
  actif touché. Magasin absent de recette, pas de fixture active/Dropbox.
- CI intègre ces huit tests dans la gate runtime ; AST/YAML valides, pas de CI
  distante annoncée. Procédure bundle-individuel-2026-10-04.md publiée.
- Limites : ce snapshot ne contient pas Python/dépendances/moteur et n'est pas
  une instance qualifiée. Scripts legacy par défaut conservés : lanceur fermé
  requis avant activation, parcours authentifiés depuis le snapshot et MCP,
  jonctions natives, droits privés, charge/service/rollback encore ouverts.
  Automatisation utile conservée ; aucun lot global clôturé.

- Fiche v31 et plan actualises : 11 584/12 000 octets UTF-8, aucun avertissement,
  decisions inchangees. card_sha256
  92899836ee721b5fc01d3bf2b68f905ff0c3fd24308582ab093fda3f47d34ac5.


## L2/L4/L9 — Lanceur Dashboard individuel et parcours authentifié du snapshot

- Reprise fiche v31/registre obligatoire, Git, journal snapshot et tests concernés.
  MCP contexte accessible ; mémoire lue pour isolation. Sources launcher/API,
  client individuel, NTFS et fixtures avant modification. Décisions inchangées.
- Ajout launch_individual_candidate.py : SHA manifeste obligatoire, vérification
  snapshot et recontrôle SHA, racines/identité explicites existantes séparées,
  chemins liés refusés, moteur sous sys.prefix, NTFS identité et SQLite corrigé.
  Force individual/127.0.0.1/CORS exact et proxy_headers=False avant serveur.
  --check sans listener/création/migration ; erreur générique code 2. Pas de MCP,
  pas de gestion de service Windows ou de bascule par ce lanceur.
- Premier passage 11 réussites/5,02 s ; ajout socket HTTP réel 12/9,97 s ; après
  recontrôle manifeste final **12 réussites en 9,45 s**, aucun skip/échec. Préflight
  Python -I sur magasin privé réel intact et environnement legacy, puis snapshot
  HTTP sur localhost temporaire : lecture alpha, refus beta/routes globales,
  clôture versionnée et audit Alice/done/v2, beta todo/v1 conservé. Processus de
  fixture terminé dans finally ; arrêt gracieux/service non qualifiés.
- Trace finale : C:/Users/Administrateur/AppData/Local/Temp/devcore-candidate-launcher-7ac9ff82c22243f9bcd079ba3c9b6cf7/tests-final.txt,
  SHA-256 2a78d0d01c0f642bb9811effc799c88b5d21f190fce004091041c0c517d7fbcb.
- Copie contrôleur/verifier sous release/candidate-control ; empreintes exactes
  conservées, manifest SHA-256
  a1923be9771b0406c0ceefa83d90ff628edf2bbbb04ca0337731b07a6a9b6df3.
  Snapshot initial inchangé. Données de tests sous racines temporaires avant
  imports/processus ; aucune donnée active, Dropbox ou index réel utilisé.
- CI inclut le fichier et installe le moteur non editable, nécessaire au contrôle
  sys.prefix dans les processus Python -I. AST/YAML/diff --check ciblés validés ;
  gate complète/CI distante non annoncées. Procédure lanceur-individuel publiée.
- Limites : MCP snapshot, code/runtime/parents NTFS, modifications post-vérification,
  compte de service, navigateur, charge et rollback encore ouverts. Pas de source
  sandboxée ni de vérification exhaustive des chemins Dropbox. Instance active
  et automatisation conservées, critères globaux non clôturés.

- Fiche v32/manifeste et plan actualises : 11 641/12 000 octets UTF-8,
  aucun avertissement, decisions inchangees. card_sha256
  12e1902caae5d93309f93b87e312a281fdc363c665ae0115e1f4dd4a1c9f220f.


## L2/L4/L7/L9 — MCP réel du snapshot via lanceur individuel

- Reprise fiche v32, décisions obligatoires, état Git, journal et sources/tests
  concernés avant modification ; outil DevCore contexte répond. Mémoire utilisée
  pour isolation. Aucune mise à jour d'index RepoWise ou de données actives.
- Vérificateur snapshot partagé extrait du lanceur HTTP ; nouveau lanceur MCP
  épingle le manifeste, exige moteur installé et credential NTFS, projet/origine
  explicites 127.0.0.1:port. Forces individual et capacités explicites avant import
  serveur. Default contexte seul, tâches disabled, audit/delete fermés ; delete
  exige write. Diagnostic de refus code 2 stderr sans secret, stdout MCP seul.
- Premier passage 19/33,28 s ; refus credential absent ajouté 20/24,98 s ; après
  contexte durable ajouté, final **20 réussites en 23,48 s**, zéro skip/échec.
  Deux fichiers HTTP12/MCP8 ; pas d'addition de passages répétés.
- Trois clients stdio Python -I/engine wheel installé sur snapshot HTTP temporaire :
  default contexte seulement, reader tâches/audit sans mutation, writer clôture
  sans suppression ; environnement legacy/write/delete/audit remplacé. Lecture
  Alpha, refus Beta, ping, clôture version1 et audit Alice/done/v2. Révocation du
  credential en session : HTTP401 à l'appel suivant. T-01 Beta todo/v1 préservé.
  Fiche/décision effective via API : <= 2 000 octets mesurés UTF-8, décision old
  superseded exclue. Racines MCP vides, snapshot inchangé, API et clients arrêtés.
  Ce transport qualifié n'établit ni injection Codex neuve ni économie de tokens.
- Trace finale C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-launcher-cd93549451044892ae6fbca3e703585c/tests-final.txt, SHA-256 b482c2a9db11532aacd84a0541b3fb9c2fc3ba0ddc3203dd3055d50f9e35a221.
  AST/YAML/diff ciblés valides ; gate CI ajoute le fichier, pas de CI globale.
- Contrôleurs v2 copiés sous E:/DevCoreRuntime/releases/devcore-py31316-20261003/candidate-control-v2,
  manifest SHA-256 324d35c970546344e2d07d2b7b4ee98b41618c2bc676208bfa2799c82e5f51da.
  v1 conservé. Snapshot plateforme et moteur inchangés, configuration active
  préservée. Doc lanceur-mcp-individuel-2026-10-04.md ajoutée.
- Limites : suppression/rotation/expiration/pannes snapshot non toutes rejouées,
  service/runtime/code NTFS, modification après vérification, charge/rollback et
  critères globaux ouverts. Timeout socket non global strict, --check n'atteste
  pas autorisation/disponibilité HTTP. Automatisation conservée.

- Fiche v33/manifeste et plan actualises : 11 711/12 000 octets UTF-8,
  aucun avertissement, decisions inchangees. card_sha256
  56df1afab8987073691a0920f46c3d3f44e06fb06102b3d12b341c1f4828056b.

## L7/L8 — Séparation explicite des routes natives et auxiliaires

- Instruction utilisateur enregistrée D-007 : 8787 conserve modèle/fournisseur,
  8789 auxiliaire vers Router 20130, embeddings directs ; aucun routage global.
  Consultation DevCore bornée au départ, RepoWise ciblé sur config Router (index
  neuf jours, mock/sémantique désactivée), puis code actuel et processus vérifiés.
- Headroom 0.34.0 installé sous C:/Python314 : endpoints natifs et backend direct
  confirmés dans le code ; options de changement de modèle/upstream identifiées.
  Scripts/headroom_routes.py fixe deux profils, model_router désactivé, settings
  isolés/stateless, compression structurelle sans perte et Kompress désactivé.
  Garde ASGI fermant overrides upstream, écritures admin et endpoints hors route.
  Native autorise Responses/Messages et protocoles Google reconnus ; WS natif
  autorisé mais non rejoué, Antigravity réel et authentification encore ouverts.
- Router refuse modèles natifs/anciens alias/mode seul avant état ou réseau.
  Quatre alias explicites ; registre de capacités retiré du choix réel. Secours
  seulement avec fallback_providers autorisé ; streaming/embeddings sans secours.
  Base Google compatible corrigée ; EmbeddingService produit input et endpoint
  direct. Adaptateur 8788 auxiliaire/8789 uniquement, plus lancé pour Claude.
- Profils workflow Python/PowerShell coding/reasoning/plan natifs ; bulk auxiliaire.
  Lanceur applications utilise un environnement enfant, sans User/Machine/parent.
  Inventaire des variables de routage inspectées : aucun override partagé présent.
  Configuration native Codex conservée, injection/passage Headroom non établis.
- Métadonnées route/requested_model/resolved_model/provider/task_type/status dans
  headers/logs et historique mémoire borné 256 par instance ; requested_provider
  et upstream_provider natifs vérifiés. Compteurs Headroom séparés par processus,
  JSON Router auxiliaire nommé gemini_auxiliary_stats.json. Ancienne attribution
  active_project et estimates : pas une qualification multiutilisateur ni économie.
- Recette Python 3.13 avec trois racines temporaires et clés factices : **52 tests
  réussis en 11,92 s**, zéro skip/échec, un avertissement ; contrat PowerShell OK.
  Passage final, sans addition des répétitions. Headroom installé : **2 tests
  réussis en 8,26 s**, HTTP intercepté en mémoire, connexions externes bloquées,
  fournisseur/URL/modèle identiques sur Responses et Messages. Sonde initiale
  interrompue sans qualification ; garde réseau corrigé pour socketpair Windows.
  AST/YAML/diff ciblés valides ; nouveau gate CI, exécution distante non attestée.
- Trace finale C:/Users/Administrateur/AppData/Local/Temp/devcore-routing-proof-552d6e1a35804113a391818e7861cdad/tests.txt.
  SHA-256 c4a9ded38a9362379dc2cfeedf0a9f45b2879dec9c9d4cfe732fa241675e84b4.
  Fiche v34 et D-007 : **11 866/12 000 octets UTF-8**, ligne JSON complète,
  aucun avertissement, décisions obligatoires D002/D003/D004/D006/D007 incluses.
  card_sha256 45ef39d899eddfd680e0c68002340ee91309a9df16b27fe7f1224233e51f561d ;
  manifeste 5b24c86142613dcb26bfbb213073ec41c58551dc0a6af0025b8fae566e7368e5.
- Remplacement des anciennes instances refusé par le contrôle automatique
  d'exécution : seul motif communiqué « blocked by policy ». Aucun processus
  arrêté/lancé par cette commande. Après refus, PIDs 7580 Router, 3780/15536
  Headroom 8787 upstream 20130, 20372 adaptateur encore présents, lignes vérifiées.
  **Architecture livrée dans les sources, pas activée** ; bascule indispensable
  via gestionnaire/terminal utilisateur. Procédure et limites dans
  separation-llm-2026-10-04.md. Snapshot/wheel candidat antérieur conservé.
  Authentification, longue compression, charge, tokens/qualité et lots L0–L9
  globaux restent ouverts ; automatisation conservée.

## L8 — Admission Headroom : durée, concurrence et readiness

- Lecture des preuves de séparation, tests concernés, Git et section L8 avant
  modification ; contexte MCP v34 avec D-007 chargé en 11 866/12 000 octets,
  sans avertissement. Board consulté via devcore_task_status ; aucun état de
  service ou critère de sortie déduit du board.
- Garde ASGI : lecture totale du corps limitée à 30 s (pas de renouvellement à
  chaque fragment), 408 avant amont ; taille 16 MiB préservée, déconnexion sans
  envoi et annulation externe propagée. Flux de réponse toujours transmis sans
  collecte/buffer complet. Readiness retourne 503 jusqu'à la fin du démarrage
  Headroom (`app.state.ready=True`), identité et profil restent consultables.
- Sept nouveaux cas : client lent et autre appel concurrent, deadline totale
  malgré fragments, émission progressive, corps excessif/déconnexion, annulation
  et readiness false/true. Recette Python 3.13 vérifiée présente, trois racines
  temporaires avant imports, clés factices et aucune requête fournisseur réelle.
- Passage final **59 réussites en 11,97 s**, un avertissement, zéro skip/échec ;
  AST et diff ciblés valides. Gate CI enrichi, CI distante non exécutée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-route-liveness-final-487efe4aaa564b00a8fbb27045c456bc/tests.txt.
  SHA-256 f0e1fea8ec4b9a44e005fd4c0334f1468e68f623d5207dedc1e8d9855645d1ac.
  Fiche v35 vérifiée : 11 934/12 000 octets UTF-8, sans avertissement,
  décisions obligatoires conservées.
- Limites : délai de lecture seulement, pas de délai global fournisseur/WS ;
  concurrence ASGI simulée, pas une mesure de charge de Headroom. La sonde
  installée précédente reste distincte, non répétée. Anciennes instances non
  arrêtées, refus automatique de bascule inchangé ; aucun nouvel essai de kill.
  Aucun changement de données actives/Dropbox, runtime ou bundle candidat.

## L8/L9 — Activation locale des routes séparées

- Utilisateur : anciennes instances arrêtées avec Scripts/stop.ps1, puis demande
  de continuer. Inventaire courant : zéro processus de routage et ports libres.
- Lancement caché réussi, sans arrêt forcé ni modification globale des variables :
  native PID5744/8787, auxiliary PID8852/8789, Router PID9844/20130.
  Deux contrôles Headroom /healthz 200/ready avec profils attendus ; Router
  service gemini-router, route auxiliary, policy_version2. Listeners 127.0.0.1,
  aucun 8788. Ancien refus de remplacement levé par arrêt manuel utilisateur.
- test_agent_conformity.ps1 réussi : six refus 400 gpt/codex/claude via 8789 et
  20130. Requêtes de refus uniquement, aucune génération/provider, pas de fixture
  dans les données actives/Dropbox. Readiness vérifiée, pas un test de charge.
- stop.ps1 ajoute 8789 et filtre State Listen pour ne pas viser un client TCP.
  Analyse syntaxique PowerShell seulement ; arrêt réel non rejoué car il clôture
  la session active et arrêterait les services nouvellement lancés.
- Logs C:/Users/Administrateur/AppData/Local/Temp/devcore-llm-activation-742eb0f85ee5446b9bc34a45d2c5ba34/.
  Appels authentifiés natifs/auxiliaires, Codex/Claude/Antigravity réels, mesure
  des tokens et lots globaux restent ouverts. Runtime et bundle antérieur inchangés.

## L8 — Admission native WebSocket

- Git/journal/tests concernés relus. Le garde déléguait les frames WS sans
  validation de modèle. Validation native HTTP extraite et appliquée à chaque
  response.create, format plat/enveloppé ; modèle explicite, options de provider
  interdites aussi dans l'enveloppe. Rejet 1008 arrête le handler sans transmettre
  la frame refusée. Binaire/invalide/type non pris en charge et >16 MiB refusés.
- 18 nouveaux cas ASGI sans réseau, dont refus après une première frame valide
  et intégrité des messages admis. **77 tests réussis en 12,13 s**, un warning,
  zéro skip/échec sous Python 3.13 et racines temporaires avant imports.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-native-ws-3c2985dec61242f7a8818166da8d2977/tests.txt.
  SHA-256 fae03bc1cf324cdcd78e3c7f4b8a83be1a13a538c7f07986e9e6bb3fcd101f75.
  Gate CI étendu ; CI distante non exécutée. Aucun appel fournisseur réel.
- Native PID5744 identité/lanceur vérifiés, rechargé en PID15716 ; les autres
  services conservés. Logs C:/Users/Administrateur/AppData/Local/Temp/devcore-native-ws-reload-d84e7db94b9e40a7b06b6b379bb71bf8/.
- Limites : admission ASGI seulement ; WS réel, types autres que response.create,
  annulation/reconnexion, métriques WS, applications authentifiées et économies
  restent à qualifier. Aucune mutation des données actives par un test.
  Après rechargement, readiness des deux Headroom et identité Router vérifiées ;
  conformité des refus natifs auxiliaires réussie. Fiche v37 actualisée/bornée.

## L7/L8 — Compacteur auxiliaire et environnement des applications

- Git/journal/tests concernés lus. Recherche ciblée des anciennes routes :
  Auto/memory_compactor.py demandait gemini-2.5-flash directement au Router,
  désormais refusé. Corrigé vers Headroom8789, alias devcore-summary, task_type
  summary, aucun repli. Override legacy ignoré ; pas de proxy hérité/redirection.
  Réponse bornée 1 MiB, originales conservées sur erreur/réponse invalide.
- Sept cas ajoutés : route explicite, payload, limites, indisponibilité/JSON
  invalide, et trois vrais enfants Python lancés par PowerShell7. Variables
  non pertinentes retirées, chemins/arguments avec espaces correctement transmis.
  Un premier wrapper -Command incorrect a été remplacé par un script fixture
  -File ; aucun changement du lanceur justifié par cet échec de test.
- Passage final **84 réussites en 18,59 s**, un warning, zéro skip/échec, Python
  3.13 de recette, racines temporaires avant imports/sous-processus, HTTP simulé.
  AST/diff ciblés valides, gate CI étendu sans exécution distante.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-caller-final-bf2034726f7343b9a39791f542e11df9/tests.txt.
  SHA-256 1648922674a787dacba3b7a01a6a211a8c71c8019693499811292f820719be1f.
  Fiche v38 vérifiée : 11 951/12 000 octets UTF-8, aucun avertissement.
- Aucune exécution de compactage sur LESSONS.md actif/Dropbox, aucun appel payant,
  ni changement du modèle/configuration Codex. La publication concurrente mémoire
  reste à qualifier ; ce compacteur historique ne fournit pas les ACL individuelles.
  Respect des variables par Codex Desktop/Antigravity et appels authentifiés ouverts.

## L8 — Contrat de santé complet, suivi actualisé

- Journal, Git, tests et section de supervision relus. RepoWise ciblé retrouve
  SystemWatcher, index neuf jours/mock sans recherche sémantique ; conclusions
  confrontées au code actuel. Recette Python3.13 présente.
- Contrat partagé extrait dans infra/llm_route_contract.py, sans accès aux
  magasins : configuration native/auxiliaire unique pour lanceur/superviseur.
  Validation stricte service/route/ready/port et de chaque option/type du profil.
  Un listener native pointant Router ou avec model_router réactivé est dégradé.
- Script de conformité vérifie aussi le profil complet, pas seulement l'identité.
  Contrôle réussi sur les trois services actifs et six refus natifs auxiliaires,
  sans génération ni accès métier. Contrat runtime inchangé : pas de recharge.
- 48 cas de contrat ajoutés ; suite **132 réussites en 22,50 s**, un warning,
  zéro skip/échec, racines temporaires avant imports/sous-processus. Tests des
  profils existants inclus. Syntaxe PowerShell et diff ciblés valides ; CI étendu,
  exécution distante non attestée. Aucun test sur données actives/Dropbox.
- Plan L8 actualisé, fiche v39 et manifeste : profil strict et nouveau résultat,
  budget vérifié sans avertissement. Document separation-llm mis à jour.
- Limites : déclaration JSON, pas attestation cryptographique/processus ;
  verrou de démarrage, backoff/restart borné et délais du probe restent ouverts.
  Tests métier de supervision globale non rejoués. Applications authentifiées,
  charge, économies réelles et critères de sortie L0–L9 toujours ouverts.

## L8 — Budget de redémarrage partagé et sonde bornée

- Git/journal/tests et superviseur relus. Réservation SQLite locale distincte de
  la base métier, par host:port, transaction BEGIN IMMEDIATE et attente verrou
  200 ms. Trois tentatives par fenêtre dix minutes, attente 5/10/20 s et bail60 s.
  Refus sur magasin indisponible/backoff/budget épuisé ; Popen échoué consomme
  une tentative ; libération seulement par son propriétaire, après chaque essai.
  Service en ligne : aucun magasin créé. Nouvelle vérification après réservation.
- Poll de démarrage corrigé : deadline monotone, attente <=30 s, délai socket
  ajusté au temps restant. Ancien calcul d'itérations doublait potentiellement
  l'attente. Création de processus portable, sans console sous Windows.
- Probe Headroom isolé dans un enfant Python -I : GET localhost fixe, pas de
  proxy/redirection, <=32 KiB de réponse, timeout parent3 s couvrant lancement,
  réseau et lecture. Enfant bloqué interrompu automatiquement ; résultat validé
  par le contrat complet. Probes réels readonly native/auxiliary réussis.
- **62 tests réussis en 8,48 s**, zéro warning/skip/échec : réservations concurrentes,
  persistance/backoff/limite, bail orphelin/ancien owner, échec lancement/magasin,
  démarrage borné, vrai enfant endormi interrompu, contrat et launch non importeur
  de JSON legacy. Python3.13 de recette, racines temporaires avant imports/enfants,
  processus de lancement simulés. Aucun redémarrage réel ni mutation active/Dropbox.
- Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-restarts-final-8bec80ec339143fcad2b568393fb22ef/tests.txt,
  SHA-256 23a259f3e02cd27e7cc9e466c8383d147f216ca63de5ad30ae2901245df28c05.
  CI enrichi, non exécuté à distance ; suite routage précédente132 distincte,
  pas d'addition des tests qui se recouvrent. Plan/fiche/document de suivi actualisés.
- Limites : garde pour check_and_heal_service seulement, daemon scheduler séparé
  encore non borné. Bail temporisé, pas attestation OS du processus ni arrêt de
  descendants. SQLite local privé/compte de service et résistance à modification
  externe non qualifiés. Processus démarré mais non prêt peut survivre au délai ;
  budget borne les tentatives, pas ces processus. Event ServiceAutoHealed annonce
  l'ouverture du port, qualification Headroom appliquée ensuite au rapport.
  Aucun appel audit_and_heal global sur instance active ; règles disponibles au
  prochain passage source. Appels IA authentifiés/charge/tokens restent ouverts.
  AST/YAML/diff ciblés valides ; fiche v40 : 11 956/12 000 octets UTF-8,
  aucun avertissement et décisions obligatoires conservées.

## L8 — Événement de reprise fondé sur readiness

- Git/journal/tests relus ; corrigé le faux signal identifié au passage précédent :
  Headroom ne retourne plus true sur le seul port et ne publie plus AutoHealed
  avant validation du profil complet. READY/route_contract dans l'événement ;
  autres services gardent ONLINE/tcp_listener sans prétendre être prêts.
- Port déjà occupé et profil incorrect : false, aucun lancement ni événement.
  Sonde de reprise bornée par le temps restant du délai monotone de démarrage.
- Trois cas ajoutés : mauvais profil actif, reprise non prête/qualifiée ;
  **65 tests réussis en 10,96 s**, zéro avertissement/skip/échec sous Python3.13,
  racines temporaires et faux lancements. Le vrai enfant bloqué de la suite est
  arrêté après trois secondes. Aucun test des données actives/Dropbox.
- Diff ciblé valide ; plan, document séparation et fiche v41 actualisés.
  Supervision source disponible au prochain passage ; services IA non rechargés
  car contrat runtime inchangé. Scheduler/identité OS/descendants et lots globaux
  restent ouverts. Automatisation conservée.

## L8 — Refus d'une reprise constatée après le délai

- Relecture contexte MCP, état Git, journal et tests. RepoWise trouve le
  superviseur, mais son index a neuf jours et sa recherche sémantique est
  désactivée : vérification effectuée directement sur la source actuelle.
- Correction du délai de démarrage : même une sonde TCP ou Headroom réussie
  ne peut publier ServiceAutoHealed si elle termine à la deadline ou après.
  Deux scénarios simulent le dépassement sur service générique et natif.
- **67 tests réussis en 9,54 s**, zéro échec/skip, Python 3.13 de recette ;
  racines local/data/platform temporaires définies avant imports et enfants.
  Aucun lancement réel de service ni test sur données actives/Dropbox.
  Trace tests.txt SHA-256
  C:/Users/Administrateur/AppData/Local/Temp/devcore-restart-deadline-6e74900a4a4041cdb426bf729bd87b01/tests.txt,
  023c471c93d6bc3ac2a1d9a8a9ab244cd9fb94cd01de261c9a844a53907a3347.
- Diff ciblé valide. Plan et fiche actualisés. Processus non prêt éventuellement
  survivant, descendants, identité OS et scheduler restent à qualifier ;
  aucun succès global L0–L9 ni gain de tokens annoncé. Automatisation conservée.

## L8 — Détection d'un processus mort pendant le démarrage

- Contexte et statut DevCore consultés, Git/journal/tests relus. Statut MCP
  historique T-388 : ne prouve pas les critères de sortie du plan. RepoWise
  retrouve le superviseur, index âgé de neuf jours ; source actuelle vérifiée.
- Le superviseur conserve désormais le handle Popen et vérifie sa terminaison
  avant l'attente et avant d'annoncer la reprise. Un enfant déjà terminé, même
  avec code zéro, produit un échec explicite avec code de sortie, libère le bail
  et conserve le budget consommé. Aucune boucle d'attente inutile ni succès
  attribué à cet enfant sur le seul port ouvert par un autre processus.
- Quatre scénarios simulés : codes 0/17, terminaison immédiate ou après readiness.
  Suite **71 tests réussis en 11,43 s**, Python 3.13 de recette, trois racines
  temporaires avant imports/enfants ; aucun service réel lancé ou arrêté.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-startup-exit-d074cf9d062b4822a19668ca8e853d30/tests.txt,
  SHA-256 fa2624303390989c000a36cb8828367d7c8f6a8419cf8e384f285b1fcf665909.
- Diff ciblé valide ; plan, fiche et document de suivi actualisés. Contrat de
  lancement direct requis : un wrapper qui quitte après délégation ne constitue
  pas une reprise qualifiée. Pas d'attestation du propriétaire OS du port ni
  arrêt des descendants ; un enfant non prêt peut encore survivre au timeout.
  Scheduler, qualification globale et économie de tokens restent ouverts.

## L8 — Budget de reprise invalide : refus sans remise à zéro

- Contexte et statut MCP, Git et journal relus. Lecture ciblée du scheduler,
  retrouvée via RepoWise (index neuf jours, sémantique désactivée) : son bail
  JSON et ses écritures historiques ne constituent pas une réservation atomique
  qualifiée. Cette voie reste ouverte, sans démarrage ni mutation du scheduler.
- Le magasin de reprises refuse désormais un état incohérent avant tout calcul
  de fenêtre : compte hors 1..3, horodatage négatif/non numérique/non fini,
  prochaine tentative avant début, bail incohérent. Refus explicite
  restart_state_invalid ; ligne conservée, aucun effacement/repli automatique.
  Clé vide/trop longue et horloge invalide refusées avant création du magasin.
- Treize cas ajoutés ; **84 tests réussis en 16,52 s**, Python 3.13 de recette,
  racines temporaires définies avant imports/enfants, aucun test actif/Dropbox.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-restart-corruption-9c0d6f9a7e1f47a9adbfa6bb4d22539b/tests.txt,
  SHA-256 570f297272ae468dede423c1e4b014bcbd7aaf5d170696d3df888efcac2fd7ef.
- Diff ciblé valide. Plan, fiche et document de suivi actualisés. Contrôle de
  cohérence seulement : absence d'authenticité cryptographique ou ACL qualifiée
  de ce sidecar. Concurrence testée par threads, attestation OS et arrêt des
  descendants ouverts. Aucun gain de tokens ni achèvement L0–L9 annoncé.

## L8 — Bail scheduler sérialisé entre processus

- MCP contexte indisponible à la première invocation ; lecteur local utilisé
  (11 967/12 000 octets, aucun avertissement). Statut DevCore ensuite disponible ;
  RepoWise retrouve scheduler_lock, index neuf jours, source/tests relus.
- Remplacement du read/write JSON concurrent par une section critique OS
  non bloquante, sur fichier guard persistant (msvcrt Windows, flock POSIX).
  Publication par fichier temporaire unique, flush/fsync puis os.replace,
  sans suppression préalable de l'ancien bail. État malformé/trop volumineux
  refusé et conservé. Renouvellement expiré et libération étrangère refusés.
  Nouveaux horodatages UTC, anciens horodatages locaux lisibles.
- **9 tests réussis en 2,48 s** : quatre vrais enfants concurrents (un seul
  propriétaire), contention immédiate, enfant quittant sous verrou (libération
  OS constatée), corruption, ancien propriétaire et publication échouée ; test
  historique du bail inclus. Racines temporaires avant imports/enfants, aucun
  daemon réel ni donnée active/Dropbox touché. CI enrichi, non exécuté à distance.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-lease-final-f85cc0c6ed6f403a89f31d1d0376372a/tests.txt,
  SHA-256 e5865f21dcb75c724c1931fc2423c99d266058313b76684c5d0e006ea6a86da8.
- Première suite élargie : 12 réussites, 10 échecs, 2 erreurs. Deux erreurs de
  fixture corrigées (id paramétré géant dépassant la limite Windows). Échecs
  hors bail : tzdata absent du runtime pour Europe/Paris et attente SystemExit
  du test CLI historique. Ces gates restent ouverts ; aucune réussite globale
  du scheduler revendiquée. Pas d'installation/modification du runtime.
- Source non rechargée : activation exige l'arrêt de toutes les anciennes
  versions, qui ignorent le guard. POSIX non exécuté ici. Bail temporisé sans
  fencing des effets métiers ni renouvellement pendant un job long ; scheduler
  peut encore perdre son bail en exécution. Démarrage/backoff scheduler et
  propriétaire OS restent ouverts. Plan/fiche actualisés, diff ciblé valide.

## L8/L9 — Dépendance timezone Windows et contrat CLI scheduler

- Lecteur local de contexte utilisé, puis outils statut/RepoWise disponibles.
  Git/journal/tests et dépendances relus. Index RepoWise neuf jours ; source
  actuelle contrôlée. Aucun service ni magasin actif utilisé pour les tests.
- tzdata déclaré dans pyproject pour Windows ; lock Python 3.13 régénéré avec
  uv, versions existantes conservées, tzdata 2026.5 et hashes ajoutés. Runtime
  de recette dépourvu de pip : installation uv avec hashes dans un overlay
  temporaire seulement, sans modifier la recette ni les releases figées.
- Test CLI historique corrigé : scheduler_status lit get_local_root, le test
  patchait get_data_root et interrogeait un autre dossier temporaire. La source
  CLI conserve sa séparation local/shared, aucun repli vers données partagées.
- **23 tests réussis en 13,77 s** : bail concurrent, bootstrap YAML, commandes,
  timeout, contrat timezone/cron/DST, synchronisation registre et CLI ; trois
  racines temporaires avant imports/enfants et timezone via overlay. Échecs
  du passage précédent résolus sur ce périmètre. CI scheduler enrichi ; distant
  non exécuté. Diff ciblé valide.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-tzdata-da036fddf60d452c8a8f311d0dc8d816/tests.txt,
  SHA-256 687353015e37dd4212af83768e1edc190edb533cc8f5dd86696277a605f43b31.
- Plan et fiche actualisés. Source dépendance qualifiée sur overlay, activation
  et reconstruction de bundle figé ouvertes : les snapshots/wheels déjà publiés
  restent inchangés, leur présence ne prouve pas tzdata. Jobs longs, fencing,
  démarrage/backoff du scheduler et qualification L0–L9 toujours ouverts.

## L8 — Exclusion conservée pendant les jobs longs

- Contexte local, statut MCP, Git/journal/tests relus ; RepoWise ciblé, index
  neuf jours, code actuel contrôlé. Correction du risque de reprise par un
  autre daemon après expiration du bail pendant une commande bloquante.
- Nouvelle portée hold : guard OS conservé du chargement des jobs jusqu'à
  commande, publication d'historique et sauvegarde finale. Validation du bail
  propriétaire avant entrée ; renouvellement avant libération en sortie normale.
  Une exception libère le guard sans renouveler aveuglément le bail. Les autres
  schedulers refusent immédiatement l'acquisition même après expiration temporelle.
- **27 tests réussis en 17,27 s**, dont quatre nouveaux : vrai enfant refusé
  après expiration du bail durant hold, propriétaire étranger, exception avec
  reprise après expiration et cycle main_loop vérifié aux trois étapes.
  Trois racines temporaires avant imports/enfants, overlay tzdata précédent ;
  aucun daemon ni données actives/Dropbox touchés. Diff ciblé valide après
  suppression d'espaces hérités dans les blocs réindentés.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-long-job-fd4290b9aaf145d0bd4543d4882934e4/tests.txt,
  SHA-256 995ba7c13f58a769161776b0d5aabd09e17116e5971fab97f5ad43b31202bfa4.
- Plan et fiche actualisés, source non activée. Ce protocole exige toutes les
  instances à jour et un disque local, guard persistant non remplacé. Crash parent
  avec descendants survivants, fencing des effets externes, synchronisation du
  registre au démarrage hors guard, arrêt/timeout et readiness scheduler ouverts.
  Un get_owner indisponible pendant hold ne prouve pas l'absence de daemon.
  POSIX et déploiement réel non qualifiés ; lots L0–L9 toujours ouverts.

## L8 — Registre scheduler local sous le même guard

- Contexte local, statut MCP, Git/journal/tests relus ; recherche RepoWise ciblée
  confrontée à la source (index neuf jours). Synchronisation du registre désormais
  sérialisée avec hold ; contention refusée sans attente ni écriture. État dynamique
  invalide ou identifiants dupliqués refusés et conservés, sans remise à zéro.
- Publication JSON commune par temporaire unique/fsync/os.replace, utilisée par
  sync_registry et save_jobs ; échec de remplacement préserve l'ancien fichier.
  CLI sync corrigé vers local_root, aucun accès au registre dans data_root.
  Démarrage refusé si sync échoue/est occupée : suppression du repli YAML automatique
  qui pouvait masquer une erreur. Imports Scheduler explicites pour python -I.
- Huit cas ajoutés, dont vrai CLI isolé et sentinelle shared inchangée, refus de
  démarrage sans bootstrap, registre occupé/corrompu/dupliqué, publication échouée.
  **35 tests réussis en 18,05 s** sous Python 3.13, trois racines temporaires et
  overlay tzdata ; aucun daemon réel ni donnée active/Dropbox modifié. Première
  passe : deux échecs exposant {} accepté et import -I incomplet, corrigés.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-registry-final-a892a277419041c38e5e8ea72f5ea7a9/tests.txt,
  SHA-256 565244ec53ce288f03c93a0b5fa5bda1fd8f1cad7b0800bb88351f89cf82d3af.
- Diff ciblé valide, plan et fiche actualisés. Sources non activées ; tous les
  writers doivent adopter le guard. Helper YAML historique conservé pour ses
  appels explicites/tests, sans repli au démarrage. Fencing/crash avec descendants,
  reprise après sync refusée, superviseur scheduler et déploiement encore ouverts.

## L8 — Échecs de lecture/publication remontés au cycle scheduler

- Contexte local, Git/journal/tests et statut MCP relus ; RepoWise ciblé, source
  actuelle vérifiée. Le cycle traitait un registre illisible comme liste vide et
  absorbait une erreur de sauvegarde : le guard pouvait être renouvelé normalement.
- load_jobs propage désormais fichier absent, JSON/type/modèle invalide et
  identifiant dupliqué ; save_jobs journalise puis propage l'échec de publication.
  Le cycle interrompu ne renouvelle donc pas le bail à la sortie de hold. L'ancien
  fichier reste intact, aucun registre vide de remplacement n'est publié.
- Six cas ajoutés : registre manquant/malformé/non-list/incomplet, disque refusant
  publication et cycle annulé avant commande sans renouvellement de sortie.
  **41 tests réussis en 17,85 s**, Python 3.13 et overlay tzdata, trois racines
  temporaires avant imports/enfants ; aucun daemon ni donnée active/Dropbox touché.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-state-failure-eaab6d50cd0d49d6a617506f8628cf40/tests.txt,
  SHA-256 334b42f4a9ad91337262c7756f6424896328d9c63d758d281504626f94493e68.
- Diff ciblé valide, plan/fiche actualisés. Sources non activées ; cycle en erreur
  toujours journalisé et retenté par la boucle historique, pas de readiness globale
  qualifiée. Historique SQLite et JSON ne sont pas une transaction commune ;
  crash/reconciliation restent ouverts. Timeout actuel tue le wrapper run_job,
  arrêt de ses descendants non qualifié : prochain risque concret à traiter.

## L5/L8 — Timeout et crash : arbre scheduler contenu sur Windows

- Contexte local, Git/journal/tests et statut MCP relus ; recherche RepoWise
  confrontée à run_job actuel. Contrats Win32 vérifiés dans les sources Microsoft :
  [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
  [ExtendedLimitInformation](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
- Job Object non héritable, KILL_ON_JOB_CLOSE, sans permission breakaway. Wrapper
  run_job derrière une porte stdin : aucune commande enfant avant association
  confirmée au Job. Échec d'association : erreur explicite et wrapper interrompu,
  sans exécution. Timeout : fermeture du Job, drainage/attente bornés 5 s ; sortie
  normale : fermeture également pour les éventuels descendants restants. Crash
  du parent ferme le handle OS et provoque la terminaison de l'arbre associé.
- **48 tests réussis en 11,31 s**, sept nouveaux : vrai petit-enfant arrêté au
  timeout, vrai crash parent avec petit-enfant arrêté, refus d'association sans
  commande exécutée et quatre délais invalides. Processus de fixtures uniquement,
  PID propre contrôlé via OpenProcess/WaitForSingleObject en lecture. Trois racines
  temporaires avant imports/enfants et overlay tzdata ; aucun daemon/donnée active.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-job-object-6c079593b8ed447fb09545593b600f40/tests.txt,
  SHA-256 8e89a9b62851c32f103fab12fe71c670af273b7af808c47e3a31b3a7d767d514.
- CI Windows enrichi, distant non exécuté ; diff ciblé valide. Plan et fiche
  actualisés, source non activée. Containment Windows seulement : autre OS refusé
  avant lancement, aucune promesse POSIX. Pas sandbox pour code hostile ni fencing
  de services externes ; appels via broker/service extérieur hors Job non couverts.
  Sorties stdout/stderr encore sans plafond mémoire, admission/annulation générale
  et coût de démarrage/assignation hors timeout de communicate restent ouverts.
  Autres runners non raccordés à ce mécanisme, qualification L0–L9 ouverte.

## L5/L8 — Sorties scheduler bornées et dépassement interruptif

- Contexte local, Git/journal/tests relus ; statut MCP et RepoWise ciblé disponibles.
  Index RepoWise maintenant dix jours, code actuel vérifié. communicate capturait
  stdout/stderr sans plafond mémoire : remplacement par deux drains binaires.
- Chaque flux conserve au plus 1 MiB brut par défaut, limite explicite 1 octet
  à 16 MiB. Lectures par blocs <=64 KiB, excédent jeté et signalé. Dépassement :
  statut -10, message explicite et fermeture du Job Object (arbre interrompu).
  Collecte concurrente des deux flux ; vérification finale après drainage pour
  ne pas accepter le succès d'un processus qui dépasse puis termine rapidement.
  Timeout et erreur de collecte restent des échecs ; cleanup/drains partagent 5 s.
- **55 tests réussis en 11,99 s**, sept nouveaux : floods stdout/stderr 2 MiB
  avec limite 64 KiB et vrais descendants arrêtés, deux flux simultanés sous
  plafond et quatre plafonds invalides refusés avant lancement. Première passe :
  deux erreurs de syntaxe dans les programmes de fixture, corrigées.
  Python 3.13, overlay tzdata et trois racines temporaires avant imports/enfants.
  Aucun service/donnée active/Dropbox utilisé ; diff ciblé valide.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-output-final-ba2164fbfb624ab8af44f0ed3dd35eaa/tests.txt,
  SHA-256 8c83f615d94e5e5a304776f7f6fcf3a3f1d258f5997c1cc00cccd76f2db591ee.
- Plan/fiche actualisés, source non activée. Plafond de bytes capturés, pas mesure
  des tokens ni plafond mémoire de l'enfant. Décodage UTF-8 avec remplacement,
  préfixe d'erreur séparé ; coût du lancement/assignation et quotas multiutilisateurs
  restent ouverts. Runners hors scheduler, sandbox et effets externes non qualifiés.

## L5/L8 — Budget temporel compté dès le démarrage du job

- Contexte local, Git/journal/tests, statut MCP et RepoWise relus ; index dix jours,
  source actuelle contrôlée. Le timeout commençait après création/assignation :
  une phase lente pouvait ouvrir la porte d'exécution avec un budget déjà dépassé.
- Deadline monotone créée avant le Job Object. Contrôles après création, après
  assignation et avant ouverture stdin ; dépassement refusé avec statut -9 sans
  commande exécutée. Boucle vérifie le délai avant d'accepter une terminaison.
  Cleanup partage une seule échéance de cinq secondes, y compris le finally et
  les drains, sans réinitialiser une attente entière après un premier échec.
- Deux cas ajoutés : création du Job lente sans lancement et assignation lente
  sur vrai wrapper, marqueur de commande absent. **57 tests réussis en 12,45 s**
  après la dernière modification, Python 3.13 et overlay tzdata ; trois racines
  temporaires avant imports/enfants, aucun daemon ou donnée active/Dropbox touché.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-total-deadline-final-18ae0ddd3ab84257afe9b9534232c392/tests.txt,
  SHA-256 f9873d38718da273913169638dfb9ed7762a0e2443033a51d6f39be1dfbd9902.
- Diff ciblé valide ; plan/fiche actualisés, source non activée. Le temps des
  appels OS/Popen est compté et vérifié après retour, pas préempté s'ils bloquent
  dans l'OS : aucune borne murale absolue sur ce cas annoncée. Admission, quotas,
  annulation générale, autres runners et qualification L0–L9 toujours ouverts.

## L5/L8 — Résultat absent de l'historique : aucun avancement

- Contexte local, statut MCP, Git/journal/tests et recherche RepoWise relus ;
  index dix jours, code actuel vérifié. update_run annonçait true même si aucune
  ligne n'était mise à jour ; son résultat était ignoré par le cycle.
- update_run exige une ligne affectée et retourne false sinon. Le cycle refuse
  alors d'incrémenter le compteur, de recalculer le prochain run ou de publier
  jobs.json ; exception journalisée et aucune sortie normale de hold. Le log de
  commande distingue maintenant code zéro et persistance encore à effectuer.
- Trois tests ajoutés : ligne absente, vraie base avec trigger refusant UPDATE
  (claim running préservé), cycle dont la commande réussit mais l'écriture échoue.
  **60 tests réussis en 14,85 s**, Python 3.13, overlay tzdata, trois racines
  temporaires avant imports/enfants ; aucune donnée active/Dropbox utilisée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-history-failure-254eb24b6a114479bdfb5000ef7c3c96/tests.txt,
  SHA-256 211119e82b7a3a297631435c5607aa1768f7f97bd5bad05e1c74589b0160a2f9.
- Diff ciblé valide ; CI, plan et fiche actualisés. Source non activée. Claim
  running conservé : ne déclenche pas de répétition automatique d'effets externes.
  Réconciliation/crash et résolution contrôlée des claims orphelins restent
  ouverts ; historique SQLite et registre JSON ne sont pas atomiques ensemble.

## L5/L8 — Claim non résolu conservé au passage suivant

- Contexte local, Git/journal/tests et statut DevCore relus ; RepoWise ciblé
  retrouve l'historique, index dix jours/sémantique désactivée, code actuel vérifié.
  Risque confirmé : is_run_completed incluait running. Après une persistance
  échouée, le passage suivant pouvait ainsi avancer silencieusement le planning.
- Seuls ok/skipped constituent une occurrence terminée. Claim running/error
  existant : contrainte d'unicité empêche la réexécution, planning conservé et
  warning pending reconciliation explicite. Aucun effacement ni retry automatique
  des effets externes dont le résultat est incertain.
- Six cas ajoutés : quatre statuts sur vraie base, puis cycles réels avec claim
  running/error, commande et sauvegarde interdites, même échéance et une seule
  ligne conservées. **66 tests réussis en 16,50 s**, Python 3.13, overlay tzdata,
  trois racines temporaires avant imports/enfants ; aucun état actif/Dropbox testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-unresolved-c66eb68469144e3eac925e1829c087b1/tests.txt,
  SHA-256 745d8850943c924063afa956159d6f1a0a065d20796308f06e62bf4be13b2a0e.
- Diff ciblé valide ; journal/plan/fiche actualisés. Sources non activées.
  Résolution contrôlée et diagnostic opérateur des claims orphelins restent ouverts ;
  l'attente explicite évite un faux achèvement sans prétendre résoudre le crash.
  Transactions communes, autres runners et critères L0–L9 toujours ouverts.

## L5/L8 — Diagnostic borné des occurrences non résolues

- Contexte local, Git, journal et tests relus ; statut MCP consulté pour devcore.
  RepoWise retrouve scheduler_history, index dix jours/sémantique désactivée ;
  schéma actuel vérifié dans le code, sans assimilation du board aux lots L0–L9.
- Ajout inspect_claims.py : chemin DB obligatoire, aucun chargement des racines,
  aucune initialisation ; SQLite mode=ro/query_only, pagination par ID, 1 à 100
  lignes running/error, texte tronqué dans SQL avec indicateur explicite.
  Attente verrou 1 s, contrôle SQL 2 s ; appels OS non préemptés. Aucun COUNT
  global, effacement, retry ou changement de statut. WAL refusé avant connexion
  car SQLite peut créer des sidecars en lecture seule ; mode DELETE exigé sans
  changement concurrent du journal. Chaque page est un snapshot distinct.
- Dix cas ajoutés : pagination/exclusion des succès, champs bornés, conservation
  exacte des fichiers, paramètres invalides, absence sans création, refus WAL,
  CLI Python -I et schéma invalide sans résultat vide de repli.
  **76 tests réussis en 19,72 s**, Python 3.13, overlay tzdata et trois racines
  temporaires avant imports/enfants. Aucune donnée active/Dropbox/index testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-scheduler-inspection-final-6afe72328156472caa731623e8c04e47/tests.txt,
  SHA-256 1107c3db1a8db3ec4bdf4d06da7dbc156c49821aab54a6bc5a9a62edcc4900b4.
- CI enrichie, procédure scheduler-claims.md, plan et fiche v55 actualisés.
  Contexte complet : 11749/12000 octets UTF-8, warnings vides ; gain tokens non
  mesuré. Contrôle diff global relève du whitespace préexistant dans le Dashboard
  généré ; ces changements étrangers conservés. Contrôle ciblé effectué séparément.
- Source non activée et releases figées non reconstruites. running/error ne prouve
  pas un claim orphelin ni l'absence d'effets externes. Résolution contrôlée avec
  audit, transaction commune historique/registre, autres runners et L0–L9 ouverts.

## L5/L8 — Résolution locale explicite et audit atomique

- Fiche/décisions, Git, journal et tests relus ; statut MCP devcore consulté.
  Recherche RepoWise scheduler_lock ciblée : index dix jours, sémantique mock ;
  protocole actuel contrôlé dans le code. Aucun magasin actif testé.
- Nouveau maintenance_guard : même guard OS que les cycles, refus d'un bail
  actif ou invalide ; guard conservé pendant la transaction de résolution.
  resolve_claim.py exige scheduler.db existante, verrou standard sibling,
  DELETE journal, ID/statut attendu et justification bornée à 4096 octets.
  Actions limitées à confirm-success/skip ; ni retry ni suppression de claim.
- BEGIN IMMEDIATE : audit et changement running/error vers ok/skipped dans une
  transaction, rollback sur échec ; détails d'exécution conservés. jobs.json
  inchangé ; prochain cycle pourra avancer une occurrence désormais terminée.
  Compte local getpass/PID/date UTC consignés, sans attestation SID ni identité
  API authentifiée. Les preuves externes demeurent une vérification opérateur.
- Quinze cas ajoutés : succès/skip, audit, conservation du registre/détails,
  résolution répétée/claim absent, running/error, bail actif/guard occupé,
  vrais triggers d'échec audit et update avec rollback, bornes/absence/WAL,
  CLI -I et bail corrompu. Premier passage 88 réussis/1 échec : import local
  absent sous -I ; correction du chemin explicite et assertion JSON du refus.
  Passage final **91 tests réussis en 27,25 s**, Python 3.13/overlay tzdata,
  trois racines temporaires avant imports/enfants ; aucune donnée Dropbox active.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-claim-resolution-final-ccd54402255448249e6f0fb94a1cc0c9/tests.txt,
  SHA-256 9e7837ec9efbc27cb28c61806ca8ab39f1f4d6acdccd1e99f823746977081e97.
- CI, procédure, plan et fiche v56 mis à jour ; diff ciblé valide. Retour CRLF
  automatique avait dépassé le plafond du contexte : LF explicite et empreinte
  actualisée, contexte complet 11765/12000 octets, warnings vides. Gain de tokens
  non mesuré. Releases figées non reconstruites, source non activée.
- Toutes les anciennes instances doivent être arrêtées et tous les participants
  utiliser ce guard ; un verrou personnalisé/ancien worker n'est pas couvert.
  Administration authentifiée, preuve d'arrêt/effects externes, inviolabilité
  de l'audit et transaction commune historique/registre restent ouvertes.
  Aucun claim actif résolu ; lots L0–L9 non déclarés terminés, automatisation conservée.

## L5/L8 — Reprise du registre après résultat SQLite publié

- Contexte obligatoire v56 chargé à 11765/12000 octets, Git/journal/tests relus,
  statut DevCore devcore consulté. RepoWise ciblé scheduler_tick, index dix jours
  sans sémantique ; comportement confronté au code/contrat de planification.
- Défaut confirmé : branche « occurrence déjà terminée » recalculait l'échéance
  sans restaurer last_run_at/statut/erreur/compteur. Après succès SQLite suivi
  d'un échec JSON, job once pouvait garder son échéance passée ; catch_up pouvait
  recalculer depuis un mauvais point de départ et le compteur perdre un succès.
- Lecture explicite du résultat terminal ok/skipped, puis restauration des
  champs avant calcul du prochain slot. Succès compté si son marqueur n'était
  pas déjà publié ; skip non compté. Marqueur/compteur/échéance publiés ensemble
  par le JSON atomique existant. Résultat devenu indisponible : erreur sans
  avancement. Aucun retry de commande pour une occurrence terminée.
- Six cas réels SQLite/JSON ajoutés : once ok/skipped puis second cycle,
  succès déjà appliqué non recompté, interval catch_up depuis le slot restauré,
  commande réussie puis publication refusée suivie de deux reprises (une seule
  exécution/ligne historique), résultat absent après vérification préservant JSON.
  **97 tests réussis en 31,58 s**, Python 3.13, overlay tzdata, trois racines
  temporaires avant imports/enfants ; aucun état actif/Dropbox/index réel testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-registry-recovery-6699dc48069042048de4b56ce35dc54a/tests.txt,
  SHA-256 128f6053a7cbe77f4b13550e2226ac9c64479a1729e328c92e9f49e54138ccec.
- CI/procédure/plan/fiche v57 actualisés, diff ciblé valide ; contexte complet
  11770/12000 octets, warnings vides. Gain tokens non mesuré. Sources non activées,
  releases figées non reconstruites. SQLite et JSON ne constituent toujours pas
  une transaction unique ; effets externes incertains restent à réconcilier.
- Prochain contrôle : validation/bornes des calculs de planning (intervalle nul
  ou négatif et retard important), puis démarrage/identité et qualification des
  critères encore ouverts. L0–L9 non achevés ; automatisation conservée.

## L5/L8 — Intervalles validés et rattrapage sans boucle sur le retard

- Contexte obligatoire v57, Git, journal et tests relus avant modification ;
  statut MCP devcore consulté. RepoWise ciblé scheduler_contract : index dix
  jours/mock, résultats confrontés au code et tests historiques cron/DST.
- Risques confirmés : intervalle nul/négatif peut bloquer la boucle skip ;
  retard important fait parcourir chaque slot ; run_once sélectionnait la fin
  d'une liste tronquée à 1000 et non le plus récent slot effectivement manqué.
- Validation modèle des intervalles entiers 1..525600 minutes (365 jours),
  expression limitée à 64 caractères, plus contrôle au calcul/helper direct.
  Registre invalide refusé avant commande même avec next_run_at déjà fourni.
  Aucun ajustement des données existantes : intervalles supérieurs à revoir.
- Calcul arithmétique skip, run_once et catch_up sans énumérer le retard.
  Fenêtre historique de 30 jours et ancrage sur sa borne conservés ; run_once
  calcule désormais le dernier slot complet et catch_up le premier manqué.
  Helper de liste historique reste borné à 1000, hors décision de planning.
- Dix-neuf cas ajoutés : zéro/négatif/décimal/texte/borne/taille, helper direct,
  mutation en mémoire, trois politiques sur retard depuis 1900 sans énumération,
  run_once au-delà de 1000 slots, dernier slot futur et cycle réel refusant une
  configuration invalide avant exécution sans réécriture de jobs.json.
  **116 tests réussis en 30,66 s**, Python 3.13, overlay tzdata et trois racines
  temporaires avant imports/enfants ; aucun état actif/Dropbox/index réel testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-interval-bounds-f91d8941642c423aa75eb5fa63431fc7/tests.txt,
  SHA-256 225b77f0f635106d70b16ddb67450648f5d19e307571427d79a93687c83a0055.
- CI, procédure, plan et fiche v58 actualisés ; diff ciblé valide. Contexte
  complet 11792/12000 octets, warnings vides ; économie tokens non mesurée.
  Sources non activées, releases figées non reconstruites. Sémantique locale
  conservée ; ambiguïtés DST, cron global, quotas/admission/rattrapage, durée
  complète du cycle et démarrage/identité du daemon restent à qualifier.
  L0–L9 non terminés, automatisation conservée.

## L5/L8 — Métadonnées refusées avant commande et recherche cron bornée

- Fiche/décisions v58 chargées localement, Git/journal/tests relus ; statut MCP
  devcore consulté. Recherche RepoWise system_watcher, index dix jours/mock,
  confrontée au code : WMIC par sous-chaîne et succès immédiat après Popen encore
  présents, non qualifiés. Prérequis traité : sync démarre avant le daemon mais
  un registre doté d'une échéance pouvait transmettre un planning invalide.
- Validation modèle : kind/policy connus, expression 1..256 caractères,
  cron syntaxiquement valide/dépendance exigée, once ISO, timezone explicite
  valide, timestamps d'état parsables/bornés, compteur entier non négatif.
  Refus avant commande ou publication du registre ; aucune correction automatique.
- Tous les croniter de ce contrat reçoivent max_years_between_matches=8,
  signature vérifiée sur le runtime installé. Absence croniter devient une
  erreur, sans planning vide. Calendrier sans occurrence dans cet horizon reste
  une erreur de calcul ; borne de recherche, pas deadline murale absolue.
- Dates anciennes sans timezone comparées selon la convention UTC existante.
  Représentation historique de la clé préservée (naive/offset) : aucune conversion
  de timezone ne crée un nouveau claim. Premier passage 128 réussis/2 échecs
  a détecté une normalisation changeant la clé via le helper mock ; correction
  limitée à la comparaison et deux scénarios réels anti-réexécution ajoutés.
- Seize cas ajoutés : types/politiques/cron/dates/timezone/compteur invalides,
  sync préservant l'ancien JSON, absence croniter, horizon explicite, date naive
  exécutée avec sa clé historique et claims existants naive/offset non répétés.
  **132 tests réussis en 37,79 s**, Python 3.13/overlay tzdata, trois racines
  temporaires avant imports/enfants ; aucune donnée active/Dropbox/index réel testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-config-validation-final-16f9d6b344574194a9c03a704a906854/tests.txt,
  SHA-256 4e7d545c9b921b540ca5d8ad33a96dd130f3736a616d9cb86239c19923978dd7.
- CI/procédure/plan/fiche v59 actualisés ; diff ciblé valide. Contexte complet
  11788/12000 octets, warnings vides, économie tokens non mesurée. Sources non
  activées et releases figées non reconstruites. Ce total scheduler est distinct
  des 132 tests antérieurs de routage LLM ; ne pas additionner sans déduplication.
- Démarrage/identité/readiness scheduler, cron run_once au-delà de 1000 slots,
  canonicalisation globale des clés/DST, quotas et qualification L0–L9 ouverts.
  Aucun service actif relancé ; automatisation conservée.

## L5/L8 — Cron run_once : dernier slot sans liste tronquée

- Contexte obligatoire v59 chargé via MCP devcore_project_context, 11788/12000
  octets, warnings vides ; statut devcore, Git, journal et tests relus.
  RepoWise ciblé scheduler_contract, index dix jours/mock, code actuel vérifié.
- Défaut confirmé : run_once cron prenait le dernier élément d'une liste
  plafonnée à 1000, donc une occurrence trop ancienne lorsque le retard excédait
  cette limite. Autre cas : absence de slot dans la fenêtre puis calcul depuis
  une base ancienne pouvait retourner une échéance antérieure aux 30 jours.
- Recherche arrière directe avec horizon huit ans, inclusive à now (borne
  microseconde testée sur le croniter installé) ; slot strictement après la base
  bornée aux 30 jours. Aucune liste de slots parcourue. En absence de match
  précédent dans l'horizon, recherche future depuis max(now,last_run), elle aussi
  bornée, notamment pour une année future explicite sans occurrence précédente.
  Pas de retour silencieux d'un slot plus ancien que la fenêtre.
- Dix cas ajoutés : milliers de slots sans helper d'énumération, instant exact
  et sous-minute, cron à la seconde, dernier slot appliqué/futur non resélectionné,
  annuel sans slot dans la fenêtre, année future explicite, ancien état/no-history.
  **142 tests réussis en 37,99 s**, Python 3.13/overlay tzdata, trois racines
  temporaires avant imports/enfants ; aucun état actif/Dropbox/index réel testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-cron-latest-af6df5b5aede438c9c60b5f6eb53b9b0/tests.txt,
  SHA-256 6121b424afc2712722826766510dce763c6409863e42b9899e4efd28ab55066f.
- CI/procédure/plan/fiche v60 actualisés ; diff ciblé valide. Contexte complet
  11812/12000 octets, warnings vides ; gain tokens non mesuré. Sources non activées,
  releases figées non reconstruites. Plafond de liste historique conservé pour
  les autres usages ; qualification générale DST, canonicalisation de toutes
  les clés et effets externes toujours ouverts.
- Prochain point : supervision/démarrage scheduler (WMIC, readiness, identité,
  budget de reprise) puis quotas/admission. L0–L9 non terminés ; automatisation
  conservée. Aucun service actif lancé ou occurrence active modifiée.

## L5/L8 — Démarrage gardé et signal lié à l'enfant connu

- Contexte MCP v60, statut devcore, Git/journal/tests relus ; RepoWise ciblé
  system_watcher, index dix jours/mock, comportement actuel contrôlé dans le code.
- Suppression de WMIC par sous-chaîne et du succès dès Popen. Réservation locale
  RestartBudget pour scheduler-daemon (trois/dix minutes, 5/10/20 s, lease 60 s),
  état invalide/erreur de réservation refusés. Attente 5 s/max30 comptée avant
  Popen ; pas de préemption d'un appel OS bloqué. Roots/nonce dans l'enfant seul.
- Nouveau guard OS d'instance persistant sur la vie du daemon, couvrant sync/
  initialisation/sommeil ; distinct du guard de cycle. Sync utilise désormais
  paths.platform_root, nécessaire pour isoler entièrement le registre de recette.
  Anciennes instances sans protocole à arrêter avant activation.
- Signal atomique après historique initialisé et registre validé, sous guard
  de cycle ; rafraîchi au cycle et invalidé sur exception. Lecture 4096 octets,
  nonce/PID/Python/racine locale/fraîcheur30s/handle enfant vivant vérifiés. Enfant
  connu après timeout conservé sans relance aveugle ; mort soumise au budget.
- Première recette 195 réussis/1 échec : le lanceur Python venv Windows a un PID
  différent de l'interpréteur ; relation confirmée sur vrai sous-processus. Signal
  accepte PID interpréteur si son parent déclaré est le lanceur vivant avec nonce
  attendu. Ce parent déclaré n'est pas une attestation indépendante du noyau.
  Aucun ancien PID de recette encore présent lors du contrôle ciblé.
- Vingt et un cas de supervision ajoutés : budget/échec, busy sans doublon,
  enfant mort/en attente, nonce/roots par lancement, profils/types/fraîcheur
  refusés, délais invalides, invalidation limitée au nonce courant. Vrai daemon
  sur statique [] avec roots temporaires : signal/guard/jobs vide vérifiés ; arrêt
  du seul arbre fixture (taskkill PID capturé/Popen, aucune instance active), guard
  libéré et signal mort refusé. **197 tests réussis en 52,20 s** avec scheduler et
  RestartBudget, Python3.13/overlaytzdata, trois roots avant imports/enfants.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-supervision-final-1f6a41a547bc48f586568c863a843e88/tests.txt,
  SHA-256 9956c26376e9c2dc68b8f7588a7f58bd605dc602bbb556f077173fbff5211657.
- CI/protocole/plan/fiche v61 actualisés, diff ciblé valide ; contexte complet
  11836/12000 octets, warnings vides. Sources non activées, releases non reconstruites,
  aucune donnée active/Dropbox/index réel testée, économie tokens non mesurée.
- Limites : un autre watcher ne reprend pas l'identité du daemon existant,
  retourne non confirmé/dégradé sans doublon. Adoption OS/temps de création et
  profil complet ouverts ; signal de préparation, pas réussite globale des jobs,
  fichiers supposés dignes de confiance. Long job peut expirer le signal. Job
  Object du daemon, arrêt/ACL/compte de service, charge/quotas/admission et L0–L9
  encore ouverts ; automatisation conservée.

## L5/L8 — Reconnaissance du daemon par identité Windows et profil

- Contexte MCP v61, statut devcore, Git/journal/tests relus ; RepoWise ciblé
  scheduler_tick, index dix jours/mock, source actuelle vérifiée. API Win32
  GetProcessTimes/QueryFullProcessImageNameW confrontées aux documents Microsoft.
- Helper Windows lecture seule : handle QUERY_LIMITED_INFORMATION/SYNCHRONIZE,
  heure de création en unités100ns, chemin image, liveness instantanée sur le
  même handle, fermeture en finally. PID borné/type exact, erreurs OS refusées.
  Signal protocole2 inclut identité OS et script/racines données/plateforme.
- Enfant connu : identité réelle du PID vérifiée en plus du nonce/handle vivant.
  Nouveau watcher : signal frais, guard confirmé busy avant/après lecture,
  PID/heure/image identiques, même image du watcher/Python venv/script et racines
  attendues. Aucun lancement ni consommation du budget sur reconnaissance.
  Guard inaccessible distingué d'une vraie contention lors de la prise du verrou
  OS ; pas d'adoption déduite d'une erreur d'ouverture. Protocole1 refusé.
- Quatorze cas ajoutés/étendus : nouveau watcher sans lancement, faux temps de
  création/image/types, profils script/Python/données/plateforme étrangers,
  accès OS refusé/protocole1, bornes PID et guard inaccessible. Vrai daemon vide
  reconnu depuis signal OS ; autre racine refusée ; mort/guard libéré refusés.
  **211 tests réussis en 50,01 s**, Python3.13/overlaytzdata, trois racines
  temporaires avant imports/enfants. Aucun service/donnée active/Dropbox/index
  réel testé ; seule l'arborescence du daemon fixture arrêté par son PID capturé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-os-adoption-final-5865830de1d545a6bc73ff4d871cc883/tests.txt,
  SHA-256 db9ca141f9ecbe907f6bac4f5cb3c7773a67aa0ff05b16b87760c8e36796fc1f.
- Plan/protocole/fiche v62 actualisés ; CI conserve cette suite déjà incluse.
  Diff ciblé valide, contexte complet 11863/12000 octets, warnings vides, gain
  tokens non mesuré. Sources non activées, releases figées non reconstruites.
- Limites explicites : snapshot OS, pas garantie permanente ni authentification
  administrative. Script/racines restent déclarés par le daemon ; correspondance
  entre détenteur du guard et signal dépend du protocole et d'un magasin protégé.
  Résistance à un signal forgé avec mêmes droits, ACL/compte de service, arrêt,
  Job Object du daemon, charge/quotas/admission et L0–L9 encore ouverts. Démarrage
  direct sans nonce non reconnu automatiquement ; automatisation conservée.

## L5/L8 — Signal vérifiable pour le démarrage direct

- Contexte MCP v62, statut devcore, Git/journal/tests relus ; RepoWise ciblé
  scheduler_tick, index dix jours/mock, source actuelle confrontée aux tests.
- Démarrage direct sans variable nonce : UUID local généré et même signal de
  préparation/identité OS que l'enfant du watcher. Aucune mutation d'environnement
  global. Une valeur explicitement vide/invalide refuse le démarrage avant sync.
- Publication reçoit les racines données/plateforme des chemins résolus ; ne
  dépend plus de leur présence dans l'environnement du daemon. Arguments
  explicites ajoutés à publish_ready ; compatibilité du helper existant conservée.
  finally de start_daemon invalide son propre signal à la sortie ; arrêt forcé
  reste refusé par identité/guard. Arrêt opérationnel complet non qualifié.
- Cinq cas ajoutés : vrai daemon de recette sans nonce en plus du lancement
  avec nonce, profil explicite sans variables racines, trois nonces invalides
  refusés avant sync et sans création de fichiers. Registres vides et trois roots
  temporaires définis avant imports/enfants ; aucun job ni état actif/Dropbox testé.
  **216 tests réussis en 52,67 s**, Python3.13/overlaytzdata, suite supervision/
  scheduler/reprise ; seule l'arborescence du processus fixture arrêtée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-direct-readiness-c7d1bd49c2204d6fa49448c32336d1ac/tests.txt,
  SHA-256 a610559779f99223812ff25b9398b65b5939c725da1b7dc34605e0da53687ee2.
- Protocole/plan/fiche v63 actualisés ; suite déjà en CI, diff ciblé valide.
  Contexte complet 11893/12000 octets, warnings vides ; gain tokens non mesuré.
  Sources non activées et releases non reconstruites. ACL/compte de service,
  arrêt contrôlé/Job Object du daemon, charge/quotas/admission et critères L0–L9
  restent ouverts ; automatisation conservée.

## L5/L8 — Arrêt coopératif du scheduler

- Contexte MCP v63 (11893/12000 octets), statut projet, Git/journal/tests et
  RepoWise ciblé relus avant modification ; index dix jours/mock confronté au code.
- CLI stop_scheduler.py : trois racines explicites, guard occupé et identité
  Windows/profil vérifiés avant demande atomique liée au nonce/PID/création OS.
  Fraîcheur du signal facultative pour cette demande pendant un job long ;
  adoption readiness inchangée, exigeant un signal frais. Aucun kill.
- Le cycle termine la commande courante, persiste résultat/état, puis ne lance
  pas le job suivant. Consultation au repos environ toutes les 200 ms ; propre
  bail libéré, propres signaux nettoyés. Acceptation de demande distincte d'une
  confirmation d'arrêt. Magasin local supposé protégé, pas authentification forte.
- Dix tests nouveaux : deux jobs avec résultat et registre réellement persistés,
  daemon réel vide arrêté par CLI isolé, signal ancien avec profil vérifié,
  profils étrangers et demandes invalides/volumineuses ignorés. Première fixture
  corrigée (commande reçue, non job) après arrêt de sa seule arborescence pytest.
  **226 tests réussis en 59,00 s** avec trois racines temporaires avant imports et
  sous-processus, Python 3.13/overlay tzdata ; aucune donnée active/Dropbox utilisée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-stop-regression-27ad93c050b04e4a8653cc3f643b92ca/tests.txt,
  SHA-256 fc33f5854d546e9505d6119151d20497be5d2c7bfd5370ea28b5d36dab0ad003.
- CI Windows enrichie (non exécutée à distance), protocole/plan/fiche v64 mis
  à jour. Contexte complet 11904/12000 octets, warnings vides ; aucun gain de
  tokens modèle mesuré. Sources non activées, releases figées non reconstruites.
  Intégration stop.ps1/service/watchdog, fermeture du daemon/arbre, ACL/compte de
  service, charge/quotas et critères L0–L9 restent ouverts ; automatisation gardée.

## L5/L8 — Pause des relances et raccordement stop.ps1

- Fiche MCP v64 (11904/12000 octets), board devcore, Git, journal et tests relus.
  RepoWise ciblé stop.ps1 sans résultat (index dix jours/mock) ; code local vérifié.
- CLI : --pause publie un marqueur de profil après vérification du daemon ;
  --wait-seconds 0..30 observe libération du guard et nettoyage de la demande.
  shutdown_completed confirme ce protocole, sans prétendre certifier la mort OS.
  Délai dépassé : code 2, demande/pause conservées, aucun kill. Refus : code 1.
- Watcher : pause présente/inaccessible refuse lancement et readiness ; daemon
  direct vérifie sous son guard de vie avant sync. --resume exige guard libre
  et profil correspondant, retire la pause sans démarrer. Magasin corrompu
  conservé ; diagnostic requis avant reprise. Pause locale persistante, non ACL.
- stop.ps1 remplace le kill des schedulers par nom par ce protocole ; racines
  local/data explicites requises. -SchedulerOnly permet le parcours isolé ;
  session et réseau ne sont traités qu'après fin de protocole, erreur/timeout
  conserve les autres services. Le watcher en fonctionnement peut encore relancer
  les autres services réseau : arrêt global/identités réseau restent ouverts.
- **240 tests de régression réussis en 57,72 s** avec Python 3.13 et overlay tzdata,
  trois racines temporaires avant imports/enfants. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-pause-regression-0237116f038d41648a1f825a43051a89/tests.txt,
  SHA-256 ef20988e7058ae8d85ca7f9e6947c60f77e780cb8628452262b6f45b0833503d.
  Puis **25 tests arrêt réussis en 10,38 s** (chevauchent les précédents), dont
  stop.ps1 réel devant daemon réel dans une plateforme copiée à registre vide.
  Fixture initialement dépourvue du module devcore corrigée avec Tools dans son
  PYTHONPATH ; refus observé avant cette correction, aucune donnée active touchée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-stop-powershell-4d2d6b13e6914095a0d93db5c2e45765/tests.txt,
  SHA-256 02e7bd5353632c46777ddf97d5ca8745d9ab3359ee59d5d681e302cdb30be1ed.
  Nettoyage forcé de secours limité aux PID capturés des processus de fixture.
- CI inclut déjà ce fichier (non exécutée à distance), protocole/plan/fiche v65
  actualisés ; contexte complet 11922/12000 octets, warnings vides. Diff ciblé
  vérifié. Pas d'arrêt d'instance active, de donnée Dropbox ni d'index réel testé.
  Releases non reconstruites/services non rechargés. Identité/ACL/service,
  fermeture du watcher/arbre, scheduler absent/ancien Hermes et réseau global
  restent ouverts ; L0–L9 non achevés, automatisation maintenue.

## L5/L8 — Guard de maintenance globale des relances

- Contexte MCP v65, board devcore, Git/journal/tests relus ; RepoWise ciblé
  system_watcher.py (dix jours/mock) confronté au source actuel. Watcher exécuté
  par audits successifs, pas de daemon dédié démontré par ce fichier.
- service_control.py : CLI pause/resume sur trois racines explicites, racine
  locale existante, profil borné et publication atomique. Guard OS persistant
  partagé avec check_and_heal_service et ensure_scheduler_daemon, conservé pendant
  leur préparation. Contention/erreur : refus sans attente bloquante ni kill.
  Pause revérifiée sous guard avant contrôle/lancement, pas de budget consommé
  si refus. Les autres audits peuvent décliner temporairement leurs contrôles.
- Pause conservée pour un nouveau watcher ; audit démarrant en pause répond PAUSED
  sans scan/sonde. Corruption/profil étranger préservés. Reprise retire seulement
  la pause globale, sans lancer de service ; pause scheduler reste indépendante.
- stop.ps1 complet exige cette pause avant scheduler/session/réseau ; refus
  conserve les services. -SchedulerOnly inchangé. Pas de processus actif arrêté.
  Anciennes instances/lanceurs externes et enfants déjà créés ne sont pas contenus.
- Douze tests ajoutés : nouveaux watchers, pas de sonde/budget/lancement, pause
  apparaissant avant relecture, contention interprocessus Windows, garde occupée,
  profil/registre corrompus et refus PowerShell avant scheduler/session/réseau.
  Attentes historiques Runtime absent remplacées par absence du budget et présence
  du guard persistant : aucun budget créé pour adoption/service déjà en ligne.
  Une fixture d'arrêt forcé attend maintenant la libération du guard (jusqu'à 5 s)
  après sortie du wrapper Python ; première suite échouait sur ce contrôle immédiat,
  aucun processus fixture résiduel identifié lors du contrôle suivant.
- **253 tests réussis en 70,22 s**, Python 3.13/overlay tzdata, trois racines
  temporaires avant imports/enfants. Aucun état actif/Dropbox/index réel testé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-service-gate-regression-f869ffb1ac874a0c9d6438256819750b/tests.txt,
  SHA-256 93f38403fb0844dacefdad687093c42ade86c3088e908ab398f6230a1790fcef.
- CI enrichie, délai de l'étape ajusté à trois minutes (suite locale précédente
  96,53 s avant correction fixture ; CI distante non exécutée). Plan/protocole et
  fiche v66 actualisés : contexte 11937/12000 octets, warnings vides. Diff ciblé
  valide ; gains de tokens non mesurés. Sources non rechargées, releases inchangées.
  Magasin/ACL de maintenance supposés protégés ; identité et arrêt des services
  par port, anciens Hermes/watchers, compte de service/arbre et critères L0–L9
  ouverts. Automatisation maintenue.

## L5/L8 — Identité et arrêt coopératif des serveurs gérés

- Fiche MCP v66 (11937/12000 octets), board, Git/journal/tests relus ; RepoWise
  headroom_routes.py absent de l'index dix jours/mock, code local confronté.
- service_runtime.py : serveur Uvicorn encadré sous guard OS de vie ; propre PID
  réel, création/image Windows, nonce et profil des trois racines/port publiés.
  Signal d'identité, pas de readiness. Watcher transmet les racines à chaque
  enfant explicitement ; fixture watcher complétée avec data_root.
- Dashboard/router/Headroom native et auxiliary raccordés au helper de cycle de
  vie. Racines explicites requises ensemble avec localhost/port déclaré ; sans
  aucune racine, lancement autonome non enregistré conservé. Modèles/fournisseurs
  inchangés. Sources non rechargées ; runtimes figés non reconstruits.
- stop_service.py : vérification du profil, nonce, identité du PID vivant et
  guard occupé ; demande atomique, moniteur refuse les demandes étrangères puis
  déclenche should_exit. Nettoyage de ses seuls signaux, confirmation du protocole
  distincte de mort OS ; timeout/refus sans kill. Aucune adoption par nom ou port.
- stop.ps1 supprime Get-NetTCPConnection/Stop-Process de l'arrêt réseau ; appelle
  quatre contrôles explicites et signale l'arrêt incomplet. Anciennes instances,
  services non enregistrés, RepoWise et adaptateur 8788 préservés. Les requêtes
  déjà engagées suivent la fermeture Uvicorn ; drainage réel non encore qualifié.
- Quatorze cas dédiés : refus de PID/protocole/token/profil/identité invalides,
  guard absent/libre, état malformé/volumineux, serveur Uvicorn réel sur port
  éphémère (nonce étranger ignoré, demande valide puis sortie/nettoyage), parcours
  PowerShell simulé complet/incomplet sans découverte de ports ni kill. Wrapper
  de recette corrigé pour propager LASTEXITCODE ; première suite échouait sur
  sa propagation de code, les avertissements du script reflétaient déjà le refus.
- **252 tests réussis, deux ignorés, un warning en 57,22 s**, suite arrêt/
  supervision/routage, Python 3.13/overlay tzdata et trois racines temporaires.
  Les deux cas natifs nécessitent le runtime Headroom séparé absent de cette
  recette ; warning Starlette/httpx existant. Pas de qualification du vrai
  démarrage/arrêt Headroom ni des API actives, aucune donnée active/Dropbox testée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-managed-service-regression-f0f8550342f546e9b703cedb42fcd292/tests.txt,
  SHA-256 b9437f52de55ab94003a286c3dee465eaf26a97c1ae42459e8b32471d41a96ba.
- CI enrichie (non exécutée à distance), plan/protocole/fiche v67 actualisés :
  contexte 11906/12000 octets, warnings vides ; diff ciblé valide. Gains de tokens
  non mesurés. Magasin protégé/ACL et lien guard/receipt supposés par le protocole,
  pas authentification administrative. Serveurs actifs anciens non modifiés.
  Drainage/WS/requêtes longues, descendants/service, Linux et critères L0–L9
  ouverts ; automatisation maintenue.

## L5/L8 — Drainage des requêtes et hook de fermeture

- Fiche MCP v67, statut, Git/journal et tests relus ; RepoWise service_runtime.py
  absent de l'index dix jours/mock, lecture du code local. Code Uvicorn installé
  consulté : shutdown attend connexions/tâches puis lifespan. websockets absent.
- Profil géré impose timeout_graceful_shutdown=None ; timeout Uvicorn qui pourrait
  annuler les tâches refusé avant enregistrement. Délai du demandeur ne tue ni
  n'annule ; tâche bloquée peut garder le service en drainage sans limite globale.
- Quatre nouveaux cas : HTTP retardé et streaming réel (deux morceaux) terminés
  intégralement après attente d'arrêt expirée ; hook lifespan retardé conserve
  signaux/guard jusqu'à sa fin ; timeout annulant les tâches refusé sans fichier.
  Ports éphémères, clients HTTP locaux et événements de fixture, aucune API active
  ni donnée Dropbox utilisée. Une erreur de placement du bloc finally dans le
  nouveau test a été corrigée après refus de collecte, avant exécution des fixtures.
- **129 tests réussis en 38,45 s**, arrêt/runtime/maintenance/scheduler-supervision/
  budget, Python 3.13/overlay tzdata et trois racines temporaires avant imports.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-service-drain-d6134d5c5bbe4a9984fbd077f570c459/tests.txt,
  SHA-256 276173bdfa1e3b6a25c24384906f2fbeeb88c68edc9d28d676e86843e11b7f15.
- CI enrichie (non exécutée à distance), protocole/plan/fiche v68 mis à jour ;
  contexte complet 11915/12000 octets, warnings vides. Diff ciblé valide. Pas de
  rechargement de services ni de reconstruction des releases. Qualification
  limitée à ASGI minimale : hooks réels/erreurs, déconnexions, charge/WS et
  descendants restent ouverts, avec activation/identité administrative/L0–L9.
  Aucun gain réel de tokens démontré ; automatisation maintenue.

## L5/L8 — Résultat de fermeture et erreurs de hooks

- Fiche MCP v68, board, Git/journal/tests relus ; RepoWise service_runtime.py
  absent (index dix jours/mock), code local et LifespanOn.shutdown installé lus.
  Uvicorn peut retourner normalement après hook en erreur : absence des signaux
  seule ne prouve pas une fermeture réussie.
- Résultat terminal atomique par service publié sous guard avant nettoyage,
  nonce/PID/création/image/profil liés ; stages ok/lifespan_error/not_started/
  forced_exit/server_error, aucun texte d'exception persisté. Échec de publication
  propage l'erreur et conserve les signaux. Observateur exige résultat correspondant
  et guard libre ; échec terminé distinct de succès (shutdown_finished=true,
  shutdown_completed=false, CLI 3). Timeout 2, refus 1, acceptation sans attente 0.
- stop.ps1 qualifie maintenant sa formulation d'échec sans présumer un processus
  encore vivant ; aucun kill. Deux vrais hooks de recette (failed et exception)
  ne produisent plus de faux succès ; injection d'échec de disque conserve les
  signaux. Contrat vérifié pour quatre résultats étrangers/invalides et quatre
  statuts CLI. Les erreurs propres aux requêtes business ne sont pas attestées.
- **132 tests réussis en 41,31 s**, suite arrêt/runtime/maintenance/scheduler/
  supervision/budget, Python 3.13/overlay tzdata, trois racines temporaires.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-service-outcome-92f81d1101e64b13ab73060234fb751d/tests.txt,
  SHA-256 2e340149c7b73b94716a215c1312705fa7517c998acdc278fe3d61f1617b68ec.
  Puis **29 tests terminal/runtime/drainage réussis en 12,52 s**, chevauchants,
  avec les huit vérifications supplémentaires de résultat/CLI. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-service-result-contract-cbf5a37cdea8428d9481e697cad5bec6/tests.txt,
  SHA-256 195d34e5f62408cff341cba56c192d48408a16455c78d1bf817cb13a026bbda6.
- Protocole/plan/fiche v69 actualisés ; contexte complet 11935/12000 octets,
  warnings vides, diff ciblé valide. Tests déjà inclus en CI, non exécutée à distance.
  Aucune donnée active/Dropbox, aucun serveur actif rechargé, releases inchangées.
  Dernier résultat seul conservé par service, historique/lecteur authentifiés,
  hooks réels/WS/charge/descendants et activation ouverts ; L0–L9 non achevés,
  automatisation maintenue. Économie de tokens toujours non mesurée.

## L5/L8 — Diagnostic local des preuves de fermeture

- Contexte MCP v69, board, Git/journal/tests relus ; RepoWise service_runtime.py
  absent, index dix jours/mock ; utilisation des sources locales.
- inspect_service_shutdown.py : trois racines explicites et service allowlist,
  consultation des trois preuves connues, 4096 octets par fichier, schéma/profil
  validés. Résultats absents/corrompus/étrangers distingués, nonces/données brutes
  et chemins d'image masqués ; hash de référence pour corréler les instances.
  Ancien résultat distingué de l'instance courante, pas déduit en succès actuel.
- Vérification OS optionnelle --verify-live, matches/mismatch/unavailable ; accès
  refusé ne prouve pas la mort. Pas de guard ni de création de répertoire, de base,
  de mutation, de sonde, de stop ni de relance. Bytecode désactivé au CLI.
  Code 0 = diagnostic fourni, pas service sain ; preuve invalide/inaccessible 1.
  Lectures/snapshot OS non transactionnels explicitement signalés.
- Vingt et un nouveaux cas : corrélation/ancienne instance/profil étranger,
  JSON malformé/UTF8 invalide/nesting excessif/volume, schéma invalide, fichiers
  non réguliers, preuves absentes sans création, vérification OS simulée/refusée
  et réelle Windows, CLI isolé sur racine absente et résultat historique valide.
  Octets et mtimes des fixtures conservés ; réponse testée sous 2048 octets.
- **50 tests réussis en 14,09 s**, diagnostic/runtime/drainage, Python 3.13/overlay
  tzdata et trois racines temporaires avant imports/enfants. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-shutdown-inspection-f8570a3460d147a6b8553983c61f1610/tests.txt,
  SHA-256 d6fbd57059e164f5853cdb00d982872e0c7f4b72dd4b547d166b5d4804ae8d7a.
- CI enrichie (non exécutée à distance), protocole/plan/fiche v70 actualisés ;
  contexte complet 11952/12000 octets, warnings vides, diff ciblé valide.
  Aucune donnée active/Dropbox ni serveur actif testé/rechargé ; releases inchangées.
  Pas d'authentification administrative du lecteur, magasin/parents/reparse/ACL,
  historique, WS/charge/hook métier/descendants et activation restent ouverts.
  L0–L9 non achevés, automatisation conservée, économie réelle de tokens non mesurée.

## L5/L8 — Qualification WebSocket réelle

- Fiche MCP v70, board devcore, Git/journal/tests relus ; RepoWise service_runtime.py
  absent (dix jours/mock), source actuel vérifié. Dépendance WS absente de recette
  et pyproject : ajout explicite websockets>=17.2,<18.0, source PyPI officielle
  https://pypi.org/project/websockets/ consultée. Uvicorn installé 0.54.0 choisit
  le protocole SansIO quand la dépendance est présente (code auto.py consulté).
- Résolution uv Windows/Python3.13 sur copie du lock existant : seule version
  ajoutée websockets 17.2, aucune suppression/autre changement de version ; bloc
  hashes généré incorporé en conservant les autres blocs. Overlay temporaire
  CP313 installé explicitement, extension speedups.cp313-win_amd64 vérifiée par
  la recette. Premier overlay issu du pip machine CP314 inutilisé pour les tests.
- Deux scénarios WS réels : echo, stop coopératif, close/disconnect 1012, hook et
  résultat terminal ok. Variante ASGI retardée après disconnect : dépassement
  d'attente sans annulation, signaux conservés, puis fermeture une fois libérée.
  Aucun proxy machine (proxy=None) ni fournisseur contacté ; ports éphémères,
  trois racines temporaires définies avant imports/enfants, données actives intactes.
- **70 tests réussis en 15,02 s**, diagnostic/runtime/drainage et politiques WS
  natif/auxiliaire, Python3.13/overlaytzdata/websockets. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-websocket-drain-final-2095e3c4a03e44b5ac28c2f2f41c851c/tests.txt,
  SHA-256 e439f571df83d8133812e4699d236f74a02f19a4ee4b5f59303860d2913cb736.
- CI couvre déjà les nouveaux cas via test_service_drain (dépendance pyproject),
  non exécutée à distance. Plan/protocole/fiche v71 actualisés : contexte complet
  11955/12000 octets, warnings vides ; diff ciblé valide. Overlay seulement,
  runtime/wheels/snapshots figés non reconstruits et services actifs non rechargés.
  Acheminement des messages en cours, reprise/WS fournisseur authentifié, vrais
  Headroom/hooks métier, charge/descendants et activation ouverts ; L0–L9 non
  achevés, automatisation maintenue, économie de tokens non mesurée.


## L5/L8 — Surveillance résistante aux signaux JSON corrompus

- Fiche MCP v71, board devcore, Git/journal/tests relus. RepoWise ne trouve pas
  service_runtime.py (index dix jours/mock), source locale utilisée.
- Défaut confirmé dans le code : json.loads peut lever RecursionError sous
  la borne de 4096 octets, non interceptée par le monitor d'arrêt. Conversion
  centrale en ValueError ; le monitor reste disponible. Nettoyage préservant
  les signaux malformés sans masquer un résultat terminal déjà publié.
  Un signal restant empêche toujours l'accusé de fermeture, pas de faux succès.
- Serveur Uvicorn réel sur port éphémère : nonce erroné puis JSON invalide,
  UTF8 invalide, nesting excessif et volume excessif conservés ; arrêt valide
  ensuite terminé. Tests de refus du lecteur et nettoyage avec guard libéré.
- **54 tests réussis en 15,63 s**, runtime/drainage/diagnostic, Python3.13
  avec overlays tzdata/WS et trois racines temporaires avant imports. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-malformed-stop-27924fa291644ee5bc230cf45a957b48/tests.txt,
  SHA-256 cab8dccd45d93e0c6d83fd34515c747af6b8816d9725164895dc1f14b87c2c99.
- Plan/protocole/fiche v72 actualisés ; CI couvre les fichiers mais pas exécutée
  à distance. Services actifs non rechargés, releases figées inchangées.
  Aucune donnée active/Dropbox testée. ACL/course de remplacement, vrais hooks,
  fournisseurs, charge et activation ouverts ; L0–L9 non achevés, automatisation
  conservée et économie de tokens non mesurée.
- Contexte complet v72 vérifié : 11929/12000 octets UTF-8, avertissements vides ; contrôle Git ciblé sans erreur (fichiers non suivis hors diff Git).


## L5/L8 — Admission HTTP/WS bornée sur tous les chemins LLM

- Fiche MCP v72, board, Git et tests relus. RepoWise headroom_routes.py absent
  (index dix jours/mock), sources locales confrontées au contrat.
- request_body.py ajouté : chunks HTTP, total 16 Mio et délai total 30 s ;
  Router chat/embeddings et adaptateur auxiliaire raccordés avant toute lecture
  de protocole/état et appel réseau. Refus 413/408, cancellation propagée,
  déconnexion refusée. Aucun repli ou fournisseur appelé sur refus.
- Headroom HTTP/WS utilise le même décodeur : profondeur maximale explicite
  64, chaînes/échappements ignorés pour ce comptage, UTF8/JSON invalides refusés
  sans détails de parseur. HTTP 400 ou fermeture WS 1008. Contrat plus strict
  à documenter pour les clients utilisant des structures de plus de 64 niveaux.
- Nouveaux cas : trois endpoints auxiliaires/profondeur/UTF8/volume, trois
  chemins Headroom, trame WS profonde, plafond cumulé par chunks, délai global
  et requête rapide concurrente, annulation externe et déconnexion.
- Premier passage : 3 échecs/6 erreurs de fixtures (IDs pytest énormes dépassant
  la borne Windows et lifespan manquant). Deux passages suivants : 3 échecs
  d'attente de message ; le parseur ne refusait pas la profondeur supposée.
  Correction avec plafond explicite et test de limite/chaînes, puis suite complète.
- **102 tests réussis en 24,91 s**, Python3.13, trois racines temporaires avant
  imports, overlays tzdata/WS. Un avertissement Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-body-bounds-ed28116abf244afea7390a8c5add95b4/tests.txt,
  SHA-256 30af5c79e5cd5797d562ad933e1acc076094f46043d7ec03023021f3bb533c8c.
- CI enrichie, non exécutée à distance. Plan/contrat/fiche v73 actualisés.
  Sources seulement, services actifs non rechargés, releases non reconstruites ;
  aucune donnée active/Dropbox ni fournisseur réel utilisé. Admission de
  connexions, charge/CPU du parsing, quotas agrégés, authentification fournisseur
  et activation ouverts. L0–L9 incomplets, automatisation conservée ; gain de
  tokens toujours non mesuré.
- Fiche v73 complète : 11953/12000 octets UTF-8, warnings vides ; diff des fichiers suivis concernés sans erreur. Nouveaux fichiers contrôlés par les tests, hors diff Git.


## L5/L8 — Capacité simultanée et refus non bloquant des chemins LLM

- Contexte MCP v73, board, Git, journal/tests et plan relus. RepoWise ne trouve
  pas headroom_routes.py (dix jours/mock), sources actuelles vérifiées.
- AdmissionGuard partagé ajouté : huit POST/WS simultanés par instance ASGI ;
  aucune attente si saturé, HTTP 503/Retry-After ou close ASGI WS 1013 avant
  admission. Aucun corps lu ni appel fournisseur pour la requête refusée.
  Headroom native/auxiliary et middlewares Router/adaptateur raccordés.
- GET/health/lifespan indépendants du budget ; les créneaux restent occupés
  durant streaming/WS/nettoyage, libérés par finally après erreur/annulation.
  Budget indépendant entre instances, sans variable globale de machine.
- Tests : requête lente et refusal avant receive, health accessible, flux/WS
  occupés et autres instances libres, réadmission après fermeture, annulation
  et erreur ; huit corps en cours puis neuvième refusée dans les applications
  Router/adaptateur, état et provider interdits, réadmission après libération.
- **100 tests réussis en 25,17 s**, capacité/admission/routage/WS/drainage,
  Python3.13 et overlays WS/tzdata, trois racines temporaires avant imports.
  Un avertissement Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-route-capacity-ae5f5fc9dd2342388b564cbe3328e4d7/tests.txt,
  SHA-256 caed4a624d4b2f353f0d7867c897bb7d0f128e41b7cadde52f8216bf17d09270.
- CI enrichie, non exécutée à distance ; plan/contrat/fiche v74 actualisés.
  Sources seulement, services actifs non rechargés, releases inchangées,
  données actives/Dropbox et fournisseurs réels non utilisés par les tests.
  Budget par instance/boucle, multiplié par les workers ; équité utilisateur,
  quotas de projet, connexions avant ASGI, charge/RSS/CPU et parsing synchrone
  restent ouverts. L0–L9 incomplets, automatisation conservée ; tokens non mesurés.
- Fiche v74 complète vérifiée : 11982/12000 octets UTF-8, avertissements vides ; diff ciblé des fichiers suivis sans erreur, nouveaux fichiers couverts par les tests.


## L5/L8 — Lecture et scan JSON coopératifs

- Fiche MCP v74, board, état Git, journal/plan/tests relus ; RepoWise ne trouve
  pas request_body.py (dix jours/mock), source locale utilisée.
- Scan de profondeur par blocs de 64 K caractères avec yield asyncio, état des
  chaînes/échappements conservé ; Headroom HTTP/WS et Router/adaptateur utilisent
  le décodeur asynchrone. Annulation propagée dans la coroutine, sans thread
  poursuivant le travail. Version synchrone du lecteur conservée pour les usages
  explicites. Lecture HTTP par bytearray, sans accumulation d'une liste de chunks.
- Première suite **105 réussis**. Ajout d'une vérification concrète des événements
  vides immédiatement disponibles : 106 réussis/1 échec, car Request.stream
  masque ces événements et empêche le yield de notre lecteur. Lecture des
  événements ASGI directs, comptage/yield tous les 64 événements dans les deux
  chemins HTTP ; deadline globale alors respectée sur ce flux.
- **107 tests réussis en 26,25 s**, scan/admission/capacité/routage/WS/drainage,
  Python3.13, overlays WS/tzdata, trois racines temporaires avant imports.
  Sonde servie avant fin du scan de 2 Mio (natif et auxiliaire), corps intact,
  annulation, chaîne échappée sur frontière et nombreux petits/chunks vides.
  Un avertissement Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-json-fairness-5954325bc8e246418847883ef84408c7/tests.txt,
  SHA-256 33c4b1b582e278156bdb4c1f759a79c836b728c783a00f00957007476db0d08b.
- Plan/contrat/fiche v75 actualisés ; fichiers déjà couverts en CI, exécution
  distante non réalisée. Sources seulement, services actifs non rechargés et
  releases inchangées. Données actives/Dropbox/providers réels non utilisés.
  UTF8/conversion du tampon/parseur standard restent synchrones, RSS/CPU/durée
  et charge globale à qualifier ; équité par utilisateur et activation ouvertes.
  L0–L9 incomplets, automatisation maintenue, économie de tokens non mesurée.
- Fiche v75 complète vérifiée : 11977/12000 octets UTF-8, avertissements vides. Fichiers modifiés non suivis, vérifiés par la suite ciblée.


## L8 — Diagnostic borné de l'admission LLM

- Contexte MCP v75, board, état Git, journal/plan et tests relus. Recherche
  RepoWise admission.py vide (dix jours/mock), sources locales vérifiées.
- Compteurs agrégés fixes dans AdmissionGuard : admis, terminés ASGI, erreurs,
  annulations, refus HTTP/WS ; active/peak/capacity par instance, entiers
  plafonnés à 2^63-1 avec flag de saturation. Pas de données de requête retenues.
- GET /devcore/admission intercepté en amont dans les quatre profils, sans
  créneau ni lecture du corps, Cache-Control no-store, JSON sous 1 Kio.
  Lecture sans authentification dans le pilote localhost, aucune certification
  de santé ; finished n'est pas un succès métier/provider.
- Tests complétés : diagnostics pendant saturation dans les vraies apps
  Router/adaptateur, active=8/refused=1 puis active=0/finished=9 après refus de
  politique et réadmission ; annulation/exception et WS/stream comptés ;
  indépendance des instances, headers/query privés absents, saturation des
  compteurs sans croissance/rebouclage, endpoint ne consommant pas de créneau.
- **90 tests réussis en 18,64 s**, capacité/routage/liveness/WS, Python3.13
  et overlays tzdata/WS, trois racines temporaires avant imports. Avertissement
  Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-admission-metrics-a460565623ad4366a3fc250d761d7538/tests.txt,
  SHA-256 84da1a58212a4aa195f7639b3cb04dadec953e164c3e978016d941340d12120c.
- Plan/contrat/fiche v76 actualisés ; fichiers déjà couverts en CI, distante
  non exécutée. Compteurs volatils/par instance, pas d'export historique LLMOps,
  d'authentification administrative ou de métriques tokens/coût/trace_id.
  Sources seulement, services actifs non rechargés, releases inchangées ;
  aucune donnée active/Dropbox ou fournisseur réel utilisé. Charge/équité
  et activation ouverts ; L0–L9 incomplets, automatisation conservée.
- Fiche v76 complète vérifiée : 11969/12000 octets UTF-8, avertissements vides. Sources modifiées non suivies, couvertes par les tests ciblés.


## L8 — Tampon LLMOps borné et erreurs contenues

- Contexte MCP v76, board, Git, journal/plan/tests relus. RepoWise trouve
  API/devcore_api/llmops.py (index dix jours/mock), source actuelle confrontée :
  liste sans limite et exception de transport propagée, pas d'appelant hors tests.
- Client : 256 événements/1 Mio sérialisé par défaut, événement 4 Kio max,
  schéma/IDs/usage/coût validés ; overflow refuse le nouveau et compte la perte.
  snapshot agrégé, copie de lecture, lock et callback hors lock ; exceptions
  ordinaires contenues, aucun détail sensible/retry, rétention bornée si échec.
  sent signifie callback revenu, pas ingestion prouvée ; usage reste déclaré.
- **16 tests réussis en 1,82 s**, LLMOps/observabilité, Python3.13 et trois
  racines temporaires avant imports. Compatibilité, bornes count/bytes,
  événements invalides sans buffer/envoi, erreur de transport et concurrence
  128 captures/capacité huit. Avertissement Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-llmops-bounds-2d2fb15d05e647d6aef875dbc2985ba1/tests.txt,
  SHA-256 726f2728c6354b80d36cdd9dac9887872bde701c2c81805609f3c0f95d5d9fc6.
- CI enrichie non exécutée à distance, diff ciblé valide ; plan/fiche v77 et
  contrat llmops-client.md actualisés. Aucun transport réseau réel/flush, worker
  asynchrone ni branchement au workflow ; callbacks synchrones sans délai
  garanti, IDs de confiance, tokens observés/estimés encore à distinguer.
  Services actifs/releases inchangés ; données actives/Dropbox non utilisées.
  Export/ingestion et L0–L9 ouverts, automatisation maintenue, gains non mesurés.
- Fiche v77 complète vérifiée : 11984/12000 octets UTF-8, avertissements vides ; diff des sources/tests/CI suivis sans erreur.


## L8 — Export OTLP réseau asynchrone sur recette locale

- Fiche MCP v77, board, Git, journal/tests relus ; RepoWise llmops.py trouvé
  (dix jours/mock), code actuel vérifié. Docs officielles Langfuse/OTLP consultées
  (liens dans llmops-client.md) : JSON HTTP et header v4, ancien ingestion
  déprécié ; choix du endpoint moderne sans SDK/instrumentation globale.
- OtlpExporter explicite ajouté : HTTPS, clé/endpoint passés par application,
  loopback HTTP seulement opt-in, sans proxy environnement/redirect/retry.
  Une requête par instance, payload/réponse 8 Kio, délai total 2 s ; ACK plein,
  warning et refus partiel distingués, erreurs réseau bornées sans texte sensible.
  Annulation propagée, busy libéré, fermeture explicite sans interrompre un envoi.
- Trace UUID non nulle/timing explicite, spans et attributs modèle/corrélation/
  usage déclaré seulement, aucun prompt. Pas d'invention de durée ni de gains.
- Premier passage : huit échecs d'assertion sur casse HTTP des headers, vingt-
  quatre réussites. Assertions corrigées sans changement de comportement.
- **32 tests réussis en 12,31 s**, OTLP/client/observabilité, Python3.13 et trois
  racines temporaires avant imports ; vrais serveurs HTTP loopback/ports
  éphémères, faux credentials et ACK, aucun fournisseur/Langfuse réel.
  Avertissement Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-otlp-export-final-bafe952665004eabb4cb34374529424b/tests.txt,
  SHA-256 af412eb79582dfcd8490f106fbb06c893e27f0ecaa7c6213e3a106b5105efe73.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v78 actualisés.
  Module séparé, non raccordé au workflow, export volontaire sans file/flush
  durable ni retry. Langfuse UI, TLS/identités réelles, quota global et activation
  encore ouverts ; tokens/coût déclarés pas certifiés. Sources seulement,
  services actifs/releases et données actives/Dropbox inchangés. L0–L9 ouverts,
  automatisation conservée ; économie effective non mesurée.
- Fiche v78 complète : 11995/12000 octets UTF-8, avertissements vides ; diff CI sans erreur, nouveaux modules/tests couverts par la suite ciblée.


## L8 — File OTLP bornée et drainage suivi

- Reprise fiche MCP v78, board, mémoire de continuité, Git et journal/tests
  pertinents ; RepoWise ne référence pas otlp_export.py, index ancien/mock :
  code local utilisé. Environnement de recette Python 3.13 vérifié.
- OtlpWorker explicite ajouté : tâche asyncio suivie, propriétaire exclusif du
  transport, FIFO volatile 256 événements/1 Mio par défaut, en cours inclus.
  Validation et mesure du payload avant admission, refus immédiat à saturation,
  compteurs fixes sans contenu ni texte d’erreur ; yield entre envois.
- Fermeture : nouvelles admissions refusées, drainage puis fermeture du client.
  Expiration de l’attente retourne False ; annulation de l’appelant propagée
  sans annuler le worker. Refaire aclose pour confirmer la fin avant arrêt de
  boucle. Erreurs ordinaires comptées, suite de file poursuivie sans retry.
- Premier passage : 1 échec / 38 réussites ; fixture supposée >1 Kio mais plus
  petite. Fixture agrandie dans les limites du schéma et taille explicitement
  vérifiée ; 39 réussites. Dernier passage refait avec LOCAL/DATA/PLATFORM
  temporaires définis avant imports (PROJECTS ne remplace pas PLATFORM).
- **39 tests réussis en 17,67 s**, Python 3.13, vrais récepteurs HTTP loopback
  et credentials factices ; saturation count/bytes, réseau retardé, fermeture
  expirée/annulée, refus partiel/HTTP, poursuite après exception et régression
  exporter/client/observabilité. Warning Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-otlp-worker-isolated-9f3f76b2352b44e6916420390225f23b/tests.txt,
  SHA-256 547f26d654c2fe27bc866fc31a79261a409b1f0bb78aaab0e6c20ce80ffbf2f1.
- CI enrichie non exécutée à distance ; plan, contrat et fiche v79 mis à jour.
  Lecteur local : 11983/12000 octets UTF-8, warnings vides, décision remplacée
  D-001 exclue ; gains tokens non mesurés. Diff CI valide.
- Module non raccordé au workflow ni activé ; arrêt de boucle/processus peut
  perdre la file. Persistance/flush durable, identité/TLS réels, ingestion/UI
  Langfuse, quota global et activation restent ouverts. ACK de fixture ne prouve
  pas le stockage opérationnel. Services/releases non modifiés, aucune fixture
  active/Dropbox/RepoWise utilisée ; L0–L9 et automatisation toujours ouverts.


## L8 — Observation explicite des appels asynchrones

- Reprise fiche v79 (lecteur local et MCP), board projet, état Git et journal/
  tests pertinents. RepoWise trouve CodexManualAgentRunner, index dix jours/
  mock ; code actuel confronté : ce runner écrit des instructions manuelles,
  sans réponse modèle ni usage. Pas de génération ou de coût inventés.
- GenerationObserver ajouté, opt-in : opération asynchrone appelée une fois,
  même objet résultat retourné ; adaptateur synchrone explicite construit
  l’événement depuis la réponse, horodatages entourent l’appel observé. Aucun
  routage/mapping, retry, prompt ni défaut d’usage/coût. Worker déjà démarré,
  fermeture/drainage restent à la charge du propriétaire de la boucle.
- Échecs/annulations de l’opération propagés sans événement de succès ; pannes
  ordinaires de télémétrie/horloge, événement invalide et saturation n’altèrent
  pas le résultat. Compteurs bornés sans contenu, refus distingués. L’adaptateur
  doit rester borné et sans réseau ; pas de promesse pour un callback arbitraire.
- **48 tests réussis en 25,65 s**, Python 3.13 documenté, racines LOCAL/DATA/
  PLATFORM temporaires avant imports, connexions HTTP loopback/clés factices.
  Réponse avant ACK retardé, saturation laissant la génération suivante
  disponible, usage/modèle/timing conservés, erreurs/annulation propagées,
  erreurs de télémétrie contenues et régression des 39 tests précédents.
  Warning Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-generation-observer-d7e2f789548b442baf16e321036b578b/tests.txt,
  SHA-256 5f6f8a514e1094a531763c27ee62d9d81770c12057774a146fc6be8a8ba00f52.
- CI enrichie non exécutée à distance, protocole/plan/fiche v80 actualisés.
  Premier contrôle de contexte refusé après conversion Windows LF→CRLF ;
  fiche réécrite en LF, empreinte recalculée, contrôle intégral réussi :
  11979/12000 octets UTF-8, warnings vides, aucun extrait de secours utilisé.
- Raccordement générique sur fixtures seulement : adaptateur fournisseur réel
  et intégration workflow ouverts. Aucun service/release actif modifié, aucune
  donnée active/Dropbox/index réel comme fixture. Persistance/flush durable,
  ingestion/UI Langfuse réelles, identités et quota global ouverts. Usage déclaré
  et durée applicative ne prouvent pas un gain de tokens. L0–L9 non terminés ;
  automatisation maintenue.


## L8 — Branchement HTTP du Router auxiliaire à l’export OTLP

- Fiche MCP v80/board explicite, mémoire de continuité, Git, journal et tests
  concernés consultés. RepoWise trouve providers.py (index dix jours/mock),
  code actuel relu. Estimations historiques du Router identifiées : non utilisées
  par ce nouvel adaptateur et toujours distinctes des mesures fournisseur.
- POST chat/completions non-streaming : observation seulement si app.state
  fournit generation_observer et generation_event_factory. Sans configuration,
  chemin existant. Validation auxiliaire avant observation ; refus des modèles
  natifs, embeddings/streams inchangés. Aucun import API au démarrage du Router.
- Adaptateur event_from_chat_response : HTTP 200/route auxiliaire, JSON 64 Kio
  maximum, modèle résolu cohérent, usage explicite entier et total cohérent ;
  coût/corrélation fournis par application. Aucun token/coût estimé, prompt ou
  consultation du projet actif. Réponse invalide/volumineuse préservée par
  l’observateur, erreur comptée sans nouvelle tentative de l’opération.
- **73 tests réussis en 25,67 s**, Python 3.13 documenté, racines LOCAL/DATA/
  PLATFORM temporaires avant imports : ASGI réel sur Router, opération
  fournisseur substituée, vrai HTTP loopback OTLP/clés factices. ACK retardé
  sans blocage de réponse, natif refusé avant opération, usage/modèle/projet
  exportés sans contenu ; défaut de configuration/usage conserve octets/statut/
  headers sans retry. Régressions observateur/worker/exporter/client, politique
  et admission de corps incluses. Warning Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-router-observation-final-1dc8d933d36347d0a14a50c44bb3c00a/tests.txt,
  SHA-256 33e29d414178cc32e6e9fd8e6c8e91d4e59d6a951b8b58f8ce58e4f9f3ad7466.
- Chemin source explicite ajouté au nouveau test pour la CI sans PYTHONPATH ;
  vérification complémentaire ciblée : 10 tests réussis en 3,97 s sans cette
  variable, mêmes racines temporaires. CI enrichie non exécutée à distance.
- Plan/contrat/fiche v81 mis à jour, empreinte recalculée, lecteur intégral
  11964/12000 octets UTF-8 et warnings vides ; diff Router/CI sans erreur.
- Branchement non activé et fournisseur réel non contacté. Durée observée
  englobe les attentes/retries internes existants, sans preuve des tokens des
  tentatives échouées. Usage/coût restent déclarés, corrélation de confiance
  non authentifiée. Adaptateur de coûts/principal, démarrage/drainage applicatif,
  workflow/streams, persistance/flush durable et Langfuse réel ouverts. Services
  et releases actives non modifiés, données actives/Dropbox/index réel non utilisés
  comme fixtures. Gains non mesurés ; L0–L9 et automatisation restent ouverts.


## L8 — Cycle de vie OTLP du Router

- Fiche MCP v81/board explicite, mémoire, état Git, journal et tests lus.
  RepoWise trouve gemini_router.py, dix jours/mock ; code actuel confronté.
  Python 3.13 de recette utilisé ; changement du seul cycle de vie facultatif.
- FastAPI raccordé à observation_lifespan : par défaut rien créé ; factory
  explicite retourne observer et callback, worker neuf démarré avant installation
  des références. Dépendances existantes/worker actif refusés sans remplacement.
  Callback invalide fait échouer startup en fermant le client possédé.
- Shutdown : refus des admissions, attente répétée du drainage, fermeture du
  client avant sortie, retrait des seules références possédées. Timeout de
  l’attente ne vaut pas succès ; fin de tâche relue en cas de course. Fermeture
  définitivement refusée fait échouer lifespan, références gardées pour diagnostic.
- Deux premiers passages : 2 échecs / 76 puis 78 réussites. Course timeout/fin
  de tâche faussement traitée comme échec ; nettoyage d’attribut absent avec
  valeur None masquant l’erreur de startup. Lecture du résultat terminal et
  contrôle d’existence corrigés, sans ignorer la fermeture.
- **80 tests réussis en 30,07 s**, vraies connexions HTTP loopback et clés
  factices, racines LOCAL/DATA/PLATFORM temporaires avant imports. Drainage
  retardé restant suivi après timeout, admissions closes, cycles successifs,
  callback invalide, exception du corps préservée, références existantes
  protégées ; startup/shutdown ASGI via TestClient du Router. Régressions
  route/observateur/worker/exporter/client/politique/admission incluses.
  Warning Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-observation-lifecycle-fixed-ed0451932dd449da87727cb66269e163/tests.txt,
  SHA-256 89c498dbc643377d82aa528823f57db561a35ea539e9c1518a25a8ce33434c49.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v82 actualisés,
  empreinte recalculée. Lecteur intégral 11966/12000 octets UTF-8, warnings
  vides ; diff Router/CI sans erreur.
- Activation absente : aucun fournisseur/Langfuse réel contacté, aucune release
  ni service actif modifié. File volatile, arrêt variable (capacité × délai
  transport), annulation externe/kill non qualifiés ; pas de délai global
  garanti, persistance ni supervision externe. Factories de confiance bornées,
  coût/principal et workflow/streams encore ouverts. Données actives/Dropbox/
  index réels jamais utilisés comme fixtures ; gains non mesurés, L0–L9 ouverts,
  automatisation maintenue.


## L8 — Usage fournisseur distingué des estimations non-streaming

- Fiche MCP v82/board explicite, mémoire, Git, journal/plan et code/tests
  concernés lus. RepoWise providers.py disponible, index dix jours/mock ;
  comportement actuel confirmé dans le code : estimation du texte remplaçant
  un usage absent ou nul dans les réponses Gemini non-streaming.
- reported_usage ajouté : usage entier non booléen, non négatif, somme <2^63,
  total optionnel cohérent ; incomplet/invalide refusé sans valeur inventée.
  Embeddings : prompt explicite et zéro de complétion si absent. Zéros réels
  préservés au lieu d’être remplacés par taille de texte.
- Chemins Gemini et replis autorisés non-streaming raccordés : comptabilité
  seulement si usage valide, header provider_reported/unavailable. Réponse
  (octets/statut) conservée, pas de nouveaux retries, prix ni export automatique.
- **97 tests réussis en 30,40 s**, Python 3.13, racines LOCAL/DATA/PLATFORM
  temporaires avant imports. 17 nouveaux cas : zéros/incomplet/bool/négatif/
  chaîne/total invalide/overflow/embedding, vraies fonctions de provider sur
  transport substitué Gemini et Cerebras, sans réseaux/credentials réels,
  compteurs observés via spies sans écriture de statistiques. Régressions
  Router/OTLP/lifecycle et admission incluses. Warning Starlette/httpx connu.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-reported-usage-bc92b8a068434eb293ad413c294fb04c/tests.txt,
  SHA-256 681d4b23013a2d82c98b082a21615fd9b07b7ff0d38e3b5b7d53a2b919393051.
- Plan/protocole/fiche v83 et empreinte actualisés ; lecteur intégral
  11962/12000 octets UTF-8, warnings vides ; CI enrichie non exécutée à distance,
  diff providers/CI sans erreur.
- Estimations d’admission avant appel conservées. Streams et historique de
  statistiques peuvent encore être mélangés : pas de migration/qualification
  silencieuse. Absence d’usage ne vaut ni consommation nulle ni économie.
  Attribution projet actif, retries/facturation/coûts, fournisseur réel et
  qualité équivalente restent ouverts. Sources seulement, services/releases
  actives inchangés ; données actives/Dropbox/index réels non utilisés comme
  fixtures. L0–L9 non terminés, automatisation maintenue, gains non mesurés.


## L8 — Usage SSE borné, fragments et absence de reprise après émission

- Fiche MCP v83/board, mémoire, Git, journal et tests concernés lus. RepoWise
  trouve stream_parser.py, index dix jours/mock ; code actuel confirmé :
  estimation prompt/sortie, accumulation illimitée du texte et parse par chunk
  pouvant manquer un événement fragmenté.
- SseUsage ajouté : framing LF/CRLF et data multi-lignes, ligne/événement
  chacun <=64 Kio, invalidité/dépassement désactivent l’observation et libèrent
  les tampons. Usage explicite validé, dernier couple retenu, aucune accumulation
  de texte. Compteurs publiés seulement avec DONE complet et EOF normal.
- Forwarding inchangé octet par octet ; usage absent/invalide/incomplet ou
  annulation/erreur sans comptabilité inventée. Après émission, erreur propagée
  sans retry qui dupliquerait du texte. Avant émission : trois tentatives
  historiques, succès marqué seulement après consommation normale.
- Premier passage : 108 réussites, quatre erreurs de setup/teardown Windows
  (PYTEST_CURRENT_TEST dépassait 32767 caractères pour les grosses fixtures).
  IDs courts ajoutés, aucun besoin de réduire les scénarios de dépassement.
- **110 tests réussis en 29,81 s**, Python 3.13, trois racines temporaires avant
  imports, providers substitués et OTLP loopback/faux credentials. Fragments
  d’un octet, CRLF/multi-lignes, zéros, absence/DONE incomplet, volume/JSON,
  octets conservés, erreur après émission et annulation sans retry ; régressions
  non-stream/lifecycle/OTLP/politique/admission incluses. Warning connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-usage-final-3ee5e7bd58d14369ba52d00369c851ad/tests.txt,
  SHA-256 adee46b944340111437fa08eaf7017026e4fade05942dbc53814c533eabff614.
- Cas supplémentaire avant émission ajouté : trois tentatives puis erreur
  visible, sans faux succès. **14 tests ciblés réussis en 1,91 s** sur le
  parseur final, racines temporaires et aucun réseau réel. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-usage-probe-d427aa19975d4a81b0dd8bb531e2b0e2/tests.txt,
  SHA-256 f72b18dbbb4176d8d40510035013b51cb2d3d38146838ac5ff34ebb336f38b03.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v84 actualisés,
  empreinte recalculée, lecteur intégral 11960/12000 octets UTF-8, warnings
  vides, diff stream/CI sans erreur.
- CR seul/autres formats SSE non qualifiés, export OTLP des streams non ajouté.
  Usage indisponible n’est ni zéro ni économie. Estimation d’admission,
  attribution au projet actif, stockage JSON historique/mélangé, coûts et
  tentatives perdues restent à qualifier. Sources seulement ; services/releases
  actifs inchangés et aucun fournisseur réel. Données actives/Dropbox/indexs
  réels non utilisés comme fixtures. L0–L9 et automatisation ouverts.


## L8 — Admission locale sans attente sous verrou

- Fiche MCP v84/board, mémoire, Git, journal et tests relus. RepoWise trouve
  SlidingWindowRateLimiter (index dix jours/mock) ; code actuel confirme
  asyncio.sleep sous verrou pendant la fenêtre d’une minute.
- Limiteur extrait dans rate_limit.py : une boucle propriétaire, horloge
  monotone, méthodes asynchrones sans await interne/lock/sleep. RPM et
  réservations de tokens atomiques, refus immédiat RateLimitRefusal ; Gemini
  non-streaming retourne 429/Retry-After 1..61 s, sans retry ni fallback qui
  contournerait ce refus local. Appelant n’attend plus sous verrou.
- Réservations <=max_rpm (max4096), usage déclaré groupé par seconde (<=61
  groupes, plafonnement capacité+1), expiration conservatrice <1 s. Estimation
  réservée plus compteurs déclarés : double compte possible, aucun plafond
  financier affirmé. Tokens invalides et horloge/boucle étrangères refusés.
- **119 tests réussis en 29,81 s**, Python 3.13 documenté, LOCAL/DATA/PLATFORM
  temporaires avant imports. Huit nouveaux cas : vingt admissions concurrentes
  pour capacité deux, refus/réouverture, comptage disponible après refus,
  réservations TPM, dix mille enregistrements bornés, expiration arrondie,
  valeurs invalides, refus direct avant fournisseur/repli pourtant autorisé.
  Aucun vrai provider ni écriture de statistiques ; régressions Router/SSE/
  OTLP/lifecycle et admission incluses. Warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-rate-limit-f1312777924e4a12a47e6962d020719d/tests.txt,
  SHA-256 14796869f233c2b31be2d0a0a38dfbe01f82bbbec2004f9a1e2377996d753a34.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v85 et empreinte
  actualisés, lecteur intégral 11960/12000 octets UTF-8, warnings vides. Diff
  providers/CI sans erreur.
- Portée instance/boucle sur Gemini non-streaming seulement ; streams/replis
  directs, quotas par utilisateur/interprocessus et adaptation fournisseur
  ouverts. Réservations conservatrices peuvent refuser avant quota réel, restart
  processus sans état ; nouvelle boucle exige nouveau limiteur. JSON/statistiques
  historiques et attribution projet actif encore ouverts, gains non mesurés.
  Sources seulement, services/releases actifs inchangés ; données actives/
  Dropbox/index réel non utilisés comme fixtures. L0–L9 non terminés, automation
  conservée.


## L8 — Admission HTTP des flux Gemini et retour d’usage au limiteur

- Fiche MCP v85/board, mémoire, Git, journal/tests relus. RepoWise
  gemini_router.py dix jours/mock confronté au code actuel ; streams
  jusque-là sans admission RPM/TPM, usage déclaré non transmis au limiteur.
- Route streaming : réservation après politique/clé valide et avant
  StreamingResponse/générateur, sur la même instance que non-streaming.
  Saturation : HTTP429 JSON et Retry-After avant en-têtes SSE, aucun appel
  réseau/repli. Modèle natif ou clé absente ne consomme pas de réservation.
- Limiteur injecté explicitement au générateur : total déclaré après DONE/
  EOF normal enregistré ; aucun compteur après usage absent/incomplet,
  erreur ou annulation. Octets conservés, pas d’estimation de sortie/coût.
- **121 tests réussis en 30,23 s**, Python3.13 documenté et trois racines
  temporaires avant imports. Deux nouveaux parcours ASGI : stream admis puis
  stream refusé avant générateur, absence de clé/natif sans admission ; tests
  SSE existants vérifient total validé/absence/incomplet/erreur/annulation
  vers le limiteur injecté. Régressions rate/usage/OTLP/lifecycle incluses.
  Warning Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-admission-ad1f87f2718c46ba8a7ab07aa0731f8d/tests.txt,
  SHA-256 2de09120f2a94e0395d93bdc767cf414552e06c35316a34e0a69b98d3f23f34c.
- Assertion renforcée : vraie route non-stream après stream reçoit aussi 429
  avant client amont, exception typée vérifiée. **16 tests ciblés réussis en
  2,14 s** sur fixtures finales, aucun fournisseur ni donnée active. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-admission-probe-d819317d816540739fe47a4b2d5a6dcd/tests.txt,
  SHA-256 a0df3ec80d668c91703d163256c0e8c11f2937770f1ca6761a10bffa6d50ccce.
- Plan/protocole/fiche v86 actualisés et empreinte recalculée ; contexte
  intégral 11969/12000 octets UTF-8, warnings vides. CI enrichie non exécutée
  à distance, diff Router/stream/CI sans erreur.
- Stream réserve une requête logique ; tentatives amont avant émission
  pas encore admises chacune. Replis directs, quotas par utilisateur/processus,
  attribution projet actif, statistiques JSON/historique et facturation encore
  ouverts ; réservation conservatrice peut surestimer et reste jusqu’à expiry.
  Sources seulement, services/releases inchangés ; aucun fournisseur réel et
  aucune donnée active/Dropbox/index réel comme fixture. Gains non mesurés,
  L0–L9 et automatisation toujours ouverts.


## L8 — Admission de chaque retry streaming avant émission

- Fiche MCP v86/board, mémoire, Git, journal/tests relus. RepoWise
  stream_parser.py dix jours/mock confronté au code actuel : une seule
  réservation logique malgré les trois tentatives internes possibles.
- Route transmet limiteur et estimation initiale ; première tentative déjà
  admise avant en-têtes. Chaque retry avant émission revérifie l’admission
  avant tout appel réseau. Refus local : erreur SSE explicite/bornée avec
  type local_rate_limit et retry_after, fin du générateur, aucun appel/repli.
  HTTP déjà ouvert reste200 ; refus initial reste HTTP429 JSON.
- Plafond trois/backoff amont conservés et aucun retry après données émises.
  Usage réussi enregistré une seule fois, pas de tokens attribués aux erreurs.
  Message public d’épuisement sans texte de dernière exception.
- **125 tests réussis en 30,48 s**, Python3.13 de recette, racines LOCAL/DATA/
  PLATFORM temporaires avant imports. Quatre nouveaux cas avec vrai limiteur
  et amont substitué : 429/500/transport puis retry saturé sans deuxième appel,
  erreur SSE <512 octets sans détail privé ; retry admis après500, deux
  réservations, réponse conservée et usage enregistré une fois. Régressions
  Router/SSE/limiteur/OTLP/lifecycle/politique/admission incluses. Aucun vrai
  fournisseur ; warning Starlette/httpx préexistant. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-retries-4ce15f9d3d404402aceb136e3ced0df0/tests.txt,
  SHA-256 a55251f1973f93745fe5b227f04e1c4e508b7f287dfdc2d74650c9a58a184402.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v87 actualisés,
  empreinte recalculée et lecteur intégral 11978/12000 octets UTF-8, warnings
  vides. Diff Router/stream/CI sans erreur.
- Calls directs sans limiteur internes seulement ; route HTTP injectée.
  Réservations conservatrices locales, replis directs/quotas utilisateur et
  interprocessus, budget financier, redaction globale des logs/historique
  et attribution projet actif restent ouverts. Sources seulement ; services/
  releases actifs inchangés, données actives/Dropbox/index réel non utilisés
  comme fixtures. Gains non mesurés, L0–L9 et automatisation ouverts.


## L8 — Admission des replis Cerebras/NVIDIA sans contournement local

- Fiche MCP v87/board, mémoire, Git et journal/tests relus. RepoWise
  providers.py dix jours/mock confronté au code actuel : _try_provider_request
  jusque-là sans admission. Modifications existantes conservées.
- fallback_limiters séparés cerebras/nvidia-nim, politique DevCore locale
  par défaut 8 RPM/capacité tokens 200000 (pas un quota commercial affirmé).
  Réservation estimée avant réseau, usage explicite valide vers son limiteur
  avant comptabilité historique, zéro/absent conservés sans estimation.
- Refus local terminal HTTP429/Retry-After, sans appel ni continuation de
  chaîne. Panne amont peut poursuivre un autre repli seulement autorisé,
  avec admission indépendante. Modèles natifs et route auxiliaire inchangés.
- **129 tests réussis en 30,43 s**, Python3.13 documenté et trois racines
  temporaires avant imports. Quatre nouveaux cas : saturation Cerebras/NVIDIA
  sans réseau ni next-provider, panne500 Cerebras suivie de NVIDIA admis/usage
  enregistré une fois au bon état, absence d’autorisation sans réservation
  ou appel. Tests d’usage précédents adaptés aux nouveaux états injectés,
  conservant cas zéro/absent et compteurs ; régressions Router/SSE/limiteur/
  OTLP/lifecycle incluses. Warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-fallback-admission-ba6afd2a11cf483584a2be5d9c5e9abe/tests.txt,
  SHA-256 edd05e6cf83e57d6ed61fb0d462ae010cf325f47e6f10c3be9037404c61b2248.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v88 et empreinte
  actualisés, lecteur intégral 11972/12000 octets UTF-8, warnings vides.
  Diff providers/CI sans erreur.
- Trois états locaux indépendants et conservateurs, sans équité utilisateur/
  quotas interprocessus/persistance ni budget financier réel. Attribution
  projet actif/statistiques JSON/historique, adaptation des quotas commerciaux
  et redaction globale ouvertes. Réservations échouées expirent sans inventer
  des tokens. Sources seulement, services/releases inchangés, aucun fournisseur
  réel ; données actives/Dropbox/index réel non utilisés comme fixtures.
  Gains non mesurés, L0–L9 et automatisation toujours ouverts.


## L8 — Diagnostics explicites sans corps amont ni exceptions brutes

- Fiche MCP v88/board, mémoire, Git, journal/tests relus. RepoWise
  providers.py dix jours/mock confronté au code actuel ; impression de
  r.text[:200] et de textes d’exceptions dans plusieurs catches confirmée.
- Diagnostics providers/stream réduits aux messages fixes, fournisseur/statut
  et tentative. Corps HTTP d’erreur et exceptions brutes retirés des print,
  erreurs de persistance/usage remplacées par libellés fixes ; dernière
  exception streaming non retenue inutilement. Résultats/retries inchangés.
- **132 tests réussis en 30,36 s**, Python3.13 documenté et trois racines
  temporaires avant imports. Trois nouveaux cas Gemini/Cerebras/NVIDIA :
  marqueur privé dans exception ou HTTP500 absent stdout/stderr et erreur
  publique, nombre de tentatives conservé. Assertions supplémentaires
  streaming avant émission sur exception privée ; régressions admission/
  usage/SSE/OTLP/lifecycle incluses. Aucune donnée active/fournisseur réel,
  amonts substitués et seuls récepteurs OTLP loopback. Warning connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-private-diagnostics-880ec3a763e64c298f82f431e4535e7d/tests.txt,
  SHA-256 a7b4b70d0c3495eace04ed0996f3cfd6919b92e931188fbbd934050be630bd68.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v89 et empreinte
  actualisés, lecteur intégral 11977/12000 octets UTF-8, warnings vides ; diff
  providers/stream/CI sans erreur.
- Confidentialité end-to-end non qualifiée : exceptions après émission
  propagées et possibles tracebacks framework, fichiers historiques/alertes,
  identités/corrélation et autres composants ouverts. Aucune affirmation de
  redaction globale. Quotas utilisateur/processus, attribution et facturation
  toujours ouverts. Sources seulement, services/releases actifs inchangés ;
  données actives/Dropbox/index réel non utilisés comme fixtures. Gains
  non mesurés, L0–L9 et automatisation restent ouverts.


## L8 — Deadline asynchrone unique des complétions et replis

- Fiche MCP v89/board, mémoire, Git, journal/tests lus. RepoWise providers.py
  dix jours/mock confronté au code : timeouts HTTPX par phase, sans plafond
  global de chaîne incluant Retry-After/backoffs et replis.
- call_with_fallback enveloppe la chaîne dans asyncio.timeout : 120 s par
  défaut, paramètre interne explicite >0..120 s, pas un champ du corps client.
  Budget partagé entre admission/appels/backoffs/replis ; expiration504 JSON
  provider_deadline, sans nouveau provider. Annulation externe propagée.
- Premier passage : 2 échecs / 138 réussites. Réponse HTTPX simulée sans
  Request associée : raise_for_status échouait et retardait la réponse rapide.
  Fixture corrigée avec Request, aucun changement de comportement métier.
- **140 tests réussis en 30,90 s**, Python3.13 documenté, LOCAL/DATA/PLATFORM
  temporaires avant imports. Huit nouveaux cas : appel Gemini/repli suspendu
  ou Retry-After3600 sous délai .03 s, autre requête rapide disponible, 504
  sans second appel ; annulation externe propagée, paramètres invalides
  refusés avant fournisseur. Amonts substitués et aucune donnée active,
  régressions Router/SSE/admission/OTLP/lifecycle incluses. Warning connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-provider-deadline-final-c5b0d28feaf145f48c69d61b418903e7/tests.txt,
  SHA-256 eab83438f2b0d5384e734039a13f7d1ec5989dcbb815391192ba8a7c7ac4c2d9.
- Plan/protocole/fiche v90 et empreinte actualisés ; lecteur intégral
  11987/12000 octets UTF-8, warnings vides ; CI enrichie non exécutée à
  distance, diff providers/CI sans erreur.
- Deadline coopérative seulement aux await : JSON/CPU, writes synchrones et
  time.sleep historiques non préemptés, délai mural strict non garanti.
  Durée globale des streams et bornes de réponse amont encore ouvertes.
  Timeout ne prouve pas non-réception/amont ou coût nul ; pas de tokens
  inventés pour résultat perdu. Quotas utilisateur/processus et historique
  ouverts. Sources seulement, services/releases actifs inchangés ; données
  actives/Dropbox/indexs réels non utilisés comme fixtures. Gains non mesurés,
  L0–L9 et automatisation toujours ouverts.


## L8 — Échéance coopérative unique et fermeture des flux Gemini

- Fiche MCP v90/board, mémoire, Git, journal/tests relus. RepoWise
  stream_parser.py dix jours/mock confronté au code actuel : pas de budget
  total du flux au-delà des timeouts HTTPX/backoffs par tentative.
- Wrapper stream_generator : échéance monotone unique <=120 s, chaque pull
  anext attend le temps restant via wait_for. Appels/attentes/backoffs/lecture
  inclus, aucun redémarrage de budget. Source possédée par aclosing, fermée
  avant erreur SSE provider_deadline à expiration, sans retry ou détails privés.
- Pas de contexte de timeout traversant yield : consommateur non annulé lors
  de send/pause, échéance revérifiée à la reprise. Annulation externe propagée,
  await amont annulé, aclose consommateur ferme la source après chunk.
- **146 tests réussis en 30,76 s**, Python3.13 documenté, racines LOCAL/DATA/
  PLATFORM temporaires avant imports. Six nouveaux scénarios : suspension
  avant/après données, backoff500, pause du consommateur dépassant budget
  sans annulation parasite, annulation externe et aclose après chunk ; amont
  fermé une fois, octets émis préservés, aucun compteur inventé. Contextes
  amont substitués ; régressions Router/SSE/admission/usage/OTLP/lifecycle
  incluses, aucun fournisseur réel. Warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-deadline-a5b3c5bb22a24d1785aa08c0d321ffb8/tests.txt,
  SHA-256 48eacb843c2373e4e64ce1f8a3ccde28745386ca790c3e9b685138eea4a2210c.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v91 et empreinte
  actualisés, contexte intégral 11994/12000 octets UTF-8, warnings vides.
  Diff stream/CI sans erreur.
- Contrôle coopératif aux pulls : send client bloqué, CPU/I/O synchrones et
  cleanup non préemptés ; pas de garantie de durée murale stricte ASGI.
  Amont doit respecter annulation/fermeture. Usage interrompu/coût non inventés.
  Taille réponse totale, authentification/quotas utilisateur/processus,
  statistiques JSON/historique et activation restent ouverts. Sources seules,
  services/releases actifs inchangés ; données actives/Dropbox/index réels
  non utilisés comme fixtures. Gains non mesurés, L0–L9 et automatisation ouverts.


## L8 — Plafond du volume des flux décodés

- Fiche MCP v91/board, mémoire, Git et journal/tests relus. RepoWise
  stream_parser.py dix jours/mock confronté au code : durée bornée mais
  absence de plafond de volume global. Modifications existantes conservées.
- Wrapper streaming compte les octets, plafond16 Mio par défaut, paramètre
  interne entier1..16 Mio. Morceau excédant le restant refusé entier, source
  fermée avant erreur SSE provider_response_too_large, aucun retry ni
  comptabilité du flux interrompu. Chunks précédents identiques, compteur
  sans accumulation de contenu ; statut HTTP déjà émis reste200.
- **154 tests réussis en 31,28 s**, Python3.13 documenté, LOCAL/DATA/PLATFORM
  temporaires avant imports. Huit nouveaux cas : limite exacte, dépassement
  après chunk/au premier chunk, fermeture unique/no retry/no tokens inventés,
  paramètres invalides avant amont. Capacité miniature en fixture pour tester
  la même branche sans allocation16 Mio ; transport substitué. Régressions
  délai/admission/SSE/usage/OTLP/lifecycle incluses ; aucun fournisseur réel,
  warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-volume-a91ef0be289f4e5c875217e1a3d92fa4/tests.txt,
  SHA-256 dfbae72ee648e7669549d81ee0ce6b6ba8f2e565d74aaa7eaa77e74ade285dea.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v92 et empreinte
  actualisés, lecteur intégral11984/12000 octets UTF-8, warnings vides.
  Diff stream/CI sans erreur.
- Borne sur bytes après décodage HTTPX, pas sur mémoire/volume compressé du
  transport : morceau déjà alloué avant refus possible. Événement SSE peut
  être interrompu entre chunks ; aucune garantie de réponse applicative
  complète, client doit traiter échec. Réponses non-streaming, mémoire
  transport/décompression, send/cleanup et CPU/I/O synchrones encore ouverts.
  Sources seules, services/releases actifs inchangés ; données actives/
  Dropbox/index réel non utilisés comme fixtures. Gains non mesurés, L0–L9
  et automatisation ouverts.


## L8 — Lecture bornée des réponses auxiliaires non-streaming

- Fiche MCP v92/board, mémoire, Git et journal/tests relus. RepoWise
  providers.py dix jours/mock confronté au code : client.post chargeait le
  corps complet avant contrôle. Modifications existantes conservées.
- Gemini/replis utilisent maintenant post_bounded : streaming HTTPX raw,
  Accept-Encoding identity, redirections désactivées, tampon <=16 Mio.
  Compression et longueur excessive refusées avant lecture ; dépassement
  refusé avant ajout, réponse fermée. Statuts non200 conservés avec leurs
  en-têtes mais sans lecture du corps. Refus terminal502 sans retry/repli
  ni détail privé ; annulation externe propagée.
- **162 tests réussis en 31,32 s**, Python3.13 documenté, LOCAL/DATA/PLATFORM
  temporaires avant imports. Huit nouveaux cas avec AsyncClient/MockTransport,
  AsyncByteStream et capacités miniatures : borne exacte/dépassement,
  longueur, compression, erreur, annulation et refus terminal Gemini/replis.
  Les anciens tests d'orchestration substituent explicitement ce lecteur.
  Régressions délai/admission/SSE/usage/OTLP/lifecycle incluses. Aucun
  fournisseur réel ; warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-upstream-body-48da6904e65b4340912c8336bb2d00fd/tests.txt,
  SHA-256 007d3f63f8cb8e45605006114ae9a394d06f092e4cdcd3ed65d71ab65617eef8.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v93 et empreinte
  actualisés. Lecteur local intégral11989/12000 octets UTF-8, warnings vides.
- Borne du tampon, pas du RSS : chunk transport déjà alloué, copie bytes
  finale et décodage JSON possibles. CPU/I/O synchrones, send/cleanup
  bloqués, métriques historiques et quotas utilisateurs/globaux ouverts.
  Sources seules, services/releases actifs inchangés ; données actives/
  Dropbox/index réel non utilisés comme fixtures. Gains non mesurés,
  critères L0–L9 et automatisation restent ouverts.


## L8 — Refus de compression du flux auxiliaire avant lecture

- Fiche MCP v93 et board explicite relus, Git/journal/tests/mémoire consultés.
  RepoWise index dix jours/mock sans correspondance exacte confronté au code :
  aiter_bytes décompressait avant la borne de volume. Changements préservés.
- Streaming demande Accept-Encoding identity, redirections désactivées ;
  encodage autre que identity sur réponse réussie refusé avant lecture.
  aiter_raw transmet les morceaux sans décompression HTTPX ; même plafond
  16 Mio. Refus terminal propagé sans retry, réponse fermée avant SSE
  provider_response_refused, aucun usage du flux refusé. HTTP déjà émis200.
- **167 tests réussis en 31,16 s** sur Python3.13 documenté, trois racines
  temporaires avant imports. Cinq nouveaux cas réel AsyncClient/MockTransport
  et AsyncByteStream : absent/identity, gzip/br/casse, en-tête demandé,
  fermeture unique, aucune lecture du corps refusé ni retry, chunks/usage
  de succès inchangés. Anciennes fixtures suivent le contrat raw.
  Régressions volume/délai/admission/usage/OTLP/lifecycle incluses, aucun
  fournisseur réel ; warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-encoding-6896643e308b45508fbb9b545505614c/tests.txt,
  SHA-256 63e207efcdfb972806dc78e7cb968a3cce96966904b5479dc39144b73ca7adcb.
- CI enrichie non exécutée à distance. Plan/protocole/fiche v94 et empreinte
  actualisés : lecteur11996/12000 octets UTF-8, warnings vides ; diff sans erreur.
- Pas de borne RSS transport : chunk déjà alloué possible. Send/cleanup
  bloqués, CPU/I/O synchrones, historique/quotas globaux/utilisateur et
  activation ouverts. Sources seules, services/releases inchangés ; données
  actives/Dropbox/index réels non utilisés comme fixtures. Gains non mesurés,
  critères L0–L9 et automatisation toujours ouverts.


## L8 — Équité de lecture hors streaming sur transport tamponné

- Fiche MCP v94/board, mémoire, Git, journal et tests relus. RepoWise dix
  jours/mock sans symbole exact confronté au lecteur local. Boucle raw
  pouvait consommer tout le tampon sans suspension, retardant autre travail
  et annulation. Modifications existantes préservées.
- post_bounded cède la boucle après64 morceaux ou64 Kio reçus, compteurs
  locaux remis à zéro, même capacité16 Mio et fermeture/erreurs.
- Quatre nouvelles recettes concurrentes AsyncClient/MockTransport sur128
  morceaux1 octet/64 Kio, avec/sans annulation : **quatre échecs avant
  correctif**, autre coroutine servie après128 lectures et annulation trop
  tardive ; après correctif progression avant fin, corps identique sur
  succès, CancelledError propagée et fermeture unique.
  Trace avant : C:/Users/Administrateur/AppData/Local/Temp/devcore-body-fairness-8fa2227075e74dadad39d8aa69cd6919/before.txt.
- **171 tests réussis en 31,70 s** sur Python3.13 documenté, trois racines
  temporaires avant imports ; régressions admission/délai/volume/usage/
  observation/OTLP incluses. Aucun fournisseur réel ; warning Starlette/httpx
  connu. Trace après :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-body-fairness-after-8d93cacb2ed6431191e2965122962ac3/tests.txt,
  SHA-256 b3d93ba3958d513364a8b7b52093e8e8407694c7f5e4d384fa9f02117428f462.
- Tests déjà inclus dans la commande CI ; CI distante non exécutée.
  Plan/protocole/fiche v95 et empreinte actualisés, lecteur intégral
 11996/12000 octets UTF-8, warnings vides.
- Équité coopérative, pas plafond temporel strict ni benchmark : chunk,
  copie finale, JSON et I/O synchrones, send/cleanup et mémoire transport
  encore ouverts. Services/releases actifs inchangés, données actives/
  Dropbox/index réels non utilisés comme fixtures. Gain non mesuré,
  critères L0–L9 et automatisation restent ouverts.


## L8 — JSON amont hors streaming contrôlé avant succès

- Fiche MCP v95/board, mémoire, Git et journal/tests relus. RepoWise dix
  jours/mock sans correspondance exacte confronté au code : JSON fournisseur
  directement décodé sous un try de statistiques, invalide/trop profond
  pouvant encore être transmis200. Changements existants préservés.
- Gemini/replis appellent decode_provider_json avant usage/succès : bytes
  <=16 Mio, UTF-8 valide, scan partagé coopératif64 K caractères, profondeur
  <=64 puis objet racine. Refus terminal502 sans retry/repli ni détails privés
  ou statistiques. Contenu accepté inchangé, usage absent reste unavailable.
- **184 tests réussis en 31,28 s**, Python3.13 documenté et trois racines
  temporaires avant imports. Treize nouveaux cas : Gemini/Cerebras,
  profondeur64/65, chaînes échappées, syntaxe/UTF-8 incorrects, racine tableau,
  absence de nouveau provider/statistiques après refus et annulation du scan
  volumineux. Frontière provider substituée ; lecteur/fermeture qualifiés
  séparément. Régressions Router/observation/OTLP incluses. Aucun fournisseur
  réel ; warning Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-provider-json-6ae6a0a8b5484ad3b9e3fabe5290fef5/tests.txt,
  SHA-256 98cb3c60a251740fc0ee835f561cc3ae7dc15c62754aa232e3ab21b144287cc5.
- CI enrichie non exécutée à distance. Plan/protocole/fiche v96 et empreinte
  actualisés, lecteur intégral11987/12000 octets UTF-8, warnings vides ;
  diff providers/CI sans erreur.
- Pas de validation intégrale du schéma fournisseur ni limite de nombre
  d'objets. UTF-8/parse/allocation et historique restent synchrones ; mémoire
  transport, send/cleanup, quotas utilisateurs/globaux et activation ouverts.
  Sources seules, services/releases actifs inchangés ; données actives/
  Dropbox/index réels non utilisés comme fixtures. Gains non mesurés,
  critères L0–L9 et automatisation toujours ouverts.


## L8 — Observation SSE coopérative et profondeur JSON

- Fiche MCP v96/board, mémoire, Git et journal/tests relus. RepoWise dix
  jours/mock sans symbole exact confronté au code : observation entière
  d'un chunk synchrone et événements JSON sans borne explicite de profondeur.
  Modifications existantes conservées.
- Router appelle feed_async, analyse par lots64 Kio avec suspension entre
  lots. Décodeur partagé JSON profondeur64, chaînes échappées respectées ;
  événement invalide/trop profond désactive/vide l'observation. Annulation
  désactive/vide et propage CancelledError ; flux transmis inchangé, aucun
  usage inventé ni retry introduit. Bornes lignes/événements64 Kio conservées.
- **189 tests réussis en 31,97 s** sur Python3.13 documenté, trois racines
  temporaires avant imports. Cinq nouveaux cas : profondeur64/65, chaînes
  échappées, progression concurrente pendant gros chunk de commentaires,
  annulation et absence de réactivation/comptabilité. Régressions flux/
  délai/volume/admission/usage/OTLP incluses. Aucun fournisseur réel ; warning
  Starlette/httpx connu. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-cooperative-6833c63e62594b719a1baa4c7382a751/tests.txt,
  SHA-256 81a1276bc5aff2a906ce13f2c7a3e3e996e0f23f3900deb1890b2d067bae660f.
- Tests déjà dans la commande CI ; CI distante non exécutée. Plan/protocole/
  fiche v97 et empreinte actualisés, lecteur11994/12000 octets UTF-8, warnings
  vides ; diff stream sans erreur.
- Feed synchrone disponible pour appels locaux ; un lot et son parse restent
  synchrones. Pas de borne murale stricte ni RSS transport : CPU/I/O, send/
  cleanup, historique/quotas utilisateur/globaux et activation ouverts.
  Sources seules, services/releases actifs inchangés ; données actives/
  Dropbox/index réels non utilisés comme fixtures. Gains non mesurés,
  critères L0–L9 et automatisation toujours ouverts.


## L8 — Longueurs amont et erreurs de framing

- Fiche MCP v97/board, mémoire, Git et journal/tests relus. RepoWise dix
  jours/mock sans correspondance exacte confronté au code : conversion
  directe de Content-Length potentiellement démesuré, absence de concordance
  explicite finale ; changements existants conservés.
- Validation partagée des en-têtes SSE/non-streaming : longueur ASCII
  non négative unique, normalisation zéros, comparaison lexicale avant petit
  entier ; absence acceptée sous plafond cumulatif. Valeur invalide ou
  supérieure à capacité refusée avant lecture. Morceau dépassant longueur
  déclarée refusé entier, concordance à EOF avant comptabilité/succès.
  RemoteProtocolError HTTPX devient refus terminal, pas de retry/repli.
  SSE ferme avant erreur publique ; chunks précédents peuvent déjà être
  transmis, HTTP200 déjà émis.
- **209 tests réussis en 31,40 s**, Python3.13 documenté, trois racines
  temporaires avant imports. Vingt nouveaux cas AsyncClient/MockTransport
  sur les deux lecteurs : exact/zéros5000/absent, énorme5000/vide/liste/négatif,
  corps inférieur/supérieur à déclaration, erreur protocole après chunk.
  Fermeture unique, succès identique, absence de retry/usage après refus.
  Régressions Router/observation/OTLP incluses, aucun fournisseur réel ;
  warning Starlette/httpx connu. Trace finale
  C:/Users/Administrateur/AppData/Local/Temp/devcore-response-framing-766c9f088f6b435da08fa294fec897d2/tests.txt,
  SHA-256 ee3d14cc839b822088c1d04b668806a3460752ff411e476a0375696aa1fccd07.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v98 et empreinte
  actualisés. Lecteur11994/12000 octets UTF-8, warnings vides ; diff stream/
  CI sans erreur. Premier passage207 tests avant ajout traduction des erreurs
  protocole, puis suite relancée pour les deux cas supplémentaires.
- Pas de preuve d'intégrité sémantique sans longueur déclarée sur JSON
  non-streaming valide ; transport distant non qualifié. En-têtes/chunks
  déjà alloués possibles, CPU/I/O synchrones, send/cleanup, historique/quotas
  utilisateur/globaux et activation ouverts. Sources seules, services/
  releases actifs inchangés ; données actives/Dropbox/index réels non utilisés
  comme fixtures. Gains non mesurés, critères L0–L9/automatisation ouverts.


## L8 — Statistiques JSON héritées bornées et atomiques

- Fiche MCP v98/board, mémoire, Git et journal/tests relus. RepoWise dix
  jours/mock confronté au code, ancien chemin headroom_stats obsolète :
  gemini_auxiliary_stats écrit directement et cinq retries/sleep bloquants
  englobaient aussi l'alerte après commit. Changements préservés.
- stats_store : lecture/snapshot <=1 Mio, <=4096 tâches, identifiants/modes
  bornés, compteurs63 bits/totaux cohérents. Fichier invalide préservé.
  Verrou intra-processus sans attente ; temporaire même dossier flush/fsync
  puis replace atomique, nettoyage sur échec normal. record_tokens retourne
  False/diagnostic fixe sur refus, sans retry ; alerte post-commit séparée
  ne répète pas le comptage. has_budget_alert utilise la lecture bornée.
- **217 tests réussis en 33,59 s**, Python3.13 documenté, trois racines
  temporaires avant imports. Huit nouveaux cas : alerte post-commit échouée,
  replace refusé/ancien fichier et cleanup, invalidité/volume/cohérence,
  écrivain concurrent refusé sans attendre/lecteur voyant ancien snapshot,
  capacité tâches et overflow. Régressions Router/observation/OTLP incluses ;
  aucun fournisseur réel. Warning Starlette/httpx connu. Premier passage :
  deux erreurs de setup Windows (PYTEST_CURRENT_TEST >32767 caractères à
  cause d'un identifiant de paramètre1 Mio) ; IDs courts ajoutés puis suite
  complète relancée. Trace finale
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stats-atomic-final-84af6420afdc4a81b96910f1b60ec1cb/tests.txt,
  SHA-256 25cf4691222d0bb81ad0d725113cdcb74800ea4333ee21d661ecc2870ecd3309.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v99 et empreinte
  actualisés, lecteur11994/12000 octets UTF-8, warnings vides ; diff sans erreur.
- Historique de compatibilité : refus peut perdre un événement, diagnostic
  fixe mais aucune queue/reprise/déduplication durable. Verrou ne protège pas
  plusieurs processus ; I/O/fsync/JSON restent synchrones. Attribution
  active_project globale, ACL, mémoire transport, send/cleanup et quotas
  utilisateur/globaux ouverts. Sources seules, services/releases inchangés ;
  données actives/Dropbox/index réels non utilisés comme fixtures. Gains
  non mesurés, critères L0–L9/automatisation toujours ouverts.


## L8 — Verrou interprocessus des statistiques

- Fiche MCP v99/board, mémoire, Git et journal/tests relus. RepoWise dix
  jours/mock sans symbole exact confronté au magasin local. Verrou thread
  ne protégeait pas deux processus ; modifications préservées.
- Verrou système sans attente sur fichier latéral stable stats.json.lock
  avant lecture et jusqu'après publication atomique. Windows msvcrt.LK_NBLCK
  premier octet ; POSIX flock prévu non qualifié. Lockfile conservé, jamais
  suppression ni verrou sur le snapshot remplacé. Écrivains coopérants
  concurrents refusés ; OS libère à sortie/mort du détenteur.
- **219 tests réussis en 32,31 s**, Python3.13 documenté, trois racines
  temporaires avant imports. Deux nouveaux cas avec sous-processus Python
  réel : blocage d'un second écrivain/ancien snapshot préservé, sortie normale
  ou kill du seul helper fixture, reprise avec total/calls exacts et fichier
  latéral conservé. Régressions Router/OTLP incluses, warning Starlette/httpx
  connu ; aucun fournisseur réel. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stats-process-lock-6c955b356ccc4a94a3ba1c128c963cdb/tests.txt,
  SHA-256 59bda52bba31135f1abf6946166b25e12b69575f1e6083494389e8012cd2bbe1.
  Cleanup de la fixture durci pour ne pas attendre readline après timeout ;
  dix tests magasin relancés réussis en2,90 s, trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-stats-lock-cleanup-8f4c4fac533b46999c71518bbd5a43e4/tests.txt,
  SHA-256 b6b0b9400c6246625dd11309e6cbf635ff00f7d9a3fb485ff0c1d277a6ed9841.
- Tests déjà dans CI, distante non exécutée. Plan/protocole/fiche v100
  et empreinte actualisés : lecteur11995/12000 octets UTF-8, warnings vides.
- Événement refusé peut être perdu, aucune reprise durable/déduplication ;
  writers anciens/non coopérants, suppression externe du lockfile, réseau
  et POSIX non qualifiés. I/O/fsync synchrones, attribution globale/ACL/quotas
  encore ouverts. Sources seules, services/releases actifs inchangés ; données
  actives/Dropbox/index réels non utilisés comme fixtures. Gains non mesurés,
  critères L0–L9/automatisation ouverts.


## L1/L8 — Retrait du contexte actif global des routes auxiliaires

- Fiche MCP v100/board, mémoire, Git et journal/tests relus. RepoWise dix
  jours/mock confronté au code : bootstrap global sur chat/embedding, tâche
  globale pour statistiques/en-tête/alerte. Modifications préservées.
- Routes chat/stream/embeddings sans bootstrap protocole : aucune lecture
  globale, rappel injecté, session éphémère ni violation journalisée. Gemini/
  replis utilisent un bucket unattributed.<catégorie> issu de l'alias, jamais
  une tâche active partagée ; streaming reçoit sa catégorie de la route.
  En-tête X-DevCore-Attribution=unattributed, ancien X-DevCore-Task non-stream
  contient le bucket. Ancien snapshot préservé ; attribution authentifiée
  projet/utilisateur non inventée. Factory OTLP explicite inchangé.
- **278 tests réussis en 49,79 s**, Python3.13 documenté, trois racines
  temporaires avant imports. Quatre nouvelles recettes ASGI avec deux
  contenus alpha/beta : chat/stream/embedding/Cerebras, hooks globaux
  refusant tout appel, entrées upstream exactes, catégorie/statistiques et
  en-tête non attribué. Régressions usage/transport/OTLP et55 cas séparation
  ajoutés à la recette. Warning Starlette/httpx connu. Trace finale
  C:/Users/Administrateur/AppData/Local/Temp/devcore-router-isolation-qualified-51db072e0b6846b7a3283ddec826b979/tests.txt,
  SHA-256 8616871d2820e0df2782e5c55de7574d83aeb71f0a48e15d2284e4af2d6d3e45.
- Deux fixtures corrigées avant relance : signature du faux générateur SSE
  avec catégorie explicite ; ancienne fixture séparation patchait client.post
  plutôt que post_bounded, appel Cerebras accidentel avec clé fictive refusé401.
  Aucun secret réel utilisé ; dernier passage amont substitué/OTLP loopback.
- CI enrichie non exécutée à distance ; plan/protocole/fiche v101 et empreinte
  actualisés : lecteur11990/12000 octets UTF-8, warnings vides, diff sans erreur.
- Fonctions historiques de protocole restent exportées pour compatibilité,
  appels directs hors chemin HTTP non qualifiés. Statistiques agrégées par
  catégorie, aucune facturation/ACL utilisateur, événements refusés sans
  reprise durable, I/O synchrones et quotas utilisateur/globaux ouverts.
  Sources seules, services/releases actifs inchangés ; données actives/
  Dropbox/index réels non utilisés comme fixtures. Gains non mesurés,
  critères L0–L9/automatisation ouverts.


## L7 — Recherche mémoire sans vecteur artificiel

- Fiche MCP v101/board, mémoire, Git et journal/tests relus ; sections L7/L8
  ciblées. RepoWise dix jours/mock confirmé au code : Cockpit vector nul384
  face au contrat768, résultats potentiellement trompeurs. Changements
  existants préservés.
- EmbeddingService.embed_query appelle Router direct, modèle/dimensions768,
  version de contrat déclarée ; réponse raw128 Kio, identity, fermeture
  succès/refus/annulation. Vecteur fini/non booléen, norme finie/non nulle,
  cardinalité/modèle contrôlés. Cockpit réalise un seul embedding puis
  recherches parallèles, plus aucun vecteur nul384. Arguments bornés avant
  amont, collections autorisées, hits/corps Qdrant bornés et deadline globale
  coopérative5 s. API search_mode/degraded/raison et metadata explicites.
  Embedding invalide/indisponible : zéro Qdrant/hits, mode unavailable ;
  pas de repli lexical inventé. Profil individuel reste fermé à cette
  recherche globale, autres contextes/droits inchangés.
- **102 tests réussis en175,00 s** sur Python3.13 documenté avec overlay
  Argon2 existant E:/DevCoreRuntime/recipes/devcore-auth-py313-20261003/packages
  (runtime figé non modifié), trois racines temporaires avant imports.
  Dix-neuf nouveaux cas HTTPX MockTransport/ByteStream :768 partagé, vecteur
  nul/dimension/bool/NaN/inf, modèle/cardinalité/offline, arguments avant
  réseau, cancellation/fermeture, volume/compression/UTF-8, erreur backend
  privée non exposée. Contrat moteur, API Cockpit, ACL individuelles et
  contexte enregistré inclus. Warning Starlette/httpx connu. Trace finale
  C:/Users/Administrateur/AppData/Local/Temp/devcore-memory-embedding-qualified-c71e9b07800f4914a12002d75d7ba88a/tests.txt,
  SHA-256 d6dc1ca0a52a773b7bc4b066e2b3cc92b3e60911b780f3dcf374dd681ff18b60.
- Échecs intermédiaires résolus : fixture JSON HTTPX déjà consommée remplacée
  par ByteStream ; test démarrage ancien patch uvicorn.run inefficace,
  serveur fixture démarré sur20129 et pytest créé arrêté explicitement par
  PID/commande vérifiés (seuls19044/17468), sans toucher services actifs.
  Test corrige désormais service_runtime.run_managed. Argon2 absent du runtime
  nu, overlay déjà documenté retrouvé et utilisé sans installation.
- CI enrichie non exécutée à distance ; plan/fiche v102/manifeste et protocole
  recherche-memoire-2026-10-04.md actualisés, diff sans erreur. Première fiche
  dépassait12000 octets : historique L8 condensé sans changer les décisions ;
  lecteur final intégral11963/12000 octets UTF-8, warnings vides.
- Fournisseur authentifié, données/collections/dimensions stockées, provenance
  d'index, corpus20 questions, lexical/RRF/ACL mémoire globale et frontend
  dédié restent ouverts. Coût d'un nouvel embedding par query non mesuré,
  aucun gain de tokens annoncé. Parse/I/O/RSS et durée murale stricte non
  qualifiés. Sources seules, services/releases actifs inchangés ; données
  actives/Dropbox/index réels non utilisés comme fixtures. L0–L9 et
  automatisation restent ouverts.

## L7 — Contrat du simulateur vectoriel local (fiche v103)

- Reprise fiche v102 et board devcore, Git288 entrées préservées, journal et
  tests concernés lus avant modifications. RepoWise QdrantStore retrouvé ;
  index10 jours/mock sans recherche sémantique, confronté au code actuel.
- qdrant_server.py refusait silencieusement les dimensions invalides via
  score0 et sauvegardait même lors de l'import ; GET créait des collections.
  Validation query/batch (dimension, bool, NaN/inf, norme), ancien vecteur
  invalide503, aucun faux hit ; Cosine normalisé, reconfiguration non vide
  refusée. Collections inconnues404, lectures sans écriture. JSON corrompu
  conservé et mutations fermées ; publication mémoire après remplacement
  atomique du fichier seulement, RLock dans le même processus. Diagnostic
  HTTP fixe sans détail privé ; serveur identifié comme simulateur.
- Scroll sans vecteur, pagination incomplète explicitement refusée et options
  de filtre ignorées auparavant désormais refusées. Aucun droit projet
  implémenté ni compatibilité complète avec Qdrant revendiquée.
- 38 tests réussis en4,87 s sur Python3.13 documenté, overlay Argon2 existant,
  trois racines temporaires avant imports. Quatorze cas simulateur : invalides,
  batch tout-ou-rien, classement/extremes, ancien vecteur, corruption, échec
  replace sans perte/temporaire,16 écrivains concurrents, refus troncature,
  HTTP loopback éphémère et lecture sans mutation. Dix-neuf cas pipeline et
  cinq cas embedding inclus. Aucun appel fournisseur ni index/donnée active.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-qdrant-qualified-a6da59c428154fe2a9bf52939b02c6f0/tests.txt ;
  SHA-256 27cdb4f69b55d2fa8de2409e09e85642a987a698a4cf943dbcc9de8a52b367ef.
- CI enrichie non exécutée à distance, plan/contrat/fiche v103/manifeste
  actualisés. Sources seules, releases/services actifs inchangés. Verrou
  bloquant dans un processus, absence de coordination entre processus,
  charge/JSON/calcul/copie/I/O synchrones non bornés en RSS et lecture HTTP
  sans deadline globale : simulateur non qualifié pour la cible professionnelle.
  Vrai Qdrant, modèle/provenance des données stockées, ACL projet/principal,
  lexical/RRF/corpus réel et activation restent ouverts ; L0–L9 et
  automatisation restent ouverts. Aucun gain réel de tokens annoncé.
  Lecteur de contexte v103 vérifié :11984/12000 octets UTF-8, warnings vides,
  décisions obligatoires conservées ; diff des fichiers concernés sans erreur.

## L7 — Contrôle des résultats mémoire Cockpit (fiche v104)

- Reprise MCP fiche v10311984/12000 sans warnings, board devcore384/389
  (ne prouve pas les lots L0–L9), Git290 entrées et journal/tests lus.
  RepoWise retrouve search_qdrant_collection_async mais signature/index vieux
  de10 jours/mock : contrôle direct du code, aucune fraîcheur supposée.
- Le Cockpit acceptait des hits dict arbitraires, scores NaN et identifiants
  absents. Nouveau services/memory_results.py : JSON clés uniques, profondeur64
  avec scan coopératif ; statut/result/id/score Cosine/ordre/payload validés,
  doublons refusés, payload64 Kio/hit et4096 nœuds/collection. Projection
  id/score/payload uniquement. Une collection invalide dégradée sans exposer
  le contenu amont ni perdre les autres valides ; cancellation propagée.
- 60 tests réussis en5,65 s, Python3.13 documenté + overlay Argon2 existant,
  trois racines temporaires avant imports.22 nouveaux cas :20 refus amont
  (id, score, bool, NaN/inf, profondeur, Unicode, doublons, ordre et volumes),
  projection correcte et scan annulable ; seconde collection valide et
  fermeture HTTP vérifiées. Suite simulateur et embedding moteur incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-memory-hits-5227577456344b8b9a708cc1c704ca72/tests.txt ;
  SHA-256 31e50d4544ff4a04fcd36296d5daa1b1581ae1b8c6bb17a871a5dba93d6a8ec1.
- Tests déjà inclus dans le workflow via fichier existant, CI distante non
  exécutée. Plan/contrat/fiche v104/manifeste mis à jour. Données actives,
  Dropbox et index réels non utilisés ; amonts substitués sans coût fournisseur.
  Sources non activées. Parse/UTF-8/serialization synchrones et RSS/durée
  stricte non qualifiés ; pas d'ACL/provenance/sémantique induite par cette
  validation de transport. Profil individuel reste fermé à mémoire globale.
  Vrai fournisseur/Qdrant, lexical/RRF/corpus réel et gains restent ouverts ;
  automatisation et lots L0–L9 non terminés.
- Vérification finale : fiche v10411965/12000 octets UTF-8, warnings vides,
  décisions obligatoires conservées ; diff ciblé sans erreur.

## L1/L6 — Création et sélection atomiques avec événement local (v105)

- Fiche v104 et journal/tests/Git lus avant modification ; services/tasks.py
  déjà modifié préservé. RepoWise add_task : index10 jours/mock, signature
  obsolète confrontée au code. Allocation/sélection BEGIN IMMEDIATE déjà
  présentes ; défaut confirmé : publish après commit pouvait échouer alors
  que la tâche/import/activation était déjà persistée.
- EventBus.append_in_transaction exige une transaction active et n'effectue
  aucun commit ; méthode publish historique conserve sa sémantique. TaskAdded
  et TaskNext insérés dans la transaction de création/sélection, avant commit.
  Erreur d'insertion déclenche rollback métier et événement ; import rejoué
  et tâche déjà active ne génèrent pas de nouvel événement.
- 17 tests réussis en31,02 s sur Python3.13 documenté, trois racines temporaires
  avant imports, overlay Argon2 existant. Quatre nouveaux cas : déclencheur
  SQLite refusant événement sur création/sélection (tâche/import/projet/version
  conservés ou annulés), append sans transaction refusé/visibilité après commit
  et rollback, quatre connexions concurrentes/deux projets (une activation et
  un événement par projet). Isolation existante et EventBus historique inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-task-events-511d949c0b0f49ccba5f69aedc0d578c/tests.txt ;
  SHA-256 04cb56a69f517d514a97a9b1ac0a704ab62a37b19a8f1f4979163b02d0dcaff2.
- Plan/fiche v105/manifeste et CI ciblée enrichis. Aucune migration active,
  release ou service modifié ; aucune donnée active/Dropbox en fixture.
  Bus SQLite local uniquement : pas d'outbox distribuée, publication externe,
  consommation idempotente ou restauration de projections qualifiées. Autres
  mutations restent à rendre atomiques avec événement. Connexions SQLite
  synchrones/attente verrou30 s, ACL et allocation historique/PostgreSQL restent
  ouverts ; test concurrent sur threads à connexions distinctes, pas recette
  multi-processus ni mesure de charge. CI distante non exécutée. L1/L6 et
  ensemble L0–L9 non clos ; automatisation reste active.

## L1/L6 — Événements atomiques des autres mutations TaskService (v106)

- Reprise Git/journal v105 et tests d'atomicité/audit avant modification.
  Appel contexte MCP initial indisponible (outil non chargé), lecteur local
  v10511981/12000 utilisé ; board MCP accessible après découverte384/389.
  RepoWise non exposé dans ce passage, analyse directe des sources.
- Sept publish post-commit confirmés : clôture, suppression, étape, édition,
  pause, skip et reprise. Déplacés via append_in_transaction avant commit,
  après audit de clôture/suppression. L'échec événement annule état/version/
  audit ; résultat de clôture capturé dans la transaction. Pause/skip/reprise
  sans transition ne publient rien. Création/sélection v105 préservées.
- 33 tests réussis en60,89 s sur Python3.13 documenté avec overlay Argon2
  existant, trois racines temporaires avant imports. Dix nouveaux cas : sept
  mutations avec trigger de refus d'événement (rollback état/version/audit,
  aucun événement orphelin, second projet inchangé, nouvelle tentative valide)
  et trois changements d'état sans effet ni événement. Quatre tests v105,
  isolation, audit auteur/conflit et EventBus historique inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-task-mutations-22fc3ba3b70948299d4ddebfa083b68a/tests.txt ;
  SHA-256 9af0e3c9dfdcd1c90113c85532dd602947e7fb8188cdb396bd7d91e82a24ee34.
- Plan/fiche v106/manifeste mis à jour ; fichier de tests déjà inclus dans
  CI, exécution distante non effectuée. Sources seules, releases/services et
  données actives/Dropbox inchangés. Scope neuf méthodes TaskService, pas
  anciens adaptateurs ni outbox externe/projections/consommateurs. Auteur
  authentifié toujours seulement sur canaux déjà qualifiés ; événement
  métier ne remplace pas l'audit. Sélection implicite de complete/step reste
  une transaction préalable distincte, reprise/idempotence workflow globale
  non qualifiée. Attente SQLite synchrone30 s, crash/charge/ACL/PostgreSQL
  ouverts ; aucun lot L0–L9 clos, automatisation reste active.
- Contrôle final : contexte v10611980/12000 octets UTF-8, warnings vides,
  décisions obligatoires conservées ; diff ciblé sans erreur.

## L1 — Avance directe sans seconde tâche active (v107)

- Git, journal v106, contexte local borné et tests concernés lus avant édition.
  Board MCP devcore répond384/389 ; RepoWise non disponible dans ce passage,
  contrôle direct des sources. Préparation SQL de next/resume déjà sérialisée,
  mais step_task pouvait activer une autre tâche du même projet sans contrôle.
- Si une étape laisse la tâche in_progress, vérification d’une autre tâche
  active dans BEGIN IMMEDIATE avant UPDATE/événement. Conflit ValueError,
  rollback sans changement/version/événement. Avance de la tâche courante et
  d’un autre projet conservée. step_number exige entier strict positif, rejet
  avant next_task implicite (bool/float/str auparavant mal gérés).
- 45 tests réussis en92,10 s sur Python3.13 documenté et overlay Argon2 existant,
  trois racines temporaires avant imports. Sept nouveaux cas : conflit direct,
  cinq numéros invalides sans activation implicite, deux connexions concurrentes
  avançant des tâches différentes (un gagnant/une activation/un événement).
  Suites atomicité/isolation/versions/CLI et vrai PowerShell/moteur incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-task-step-isolation-179153b7d7cb49de86cce6b06926fda7/tests.txt ;
  SHA-256 d63e54e05d3657b42baadf6a9d35d6db400d2fa5c570938610ba4c1c351cb5c2.
- Plan/fiche v107/manifeste actualisés, test existant déjà dans CI distante
  non exécutée. Sources non activées ; aucune donnée active/Dropbox/service
  utilisé en fixture ou modifié. Contrôle TaskService, pas contrainte SQL
  globale : anciens écrivains/direct SQL et données déjà multi-actives non
  réconciliés. Transitions terminales/pause et sélection implicite préalable
  restent à qualifier, aucun moteur de workflow durable créé. Concurrence
  threads/connexions, pas charge multiprocessus ; attente SQLite30 s synchrone.
  L1 et lots L0–L9 ouverts ; automatisation active.
- Contexte final v107 :11962/12000 octets UTF-8, warnings vides, décisions obligatoires conservées.

## L1 — Respect de la pause et répétition d'étape sans effet (v108)

- Git/journal v107 et tests pertinents lus avant modification ; lecteur local
  v10711962/12000 et décisions en vigueur, board MCP384/389. RepoWise non
  exposé, analyse directe du service/tests. step_task réactivait paused/skipped
  et publiait événement/version pour étapes déjà réalisées ou tâche done.
- Après contrôle de version, tâche done retournée intacte ; autres statuts
  que todo/in_progress refusés avant écriture. Étape explicite inférieure ou
  égale au compteur retournée intacte. Incrément sans numéro continue d'avancer
  une tâche admissible ; pas d'idempotence de requête inventée pour l'incrément.
  Pause doit passer par resume_task, skipped n'est pas implicitement rouvert.
- 52 tests réussis en107,68 s sur Python3.13 documenté avec overlay Argon2
  existant, trois racines temporaires avant imports. Sept nouveaux cas :
  pause/skip x étape implicite/terminale (aucune mutation, reprise pause valide),
  répétition active/done sans effet et version périmée toujours refusée,
  deux connexions appliquant la même dernière étape (un événement/version).
  Suites atomicité/isolation/versions/CLI/PowerShell et moteur incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-task-step-transitions-ac435404b72b4d27a78e2d5c76d836fe/tests.txt ;
  SHA-256 2ae9752270cd82c3c8c25b7a01fb250292e37d3fc84a0d48fde9e76c6f8ff1b5.
- Plan/fiche v108/manifeste actualisés ; tests déjà dans CI non exécutée
  à distance. Sources non activées, données actives/Dropbox/services inchangés.
  Aucun traitement des autres transitions, de données historiques invalides
  ou de mutations SQL directes. Sélection implicite préalable distincte,
  quotas/workflow durable/ACL/PostgreSQL ouverts ; contrôle au service,
  pas contrainte globale. L1/L0–L9 et automatisation restent ouverts.
- Contexte final v108 :11973/12000 octets UTF-8, warnings vides ; décisions obligatoires conservées.

## L1/L6 — Sélection implicite dans le commit de mutation (v109)

- Git/journal v108/tests relus avant modification, contexte local borné
  v10811973/12000 et décisions en vigueur ; board MCP384/389. RepoWise
  absent dans ce passage, code local utilisé. Défaut confirmé : complete/step
  sans identifiant validaient next_task dans une transaction préalable,
  laissant une activation/TaskNext persistés après refus de la mutation.
- Sélection extraite dans un helper exigeant la transaction du caller,
  sans commit ; next_task public conserve sa transaction. complete/step
  implicites choisissent désormais sous leur BEGIN IMMEDIATE : TaskNext,
  mutation, événement et audit disponible sont validés ensemble. Aucune
  tâche admissible : transaction fermée, aucune mutation. Clôture explicite
  d'une tâche done renvoie l'état intact après contrôle de version, sans
  nouvel audit/événement/version ni modification de completed_at.
- 63 tests réussis en120,04 s sur Python3.13 documenté et overlay Argon2
  existant, trois racines temporaires avant imports. Sept nouveaux cas :
  complete/step x tâche todo/déjà active, trigger autorisant TaskNext mais
  refusant l'événement final (tout rollback, audit nul), nouvelle tentative
  valide ; replay de clôture avec autre auteur et version périmée ; deux
  opérations sans tâche admissible. Atomicité/isolation/versions/auteur et
  moteur existants inclus. Aucun fournisseur ou donnée active en fixture.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-task-implicit-transaction-f0cab8982c404adf88983d778d167f64/tests.txt ;
  SHA-256 b9bfab6884862082269893b812100526c1ae9f59a16be07e551eb38f5ec085d4.
- Plan/fiche v109/manifeste mis à jour, tests déjà dans CI distante non
  exécutée. Sources seules, releases/services/Dropbox inchangés. Contrôle
  TaskService SQLite, pas anciens adaptateurs ni outbox externe/ACL globale.
  Appels implicites ne sont pas idempotents : répéter sans identifiant peut
  sélectionner une autre tâche après clôture ; aucun retry automatique
  ajouté. Transitions restantes, données historiques, attente SQLite30 s,
  crash/charge/quotas et PostgreSQL ouverts. L0–L9 non clos, automatisation
  maintenue active ; aucun gain de tokens annoncé.
- Contexte v109 vérifié :11967/12000 octets UTF-8, warnings vides, décisions obligatoires conservées.

## L1 — Dépendance locale obligatoire pour l'avance directe (v110)

- Git/journal v109/tests concernés relus avant édition ; contexte local
  v10911967/12000 sans warnings, board MCP384/389. RepoWise absent dans
  ce passage, confrontation au code/tests. next_task respectait depends_on
  mais step_task direct pouvait avancer/terminer une tâche bloquée.
- Avant modification effective d'une étape, dans BEGIN IMMEDIATE, dependency
  relue par paire projet/id et exigée done. Manquante, pending, supprimée ou
  seulement étrangère refusée avec diagnostic fixe, rollback sans état/
  version/événement. No-op déjà qualifié conservé ; aucune recherche globale.
- 66 tests réussis en134,67 s sur Python3.13 documenté + overlay Argon2
  existant, trois racines temporaires avant imports. Neuf nouveaux cas :
  quatre états de dépendance x incrément/dernière étape, refus sans fuite de
  titre étranger et sans effet ; dépendance clôturée dans le projet autorise
  ensuite l'avance avec version attendue inchangée par le refus. Atomicité,
  isolation, versions et moteur existants inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-task-dependencies-b98c817af958456c81461acf5f0dc4be/tests.txt ;
  SHA-256 614049c4abf99db0396649f763e5a80f2e01ec62519f6663cad0b54223202d11.
- Plan/fiche v110/manifeste actualisés, test déjà dans CI distante non
  exécutée. Sources non activées ; services, releases et données actives/
  Dropbox inchangés. Scope avance TaskService : clôture explicite, reprise,
  édition de dépendances et anciens écrivains restent à qualifier ; cycles/
  références historiques non réconciliés. Pas contrainte SQL globale, ACL
  ou moteur durable ajouté. Attente SQLite30 s synchrone, crash/charge/
  PostgreSQL ouverts ; L0–L9 non terminés, automatisation active.
- Contexte v110 vérifié :11960/12000 octets UTF-8, warnings vides ; décisions obligatoires conservées.
