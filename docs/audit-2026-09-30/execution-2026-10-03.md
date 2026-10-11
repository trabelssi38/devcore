# Journal d'exécution — 3 octobre 2026

Suite du [journal du 2 octobre](execution-2026-10-02.md).
Les lots L0 à L9 restent soumis à leurs critères de sortie.

## L7 — réparer la configuration Codex du dépôt

- Git, plan, journal et configuration relus avant modification. La configuration
  `.codex/config.toml` pointait RepoWise vers `C:/devcore` et un exécutable absent.
  DevCore n'était pas configuré. Le catalogue de cette conversation ne contient
  pas encore les outils DevCore/RepoWise.
- Référence avant édition : `MCP/devcore-scripts/test_stdio_protocol.py`,
  **1 test réussi en 12,24 s**, sur racines locales/partagées temporaires.
- Ajout de `Scripts/configure_codex_mcp.py` : prévisualisation par défaut,
  remplacement des seules tables DevCore/RepoWise, contrôle sémantique des autres
  paramètres, refus d'un original modifié, sauvegarde et remplacement du fichier.
  Aucun réglage global Codex ni autre client n'a été changé.
- Configuration appliquée sur ce dépôt : DevCore avec Python 3.13 de recette,
  RepoWise avec Python 3.14 installé et lanceur local. Original sauvegardé dans
  `.codex/config.toml.backup-bd4810d4-c3bb-40e7-aafa-b4b13d8d743e`.
  Empreinte du contenu prévu :
  `deecfae290fe629717e2b2374ebf0f324df5dfe948541b2a97f0940d557d6424`.
- DevCore : profil de consultation limité à `devcore_task_status` et
  `devcore_check`, projet explicite `devcore` obligatoire. Le serveur refuse
  les mutations et les autres projets avant les hooks. Les hooks peuvent
  toujours écrire des journaux locaux ; ce profil ne constitue pas une ACL
  multiutilisateur. La connexion SQL a ensuite été durcie comme indiqué ci-dessous.
- RepoWise : `--no-workspace`, cinq outils de consultation, embedder mock et
  télémétrie désactivée. Le lanceur bloque les sockets Python externes avant
  import ; ce contrôle ne couvre pas tous les appels natifs ou sous-processus.
  Aucun index réel n'a été rafraîchi ou employé comme fixture. La pertinence de
  recherche avec mock et la fraîcheur des sources restent à qualifier.
- Après édition : `tests/test_configure_codex_mcp.py` et
  `MCP/devcore-scripts/test_stdio_protocol.py`, **5 tests réussis en 9,84 s**.
  Ils couvrent conservation des réglages, sauvegarde exacte, conflit d'édition,
  sockets locales/externes et handshake MCP réel sur base jetable avec refus
  de mutation/projet croisé. Les données actives et Dropbox ne sont pas utilisés
  par ces tests.
- Vérification en lecture seule : `codex mcp list --json` reconnaît les deux
  serveurs activés, les interpréteurs, les scripts et le cwd du dépôt.
  `codex mcp get devcore --json` confirme les deux outils autorisés.
  Cette lecture de configuration ne confirme pas le démarrage RepoWise ni des
  appels depuis une nouvelle conversation. Aucun service actif redémarré.
- Contrôle complémentaire du code : `TaskService()` appelait `connect_db()`,
  qui exécute des créations de schéma même pour une consultation. Le profil
  ouvre désormais explicitement le fichier existant avec SQLite `mode=ro`
  et `query_only`, sans initialisation. Il refuse une racine implicite ou
  relative et l'absence de base. Les journaux locaux des hooks restent actifs.
- Suite finale après ce correctif : **6 tests réussis en 10,01 s**. Une base
  temporaire au schéma minimal reste strictement au même schéma après les deux
  consultations ; une base absente n'est pas créée. Le test du profil complet
  conserve les mutations attendues sur fixture. `git diff --check` ciblé ne
  signale aucune erreur d'espacement (avertissements LF/CRLF seulement).

## L7 — premières sources de reprise versionnées

- Ajout de `docs/project-context/devcore.md` et `decisions.md` : objectif,
  vocabulaire, actuel/cible, contraintes, état, prochaine action et décisions
  en vigueur/proposée/remplacée avec sources. La date initiale du choix cloud
  n'est pas inventée ; la date précise de la priorité tokens reste à confirmer.
- Ajout d'un `AGENTS.md` racine court qui demande de lire ces deux documents
  au démarrage et d'approfondir les sources pertinentes à la demande. Les
  modèles, données actives et processus n'ont pas été changés par ces documents.
- Limites : cette première fiche est spécifique au dépôt DevCore. Le service
  de fiches par projet avec droits, fraîcheur, budget de tokens mesuré et
  chargement dans les autres clients reste à construire. La bonne compréhension
  du projet et le respect d'une décision remplacée doivent être vérifiés dans
  une conversation neuve. Aucune économie effective de tokens revendiquée.

## L7 — lecteur de contexte avec plafond et provenance

- Git, fiche/décisions, journal et services existants relus ; les outils MCP
  DevCore/RepoWise restent absents du catalogue de cette conversation.
  Référence avant modification : **6 tests MCP/configuration réussis en 9,66 s**,
  avec racines temporaires définies avant les imports et sous-processus.
- Ajout du registre `docs/project-context/context.json`, source structurée du
  lecteur, distincte de la synthèse lisible `decisions.md`. Les décisions ont
  un statut, une justification, une validation déclarée, une date éventuellement
  inconnue, des sources, tags et liens de remplacement. Une décision remplacée
  doit aboutir à une décision en vigueur ; une proposition ne peut pas clôturer
  cette chaîne. Mettre à jour la synthèse avec le registre lors d'une décision.
- `devcore_engine/services/project_context.py` et
  `Scripts/resume_project_context.py` lisent uniquement le répertoire explicite
  du projet, sans SQLite, réseau ou écriture de fichiers. Ils refusent un projet
  différent, les chemins sortants, les fichiers de plus de 256 Kio et les
  registres invalides. Les décisions remplacées sont exclues du contenu chargé.
- La fiche et les décisions obligatoires restent indivisibles. Une requête
  choisit les décisions facultatives par correspondance de mots avec leurs
  tags ; les propositions gardent leur statut. `omitted` indique absence de
  pertinence ou manque de budget. Un budget insuffisant pour le socle échoue
  avec code CLI 2 et sans contexte sur stdout.
- Le plafond couvre exactement la ligne JSON UTF-8, saut de ligne et
  diagnostics compris. L'environnement Python 3.13 de recette n'a pas de
  tokenizer : la mesure est explicitement en **octets**, pas en tokens.
  `model_tokens_measured` vaut false. Aucun gain de tokens revendiqué.
- La réponse porte les empreintes de la fiche et du manifeste, la date de
  revue et les avertissements de fiche modifiée, revue expirée ou future.
  Ces dates et citations restent déclarées ; les contenus des sources et l'état
  des services ne sont pas revalidés automatiquement.
- Suite `tests/test_project_context_resume.py` : **6 tests réussis, 1 ignoré
  en 0,49 s**. Les tests sur fixtures temporaires vérifient budget complet,
  décision remplacée exclue, proposition étiquetée, refus de projet/chemin/
  remplacement invalide, signalement de péremption, sortie CLI UTF-8 exacte,
  absence de réponse partielle et fichiers inchangés. Le test de lien symbolique
  est ignoré faute de privilège Windows ; cette branche reste à qualifier dans
  un environnement permettant la création de liens.
- Lecture opérationnelle des documents versionnés avec `--query dbos` et
  plafond 12 000 : **5 834 octets**, D-002/003/004/006 obligatoires, D-005 proposée
  sélectionnée, D-001 remplacée exclue, aucun avertissement. Cette lecture n'est
  pas un test sur les données actives. `AGENTS.md` demande maintenant ce lecteur
  à la reprise avec plafond explicite et dégradation signalée si indisponible.
- Limites : ACL de l'appelant, compteur de tokens du fournisseur, raccordement
  MCP/HTTP/hooks des autres clients, fraîcheur RepoWise et qualification en
  conversation neuve restent ouverts. Le plafond ne couvre pas les autres
  instructions de Codex, ses schémas d'outils ou les échanges ultérieurs.

## L7 — contexte accessible par MCP

- Git, lecteur borné, journal, plan et configuration relus. Référence avant
  modification : **12 tests réussis, 1 ignoré en 10,40 s** sur racines temporaires.
  DevCore/RepoWise restent absents du catalogue de la conversation actuelle ;
  la configuration réparée ne recharge pas ses outils rétroactivement.
- Ajout de `devcore_project_context` au serveur MCP et au profil de consultation.
  Il lit seulement `DEVCORE_CONTEXT_ROOT`, absolu et configuré par l'opérateur,
  et exige le projet explicite. Aucun chemin client accepté ; plafond serveur
  `DEVCORE_CONTEXT_MAX_BYTES` à 12 000 dans ce dépôt, réductible par le client.
- L'appel s'exécute hors de la boucle async, comme les autres outils. Il ne
  consulte pas SQLite et contourne les hooks qui pourraient modifier sa réponse
  ou écrire des journaux. Le contrôle du projet intervient avant la lecture.
  L'audit des identités et les ACL de l'équipe restent ouverts en L4.
- Réponse : un seul bloc texte JSON compact, sans seconde copie dans
  `structuredContent`. La mesure porte sur ce bloc et son saut de ligne ;
  l'enveloppe MCP, les schémas d'outils et les autres instructions Codex ne sont
  pas inclus. Les octets ne sont toujours pas présentés comme tokens.
- Tests finaux `tests/test_project_context_resume.py`,
  `tests/test_configure_codex_mcp.py`, `MCP/devcore-scripts/test_stdio_protocol.py` :
  **14 réussis, 1 ignoré en 12,57 s**. Le nouveau handshake réel utilise une
  fiche et un registre temporaires, sans base. Il couvre mesure du bloc reçu,
  absence de duplication, exclusion de la décision remplacée, refus du projet
  croisé, budget trop petit/trop grand, chemin client et répertoire implicite.
  Les documents de fixture sont inchangés et les racines locales/partagées
  restent vides. Le test ignoré est toujours celui du lien symbolique Windows.
- Configuration du dépôt prévisualisée puis appliquée avec conservation des
  autres paramètres et sauvegarde
  `.codex/config.toml.backup-bad44ddf-7ec4-41d9-ae88-84a7b69e182d`.
  Empreinte prévue :
  `fa8d27d88d23ed2f01887435d9fa8594d823c772ce1ca67a9f1b2c28a555016c`.
  `codex mcp get devcore --json` confirme les trois outils, le répertoire explicite
  du contexte et le plafond. Aucun réglage global ni service actif redémarré.
- Fiche revue en version 2 avec nouvelle empreinte ; `AGENTS.md` préfère le
  nouvel outil puis se replie sur la CLI en cas d'absence. Les données actives,
  Dropbox et l'index RepoWise ne sont pas utilisés comme fixtures.
- Limites inchangées : appels depuis une conversation neuve, pertinence/fraîcheur
  RepoWise, compteur du fournisseur, comparaison réelle et ACL multiutilisateur
  restent à qualifier. Le raccordement HTTP et des autres clients est à venir.

## L1/L2 — versions attendues dans les mutations HTTP du Cockpit

- Git, contexte court, plan, journal et adaptateurs relus avant modification.
  Le service commun contrôlait les versions, mais les façades HTTP `done` et
  `delete` ne transmettaient pas cette condition. Référence sur racines
  temporaires : **21 tests réussis en 19,54 s** (ports, double lecture, versions).
  Les outils DevCore/RepoWise restent absents du catalogue de cette conversation.
- Le contrat de lecture des tâches expose `version`, entier positif ou null
  si le schéma historique ne la fournit pas. Les lectures SQL restent en
  `mode=ro`, sans ajouter de colonne. La construction d'URI SQLite encode
  correctement les caractères spéciaux du chemin. La façade de liste Cockpit
  expose également ce champ, avec le même comportement sur un ancien schéma.
- `POST /api/done` et `DELETE /api/delete` acceptent `expected_version` dans
  l'objet JSON. Les valeurs booléennes, non entières ou non positives sont
  refusées avant mutation. Les gardes existantes d'authentification et de CSRF
  précèdent toujours la lecture des arguments. Les tests des transitions
  simulent ces gardes et ne constituent pas une qualification d'identités L4.
- Les façades transmettent la condition à `TaskService` avec projet et tâche
  explicites. Une version périmée retourne HTTP **409**, code
  `stale_task_version`. Une écriture conditionnelle sur un schéma sans versions
  retourne **409**, code `task_version_unavailable`, sans migration implicite.
  Les opérations restent déportées en thread hors de la boucle async.
- L'export JSON explicite conserve maintenant la version SQL. La comparaison
  de double lecture détecte un écart de version, y compris avec les mêmes
  identifiants. Les mutations ne déclenchent toujours pas d'export Dropbox.
- OpenAPI et client TypeScript régénérés. Avant écriture, comparaison du
  résultat attendu sans le nouveau champ avec les fichiers préexistants :
  **égalité exacte** du schéma et du client. Leurs changements existants sont
  conservés ; les nouveaux ajouts viennent du contrat de version.
- Vérifications finales sur fixtures temporaires : **23 réussis en 13,97 s**
  pour ports/double lecture/versions ; **10 réussis en 10,49 s** pour les anciens
  adaptateurs et les mutations HTTP conditionnelles ; **2 réussis en 4,62 s**
  pour export versionné SQL/JSON et génération OpenAPI/client. La première
  commande utilisant `-k task` globalement avait donné 26 réussis mais exclu
  39 cas ; les suites pertinentes ont ensuite été sélectionnées correctement.
- Les tests opposent alpha/beta avec chacun T-01, une modification via une
  seconde connexion, refus de la version périmée sans événement, succès avec
  la version fraîche, erreurs de type, schéma historique inchangé, export
  cohérent puis divergence. Une assertion existante de lecture après suppression,
  déplacée par erreur lors de l'insertion des tests, a été remise dans son test
  d'origine avant la validation finale. Avertissement de dépréciation existant
  Starlette/httpx ; aucune erreur d'espacement au `git diff --check` ciblé.
- Limites : version encore facultative pour compatibilité, interface actuelle
  et anciens clients pas encore convertis pour l'envoyer systématiquement.
  Les routes de mutation versionnées de l'API v1 et la propagation MCP restent
  à construire. Aucun Dashboard HTML généré n'a été écrasé, aucun service actif
  redémarré, aucune base active ni Dropbox utilisés comme fixtures. L1/L2 et
  la bascule de schéma restent ouverts.

## L1/L2 — clôture conditionnelle par MCP

- État Git, contexte court, journal, plan et implémentations CLI/HTTP/MCP relus.
  Référence avant édition, avec racines temporaires : **12 tests réussis en
  26,23 s** (protocole MCP et service des versions). Les outils restent absents
  du catalogue de cette conversation ; validation par SDK et sous-processus.
- `devcore_task_done` accepte maintenant `task_id` et `expected_version`.
  La version exige une tâche nommée ; les arguments invalides sont refusés avant
  l'ouverture du magasin. La tâche est résolue dans le projet explicite, avec
  la même tolérance de casse que la façade HTTP, puis la version est vérifiée
  sous le verrou de transaction du service commun.
- Une clôture nommée ne sélectionne ni n'active la tâche suivante. Les anciens
  appels sans identifiant gardent la sélection de tâche active et l'avancement
  historiques, sans garantie de concurrence par version. La réponse nommée
  inclut projet, identifiant canonique et version courante.
- Les refus portent les codes `stale_task_version`, `task_version_unavailable`,
  `invalid_arguments`, `task_not_found` ou `project_not_found`. Une version
  attendue sur un schéma historique est refusée sans migration. La connexion
  de clôture exige une racine locale absolue et un fichier existant, ouvre en
  `mode=rw`, active les FK et n'exécute aucun initialiseur de schéma. L'absence
  de magasin est une erreur `task_store_unavailable` ; aucune base implicite.
- Les refus métier typés ne déclenchent plus le coupe-circuit d'infrastructure.
  Ils restent des résultats en échec et sont journalisés par les hooks. Les
  vrais échecs d'infrastructure continuent de déclencher le circuit après le
  seuil configuré. Cela évite de bloquer la demande valide qui suit plusieurs
  collisions de versions.
- Suite finale `MCP/devcore-scripts/test_stdio_protocol.py`, `test_hooks.py`,
  `tests/test_task_versions.py` : **20 tests réussis en 30,93 s**. Le handshake
  conditionnel oppose alpha/beta avec chacun T-01 et une T-02 en attente,
  modifie la tâche via une autre connexion, répète trois refus de version,
  vérifie l'absence d'événement métier, puis réussit avec la version fraîche.
  T-02 reste todo, beta reste inchangé et un seul TaskCompleted est écrit.
  Le schéma minimal ancien est inchangé après refus ; le circuit reste testé
  pour les défaillances réelles. Les hooks utilisent seulement des journaux
  temporaires dans ces essais. `git diff --check` ciblé : aucune erreur
  d'espacement, avertissements LF/CRLF seulement.
- Le profil Codex de consultation reste limité à ses trois outils ; la clôture
  n'y a pas été activée. Aucun service actif redémarré, aucune configuration
  globale changée, aucune base active ni Dropbox utilisés comme fixtures.
  Les versions obligatoires dans les clients, les mutations HTTP v1, l'identité
  utilisateur et le routage CLI/MCP vers l'API centrale restent ouverts.
  L'enchaînement historique clôture/sélection suivante n'est pas une opération
  atomique ; sa suppression relève de la migration des anciens clients.

## L1/L2 — versions observées dans les deux vues Cockpit

- Contexte borné, état Git, journal, plan et tests pertinents relus avant édition.
  Les outils DevCore et RepoWise sont toujours absents du catalogue de cette
  conversation ; recherches locales ciblées utilisées. Référence avant édition
  sur racines temporaires : **13 tests réussis en 12,77 s**, 32 désélectionnés.
- Le lecteur SQL des projets inclut `version`, ou `NULL` si la colonne manque,
  sans initialiser ni migrer le magasin. Chaque bouton est produit par un
  rendu commun avec projet, tâche et version du snapshot ; chaînes encodées en
  JSON puis échappées pour l'attribut HTML. Les versions absentes, invalides ou
  non représentables exactement par JavaScript désactivent les actions.
- Les templates Cockpit et terminal envoient cette valeur dans
  `expected_version`, capturée lors de l'affichage. Ils refusent aussi un appel
  JavaScript sans version valide avant confirmation et requête. Un 409
  `stale_task_version` affiche un message puis demande une actualisation ; aucun
  second appel de mutation ni adoption automatique d'une version fraîche.
  Les erreurs structurées affichent leur message, sans `[object Object]`.
- Vérification finale : **26 tests réussis en 10,31 s**, 31 désélectionnés,
  sur `Scripts/test_dashboard_data_loader.py`, `test_dashboard_task_actions.py`
  et les scénarios pertinents de `test_dashboard_api.py`. Node exécute les vrais
  gestionnaires extraits des deux templates : corps/méthode/projet/version,
  conflits, version manquante, annulation, refus d'accès et panne de transport.
  Le générateur produit les deux pages seulement sous un répertoire temporaire,
  avec alpha/beta partageant T-01 à versions différentes et une ligne historique
  sans version ; l'empreinte de la base est identique après génération.
  Les tests HTTP reproduisent le changement concurrent via une autre connexion,
  le refus 409 puis la réussite avec une version relue, sans changement de beta.
- Les contrats `test_dashboard_mutation_methods.ps1` et
  `test_dashboard_cockpit_contract.ps1` réussissent. `git diff --check` ciblé ne
  relève aucune erreur d'espacement, seulement les avertissements LF/CRLF.
  L'avertissement Starlette/httpx déjà présent subsiste ; aucun paquet installé.
- Aucune page active régénérée, aucun service redémarré, aucune donnée active,
  Dropbox ou index RepoWise utilisés comme fixtures. L'exécution Node vérifie
  les gestionnaires, pas l'affichage ni les sessions d'un navigateur réel.
  Les anciens clients et les pages déjà générées restent compatibles côté
  serveur sans version obligatoire : leurs écritures ne bénéficient pas de cette
  protection. Migration active, déploiement, identité utilisateur, API v1 et
  routage central restent ouverts ; L1/L2 ne sont pas déclarés terminés.
- À examiner lors du prochain passage : les associations d'événements et de
  fichiers dans `gen_dashboard.py` utilisent encore l'identifiant de tâche seul
  pour plusieurs projets. Leur isolation doit être vérifiée avant qualification
  multiutilisateur du Cockpit.

## L1/L2 — associations d'interactions isolées par projet

- Reprise avec contexte court à **5 841 octets / 12 000**, aucun avertissement,
  état Git conservé, journal, plan et tests du générateur relus. Les outils MCP
  DevCore/RepoWise sont absents du catalogue ; recherche locale ciblée utilisée.
  Référence avant édition : **15 tests réussis en 1,66 s** sur les actions et
  le lecteur Cockpit, avec racines locales/partagées temporaires avant imports.
- Défaut confirmé dans le code : événements SQL, sujets de commits, titres
  et fichiers Git étaient indexés par identifiant de tâche seul. Les métriques
  et les modales avaient également un repli sans projet. Deux T-01 de projets
  différents pouvaient recevoir les mêmes interactions et statistiques.
- Nouveau module pur `Scripts/dashboard/task_interactions.py` : clés internes
  `(project, task_id)`, casse du projet conservée, casse de l'identifiant de tâche
  tolérée. Un événement exige le projet de sa ligne SQL ; un identifiant absent
  peut venir de son payload, mais un projet absent n'est jamais déduit du payload.
  Les sujets identiques conservent toutes leurs associations pour détecter une
  ambiguïté. La lecture de ces associations SQL ouvre en `mode=ro` et ferme
  aussi la connexion en cas d'erreur ; aucun initialiseur ni écriture métier.
- Les fichiers proviennent seulement du dépôt local explicitement lié par son
  propre `.devcore/project.json`. La racine retournée par Git doit correspondre
  au répertoire attendu ; aucun manifeste parent ni préférence globale ne
  choisit le projet. Les deux commandes Git ont chacune un délai de cinq secondes.
  Seules ses tâches visibles sont candidates ; sujets ambigus, multiples tags
  et tâches inconnues sont omis. Les dépôts des autres projets ne sont pas
  parcourus automatiquement et leurs listes de fichiers restent vides.
- Les métriques exigent une clé avec projet, en conservant la compatibilité des
  identifiants numériques T-1/T-01. Les données historiques sans projet ne sont
  plus empruntées par une tâche homonyme. Les deux modales vérifient aussi que
  la donnée porte exactement le projet et la tâche demandés, sans repli global.
- Textes de modules, fichiers et événements échappés dans cette modale. Le JSON
  des interactions embarqué dans les deux pages remplace `<` par `\u003c`, ce
  qui empêche un texte `</script>` de fermer sa balise. Les autres vues/payloads
  ne sont pas déclarés qualifiés par ce correctif.
- Suite finale : **36 tests réussis en 13,79 s**, 31 désélectionnés, sur les
  interactions, actions, lecteur et scénarios HTTP pertinents. Les nouveaux
  essais couvrent alpha/beta avec T-01 et titres identiques, événements sans
  projet, payload invalide, sujets ambigus, manifeste absent/incorrect/parent,
  racine Git discordante, métriques sans projet et casse des projets.
  Le générateur produit seulement des pages temporaires ; leur JSON contient
  les événements attendus, y compris le texte dangereux sans balise exécutable.
  L'empreinte de la base fixture reste identique après chaque génération.
  Node exécute les vraies modales des deux templates avec données croisées et
  textes HTML : aucun événement beta dans la modale alpha, textes échappés.
- Les contrats mutation/cockpit PowerShell réussissent ; `git diff --check`
  ciblé sans erreur d'espacement, avertissements LF/CRLF seulement. L'ancien
  avertissement Starlette/httpx subsiste. Aucun service, page active, configuration
  utilisateur, donnée active, Dropbox ou index RepoWise modifié par les essais.
- Limites : collecte bornée aux 300 événements globaux récents et 100 commits,
  pas une histoire complète par projet. Les projections, cartes et routes
  historiques restent globales ; ce correctif d'association ne remplace pas
  l'identité et les ACL HTTP/SSE/export. Pas de navigateur réel ni de déploiement
  actif qualifié. L1/L2 restent ouverts. Prochaine priorité : préparer le parcours
  d'identité et les contrôles d'accès des données/projections du Cockpit en L2/L4.

## L2/L4 — premier profil individuel pour les opérations de tâches

- Contexte borné à **5 995 octets / 12 000**, sans avertissement ; état Git,
  dernier journal, L4, routes d'authentification et tests relus avant édition.
  Les outils DevCore/RepoWise sont toujours absents du catalogue ; sources
  locales ciblées utilisées. Référence : **24 tests réussis en 7,64 s**,
  31 désélectionnés, avec racines temporaires avant imports et sous-processus.
- `devcore_engine/security/identity.py` introduit un port `IdentityProvider`,
  un principal immuable et un adaptateur SQLite de qualification. Le schéma
  séparé est initialisé uniquement par une commande locale explicite, sous
  transaction ; lecture HTTP en `mode=ro`/`query_only`, magasin existant requis.
  Schéma inconnu refusé sans migration et initialisation répétable sans changement.
- Jetons aléatoires de 32 octets, empreintes SHA-256 seules en base, durée
  60..86 400 secondes, portée explicite projet/actions. L'émission ne dépasse
  pas le rôle existant. Chaque requête revérifie compte actif, émission/expiration,
  révocation, portée et appartenance courante. Rôles reader/contributor/owner
  qualifiés pour lecture/mutation des tâches ; aucun administrateur global implicite.
- CLI `manage_local_identity.py` : init, comptes locaux sans mot de passe,
  attribution/retrait du rôle, émission/révocation du jeton et désactivation du
  compte. Le secret exige un fichier de sortie créé exclusivement ; ni écrasement
  ni secret sur stdout. Une erreur de livraison révoque le jeton éventuellement
  émis. Permissions Windows et récupération administrateur restent à qualifier.
- Le profil explicite `DEVCORE_DASHBOARD_AUTH_PROFILE=individual` protège les
  trois routes existantes liste/clôture/suppression. Projet autorisé avant accès
  métier, version positive obligatoire pour mutation, principal conservé dans
  l'état de requête. Aucun repli vers le jeton commun. Identité absente/incompatible
  503, jeton invalide/expiré/révoqué 401, droit absent 403. Recherche d'identité
  dans un thread ; statut public minimal indépendant du magasin.
- Ce profil ferme HTML, projections globales, paramètres, SSE, recherche et
  toute route non qualifiée. Les requêtes avec Origin sont refusées : parcours
  Bearer de clients explicites, sans cookie ni session navigateur. Démarrage
  sans bootstrap partagé, rotation commune refusée et injection HTML désactivée.
  Corps mutantes limités avant collecte/parsing en octets déclarés et reçus,
  y compris les flux sans Content-Length. Le profil historique reste celui par
  défaut tant que la bascule n'est pas réalisée.
- Validation : suite identité/profil/compatibilité HTTP **38 tests réussis en
  69,28 s**, 27 désélectionnés ; scénario additionnel de garde legacy Bearer/CSRF
  **1 test réussi en 4,13 s**. Soit **39 tests distincts pertinents**.
  Deux utilisateurs avec chacun T-01, lecteur refusé en écriture, accès croisés
  refusés, modification concurrente 409 puis succès avec version fraîche,
  révocation puis 401 et accès du second utilisateur conservé. Vérifications
  complémentaires : rétrogradation/retrait du rôle, désactivation, limites
  d'expiration, secrets absents de la base et de stdout, magasin absent non créé,
  schéma étranger inchangé et CLI refusant l'écrasement du fichier de secret.
- Non-blocage vérifié par ASGI : une recherche d'identité volontairement
  suspendue laisse `/api/status` répondre sous le délai de test de 0,5 s.
  Corps déclaré/flux trop grand refusé 413. Les tests legacy réels vérifient
  401 sans Bearer, 403 sans/mauvais CSRF et succès avec les deux secrets sur
  fixtures ; beta reste inchangé.
- Le contrat PowerShell de sécurité a d'abord échoué : il attendait des méthodes
  de l'ancien serveur HTTP (`send_csrf_error_response`, etc.). Il vérifie désormais
  les éléments FastAPI/CORS/gardes et le limiteur du profil individuel. Les deux
  contrats sécurité/mutations réussissent ; ces contrôles structurels complètent
  les essais HTTP et ne prouvent pas seuls les droits. Avertissement existant
  Starlette/httpx conservé, aucun paquet installé.
- L'exemple local et la [fiche de qualification](identite-locale-2026-10-03.md)
  décrivent l'activation future et la matrice. Aucun service actif, configuration
  utilisateur ou base active basculés ; aucune donnée Dropbox ni index RepoWise
  utilisés comme fixtures. Le profil courant conserve ses limites historiques.
- Limites : comptes humains/mots de passe, sessions HttpOnly/SameSite/CSRF,
  administrateur d'instance, adaptation PostgreSQL/RLS, droits API v1/CLI/MCP/
  workflows/artefacts/export/mémoire/SSE et auteur d'audit non réalisés par ce
  passage. Révocation d'une opération déjà admise puis bloquée non qualifiée ;
  essais sur requête suivante. Le navigateur n'est pas ouvert à des utilisateurs
  individuels par ce prototype. L4 reste ouvert ; prochaine priorité : parcours
  navigateur avec session et projection autorisée, puis extension aux canaux.

## L4 — backend de sessions navigateur lié aux droits individuels

- Reprise : contexte **6 228 octets / 12 000**, sans avertissement ; journal,
  état Git, L4 et tests identité/profil relus. MCP DevCore/RepoWise absents du
  catalogue ; sources locales utilisées. Référence isolée : **15 tests réussis
  en 51,39 s**, neuf désélectionnés. Aucun fixture actif/Dropbox/index RepoWise.
- `security/browser_sessions.py` ajoute une migration transactionnelle explicite
  v1→v2 via `manage_local_identity.py upgrade-sessions`. Le fournisseur de jetons
  reste compatible v1/v2. HTTP exige le schéma adapté, sans initialisation ni
  migration implicite. Création refusée sur v1 sans changer l'empreinte du fichier ;
  upgrade répétable et droits/jetons existants conservés sur fixture.
- Échange du Bearer individuel contre une session par `POST /api/auth/session`,
  projet explicite et Origin concordant. Session aléatoire de 32 octets, empreinte
  seule en base, portée d'un projet et origine, liée à son credential source.
  TTL maximal trente minutes et inférieur/égal à celui du jeton. La rotation
  révoque le cookie précédent fourni ; un précédent malformé n'invalide pas une
  nouvelle authentification valide. Validation des droits réutilisée depuis le
  fournisseur de jetons, à chaque accès et dans la transaction de création.
- Cookie HttpOnly, SameSite=Strict, Path=/, sans Domain, Secure sous HTTPS.
  HTTP n'est accepté qu'en loopback ; l'origine doit appartenir à l'allowlist
  configurée et correspondre à l'URL du serveur. Une mutation exige Origin.
  Nonce CSRF dérivé par HMAC du secret de session, comparé en temps constant
  après validation du format ASCII/longueur. Nonce d'une autre session, absent,
  malformé ou origine étrangère : 403. Pas de jeton commun injecté dans HTML.
- `GET /api/auth/session` reprend utilisateur/projet/expiration/nonce, sans
  exposer la session brute. `DELETE` exige Origin et nonce, révoque côté serveur
  et expire le cookie ; rejeu ensuite refusé. Les réponses privées de tâches
  et de session portent `Cache-Control: no-store`. Le compte, le jeton source,
  ses actions et l'appartenance courante sont revérifiés : révocation du jeton
  et rétrogradation effectives à la requête suivante.
- Suite finale identité/sessions/profil HTTP : **31 tests réussis en 91,13 s**.
  Les sept nouveaux tests réussissent aussi séparément. Après petits correctifs,
  **deux scénarios réexécutés en 6,05 s**, puis **trois tests de sessions en
  3,11 s** : ce sont des répétitions, pas 36 tests distincts. Deux clients HTTP
  avec cookies indépendants et T-01 homonyme, clôture/suppression et droits
  croisés, CSRF inter-session, logout/rejeu, rotation, révocation du jeton,
  rétrogradation, expiry exacte, schéma v1, mauvais Origin, cookie Secure et
  HTTP distant refusé. Corps trop grand sur l'échange : 413. Les refus CSRF
  Unicode/longueur invalide restent des refus métier. Beta reste inchangé.
- Contrats PowerShell sécurité/mutations réussis ; diff ciblé sans erreur
  d'espacement, avertissement LF/CRLF seulement. Avertissement Starlette/httpx
  inchangé, aucun paquet installé. [Fiche](identite-locale-2026-10-03.md) mise
  à jour avec les références primaires OWASP consultées pour origine, CSRF et
  gestion de sessions ; elles ne valent pas qualification de l'instance.
- Aucun magasin/service/page actif basculé ; aucun secret réel manipulé. Le
  profil individuel reste opt-in. HTML/projections globales et recherche/SSE
  restent fermés dans ce profil ; l'API v1 demeure non raccordée à ses contrôles.
  Les essais sont des clients ASGI/TestClient, sans navigateur réel : attributs
  des cookies vérifiés, leur politique d'envoi par navigateur non qualifiée.
  Interface individuelle, connexion par mot de passe, récupération administrateur,
  PostgreSQL/RLS et audit des auteurs restent ouverts. Le Bearer manuel est un
  bootstrap de recette, pas le parcours final de connexion. Prochaine priorité :
  interface de tâches par projet et connexion individuelle.

## L4 — Page de tâches individuelle et recette navigateur

- Reprise : outils MCP DevCore/RepoWise absents de l'inventaire de ce fil,
  lecteur local utilisé (6 322/12 000 octets, aucun avertissement), état Git et
  journal ciblés préservés. Baseline sessions : sept tests réussis en 25,14 s.
- `/project` et `/project.js` : coquille publique sans donnée privée, réservée
  au profil `individual`, avec CSP/no-store/nosniff/no-referrer. Les routes
  globales historiques restent fermées dans ce profil. Une session retournée
  décrit les actions autorisées par les mêmes contrôles que les opérations,
  tenant compte du rôle courant et de la portée du jeton source.
- La page reprend le cookie, charge vingt tâches du projet vérifié et affiche
  les textes avec textContent. Bearer seulement sur l'échange, champ effacé
  immédiatement, aucun stockage local. Lecteur sans commandes de mutation ;
  versions manquantes/invalides désactivées. CSRF, confirmation et version
  affichée pour les écritures. Un 409 actualise sans nouvelle mutation ; un
  refus de droits recharge la session, une session invalide efface la vue.
  Les requêtes en cours bloquent les doubles clics dans cette page.
- **Neuf tests Python sessions/HTTP réussis en 35,37 s**, dont deux nouveaux
  scénarios coquille/absence de bootstrap commun et intersection des droits.
  **Dix scénarios Node réussis** sur le script réellement servi : reprise,
  login, rendu inerte, lecteur/versions, clôture obsolète, suppression confirmée,
  rétrogradation, expiration, concurrence de clics/pagination, déconnexion et
  réponse d'un autre projet rejetée. Les assertions regroupent plusieurs cas.
  Deux contrats PowerShell réussis. Diff ciblé sans erreur d'espacement,
  avertissement LF/CRLF seulement ; dépréciation Starlette/httpx inchangée.
- Recette navigateur intégré sur `http://127.0.0.1:20239/project`, racines
  temporaires dédiées : Alice/alpha puis Bob/beta, cookie envoyé après
  rechargement, affichage HTML inerte, conflit après modification concurrente,
  rôle lecteur appliqué à l'actualisation, révocation du jeton effaçant la vue,
  logout puis rechargement sans session. Le clic de confirmation a produit un
  timeout de contrôle navigateur : aucune répétition ; observation suivante
  confirme le 409 attendu. Vérification SQL finale sur fixture : alpha toujours
  in_progress/version 2 (édition concurrente seulement), beta in_progress/1.
  [Capture de lecture seule](interface-projet-lecture-2026-10-03.jpg).
- Arrêt des seuls processus Python du serveur temporaire et fermeture de
  l'onglet ; fichier de jetons de fixture supprimé. Aucun service, secret,
  magasin métier, donnée Dropbox ou index RepoWise actif modifié. Aucun paquet
  installé. La fiche durable passe à la version 9, empreinte mise à jour.
- Limites : profil opt-in non déployé, connexion Bearer de recette seulement,
  pas de mots de passe/récupération administrateur, de PostgreSQL/RLS ou d'audit
  des auteurs. Un navigateur avec comptes successifs a été vérifié, pas deux
  profils indépendants ; SameSite cross-site et Secure sous HTTPS ne sont pas
  qualifiés par cet essai. Tests locaux, aucune nouvelle qualification CI.
  L4 reste ouvert. Prochaine priorité : comptes humains et récupération locale.
- Vérification finale de reprise : fiche v9 et décisions, **6 570/12 000 octets
  UTF-8**, aucun avertissement ; ce plafond ne mesure pas les tokens du modèle.
  Après correction du message d'annulation de confirmation, les dix scénarios
  Node sont réexécutés avec succès (répétition, pas dix tests supplémentaires).

## L4 — Mots de passe, admission bornée et récupération locale

- Reprise : MCP DevCore/RepoWise indisponibles ; fiche v9 et décisions par
  lecteur local, 6 570/12 000 octets, aucun avertissement. État Git, journal et
  tests concernés relus. Baseline identité/sessions : **17 tests réussis en
  37,28 s**, sous Python 3.13 et racines temporaires avant les imports.
- Argon2id par `argon2-cffi` 25.1.0 / bindings 26.1.0, profil RFC_9106_LOW_MEMORY
  explicite (65 536 KiB, t=3, p=4). Sel aléatoire, 15..256 caractères à la
  création, Unicode/espaces conservés. Les comptes inconnus vérifient un hash
  factice, sans création de ligne. Même erreur HTTP pour mauvais secret,
  compte inconnu ou désactivé ; ces tests ne prouvent pas une égalité temporelle.
- Schéma identité v3 ajouté par commande explicite après le schéma sessions v2.
  Migration répétable, comptes/membres/jetons/sessions préservés, aucune migration
  HTTP. Les profils à schéma v1/v2 restent utilisables pour leurs fonctions
  précédentes ; la connexion par mot de passe refuse un schéma non migré.
- Deux vérifications simultanées au maximum par processus ; excès : 429 et
  Retry-After. Cinq échecs du compte : délai de soixante secondes persisté,
  sans bloquer les autres comptes. Vérification/rehash hors verrou SQLite et
  dans un thread HTTP. Après hash, admission transactionnelle : mot de passe
  version/hash, état du compte et rôle revérifiés avant création atomique d'une
  source interne et de la session. Aucun Bearer brut retourné au navigateur.
- CLI locale : `upgrade-passwords`, `set-password`, `reset-password`, `enable-user`.
  Deux saisies getpass masquées et concordantes, terminal interactif exigé,
  repli affiché refusé, aucune option de secret dans argv/fichier/env. Reset
  invalide tous les jetons et sessions du seul compte concerné, ne modifie pas
  ses rôles et ne réactive pas un compte désactivé. L'UI demande identifiant,
  projet et mot de passe, efface son champ à l'envoi et reprend ensuite le cookie.
- Dépendances ajoutées au manifeste et au verrou avec hashes : toutes les
  versions antérieures sont restées identiques, comparaison automatique avec
  le candidat uv compilé sous contrainte du verrou précédent. Deux paquets
  installés uniquement dans `E:/DevCoreRuntime/recipes/devcore-auth-py313-20261003/packages`.
  Tests via le Python 3.13 documenté, avec ce PYTHONPATH explicite et des racines
  temporaires. Runtime actif non modifié ; cffi 2.1.1 existant utilisé.
- Tests ciblés : **12 tests core/sessions en 23,76 s**, **13 tests HTTP/sessions
  en 68,04 s**, puis **11 scénarios JavaScript** et deux contrats PowerShell.
  La suite élargie journalisée réussit : **49 tests en 214,73 s**. Elle contient
  les tests ciblés et historiques ; ne pas additionner ces répétitions. Un
  premier lancement de cette suite n'avait pas de résultat final récupérable
  après reprise ; il n'est pas compté comme réussi. Couverture : recovery avec
  invalidation de Bearer/cookie et autre compte intact, droits croisés, schémas,
  erreur générique, cooldown, reset/désactivation/retrait d'appartenance pendant
  hash, CLI sans écho, CSRF et versions. Deux vérifications suspendues conservent
  `/api/status` sous 0,5 s et refusent la troisième avec 429.
- Parcours navigateur intégré sur instance temporaire 127.0.0.1:20239 : mauvais
  secret refusé, Alice/alpha connectée et reprise après rechargement, champ du
  secret vide, reset local invalidant son cookie, nouveau secret accepté,
  Bob/beta puis logout/rechargement sans session. [Capture sans secret](connexion-mot-de-passe-2026-10-03.jpg).
  Un seul navigateur avec comptes successifs, pas deux profils indépendants.
  À la vérification finale, aucun processus de cette recette ne subsiste ;
  onglet fermé et script temporaire contenant les secrets de test supprimé.
  Tâches de fixture inchangées : alpha et beta in_progress/version 1.
- CI : gates explicites des six fichiers identité/sessions/mots de passe et
  JavaScript, racines temporaires avant Python et Node 24 par setup-node officiel.
  YAML chargé, chemins/racines contrôlés, commandes exécutées localement ;
  aucun résultat distant annoncé. Diff ciblé sans erreur d'espacement, seulement
  LF/CRLF ; dépréciation Starlette/httpx inchangée.
- Limites : profil opt-in non déployé, saisie masquée sur vraie console Windows
  et ACL NTFS non qualifiées, rôle administrateur d'instance/audit des auteurs
  encore ouverts, pas d'adaptateur PostgreSQL/RLS ni d'ACL sur tous les canaux.
  Pas de qualification anti-DoS réseau distribué, cross-site, HTTPS réel ou MFA.
  Le reset protège les prochains accès, pas une mutation déjà admise et bloquée.
  Aucun magasin actif, donnée Dropbox ou index RepoWise modifié. Les critères
  L4 restent ouverts ; prochaine priorité : administrateur, audit et ACL.
- Reprise finale de la fiche v10 : **6 783/12 000 octets UTF-8**, sans
  avertissement ; hash de la fiche et manifeste concordants. Tokens du modèle
  non mesurés par ce lecteur.

Références primaires consultées pour la conception :
[Argon2, paramètres](https://argon2-cffi.readthedocs.io/en/stable/parameters.html),
[Argon2, API](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[OWASP, authentification](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
[setup-node officiel](https://github.com/actions/setup-node).

## L4 — Auteur des clôtures et suppressions individuelles

Reprise du passage programmé du 3 octobre 11:03 UTC. État Git sale préservé,
fiche v10 et journal pertinent lus, runtime Python 3.13 présent. Lecture des
tests et référence avant modification : **33 tests réussis en 112,47 s**
(versions, TaskService, accès individuels et sessions HTTP).

- MCP DevCore et RepoWise disponibles et consultés en lecture seule dans ce
  fil : fiche devcore **6 783/12 000 octets**, hashes concordants, aucun
  avertissement ; task_status explicite devcore retourne T-388 et 384/389.
  Ce board historique ne mesure pas la qualification des lots L0–L9.
  RepoWise trouve TaskService, avec index b2349de865c2 aligné sur HEAD mais
  **âgé de neuf jours**, analyse du 23 septembre de provenance inconnue,
  embedder mock et recherche sémantique désactivée. Ses anciennes bornes de
  lignes et l'absence déclarée de test sont contredites par le code actuel.
  Aucun index réécrit, aucune fraîcheur ni économie réelle de tokens déduite
  des estimations tokens_saved. Appels dans une conversation neuve à qualifier.
- Le Cockpit individuel construit RequestContext depuis le principal WRITE
  admis par le middleware et le projet vérifié. Identité du JSON/en-têtes
  libres ignorée ; trace générée côté serveur et session_id non secret pour
  les cookies. Clôture/suppression transmettent ce contexte au service.
- TaskService insère auteur/projet/tâche/action et statuts/versions avant-après
  dans audit_log **avant le commit**. Journal absent ou insertion refusée :
  rollback de la mutation et de sa version. Pas de titre, corps de requête,
  cookie, nonce CSRF, mot de passe ou Bearer dans les détails sérialisés.
  Les conflits, absences et refus d'accès ne produisent pas d'entrée de succès.
- **45 tests réussis en 162,17 s** : les 33 précédents réexécutés et 12 nouveaux
  cas moteur/HTTP. Deux projets avec tâche homonyme et requêtes simultanées,
  auteurs falsifiés ignorés, deux rédacteurs concurrents sur la même version
  (un seul succès/auteur), cookie corrélé sans secret, panne d'insertion ou
  table absente avec rollback, refus lecteur/projet et conflit sans succès.
  **10 tests HTTP historiques supplémentaires réussis en 18,90 s** : ancien
  schéma non migré, arguments/versions invalides, résolution d'identifiants
  et compatibilité des façades. Soit **55 tests distincts réussis** après
  modification ; les 33 de référence ne s'ajoutent pas au total.
- CI : deux nouveaux fichiers inclus dans la gate d'identité, racines de
  recette définies avant Python. Configuration vérifiée localement ; aucun
  résultat CI distant annoncé. Avertissement Starlette/httpx existant inchangé.
- Fiche durable v11 et hash du manifeste mis à jour ; lecteur local :
  **7 197/12 000 octets UTF-8**, aucun avertissement. Plafond en octets, pas
  mesure de tokens du modèle. Plan et qualification d'identité mis à jour.
- Limites : audit des deux mutations du profil individuel seulement. Appels
  historiques sans contexte compatibles et non audités ; autres mutations,
  API v1/CLI/MCP, administration d'identité et refus à couvrir. Pas d'API
  de consultation du journal ajoutée ; rétention/protection/archivage ouverts.
  Le contexte du moteur est fourni par un adaptateur de confiance, pas une
  ACL de service. Publication du bus existant après commit : outbox L5 ouverte.
  Aucune migration active, aucun runtime actif redémarré ni donnée Dropbox modifiée.
  L4 reste ouvert : administrateur, récupération NTFS/console, tous canaux,
  RLS et deux navigateurs indépendants. Automatisation conservée.

## L4 — Administration d'instance par console authentifiée

- Contexte MCP v11 relu sous budget : **7 197/12 000 octets**, hashes concordants,
  aucun avertissement. Statut du board historique inchangé ; aucun statut de lot
  déduit. Recherche RepoWise ciblée identity.py sans résultat, index annoncé âgé
  de neuf jours, mock/sémantique désactivée ; code/tests utilisés directement.
  Git sale et modifications antérieures préservés. Avant modification :
  **27 tests identité/sessions/mots de passe/HTTP réussis en 71,27 s**.
- Nouveau administration.py et schéma **v3→v4 explicite** : administrateurs,
  credentials distincts, marqueur de bootstrap unique et identity_audit.
  Initialisations/migrations précédentes idempotentes sur v4 ; credentials
  et sessions projet conservés. Pas de migration du magasin actif.
- Premier administrateur : utilisateur activé avec mot de passe, commande
  bootstrap-admin uniquement en terminal interactif avec confirmation explicite,
  une fois ; aucune route HTTP/MCP de bootstrap. Auteur initial marqué
  local-operator, identité OS précise non attestée. Deux bootstrap concurrents
  ne créent qu'un administrateur ; échec d'audit annule aussi le marqueur.
- login-admin réutilise le vérificateur de mot de passe borné, ses places et
  le délai d'échecs ; vérification/rehash hors verrou et admission après relecture
  transactionnelle. Rôle revérifié pendant l'admission ; retrait pendant hash
  refuse l'émission. Jeton administratif 900 s par défaut, 60..3600 s permis,
  hash SHA-256 en base, renouvellement par reconnexion après expiration.
  Les droits de projets exigent toujours leur appartenance/jeton séparé.
- La console v4 exige un fichier de credential administratif pour créer,
  désactiver/réactiver, attribuer droits/rôles, révoquer et réinitialiser les
  mots de passe. Fichier d'entrée borné et absolu, secrets absents d'argv/stdout.
  Livraison exclusive avec flush/fsync dans la transaction d'émission ; erreur
  gérée annulant l'émission et supprimant le fichier créé. Les schémas v1–v3
  gardent le provisionnement historique de recette, sans nouvelle prétention
  d'authentification. Refus d'écraser un fichier existant vérifié.
- Mutation d'identité et entrée d'audit dans la même transaction, auteur
  dérivé du jeton revérifié. Métadonnées en liste explicite sans mot de passe,
  hash de mot de passe ni token brut. Journal absent : rollback qualifié.
  Dernier administrateur activé protégé sous verrou d'écriture ; deux retraits
  concurrents laissent un administrateur. Désactivation/reset révoquent accès
  administratifs, accès projet et sessions ; réactivation sans résurrection.
- Vérifications après modification : **38 tests moteur en 82,61 s**, puis
  **50 tests console/HTTP/audit en 194,55 s**, puis **un test de rollback du
  bootstrap en 2,21 s**, soit **89 tests distincts réussis**. La référence de
  27 tests est incluse dans ces suites et ne s'ajoute pas au total. L'extension
  v4 est aussi essayée par cookies HTTP : refus de projet étranger, jeton
  administratif refusé pour les tâches, auteurs corrects et projet voisin
  inchangé. Avertissement Starlette/httpx existant inchangé.
- Gate CI étendue aux onze fichiers couverts par ces exécutions ; droits,
  [matrice et protocole console](administration-locale-2026-10-03.md) documentés.
  Parse AST/YAML/chemins et différences d'espacement contrôlés localement,
  aucune réussite distante annoncée. La matrice de rôles L4 est maintenant
  marquée qualifiée pour ces capacités de recette ; lot global toujours ouvert.
- Limites : aucune console Windows réelle/ACL NTFS qualifiée ; os.open 0600
  ne qualifie pas les ACL du poste. Pas d'administration Web/API/MCP, OIDC,
  PostgreSQL/RLS, secours sans administrateur joignable ou stockage inviolable
  du journal. Canaux Python internes et migrations restent une confiance OS,
  pas une frontière contre le contrôle du processus/fichiers. Refus non audités.
  Un crash entre livraison du fichier et commit peut laisser un jeton invalide,
  sans transaction distribuée annoncée. Aucune donnée active/Dropbox/index
  modifié, aucun runtime actif redémarré. Prochaine priorité : NTFS/récupération
  locale et extension des ACL/audits aux canaux restants. Automatisation conservée.
- Reprise finale de la fiche v12 : **7 371/12 000 octets UTF-8**, aucun
  avertissement, hash de fiche vérifié et hash du manifeste mis à jour.
  Ce lecteur ne mesure pas les tokens du modèle.

## L4 — Fichiers de jetons protégés et contrôlés sur NTFS

- Reprise initiale par MCP : fiche v12 **7 371/12 000 octets UTF-8**, sans
  avertissement ; statut du board historique inchangé. RepoWise ne trouve pas
  manage_local_identity.py, index de neuf jours/mock sans sémantique ; sources
  actuelles et tests utilisés, aucun index modifié. État Git et journal lus.
  Référence avant modification : **sept tests console réussis en 17,50 s**.
- secret_files.py et helper Windows PowerShell 5.1 embarqué : chemins littéraux
  absolus, volume local NTFS, contrôle des points de réanalyse et prévalidation
  du parent. Protection d'un fichier réservé vide avant tout credential/octet
  secret : propriétaire SID courant, héritage supprimé, droits FullControl
  limités au compte courant/SYSTEM, puis contrôle du descripteur effectif.
  Erreur de protection : pas d'émission et suppression du fichier réservé.
- Vérification des fichiers administratifs avant lecture : propriétaire,
  héritage, liste exacte de règles et droits. Règle Everyone supplémentaire
  réellement ajoutée sur une fixture : refus sans réparation ni lecture du
  secret. Le compte OS courant et SYSTEM restent autorisés. Pas de nouvelle
  prétention d'isolation entre processus du même compte.
- Nouvelle commande protect-secret-dir sur un répertoire existant vide choisi
  explicitement ; pas d'initialisation de base, pas de changement récursif ou
  de protection automatique de répertoires remplis. Les émissions historiques
  de jetons de projet utilisent aussi la protection avant émission/écriture.
- Essais initiaux refusés par mélange des modules PowerShell 7/5.1 ; filtrage
  insensible à la casse de PSModulePath et import Security natif par PSHOME.
  Le contrôle indépendant des fixtures a ensuite été corrigé : alias SDDL LA
  pour le SID Administrateur, et ajout Everyone par icacls sans modification
  SACL privilégiée. Ces exécutions en échec ne sont pas des qualifications.
- Exécution finale : **17 tests distincts réussis en 38,37 s** (huit cas NTFS
  natifs, huit console/émission et le cas de saisie masquée). Descripteur relu
  avec Get-Acl indépendamment du helper, refus de permissions étendues,
  jonction temporaire sans écriture/cible préservée, chemins avec métacaractères
  littéraux, refus de modifier un secret existant ou un répertoire rempli,
  panne ACL empêchant l'appel d'émission, compatibilité et absence de secret
  sur stdout. Avertissement Starlette/httpx existant inchangé.
- Helper inclus dans package-data du moteur ; **wheel Python 3.13 construit
  sur une copie temporaire des sources**, présence du helper et SHA-256 exact
  vérifiés dans l'archive. Premier essai sans setuptools indisponible ; outil
  de build setuptools 84.0.0 installé uniquement dans un target temporaire,
  aucun runtime actif modifié. CI étendue au douzième fichier, AST/TOML/YAML,
  racines/chemins et diff d'espacement vérifiés ; pas de résultat distant.
- [Protocole, preuve et limites NTFS](secrets-ntfs-2026-10-03.md), procédure
  administrateur et plan actualisés. Fiche v13 : **7 517/12 000 octets**, sans
  avertissement, hash concordant ; plafond en octets, pas mesure des tokens.
- Restent ouverts : permissions base d'identité/WAL/SHM, parents, compte de
  service distinct, second compte Windows réel, restauration des ACL, vraie
  console getpass et secours sans administrateur joignable. Le test ne couvre
  ni la branche POSIX ni un acteur contrôlant le système de fichiers ou doté
  des privilèges d'administration OS. Aucun secret ou permission active,
  donnée Dropbox ou index RepoWise modifié. L4/L9 et automatisation ouverts.

## L4 — Création privée et contrôle du magasin d'identité NTFS

- Reprise : contexte MCP v13 chargé à **7 517/12 000 octets**, sans avertissement ;
  état Git, dernier journal, initialisation SQLite, CLI et tests relus avant
  modification. Runtime Python 3.13 de recette présent. Tableau MCP historique
  inchangé, sans en déduire l'achèvement du plan. RepoWise : aucun symbole exact
  connect_existing, seulement un résultat approché sans pertinence pour l'identité ;
  index de neuf jours, mock/sémantique désactivée et HEAD concordant ne couvrant
  pas les changements Git. Sources locales retenues.
- Référence initiale : **16 tests réussis en 13,92 s**, identité et helper NTFS.
  Nouveau module security/private_store.py et commandes init-private-store /
  check-store-protection. Création exclusivement dans un parent existant vide,
  NTFS local sans jonction ; parent protégé avant tout journal SQLite, fichier
  réservé exclusivement et protégé avant les octets du schéma. Aucun compte ou
  administrateur initialisé. Les données existantes sont refusées sans réparation.
  Une réservation interrompue reste en place pour inspection, sans suppression.
- Helper PS1 étendu à CheckStore : contrôle des DACL du parent/de la base et
  des sidecars présents -journal/-wal/-shm, sans ouvrir SQLite ni rejouer un
  journal. Droits exactement SID courant/SYSTEM ; enfants hérités acceptant le
  propriétaire Administrateurs observé sous processus élevé, sans ACE de ce
  groupe. Aucune nouvelle validation PowerShell par requête HTTP ni prétention
  de surveillance continue. Compte OS courant et administrateurs OS de confiance.
- Douze nouveaux cas natifs, plus extension du cas de jonction : droits avant
  schéma, absence de compte, répertoires occupés conservés, échec de protection
  interdisant le schéma, véritables journaux DELETE et WAL/SHM avec transaction
  ouverte, droits Tout le monde ajoutés séparément sur les cinq cibles et refus
  sans réparation, inspection CLI sans aucun appel SQLite.
- **28 tests ciblés réussis en 61,78 s** ; après ajout de la vérification de
  jonction au magasin, **110 tests distincts réussis en 300,00 s** pour la gate
  complète identité/administration/audit et clients HTTP. Un avertissement de
  dépréciation Starlette/httpx, aucun échec. Racines LOCAL/DATA temporaires avant
  imports ; Argon2 fourni par le PYTHONPATH de recette isolé.
  Trace complète : C:/Users/Administrateur/AppData/Local/Temp/devcore-private-store-regression-0028de02fa9a4f73ab988e868edbc99b/tests.txt.
- Wheel 10.2.0 Python 3.13 construit sur copie avec les outils de build
  temporaires déjà disponibles : private_store.py et windows_secret_acl.ps1
  identiques aux sources dans l'archive ; extraction puis création privée
  exécutée avec succès depuis ce paquet. Aucun outil installé dans le runtime.
  Trace : C:/Users/Administrateur/AppData/Local/Temp/devcore-private-store-wheel-0e4f93ca004647a58de8987623ee2f24/wheel.txt.
- CI étendue au treizième fichier avec racines temporaires avant pytest, sans
  résultat distant annoncé. AST/TOML/YAML et diff d'espacement des fichiers
  suivis concernés vérifiés. Le diff global signale des espaces préexistants
  dans Dashboard/index_terminal.html, conservés hors de ce changement.
  [Procédure et limites](magasin-identite-ntfs-2026-10-03.md), recette
  administrateur et plan actualisés. Fiche v14, hash concordant :
  **7 674/12 000 octets**, sans avertissement ; pas une mesure des tokens.
- Restent ouverts : activation du magasin privé et des services, permissions
  des parents/compte de service distinct, second compte Windows réel,
  sauvegarde/restauration des ACL, console getpass réelle et secours sans aucun
  administrateur joignable. Autres fichiers temporaires SQLite et exports,
  courses avec acteur contrôlant le système de fichiers et POSIX non qualifiés.
  Aucune permission/donnée active, donnée Dropbox ou index RepoWise modifié.
  L4/L9 et automatisation restent ouverts ; prochaine priorité : parcours de
  récupération locale avec frontière OS attestée, puis autres canaux du plan.

## L4 — Secours d'un administrateur existant avec auteur Windows attesté

- Reprise du passage programmé : contexte MCP v14 **7 674/12 000 octets**, sans
  avertissement, état Git conservé, dernier journal et tests/CLI/administration
  relus avant édition. Runtime Python 3.13 confirmé. Task-status MCP : board
  historique T-388 / 384 sur 389, sans qualification des lots. Recherche ciblée
  RepoWise bootstrap_admin sans correspondance exacte : voisins de bootstrap
  sans rapport, index de neuf jours/mock sans sémantique, code actuel retenu.
- Avant modification : **27 tests réussis en 73,64 s**, administration et CLI.
  local_recovery.py et commande recover-local-admin ajoutés pour magasin privé
  v4 déjà bootstrappé, administrateur et entrée de mot de passe existants.
  Prévalidation native du magasin et du rôle avant saisie, saisie/confirmation
  getpass, drapeaux explicites récupération et déclaration d'arrêt des services.
  Aucun administrateur créé/promu, aucun nouveau jeton, bootstrap inchangé.
- Hash Argon2id hors verrou d'écriture ; nouvelle connexion mode=rw avec
  locking_mode=EXCLUSIVE avant accès au schéma, puis BEGIN EXCLUSIVE, attente
  SQLite d'une seconde maximum. Permissions/SID/rôle revérifiés après hash.
  Compte ciblé réactivé, secret remplacé, cooldown remis à zéro, jetons et
  cookies du compte révoqués ; autres comptes et appartenances conservés.
  Audit admin.recover-local avec auteur windows:<SID natif> et métadonnées
  construites explicitement dans la même transaction ; insertion refusée ou
  journal absent annulant reset, réactivation et révocations.
- Vingt et un cas de récupération : administrateur activé/désactivé en DELETE
  et WAL, ancienne connexion refusée/nouvelle admise, autres accès préservés,
  utilisateurs non-admin/inconnus refusés avant hash, audit absent/rejeté,
  lecteurs/écrivains concurrents empêchant le verrou exclusif dans les deux
  modes, rôle/ACL changés pendant le hash refusés, absence des drapeaux/TTY,
  confirmation différente et prévalidation avant saisie, aucun secret stdout,
  capacité administrative ordinaire ne pouvant invoquer ce secours.
- Premier passage : **25 tests réussis en 100,53 s**. Révision finale :
  **50 tests distincts réussis en 175,56 s** : 21 récupération, 19 administration,
  huit CLI et deux compatibilité HTTP v4. Un avertissement Starlette/httpx
  existant, aucun échec. Racines LOCAL/DATA temporaires définies avant imports,
  Argon2 de recette via PYTHONPATH isolé. Trace complète :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-recovery-final-9c7a9856ad284f6b87db949c9000d218/tests.txt.
- Wheel Python 3.13 construit sur copie, modules recovery/private_store et PS1
  identiques aux sources ; récupération et reconnexion réussies depuis le
  paquet extrait. Outils de build temporaires réutilisés, aucune installation
  dans le runtime actif. Preuve de paquet :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-local-recovery-wheel-3cadd1fe0eed4789b078808edd5c86ab/qualification.json.
  CI étendue au quatorzième fichier, durée bornée à douze minutes ; pas de
  réussite distante ni de requalification des 129 cas complets annoncée.
  AST/YAML et racines avant pytest vérifiés. Plan, procédure et fiche v15 mis
  à jour : **7 939/12 000 octets**, sans avertissement, hash concordant.
- Vérification primaire SQLite lors de la préparation du verrouillage WAL :
  recette Python **3.13.3 / SQLite 3.49.1**. Cette version figure dans la plage
  officiellement concernée par le défaut WAL-reset d'écritures/checkpoints
  concurrents, corrigé en 3.51.3 et certains backports. Aucun incident/corruption
  reproduit. [Sources et limite de recette](recuperation-locale-2026-10-03.md)
  consignées : qualifier un SQLite corrigé avant ce profil concurrent, sans
  attribuer aux tests d'ACL/exclusivité une preuve de robustesse de ce scénario.
- Limites : déclaration d'arrêt des services non vérifiée par un superviseur,
  propriétaire OS/SYSTEM/administrateurs et fichiers du programme de confiance,
  contrôle ACL ponctuel. Console getpass humaine, compte de service distinct,
  droits des ancêtres, sauvegarde/restauration, arrêt brutal et parcours actif
  restent ouverts. Le bootstrap historique garde l'auteur local-operator.
  Pas de nouveau canal HTTP/MCP ; toutes mutations/canaux non encore protégés.
  Aucune donnée/permission active, Dropbox ou index RepoWise modifié. L4/L9
  demeurent ouverts et l'automatisation est conservée. Prochaine priorité :
  qualification de maintenance/restauration sur recette, puis isolation des
  autres ressources/canaux et préparation du backend PostgreSQL du plan.

## L4/L9 — Sauvegarde et restauration privées, arrêts de processus qualifiés

- Reprise : contexte MCP v15 **7 939/12 000 octets**, décisions en vigueur et
  avertissements/omissions chargés ; état Git, dernier journal, modules de
  récupération/protection et tests relus avant modification. Runtime 3.13
  présent. MCP task-status historique inchangé ; RepoWise backup renvoie des
  voisins dans une archive de code, aucune correspondance exacte pertinente.
  Index de neuf jours/mock sans sémantique : implémentation locale retenue.
  Référence avant édition : **12 tests privés réussis en 29,14 s**.
- identity_backup.py et commandes backup-private-store/restore-private-store
  ajoutés. Magasin privé v4 bootstrappé, contrôle NTFS/FK/intégrité, verrou source
  EXCLUSIVE acquis avant schéma et conservé pendant la copie SQLite ; attente
  de verrou une seconde, copie par 256 pages avec progression refusant BUSY et
  budget de 30 secondes aux callbacks. Les services ne sont pas arrêtés ni
  vérifiés automatiquement : déclaration explicite de maintenance/console.
- Destination neuve dans un dossier existant vide : parent/fichier intermédiaire
  protégés avant les octets. Archive autonome DELETE, donnée logique source
  préservée, fsync et publication exclusive par hard link, sans écraser un
  fichier. Reçu chemin/empreinte/SID et archive_only ; aucun secret brut stdout.
  Checkpoints/récupération peuvent modifier la représentation physique source.
- Restore : SHA-256 attendu avant mutation et sous verrou de l'archive autonome,
  nouvelle copie privée, tous comptes désactivés et jetons/cookies révoqués.
  Anciens mots de passe invalidés : hashes non-admin retirés, hashes admin
  remplacés par des secrets aléatoires distincts inconnus, sans délivrance ;
  comptes/rôles existants préservés. Récupération OS avec nouveau secret pour
  un administrateur puis nouveaux secrets avant réactivation des autres.
  Audit identity.restore-local avec SID natif et empreinte d'archive ; état
  désactivé/révocations/hashes revérifiés après l'audit avant commit/publication.
  Trigger réactivant un ancien credential ou audit refusé : copie non publiée.
- Quatorze nouveaux cas : cycle source DELETE/WAL, ancienne auth refusée même
  après simple réactivation du compte, récupération/nouvelle connexion admise,
  source/archive logiques préservées, mauvaise empreinte sans mutation des
  permissions cible, destination occupée jamais remplacée, lecteur actif refusé,
  audit/trigger défaillants et échec avant copie conservant seulement un stage
  privé, confirmations CLI et stdout sans secrets. Deux workers os._exit avant
  audit de récupération DELETE/WAL : réouverture rw, intégrité et rollback.
  Un worker interrompu avant audit de restore : aucun chemin final publié.
- **14 nouveaux tests réussis en 121,53 s**, puis **43 tests distincts réussis
  en 240,32 s**, sauvegarde/arrêts + récupération + CLI ; racines LOCAL/DATA
  temporaires avant imports et propres aux sous-processus. Dépendances Argon2
  de recette isolées. Trace finale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-backup-regression-b586b21a1b4f4c278ab12ae0e679c17f/tests.txt.
  Les passages se recouvrent ; ni 69 tests distincts ni toute la gate CI
  requalifiée annoncés. CI étendue au quinzième fichier, résultat distant absent.
- Wheel 10.2.0 Python 3.13 construit sur copie avec outils temporaires : modules
  backup/recovery/private_store et PS1 exacts, puis chaîne sauvegarde/restore/
  récupération/reconnexion réussie depuis le paquet extrait. Preuve :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-identity-backup-wheel-88ca1f6013da48929f6775f0f2eee22c/qualification.json.
  AST/YAML/espaces et racines avant pytest vérifiés ; diff d'espacement des
  fichiers suivis concernés sans erreur. [Protocole](sauvegarde-identite-2026-10-03.md),
  plan et fiche v16 actualisés : **8 198/12 000 octets**, hash concordant, sans
  avertissement ; ce plafond ne mesure ni tokens ni économie effective.
- Limites : identité uniquement, pas base métier/runs/artefacts/PostgreSQL ;
  vraie console, superviseur/arrêt/activation réels, compte de service/second
  compte OS, restauration sur autre poste, droits des parents, chiffrement et
  panne physique restent ouverts. Les stages d'erreur restent privés pour
  inspection et ne doivent jamais servir de magasin actif. Le fsync de fichier
  ne qualifie pas la persistance du lien face à une panne de volume. SQLite de
  recette non corrigé pour le défaut WAL concurrent : gate d'activation ouverte.
  Aucune donnée/permission active, Dropbox ou index RepoWise modifié. L4/L9 et
  automatisation ouverts. Prochaine priorité : isolation des autres ressources/
  canaux et préparation PostgreSQL, avec qualification active de maintenance
  conservée comme gate distincte de ces fixtures.

## L0/L9 — Racines configurées sans redirection silencieuse

- Reprise : contexte MCP v16 **8 198/12 000 octets**, décisions/omissions et
  fraîcheur chargées ; statut historique inchangé. RepoWise MemoryService :
  correspondance confrontée au code, index de neuf jours/mock, recherches
  globales non ouvertes. État Git, derniers résultats, résolveurs et tests relus.
  Python de recette 3.13.3 présent. Référence avant édition : **15 tests réussis
  en 28,50 s**, sessions/projets/scanner sur racines temporaires existantes.
- Défaut découvert en préparant l'isolation des autres ressources : une racine
  DATA explicite inexistante ou contenant le motif historique DEV_CORE_DATA
  pouvait être remplacée par la découverte Dropbox ; une racine LOCAL aux
  parents absents par le dossier AppData. Un échec de création pouvait donc
  ouvrir une base différente. Reproduction finale avant correctif : **10 échecs,
  4 réussites** sur 14 cas, avec Dropbox/AppData entièrement factices. Un premier
  essai avait deux cas NUL non valides : l'OS refuse cette valeur avant le
  résolveur ; ils ont été retirés, sans les présenter comme défauts du produit.
- db.py : validation commune des variables définies, valeurs vides/blanches
  et fichiers refusés. DATA résolu sans créer de dossier ni lire les métadonnées
  Dropbox ; LOCAL crée ses parents explicites et propage les erreurs. Aucun
  remplacement d'une variable définie. L'autodétection historique reste possible
  seulement quand elle est absente ; chemins relatifs compatibles.
- Quatorze cas ajoutés : racine DATA existante/neuve/motif historique, valeurs
  invalides/fichiers, base par défaut dans LOCAL imbriqué, parent fichier et
  permission refusée sans base de repli, défauts Windows avec métadonnées factices.
  **45 tests distincts réussis en 91,99 s**, avec isolation/sessions/scanner et
  16 tests HTTP individuels ; un avertissement Starlette/httpx déjà connu.
  Les passages se recouvrent : ni 60 tests distincts ni toute la gate identité
  ne sont annoncés. Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-roots-regression-a7fb40e482634e9ca85b0a60e80a0108/tests.txt.
- CI : nouvelle gate des racines/isolation sur dossiers temporaires créés avant
  imports, et création explicite des dossiers de la gate identité. Résultat
  distant absent. Profil local et plan actualisés ; aucune configuration active
  chargée, aucun service redémarré, aucune donnée active/Dropbox/index réel testé.
- Limites : résolveurs devcore_engine.db uniquement, pas contrôle des autres
  scripts ni de la propagation d'environnement de tous les services. Une racine
  explicitement située dans Dropbox/réseau ou traversant une jonction n'est pas
  interdite par ce correctif ; il ne remplace pas les ACL ni la séparation des
  données. Anciennes valeurs configurées obsolètes/vides à corriger avant lancement.
  L4/L9 et automatisation restent ouverts. Prochaine priorité : contexte/mémoire
  par projet avec autorisation serveur, autres ressources/canaux et PostgreSQL.
- Vérifications finales : AST Python et YAML CI chargés, ordre des variables et
  création des deux racines avant pytest vérifié ; espaces des fichiers concernés
  sans erreur (avertissements Git LF/CRLF). Fiche v17 : **8 530/12 000 octets**,
  SHA-256 concordant, aucun avertissement ; octets UTF-8, pas tokens ni économie.
  SHA-256 de la trace tests :
  CEE514158EEFAE85E035B1BA7947F5E50F6F045F4EE114E32AB96F379D7815B7.

## L4/L7 — Fiche et décisions accessibles par projet autorisé en HTTP

- Reprise : contexte MCP v17 **8 530/12 000 octets** avec décisions applicables,
  sans avertissement. Statut historique T-388/384 sur 389, pas une qualification
  du plan. RepoWise ne connaît pas load_project_context : voisins non retenus,
  index de neuf jours/mock, commit aligné sans couvrir les changements locaux.
  État Git, journal, modules identité/sessions/lecteur et tests relus ; Python
  de recette présent. Référence : **33 réussis, un ignoré en 70,14 s** sur racines
  LOCAL/DATA temporaires existantes avant imports ; lien symbolique non privilégié.
- Capacité context.read ajoutée aux rôles de projet reader/contributor/owner.
  L'émission conserve une liste explicite d'actions : anciens jetons/cookies
  limités aux tâches ne gagnent rien, même après promotion. Nouvelles connexions
  par mot de passe prennent les capacités courantes du rôle. Sessions décrivent
  les droits courants ; l'échange Bearer→cookie continue d'exiger task.read.
  Un Bearer de seul contexte est utilisable directement, sans Origin navigateur.
- GET /api/project/context ajouté seulement au profil individual, admission
  context.read et projet côté middleware avant accès aux métadonnées. Compte,
  appartenance, expiration et révocation revérifiés à chaque admission ; cookies
  liés à l'origine/projet. Jetons administratifs refusés. Profil legacy interdit
  cette route ; Qdrant/MemoryService et recherches globales restent fermés.
- registered_project_context : connexion métier ro/query_only sans création ou
  migration, SELECT paramétré sur le projet admis, racine enregistrée absolue et
  existante, répertoire résolu docs/project-context contenu dans cette racine.
  Lecteur existant impose manifeste du projet, confinement des fichiers et
  décisions obligatoires/remplacements. Aucun chemin client ni repli global.
  Erreurs de source génériques 503 sans chemins/contenus étrangers ; budget
  obligatoire insuffisant 413 sans contexte partiel ; arguments hors bornes 422.
- Plafond DEVCORE_HTTP_CONTEXT_MAX_BYTES serveur (12 000 par défaut, validé
  256–65 536 au démarrage), budget omis = plafond, augmentation client refusée.
  Corps succès = encode_context + newline UTF-8 exact, Content-Length concordant,
  no-store ; provenance, omissions et avertissements conservés. Ce plafond exclut
  en-têtes/protocole et ne mesure pas les tokens. Route synchrone en pool FastAPI,
  lookup d'identité en thread : second projet et status répondent sous une seconde
  pendant une lecture alpha volontairement bloquée, sans annoncer une charge SLA.
- Vingt cas HTTP nouveaux. Premier passage : 17 réussites et deux échecs de
  fixtures (with sqlite3.Connection ne ferme pas la connexion, WAL/checkpoint et
  verrou Windows). Fixtures corrigées avec closing et DELETE pour comparaison
  physique/absence de base ; pas de correction de production induite par ces
  deux échecs. Régression : **76 réussis, un ignoré en 247,22 s** sur neuf fichiers
  identité/sessions/mots de passe/HTTP/lecteur ; avertissement Starlette/httpx connu.
  Puis un cas WAL dédié : **une réussite, 19 désélectionnés en 5,69 s**, registre
  committé visible sans checkpoint, fichier principal/WAL inchangés tant que le
  writer reste ouvert. **77 réussites distinctes**, pas addition des références.
  Jonction NTFS vers le dépôt beta refusée ; test de lien symbolique du lecteur
  existant ignoré faute de privilège. Ce cas WAL n'est pas un test du défaut WAL
  concurrent signalé précédemment et ne ferme pas sa gate de runtime corrigé.
- Traces :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-context-regression-4f87b41f7a49422baa58a90651733fde/tests.txt
  (SHA-256 20E9A17B82AC6432463266E3C9717ECFD4961EB28F64C6784A2D46B53A43C0D9) ;
  C:/Users/Administrateur/AppData/Local/Temp/devcore-context-wal-2d383d08596b4c1792df57a13df3672a/tests.txt.
- CI : gate dédiée lecteur/HTTP avec deux racines créées avant pytest ; gates
  existantes d'identité conservées, résultat distant absent. AST/YAML et ordre
  des racines contrôlés ; découverte setuptools devcore_engine* vérifiée, wheel
  non reconstruit pour cette avance. Matrices de droits, exemple non actif,
  contrat HTTP, plan et fiche actualisés. Aucun service/configuration active
  basculé ; aucune donnée active, Dropbox ou index réel utilisé comme fixture.
- Limites : racines enregistrées et auteurs des fiches de confiance, contrôle
  de résolution non sandbox contre mutations OS pendant la lecture. Révocation
  vérifiée à l'admission, pas annulation d'une requête déjà admise. Lectures SQL
  ne qualifient pas les permissions/effets physiques des sidecars dans chaque
  installation WAL. Interface fiche et injection automatique des clients,
  compteur tokens/comparaison qualité, conversation neuve, ACL MCP personnelles,
  mémoire/Qdrant, autres ressources/canaux et PostgreSQL restent ouverts. Pas de
  critère L4/L7/L9 global coché, automatisation conservée. Prochaine priorité :
  raccordement des clients au contexte autorisé et isolation des autres canaux.
- Vérification finale après le cas WAL : AST/YAML et ordre des racines repassés,
  espaces des nouvelles sources et diff ciblé sans erreur ; avertissements
  Git LF/CRLF uniquement. Fiche v18 **9 036/12 000 octets**, empreinte concordante,
  sans avertissement. SHA-256 trace WAL :
  A856ABE0D6CDC57C92285CD6ED2BE8ED5C51F6A3FEE0EC73FDE114F242CD0180.

## L4/L7 — Reprise de fiche et décisions dans la page individuelle

- Reprise : contexte MCP v18 **9 036/12 000 octets**, décisions en vigueur,
  provenance/omissions chargées, sans avertissement ; statut historique inchangé.
  RepoWise ne connaît pas project_tasks.js, index de neuf jours/mock et sans
  sémantique ; sources locales retenues. État Git, dernier journal, page/script,
  tests Node et contrats HTTP relus avant édition. Python de recette présent,
  Node 24.14.0. Référence : **11 scénarios JavaScript réussis en 612,31 ms**.
- /project charge automatiquement fiche/décisions à la connexion/reprise si
  context.read est présent, puis formulaire de sujet pour les décisions
  facultatives. Anciens cookies de tâches : pas d'appel contexte, liste utilisable.
  Texte seulement (y compris sources et HTML/Markdown), justification/validation,
  date ou « non établie », statut en vigueur/proposé, omissions/remplacements,
  avertissements et revue déclarée. Aucune interprétation de proposition comme
  décision en vigueur, aucun lien source exécuté ni cache de stockage navigateur.
- Client vérifie projet, schéma, états/obligations de décisions, provenance,
  diagnostics et **longueur exacte UTF-8** du corps, avec budget serveur borné
  256–65 536. Aucun gain en tokens annoncé. Lecture indépendante des tâches :
  boutons disponibles quand elle est lente. Budget/source indisponible : contexte
  précédent effacé, tâches conservées ; identité refusée : toute vue privée effacée.
  AbortController et génération liée au projet/utilisateur/CSRF empêchent une
  réponse tardive de repeupler une session après refresh/logout/autre compte.
- **19 scénarios Node réussis**, dont huit nouveaux : reprise/cookies seuls,
  compatibilité sans droit contexte, lecture lente et abandon de réponse obsolète,
  approfondissement/proposition/diagnostics, budget/source indisponible, réponse
  étrangère/remplacée/obligatoire proposée/budget/provenance invalides, révocation,
  changement de compte avec réponse tardive. La date et les types de provenance
  ont été ajoutés ensuite et validés dans la régression finale : **166,65 ms**.
  Les autres passages se recouvrent ; pas addition de leurs comptes de tests.
  Trace finale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-context-browser-541518a6e18f45c6ac05a84807db4921/node-tests.txt.
- **26 tests HTTP réussis en 128,98 s**, contexte individuel et shell/sessions,
  LOCAL/DATA temporaires créés avant imports, Argon2 de recette isolé ; warning
  Starlette/httpx déjà connu. Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-context-ui-http-3ec595ddb69943f787dad84b5480d368/tests.txt,
  SHA-256 F12A42EE921E411226747F26B13662DF9EE32D009A091DC59568876041B8D920.
- Compétence computer-use appliquée, contrôle navigateur via cua_repl disponible
  (surface native désactivée). Serveur Uvicorn temporaire lié à 127.0.0.1,
  port dynamique et données synthétiques. Premier port : origine non déclarée,
  refus 403 attendu ; fixture corrigée pour autoriser uniquement son origine.
  Middleware de recette isolant le nom de cookie protège les sessions localhost
  existantes : seuls cookies de fixture transmis, nom applicatif préservé dedans,
  alias dédié en sortie. Aucun assouplissement de la politique en production.
- Parcours réel sur 127.0.0.1:61025 : Alice/alpha, fiche obligatoire **858 octets**,
  query worker, proposition visible **1 056 octets**, rechargement reprenant fiche
  courte, logout effaçant contexte/tâches, Bob/beta avec fiche **854 octets**, puis
  logout. Affichage vérifié visuellement, mots de passe de fixture non affichés.
  Date et derniers contrôles de types ajoutés après ce parcours : testés par Node,
  sans prétendre refaire la vérification visuelle de ces deux derniers ajustements.
  Un seul navigateur avec comptes successifs, pas deux profils indépendants.
  Onglet fermé, processus vérifié par son chemin avant arrêt, port fermé.
  État final : alpha/beta in_progress/version 1, zéro session navigateur non
  révoquée. Reçu :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-context-browser-541518a6e18f45c6ac05a84807db4921/qualification.json.
- Page/script livrés restent des fichiers du dépôt ; aucun runtime actif basculé,
  magasin actif/Dropbox/index RepoWise réel utilisé. Gate Node existante reprend
  les cas ajoutés, pas de nouvelle gate ni résultat distant. Contrat de contexte,
  plan et fiche actualisés. Limites : UI uniquement, pas injection automatique
  d'une conversation IA, mémoire globale/ACL MCP personnelles, compteur réel de
  tokens/comparaison qualité, deux profils/cross-site/HTTPS et activation encore
  ouverts. L4/L7/L9 et automatisation ouverts. Prochaine priorité : contexte
  authentifié des autres clients et isolation des canaux encore globaux.
- Vérifications finales : syntaxe Node, formulaires HTML non imbriqués,
  identifiants uniques et tous éléments du script liés au shell contrôlés ;
  espaces des fichiers concernés sans erreur. Fiche v19 **9 284/12 000 octets**,
  empreinte concordante, sans avertissement. SHA-256 trace Node :
  DAD3AAF1C65C239B7E755E4B31E7326E8CADD323F0D69BC1B9E35BF4760FD941.

## L2/L4/L7 — Contexte MCP individuel via la même API

- Reprise via devcore_project_context : fiche v19, 9 284/12 000 octets UTF-8,
  décisions obligatoires/provenance sans avertissement ; task_status historique
  T-388 384/389 consulté, sans le prendre pour une qualification du plan.
  Git sale préservé, dernier journal, contrats MCP/HTTP et tests relus.
  RepoWise ciblé sur server.py : commit b2349de865c2 concordant, index neuf jours,
  mock/sémantique désactivée et changements locaux non couverts ; code réel vérifié.
- Baseline stdio/lecteur : **13 réussis, 1 ignoré, 18,13 s**. Premier appel avait
  nommé un chemin de test inexistant : aucun test exécuté, chemin corrigé.
  Python 3.13 de recette présent ; LOCAL/DATA temporaires créés avant imports.
  Paquets Argon2 de recette isolés pour les fixtures HTTP d'identité.
- Nouveau profil explicite DEVCORE_MCP_AUTH_PROFILE=individual, inconnu refusé
  avant import des adaptateurs. Il expose seulement devcore_project_context,
  appelle GET /api/project/context, n'importe ni hooks ni adaptateurs historiques
  et n'accède à aucune base métier/identité du client. DEVCORE_MCP_READ_ONLY=0
  ne rouvre aucun autre outil. Le profil historique actif reste inchangé.
- Origine API explicite : HTTP loopback seulement, HTTPS avec vérification
  Python standard ailleurs ; pas de proxy hérité, cookies, redirection, retry
  ou repli vers une fiche/base locale. Le client lit un fichier de credential
  individuel absolu, contrôle NTFS avant lecture, limite à 4 096 octets et refuse
  token invalide/injection d'en-tête. ACL et lecture répétées à chaque appel,
  permettant rotation ; secret jamais envoyé dans les arguments MCP, TOML,
  environnement, stdout ou hooks. Autres OS fermés pour ce profil de recette.
- Projet lié explicitement avant lecture du secret, puis admission individuelle
  côté API : compte, scope context.read, rôle/appartenance, expiration/révocation.
  Les anciens jetons de tâches ne gagnent pas cette action. Corps distant borné
  à budget+1, JSON canonique UTF-8 et mesure exacte contrôlés, projet/décisions/
  provenance/omissions/fraîcheur validés ; décisions remplacées ou propositions
  obligatoires refusées. Un seul bloc texte, aucune duplication structurée.
  Erreurs HTTP traduites en codes sans corps distant, chemin privé ou contexte
  partiel. Timeout socket 1–30 s, distinct du contrôle NTFS jusqu'à 15 s ; pas un
  délai global strict. Appel hors boucle asyncio, sans cancellation garantie du thread.
- **35 nouveaux cas qualifiés**, dont deux vrais parcours stdio → Uvicorn HTTP
  sur port dynamique avec fichiers NTFS synthétiques : alpha/beta, refus croisé
  local et credential étranger côté API, rotation, révocation, retrait d'adhésion,
  désactivation/expiration, anciens scopes, budget insuffisant, outils fermés.
  Bases client volontairement invalides jamais ouvertes ; aucun fichier hook
  ou base créé, cartes et base métier serveur byte-identiques. Une lecture alpha
  bloquée laisse list_tools du même MCP répondre sous 1 s et beta sous 3 s.
  Tests de credential manquant/public/invalide/trop gros, URL/config invalide,
  redirect 307 sans suivi, réponses étrangères/invalides/tronquées/compressées,
  diagnostics erronés et timeout sans repli. API/ports temporaires arrêtés à la sortie.
- Première suite : 42 réussis, un ignoré, un échec (78,31 s). Le SDK validait
  certains arguments avant l'adaptateur et renvoyait un texte libre ; validation
  désormais faite par l'adaptateur individuel avant secret/réseau, erreurs JSON.
  Validation SDK historique conservée. Suite après correction : **52 réussis,
  1 ignoré, 1 échec en 109,16 s**. Échec historique du seuil pré-hook 50 ms :
  88,05 ms observées. Contrôle séparé des hooks : **6 réussis en 0,95 s**, sans
  changer code ni seuil ; variabilité non résolue, pas de suite globale verte
  revendiquée. Timeout ajouté ensuite : **1 réussi en 2,87 s**. Au total,
  **54 cas distincts réussis et un ignoré dans trois exécutions finales** ;
  ignoré : privilège symlink indisponible. Warning Starlette/httpx connu.
- Traces de recette (temporaires, aucun index RepoWise/Dropbox actif utilisé) :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-http-final-b771db88f1e04596975d19e4e4dc1824/tests.txt,
  SHA-256 5C821F6E7784CE8279DD9EA271C45343313E75FF91F88E63548B64447A8E30CE ;
  C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-hooks-recheck-ad379eb96e64452bb6e051b0c2733c62/tests.txt,
  SHA-256 6BCF28BEA98BE883D12C3B62F8324552055DF2CF3D9032FCF4F75FD751A3F144 ;
  C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-timeout-cbdac6b1bd2d444797c9c6a96a637290/tests.txt,
  SHA-256 A252503792D2139CEC7024A8229779F81CBFD736791FF08702F6177FB2012F54.
- Exemple mcp-individual.example.toml sans secret et contrat README ajoutés,
  gate CI Windows isolée ajoutée (6 min), sans résultat CI distant revendiqué.
  AST Python, TOML et espaces des nouveaux fichiers contrôlés ; git diff --check
  des fichiers concernés sans erreur. Contrôle global d'espaces avait signalé
  quatre lignes historiques du serveur, inchangées. Fiche v20 : **9 808/12 000
  octets**, empreinte concordante, zéro avertissement. Mise à jour initiale de
  l'empreinte refusée par le lecteur (substitution regex ambiguë), réparée puis
  JSON/hash et sortie obligatoire revérifiés, sans substituer un extrait.
- Limites : uniquement contexte MCP, aucun service/config actif basculé ni compte
  réel provisionné. API/racines/auteurs et compte OS de confiance ; contrôle ACL
  ponctuel, pas sandbox contre remplacement de fichiers par un acteur OS.
  HTTPS distant, service Windows, délais globaux/cancellation, audit de lecture,
  autres outils/canaux ACL, conversation IA neuve et gain effectif de tokens
  ouverts. Plan L2/L4/L7/L9 et automatisation restent ouverts. Prochaine priorité :
  admission des autres clients/opérations vers l'API commune et qualification
  de la reprise en conversation neuve, sans annoncer d'économie non mesurée.

## L2/L4 — Tâches MCP individuelles raccordées à l'API

- Reprise obligatoire par MCP : fiche v20 **9 808/12 000 octets**, décisions
  applicables/provenance sans avertissement. task_status historique T-388
  384/389, sans le confondre avec les critères du plan. Git sale préservé,
  dernier journal, code MCP/HTTP et tests relus avant modification. RepoWise
  ciblé sur services/task_service.py : commit b2349de865c2 concordant, index
  neuf jours/mock/sémantique désactivée ; modifications locales confrontées au code.
- Baseline des parcours HTTP individuels et auteurs/audit : **22 tests réussis,
  83,88 s**. Python 3.13 de recette vérifié, LOCAL/DATA temporaires créés avant
  imports et subprocess ; Argon2 de recette isolé. Aucun magasin actif/Dropbox
  ni index RepoWise réel utilisé comme fixture.
- Nouveau adaptateur individual_tasks.py réutilisant le transport protégé du
  contexte. DEVCORE_MCP_TASK_ACCESS=disabled par défaut, read pour liste, write
  pour liste/clôture. Configuration inconnue : démarrage refusé ; READ_ONLY=1
  ramène write à read et ferme la clôture avant lecture du credential. Mode
  annoncé distinct des droits : API exige task.read ou task.mutate à chaque
  admission, indépendamment de context.read. Autres outils globaux fermés.
- devcore_task_status : GET /api/dashboard/tasks, page limit 1–100/offset,
  réception distante limitée à 128 Kio. Lignes du projet, identifiants uniques,
  statuts/versions contrôlés avant restitution ; uniquement id/project/title/
  status/version, champs supplémentaires abandonnés. Page pleine signifie
  page_may_have_more, sans calcul de total ni parcours implicite de toutes les pages.
  Ancien schéma lisible avec version null, sans migration à la consultation.
- devcore_task_done : POST /api/done, projet/tâche nommée/version attendue
  obligatoire ; seuls project/id/expected_version envoyés. actor, user_id,
  secret et autres arguments libres refusés avant lecture du fichier NTFS.
  Auteur et trace viennent de l'admission HTTP ; audit/tâche dans la même
  transaction existante. Conflits 409 distingués (stale_task_version ou
  task_version_unavailable si reconnus), sans exposer le message distant.
  Aucun choix implicite, activation de la suivante, retry ou accès base côté client.
- Le succès de cette route reste un accusé, pas une ligne/version committée :
  réponse MCP avec requested_task_id, expected_version, acknowledged et
  refresh_required, sans inventer une nouvelle version. Perte de transport,
  réponse invalide, redirection ou erreur serveur : mutation_outcome_unknown,
  état à relire avant toute nouvelle action. Pas de repli/succès supposé.
  Une requête déjà committée peut échouer au transport ; l'API publie encore
  après commit, donc une erreur serveur peut aussi avoir un résultat incertain.
  Publication durable/outbox et réconciliation générale restent ouverts.
- Tous les outils individuels renvoient un bloc texte JSON unique ; plus de
  structuredContent dupliquant les tâches. Mesure exacte du contexte inchangée.
  La borne 128 Kio concerne la réception HTTP des tâches, pas les tokens/modèle
  ni toutes les enveloppes MCP. Protection NTFS, vérification TLS standard,
  absence de proxy/redirection/cookie/retry et timeout socket conservés.
- **21 nouveaux tests de tâches** : vrais sous-processus MCP → API temporaire,
  pagination, alpha/beta, credential étranger/lecteur, anciens scopes sans
  contexte, déclassement/révocation, version périmée, absence de tâche/version,
  champs d'auteur libres, audit et versions des deux projets simultanés.
  Deux clôtures concurrentes de la même tâche/version : un accusé, un conflit,
  une version incrémentée, un audit et un événement. La suivante reste todo.
  Racines MCP avec base volontairement invalide inchangées, aucun hook créé.
  Réponses étrangères/dupliquées/trop grosses/invalide-version rejetées, champs
  supplémentaires supprimés ; erreurs/redirect/déconnexion sans retry.
- Test après commit et avant réponse : task done/version 2, audit unique et
  événement unique ; socket expirée → résultat incertain, puis lecture autorisée
  retrouvant l'état, sans seconde écriture. Ancien schéma sans version : lecture
  réussie, clôture conditionnelle refusée 409, base byte-identique avant/après.
  Nouveau cas de démarrage avec TASK_ACCESS inconnu également qualifié.
- Première suite : 60 réussis, un échec, 154,32 s ; assertion du test utilisait
  version_after alors que le contrat audit est after.version. Test corrigé,
  aucun changement du schéma d'audit. Suite finale MCP tâches/contexte/protocole :
  **63 réussis en 167,29 s**. Ancien schéma ajouté séparément : **1 réussi en
  9,81 s**. Avec baseline HTTP : **86 cas distincts réussis dans trois exécutions**.
  Warning Starlette/httpx connu. Hooks historiques non rejoués ici : seuil 50 ms
  variable déjà consigné, conservé dans la gate CI ; pas de CI globale verte annoncée.
- Traces temporaires :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-tasks-baseline-b07686baeb894f0ca3051fc023e5022b/tests.txt,
  SHA-256 98F66C1DE1599CA2D063D46A46D59F701CD4524892EDE1EA38279ECB8AF15BFD ;
  C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-tasks-final-30182824b21e4f948d24eda7e76c76d7/tests.txt,
  SHA-256 3A2252C1CC52EA93F1CFB0EB889F4003918C16CAB37CEB272E5A9A5EFEBBBE39 ;
  C:/Users/Administrateur/AppData/Local/Temp/devcore-mcp-old-schema-5830f53f52d14c709a28a08c0bae10b7/tests.txt,
  SHA-256 EF286FED472FB68DDF7493838C299D7502D3609B594A87C0ABC86B4F7C6DE6AA.
- Gate MCP CI existante étendue, exemples TOML distincts contexte/tâches de
  lecture documentés sans secret ; configuration active non changée. AST/TOML,
  espaces nouveaux fichiers et diff concernés vérifiés. Fiche v21 **10 228/
  12 000 octets**, empreinte concordante et zéro avertissement.
- Limites : recette uniquement ; compte réel/service Windows, HTTPS distant,
  délais globaux/cancellation, autres opérations/CLI, consultation d'audit,
  outbox/worker, PostgreSQL et migration/bascule actifs ouverts. Ces courses
  temporaires ne qualifient pas le correctif SQLite WAL/checkpoints ni une charge
  de production. Nouvelle conversation IA et économie réelle de tokens ouvertes.
  Aucun critère global L2/L4/L9 fermé ; automatisation maintenue. Prochaine étape :
  clients restants et reprise IA qualifiée sur contexte de recette, puis mesures.

## L2/L4 — CLI individuelle et transport partagé avec MCP

- Reprise par MCP : fiche v21 **10 228/12 000 octets UTF-8**, décisions
  obligatoires/provenance sans avertissement. Statut historique T-388 384/389,
  sans qualification des lots. Git sale préservé ; journal, clients et tests
  relus avant modification. RepoWise ciblé sur Scripts/dc.py : HEAD/index
  b2349de865c2 concordants, index neuf jours/mock/sémantique désactivée ; les
  changements locaux sont confrontés au code. Python 3.13 de recette présent.
- Baseline protocole stdio : **7 tests réussis en 17,95 s**. Toutes les
  exécutions utilisent LOCAL/DATA temporaires créés avant imports/processus ;
  aucun magasin actif, Dropbox ou index RepoWise réel utilisé comme fixture.
- Transports individual_context et individual_tasks déplacés dans
  devcore_engine/clients ; copies vérifiées identiques avant remplacement des
  anciens modules MCP par des imports de compatibilité. Même classe et mêmes
  contrôles utilisés par les deux clients, sans duplication du transport.
  Package moteur déjà inclus par setuptools ; aucune dépendance ajoutée.
- Nouveau Scripts/individual_project_client.py : commandes context, tasks et
  done. Origine API, chemin absolu du credential et projet obligatoires,
  sans découverte d'instance, credential en variable/argv ou base locale.
  Les options globales précèdent la commande. Le choix de commande demande
  context.read, task.read ou task.mutate à l'API ; les flags d'exposition MCP
  ne constituent pas une autorisation CLI. Transport existant conservé :
  fichier NTFS privé, TLS standard, pas de proxy/cookie/redirection/retry.
- Une ligne JSON compacte UTF-8, mesure exacte du contexte inchangée. Sortie
  0 pour succès, 1 pour refus/conflit/budget/résultat incertain, 2 pour arguments
  ou configuration invalides. Diagnostics de parsing/configuration génériques
  sans echo de secret, argument ou chemin. Aucun paramètre token/mot de passe.
  Clôture nommée avec version attendue obligatoire ; accusé sans version nouvelle
  inventée, refresh_required et relecture après succès ou résultat incertain.
- **14 nouveaux cas CLI** : vrais sous-processus vers API temporaire,
  contexte borné et décisions remplacées exclues, budget insuffisant, accès
  étranger, page/version, clôture, conflit, nouvelle lecture puis révocation.
  Équivalence exacte CLI/MCP pour page et conflit. Parse/config invalides,
  credential absent/public refusés sans divulgation. Contexte et liste sont
  aussi exécutés sous python -I -S, sans MCP/FastAPI ni site-packages côté CLI.
  Base locale volontairement invalide inchangée, aucun fichier métier créé.
- Réponse CLI retardée après commit : timeout de transport donne
  mutation_outcome_unknown ; relecture trouve done/version 2, un audit et
  un événement seulement. Aucun réessai ni seconde écriture, projet beta intact.
- Suite finale CLI/contexte/tâches/protocole : **78 tests réussis en 200,25 s**
  (14 + 36 + 21 + 7), aucun ignoré, warning Starlette/httpx connu. Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-individual-cli-5e515b42727e4f6aad23622962ef0033/tests.txt,
  SHA-256 421B95490E86D5976BB58C3BE77AE28C5337917C2104A3EE58B32496DB1ED668.
  Hooks historiques non rejoués : variance du seuil 50 ms déjà consignée,
  gate CI conservée ; aucune CI globale ou distante verte annoncée.
- Gate MCP CI étendue au test CLI, procédure et exemples explicites ajoutés
  au README du contexte. Fiche v22 **10 549/12 000 octets**, empreinte concordante
  et zéro avertissement via lecteur local ; registre/décisions inchangés.
  AST, espaces des nouveaux fichiers et diff concernés vérifiés.
- Limites : CLI explicite de recette ; dc/PowerShell historiques, autres
  opérations et configuration active non reroutés. Activation réelle,
  compte de service, HTTPS distant, timeout global/cancellation, consultation
  d'audit, outbox/worker, PostgreSQL et bascule restent ouverts. Les tests de
  concurrence ne qualifient pas SQLite WAL/checkpoints ni la charge réelle.
  Reprise en conversation IA neuve et économie effective de tokens ouvertes.
  Aucun critère global L2/L4/L9 fermé ; automatisation maintenue.

## L2/L4 — Commande dc individual, sources et console installée

- Reprise par MCP : fiche v22 **10 549/12 000 octets**, décisions obligatoires
  sans avertissement ; task_status historique T-388 384/389. Git sale préservé,
  journal, dispatchers et tests relus avant modification. RepoWise ciblé sur
  devcore_engine/cli.py : commit b2349de865c2 concordant, index neuf jours/mock,
  sémantique désactivée ; code local vérifié. Python 3.13 de recette présent.
- Baseline CLI individuelle, ancien dc next SQL et tâches CLI : **24 tests
  réussis en 52,91 s**. Racines LOCAL/DATA créées avant imports/processus,
  toujours temporaires ; aucune donnée active/Dropbox ni index réel en fixture.
- Parser et orchestration CLI déplacés dans le package
  devcore_engine.clients.individual_cli. Script individuel réduit à une façade
  source ; transport partagé et contrôles d'admission inchangés. Accessible
  par dc individual, python -m devcore_engine.cli individual,
  python -m devcore_engine individual et Scripts/dc.py individual.
  Dispatch avant les imports de services locaux, résolveurs et migrateur.
- Scripts/dc.ps1 individual utilise le script voisin et le Python sélectionné,
  avant résolution de plateforme. Ne source pas platform_version.ps1, dont le
  bootstrap historique peut rechercher Dropbox et modifier une variable User.
  Arguments transmis sans interprétation métier, UTF-8 et code de sortie
  conservés. Le parcours individuel exige toujours origine API, fichier privé
  et projet ; aucune découverte de credential/instance ni repli local.
- **Neuf nouveaux cas** : quatre parcours réels modules/package/script/PowerShell
  vérifient égalité du contexte avec la CLI directe, mesure exacte UTF-8,
  accès étranger refusé, page/version, clôture, conflit, révocation, beta intact
  et audit Alice unique. Trois processus -I -S interdisent explicitement les
  imports DB/migration/mémoire/tâches/événements/paths/MCP/FastAPI/sqlite-vec ;
  erreurs génériques sans echo d'un faux secret, racines inchangées.
- Contrôle PowerShell avec bootstrap volontairement interdit : arguments avec
  espace et code 2 transmis, aucun accès au bootstrap ni écriture métier.
  Ces quatre contrôles de dispatch réussissent séparément en **2,58 s**.
- Wheel construit sur copie temporaire minimale, installé dans un nouveau venv
  sans dépendances serveur. Console dc.exe utilisée avec PYTHONPATH vide,
  contexte/liste/clôture réels vers API temporaire, un audit serveur ; absence
  de MCP/FastAPI/sqlite-vec/Argon2 vérifiée dans l'installation. Le helper NTFS
  empaqueté est donc utilisé par un client réellement installé, pas les sources.
- Première suite : **32 réussis, un échec en 110,46 s**. La recette ne contient
  ni pip ni setuptools ; hypothèse erronée du test de construction. Test corrigé
  pour appeler le backend fourni dans un target temporaire distinct. Venv de
  qualification créé sans pip puis ensurepip exécuté seulement dans ce venv ;
  installation du wheel --no-index --no-deps. Aucun runtime actif modifié.
  Cas wheel corrigé : **1 réussi en 30,39 s**.
- Outillage setuptools 84.0.0 installé d'abord en target temporaire, puis
  réinstallation vérifiée avec --require-hashes et --only-binary via le nouveau
  requirements-build-test.lock. Empreinte du wheel PyPI :
  51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670.
  La CI provisionne le même target isolé, expose DEVCORE_TEST_BUILD_TOOLS et
  passe sa gate MCP de six à huit minutes pour les nouveaux parcours.
- Suite finale sur outillage vérifié : **33 tests distincts réussis en 128,40 s**
  (23 CLI, dont neuf nouveaux, et dix tests de compatibilité locale), aucun
  ignoré. Warning Starlette/httpx connu ; aucun résultat CI distant annoncé.
  Trace finale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-dc-verified-225d4e4ec6294ea181818ebcb70f50da/tests.txt,
  SHA-256 556FAAF0BE198F0180592F40EC06059E2CD06DC54CE1F0D6C13D3114BD25EF75.
  Trace de l'échec de recette corrigé :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-dc-final-78c0a0801a3641f4baeb10f3c33a9ff9/tests.txt,
  SHA-256 171B9E5C8618BE1955B2CA0B5451F565A8AC1E29E0B0DEA9CBA9E64119BA115D.
- Fiche v23 **10 702/12 000 octets**, empreinte concordante, zéro avertissement ;
  décisions inchangées. Procédure et plan actualisés, AST de cinq fichiers,
  parsing PowerShell et diff d'espacement vérifiés. Configuration/runtime actifs
  non basculés, aucune dépendance de production ajoutée.
- Limites : individual est un parcours explicite ; les autres commandes
  historiques restent locales. Autres opérations/ACL, consultation d'audit,
  service Windows, HTTPS, timeout global, outbox/worker, PostgreSQL et bascule
  restent ouverts, ainsi que WAL/checkpoints. Reprise IA en conversation neuve
  et économie effective de tokens non qualifiées. Aucun critère global L2/L4/L9
  fermé ; automatisation maintenue. Suite : compléter les opérations individuelles
  restantes et la qualification de reprise IA selon les priorités du plan.

## L2/L4 — Suppression logique individuelle CLI/MCP

- Reprise par MCP : fiche v23 **10 702/12 000 octets**, décisions obligatoires
  et provenance sans avertissement. task_status historique T-388 384/389,
  distinct du plan. Git sale et modifications existantes préservés ; journal,
  transport, admission DELETE, service/audit et tests relus avant modification.
  RepoWise ciblé sur Scripts/dashboard_api.py : HEAD/index b2349de865c2
  concordants, index neuf jours/mock/sémantique désactivée ; code local vérifié.
  Python 3.13 de recette présent. LOCAL/DATA temporaires créés avant tous les
  imports/processus ; aucune donnée active, Dropbox ou index réel en fixture.
- Baseline tâches MCP et admission/audit HTTP : **42 réussis, un échec en
  140,26 s**. L'échec était l'arrêt de l'API temporaire après le parcours :
  thread Uvicorn encore vivant à cinq secondes, log Windows Proactor reset
  10054. Fixture ajustée à un keepalive d'une seconde et une grâce d'arrêt de
  deux secondes ; assertion de fin réelle du thread conservée. Cas concerné
  rejoué : **1 réussi en 18,81 s**. Aucun réglage de service actif changé,
  ni garantie de cancellation/exécuteur de production déduite de ce correctif.
- Transport partagé admet un verbe interne explicite pour DELETE. Nouveau
  devcore_task_delete : projet configuré, tâche nommée et version positive
  obligatoires, aucun argument actor/user_id/secret/méthode libre. Requête
  DELETE /api/delete avec le même JSON project/id/expected_version et le
  même contrôle de credential NTFS, TLS, réponses bornées et refus de redirect.
- Exposition MCP séparée : DEVCORE_MCP_TASK_DELETE=0 par défaut, 1 seulement
  sur choix explicite, toute autre valeur refuse le démarrage. Même activée,
  suppression absente des modes disabled/read et write + READ_ONLY=1, refusée
  avant lecture du credential. write seul conserve les outils existants.
  Ce flag n'accorde aucune capacité : API exige toujours task.mutate et rôle
  autorisé sur le projet à chaque admission.
- CLI individuelle ajoute delete --task-id --expected-version, également
  depuis dc individual. Activation par cette commande explicite seulement ;
  fichier de credential/projet/origine requis, codes JSON/UTF-8 inchangés.
  Réutilisation de la route et du service existants : statut deleted conservant
  identité/historique, dépendances actives refusées, audit atomique avec auteur
  du principal, aucune nouvelle migration ou écriture directe client.
- Accusé avec refresh_required, sans version committée inventée. Perte/réponse
  invalide/redirect/erreur serveur : mutation_outcome_unknown, sans seconde
  écriture. Dépendance refusée : conflit générique ; version ancienne : conflit
  de version ; tâche déjà supprimée/absente : 404. Une page vide n'atteste ni
  l'auteur ni l'audit ; consultation d'audit encore ouverte.
- Premiers nouveaux cas : **23 réussis en 50,99 s**, puis quatre cas ajoutés
  pour lecture seule MCP, course suppression/clôture et ancien schéma inchangé.
  Les tests couvrent exposition/config/arguments sans credential, vrais MCP
  et CLI source/moteur/PowerShell, lecteur/projet étranger/révocation, versions,
  audit/événement unique et beta intact. Transport DELETE exact reçu une seule
  fois sous disconnect/erreur/redirect ; perte après commit sans réessai.
  Refus de dépendance et échec d'audit annulant la mutation vérifiés sur fixtures.
- Suite finale : **114 tests réussis en 353,04 s**, aucun ignoré : 27 nouveaux
  cas de suppression, 36 contexte, 21 tâches, 23 CLI (dont wheel réellement
  installé sans dépendances serveur) et sept protocole stdio. Une course
  suppression/clôture sur la même version donne un commit et un refus
  (version périmée ou tâche supprimée), un audit du gagnant et un événement ;
  beta inchangé. Ancien schéma sans version refusé, base byte-identique.
  Warning Starlette/httpx connu ; hooks historiques non rejoués, variance du
  seuil 50 ms toujours consignée et gate CI conservée, pas de CI globale verte.
  Trace finale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-delete-final-fed3d0bfc70f4a78a6cb1758b055e59f/tests.txt,
  SHA-256 0E4F1CC82EFF96B8A14134CBCBBBDBFA774507F3BC49EB80758F67D8785BC51E.
  Trace baseline avec échec d'arrêt corrigé :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-delete-baseline-eab11b92eadc4f47bf6144f9cef78cc5/tests.txt,
  SHA-256 E8A6A253370B2CB7193E9FE5EFAD7B6D524EF4FF193270201571CE45C389F8DE.
  Revalidation du cas :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-delete-baseline-recheck-dcea3dbfd7ac4c3a99f14a54cf028f1d/tests.txt,
  SHA-256 B881F012091100A7A877A8F340CE5FCE92DD98E2E2B80FC925732A6FA6115413.
- Exemple TOML de lecture conserve suppression désactivée, activation distincte
  documentée sans secret. README, plan et fiche v24 actualisés : **11 026/
  12 000 octets**, empreinte concordante et zéro avertissement, décisions
  inchangées. AST de six fichiers, TOML et espaces vérifiés. Gate CI étendue
  à la suppression et portée à dix minutes ; résultat distant non annoncé.
- Limites : recette uniquement ; autres opérations/ACL, consultation d'audit,
  outbox/worker, service Windows, HTTPS, timeout global, PostgreSQL, migration et
  bascule ouverts. WAL/checkpoints et charge réelle non qualifiés. Reprise IA
  neuve et économie effective de tokens ouvertes. Aucun critère global L2/L4/L9
  fermé, configuration/runtime actifs conservés et automatisation maintenue.

## L2/L4 — Consultation HTTP de l'audit des tâches

- Reprise MCP : fiche v24 **11 026/12 000 octets**, registre obligatoire et
  provenance sans avertissement. task_status historique T-388 384/389,
  distinct des critères du plan. Git sale, journal pertinent, code et tests
  relus ; Python 3.13 de recette présent. RepoWise ciblé sur identity.py :
  aucun résultat pour ce module non suivi ; index/HEAD b2349de865c2 concordants,
  âge neuf jours/mock/sémantique désactivée. Sources locales utilisées.
  LOCAL/DATA temporaires définis avant imports/processus ; aucune donnée
  active, Dropbox ou index RepoWise réel utilisé comme fixture.
- Baseline identité et audit HTTP : **14 réussis en 27,25 s**, avertissement
  Starlette/httpx connu. Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-read-baseline-2006da51b2e44bd0b4946d6f28f88ece/tests.txt,
  SHA-256 ED9BC097171C587CDA52B53E37C22D25DF9DF19079D576F97DB979FC93CE274F.
- Nouvelle capacité `task.audit.read`, réservée au responsable du projet.
  Reader/contributor conservant leurs anciennes actions explicites, aucun
  gain de capacité pour leurs credentials ou les anciens credentials owner.
  Les nouvelles sessions par mot de passe du responsable suivent les actions
  du rôle ; les cookies décrivent aussi ce droit et le revérifient à l'admission.
  Aucun schéma d'identité, provisionnement, configuration ou runtime actif modifié.
- GET /api/project/task-audit admis uniquement en profil individual et sur le
  projet authentifié. Lecteur SQLite mode=ro/query_only sans création ou
  migration, exécuté par asyncio.to_thread. Filtre SQL projet/actions/type
  avant décodage ; champs et nombre de lignes bornés. Actions qualifiées
  task.complete/task.delete, schema_version=1 et cohérence des versions.
  Projection auteur/action/date/identité/statuts/versions, sans détails bruts,
  titre, trace, session ou champs supplémentaires. Magasin/entrée qualifiée
  invalide : 503 générique sans contenu partiel ni réparation.
- Cursor UUID retrouvé uniquement dans le projet et filtre demandés ; ordre
  d'insertion décroissant, sans doublon lors d'un ajout entre pages. Aucun
  snapshot durable ou garantie sous purge/réécriture. UUID absent/étranger :
  même erreur générique. Paramètres limit 1–100, task_id/before_id facultatifs ;
  auteur/chemin libre refusés. Réponse no-store, ligne JSON UTF-8 <= 65 536 octets.
- Premiers tests : **22 réussis, deux échecs en 110,00 s**. Un test utilisait
  « invalid » comme valeur secrète et le retrouvait dans le code d'erreur
  générique : fixture remplacée par un marqueur distinct. Un véritable défaut
  de borne ajoutait le curseur après mesure (1 106 octets pour une borne 1 100) :
  espace du curseur désormais réservé avant mesure. Test supplémentaire avec
  cent auteurs UTF-8 multioctets : **1 réussi en 2,41 s**, 26 autres désélectionnés ;
  plafond de production et parcours intégral sans doublon vérifiés.
  Trace initiale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-read-new-a93126732e674d76b8b9d3b6217b470c/tests.txt,
  SHA-256 57A14D65173859DEEA7BEFAC125BBE4754206EA0751DCBA1368A7A944100B1EC.
  Trace UTF-8 :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-utf8-4ae66bdf9f3e45918959d0771199a6e1/tests.txt,
  SHA-256 98B58C45C605E2DE0F4D3E73A2FAF281E1921995BE1EC8DE7ED96A26FBB0D124.
- Contrat, matrice de droits et plan mis à jour ; gate CI dédiée avec racines
  temporaires et limite de quatre minutes. Fiche v25 **11 200/12 000 octets**,
  empreinte concordante, aucune alerte, décisions inchangées. Validation du
  manifeste après erreur de substitution regex dans sa mise à jour : corrigée,
  JSON et budget vérifiés. AST de cinq fichiers et git diff --check ciblé validés ;
  blancs hérités hors diff préservés. CI distante complète non exécutée.
- Suite de régression identité/sessions/mots de passe/administration/admission/
  audit/contexte HTTP : **120 réussis en 480,73 s**, aucun ignoré et un warning
  Starlette/httpx connu, dont 26 premiers tests de consultation. Refus avant
  lecture, rôles/scope/révocation, Bearer/cookie/mot de passe, profil historique,
  projection sans détails sensibles, pages/cursor, stockage invalide et beta/
  status disponibles pendant une lecture alpha bloquée qualifiés sur fixtures.
  Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-read-final-ae8d459751ee4aa2ba5de2781b8795d6/tests.txt,
  SHA-256 21122EA5BDD38D573A7174F8268420B5D3220A78639B69A9E8BDBEFA12526530.
- Après cette collecte, garde finale de taille ajoutée pour l'enveloppe même
  vide : un projet démesuré ne produit aucune réponse au-delà du plafond.
  Borne UTF-8/cursor revérifiée : **2 réussis en 10,72 s**, 25 désélectionnés.
  Cas réel suppression après clôture ajouté : audit deleted v2→v3 et ancien
  audit complet relisibles ; cursor refusé sous un autre filtre de tâche.
  Premier essai échoué sur le helper TestClient.delete ne prenant pas json,
  corrigé en request('DELETE',...) : **1 réussi en 9,91 s**, 27 désélectionnés.
  Au total **122 cas distincts réussis**, 123 exécutions dans la suite et ces
  deux revérifications (un cas de borne est rejoué), hors baseline/essais initiaux.
  Trace bornes finales :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-utf8-final-cd39606768ff4a818b4eda2c37dd7423/tests.txt,
  SHA-256 AC3022882A6597771533F8C81F48F1FA22DBAF9A5F11F881A31674FB9CDEEF48.
  Trace fixture suppression échouée :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-deleted-history-ad72a04698764825b8286939b85e3426/tests.txt,
  SHA-256 7D9325F1930AEE837AA40A75CDA8009A6915E35BD503CAA84997C7DA569B8170.
  Trace suppression finale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-history-final-9dce27cd6dce48318c17cd2e4badf5ec/tests.txt,
  SHA-256 54CCDBA29654A2813A82061DE3A734893960C9C17188639279E214380B75935C.
- Limites : recette uniquement, lecteur HTTP des mutations déjà qualifiées.
  CLI/MCP/Cockpit pour cet audit, autres mutations/canaux, protection/rétention,
  journal des lectures/refus, outbox/workers, correction WAL/checkpoints, service
  Windows, PostgreSQL, migration/bascule et HTTPS encore ouverts. Les lecteurs
  OS restent de confiance. Reprise IA neuve et économie de tokens non qualifiées.
  Aucun critère global L2/L4/L9 fermé ; automatisation conservée.

## L2/L4 — Lecteurs CLI/MCP de l'audit des tâches

- Reprise MCP : fiche v25 **11 200/12 000 octets**, décisions/provenance sans
  avertissement ; statut T-388 384/389 historique. Git sale et modifications
  préexistantes préservés ; journal HTTP, transport, serveur MCP, CLI et tests
  concernés relus. RepoWise ciblé individual_tasks.py : aucun résultat pour ce
  module non suivi, index/HEAD b2349de865c2 concordants mais âge neuf jours et
  sémantique désactivée/mock. Sources locales utilisées. Python 3.13 de recette
  présent, racines LOCAL/DATA temporaires définies avant imports/processus,
  sans données actives, Dropbox ou index réel utilisés comme fixtures.
- Baseline tâches/CLI : **43 réussis, un échec en 141,91 s**. Le test wheel
  manquait setuptools parce que DEVCORE_TEST_BUILD_TOOLS n'était pas défini
  dans cette commande ; répertoire verrouillé de recette retrouvé et fourni
  pour la revalidation. Aucun package ajouté au runtime ni au dépôt.
  Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-client-baseline-21b838d2efdd440293706d7926a9c638/tests.txt,
  SHA-256 D6E9E0C721099BF75BCB0B5F4AC36BC103522277500C31E703B7118B834C9AB9.
- Nouveau lecteur stdlib individual_audit dans le transport partagé : GET
  /api/project/task-audit, projet explicite configuré, limit 1–100 et filtre
  tâche/cursor UUID facultatifs. Arguments invalides refusés avant credential.
  Corps distant lu au plus 65 537 octets, dépassement refusé ; projection
  de sortie <= 65 536 octets avec saut de ligne. Toute la page validée avant
  retour : projet/filtre/UUID uniques, auteur imprimable, date, statuts,
  versions before→after et curseur. Clés JSON dupliquées refusées ; détails
  bruts, session/trace et champs libres supprimés, sans restitution partielle.
- MCP individual : devcore_task_audit ajouté uniquement avec
  DEVCORE_MCP_TASK_AUDIT=1, défaut 0 et autres valeurs refusées au démarrage.
  Indépendant des outils de mutation, disponible avec READ_ONLY=1. Les outils
  effectivement exposés proviennent du client dont write est ramené à read ;
  profil historique conserve son filtrage et n'expose pas ce nouvel outil.
  Aucun changement de configuration active ni de capacité des credentials.
  API revérifiant task.audit.read et rôle owner à chaque appel. Bloc texte
  compact UTF-8 avec saut de ligne, pas de duplication structuredContent.
- Commande CLI audit explicite, également via dc individual Python/PowerShell ;
  arguments --limit/--task-id/--before-id. Même projection/transport que MCP,
  aucun import de base serveur ou accès SQLite client. Une erreur 400 de cursor
  est invalid_arguments, code CLI 2 ; autres refus/pannes code 1, succès 0.
  Détails d'erreur distants masqués, pas de retry/redirect/proxy/cookie/repli local.
- **48 nouveaux tests réussis en 83,12 s**, aucun ignoré, avertissement
  Starlette/httpx connu. Exposition/config/arguments sans credential, champs
  malformés/étrangers/dupliqués/oversize, messages génériques et absence de
  retry/redirect. Vrais subprocess MCP/HTTP et CLI source isolée/engine/ancien
  dc/PowerShell : historique conservé après suppression, pagination, scopes,
  révocation/rotation, old credential et projet étranger refusés. READ_ONLY
  exposant l'audit sans suppression ; lecture alpha retenue laissant beta et
  ping du même serveur MCP disponibles. Base métier byte-identique et fichiers
  invalides des clients non ouverts. Trace :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-client-new-507271222dff40288bb55983c29d6ba2/tests.txt,
  SHA-256 72A7231BB4DB6CAA8E408523B07FA674C9739CE9080DD5DCE015DE9C90F00297.
- Gate de régression contexte/tâches/CLI/suppression/audit/stdio : **162 tests
  réussis en 441,61 s**, aucun ignoré, avertissement Starlette/httpx connu.
  Elle inclut 36 contexte, 21 tâches, 23 CLI, 27 suppression, 48 audit et sept
  stdio. Outillage build de recette fourni ; échec baseline setuptools levé.
  Wheel réellement construit sur copie et installé sans dépendances serveur :
  audit après une mutation authentifiée et nouveau credential owner limité à
  task.audit.read qualifiés. Hooks historiques non rejoués ; variance du seuil
  50 ms antérieure toujours consignée, gate CI conservée, pas de CI globale verte.
  Trace finale :
  C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-client-final-014f8e27cb494e05a4c2a736c88655c5/tests.txt,
  SHA-256 F3FF004EEE74425EF6D6CF248A847F2570D31C69B18F40D49F7A575A75912366.
- Documentation, exemples TOML (audit désactivé), plan et fiche v26 mis à jour.
  Mesure **11 291/12 000 octets**, zéro avertissement et empreinte concordante ;
  décisions inchangées. AST de huit fichiers, TOML et diff --check ciblé validés.
  Gate CI inclut le nouveau fichier ; pas de CI distante complète annoncée.
- Limites : recette, pas de bascule. Affichage Cockpit, autres mutations/ACL,
  protection/rétention de l'audit, journal des lectures/refus, outbox/worker,
  PostgreSQL, correction WAL/checkpoints, service Windows, HTTPS et délai global
  strict encore ouverts. Une annulation MCP peut laisser le thread finir.
  Reprise IA neuve et économie effective de tokens non qualifiées. Critères
  globaux L2/L4/L9 ouverts ; automatisation conservée.


## L2/L4 — Historique d'audit dans le Cockpit individuel

- Reprise : fiche v26 et décisions obligatoires, état Git et journal pertinents
  relus avant modification. RepoWise ne retrouve pas project_tasks.js ; index
  ancien de neuf jours, embedder mock et recherche sémantique désactivée.
  Implémentation confrontée aux sources locales. Baseline UI : 19 tests réussis.
- Page /project : historique chargé à la demande, réservé à task.audit.read,
  filtre par identifiant de tâche et pagination des modifications plus anciennes.
  Auteur, action, date et versions affichés par textContent. Filtre accepté
  conservé pour la pagination ; aucune lecture automatique de l'historique.
- Lecture indépendante des tâches et du contexte : annulation et générations
  empêchent une réponse tardive de remplacer un autre projet ou une nouvelle
  session. Reload, mutation et logout effacent l'historique. 401/403 effacent
  la session ; 400/503 n'effacent pas les tâches. Cookies same-origin et no-store.
- Validation de toute la page avant affichage : projet, filtre, UUID, dates,
  auteurs, transitions, versions entières sûres JavaScript et curseur concordant.
  JSON canonique et corps UTF-8 limité à 65 536 octets. Fetch moderne arrête et
  annule le flux au dépassement ; fallback sans ReadableStream mesure après
  réception et ne garantit donc pas une borne mémoire. Aucune donnée sensible
  supplémentaire rendue. Entiers dépassant la précision JS refusés explicitement.
- Vérifications finales : **27 tests Node réussis**, zéro échec/skip, 298,039 ms ;
  **34 tests HTTP réussis** (audit 28 + sessions navigateur 6), zéro skip,
  177,20 s, un avertissement Starlette/httpx connu. Syntaxe Node et diff --check
  ciblé validés. Gate Node CI existante couvre les nouveaux tests ; aucune CI
  distante globale verte annoncée.
  Traces et SHA-256 :
  - C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-ui-node-819c64f1200e4a4284614336f407c3d7/tests.txt
    f7012542294f9a045c15cebcb6c4a0a2d14e14e33afdf44c37046547923c3f48
  - C:/Users/Administrateur/AppData/Local/Temp/devcore-audit-ui-http-54c86b1b7fcd4640a69c3628a2bf74a1/tests.txt
    d638471d9a7abe29adff4ca22f676dc3ff44561a733050e938c51bd86f5a3808
- Navigateur réel sur instance temporaire 127.0.0.1:54748 : responsable Alice,
  clôture puis suppression T-01, auteur et versions v1/v2/v3 visibles ; filtre
  T-01 vérifié. Compte lecteur : panneau absent. Logout efface l'affichage.
  Fiche absente de la fixture (503) sans bloquer l'audit. Pagination et changement
  de projet en vol vérifiés par Node, pas par ce parcours navigateur.
  En-têtes corrigés en nowrap après inspection visuelle à largeur 619 px.
  Capture finale : audit-cockpit-2026-10-03.png, SHA-256
  c01c35ca0a536ea8d40389df02d7d4731b2d7d663d23439131845857cbc0bd66.
- Racines temporaires définies avant imports/sous-processus ; données synthétiques
  uniquement. Premier bootstrap de fixture : FileExistsError pour local déjà créé,
  corrigé par une racine fixture imbriquée neuve. Instance de recette arrêtée et
  onglet fermé après vérification. Aucune donnée active, Dropbox, index RepoWise
  ou configuration active modifiés par les tests.
- Plan, guide de consultation et fiche v27 mis à jour. Manifeste recalculé :
  card_sha256 575e40adee064957bae7cd115da741b3f3cb8cf0a873977ad54ed166e9d1f363.
  Lecteur local : **11 419/12 000 octets UTF-8**, aucun avertissement, décisions
  inchangées ; cette mesure n'est pas un comptage de tokens du modèle.
- Limites : recette uniquement, pas d'activation opérationnelle. Deux profils
  navigateur indépendants, HTTPS/cross-site, autres mutations et ACL, protection
  et rétention du journal, audit des lectures/refus, correction WAL/checkpoints,
  PostgreSQL, worker/outbox et service Windows restent ouverts. Reprise IA neuve
  et économie effective de tokens non qualifiées. Lots globaux non clôturés ;
  automatisation conservée.


## L0/L9 — Prérequis SQLite WAL automatisé

- Reprise fiche v27/registre, Git et dernier journal avant modification ; MCP
  contexte et statut accessibles. Statut 384/389 historique, pas une qualification
  des lots. RepoWise retrouve db.py mais index neuf jours/mock/sémantique absente ;
  sources locales vérifiées. Recherche PowerShell avec glob rg corrigée vers -g.
- Bibliothèque réelle de recette vérifiée : Python 3.13.3, SQLite 3.49.1,
  source_id 2025-02-18 / 873d4e274b4988d260ba8354a9718324a1c26187a4ab4c1cc0227c03d0f10e70.
  Même version dans le Python 3.13 global. La documentation primaire SQLite WAL
  consultée confirme les correctifs 3.51.3+, 3.44.6 et 3.50.7 ; corruption non
  reproduite, aucun stress concurrent lancé sur ce runtime non corrigé.
- Ajout check_sqlite_runtime.py : stdlib seule, ouverture :memory: exclusivement,
  exécutable/versions SQL et module/source_id/options de compilation dans JSON,
  inconnu ou incohérence refusés. Code 0 signifie seulement admissibilité à la
  recette WAL ; operationally_qualified toujours faux. Code 2 sinon ou erreur
  SQLite expurgée. Absence de WAL compilé refusée même avec version corrigée.
- Gate CI ajoutée sans supprimer les modifications antérieures : sonde avant
  tests de qualification, puis tests de la sonde. AST/YAML et diff --check
  ciblé réussis ; pas de CI distante annoncée, pas de modification du runtime.
- Premier passage 23 réussites/0,30 s ; final **24 réussites en 1,06 s**, zéro
  skip/échec. CLI testée dans sous-processus avec racines temporaires définies
  avant imports, fausse base sentinelle intacte et aucun journal créé. La sonde
  réelle retourne **2** sur recette 3.49.1, résultat attendu du prérequis.
  Traces dans C:/Users/Administrateur/AppData/Local/Temp/devcore-sqlite-preflight-91d28ec97a54458f9e09a760c9487f40/ :
  tests-final.txt SHA-256 4e97bbd895eed6eeada233821b1f254f4cb972f2f616a16bf7cfad1ed96de182 ;
  runtime.json SHA-256 fcd5f8c6685676d876eea88bad2170d3f94a8c4cb32e4d9f62ac621a1d33cba3.
- Procédure sqlite-runtime-2026-10-03.md, plan et fiche v28 actualisés. Lecture
  bornée **11 677/12 000 octets**, sans avertissement, décisions inchangées ;
  card_sha256 6aedcfaa5559afdc1078f7c1b7187f8f0d2472540ea6358c1466f79e219fe530.
- Prochaine étape : runtime Python 3.13 séparé avec SQLite corrigé, provenance,
  régressions des extensions et application, écritures/checkpoints et restauration
  sur fixtures avant activation. La sonde ne qualifie ni des DLL vendor ni les
  autres processus ni performance/intégrité applicatives. Données actives,
  Dropbox et index RepoWise préservés. L0/L4/L9 et gain tokens restent ouverts ;
  automatisation conservée.


## L0/L4/L9 — Runtime candidat corrigé et recette WAL

- Reprise du contexte v28, décisions, état Git, journal du prérequis et tests
  pertinents. MCP contexte/statut répondent ; board historique 384/389 non
  assimilé au plan. RepoWise ne connaît pas le nouveau test, index neuf jours,
  mock et sémantique désactivée : sources locales utilisées, index non modifié.
- Premier candidat uv Python 3.13.13 installé séparément sans bin/registre :
  SQLite réel 3.50.4, prérequis refusé. Installation de dépendances terminée sur
  ce candidat mais aucune sélection/activation ; environnement conservé.
- Métadonnées upstream uv explicitement chargées pour Python 3.13.16 (build
  python-build-standalone 20261003). Installation séparée sans bin/registre sous
  E:/DevCoreRuntime/interpreters puis venv
  E:/DevCoreRuntime/releases/devcore-py31316-20261003. Sonde réelle : SQLite
  3.53.1, source_id c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9,
  code 0. Les 53 dépendances du lock installées avec --require-hashes ; pip check
  via uv réussi. Aucun nouveau magasin, compte ou serveur actif lancé.
- Provenance : URL et SHA d'archive déclarés upstream (non revérifiés par un
  second téléchargement), empreintes des binaires/lock/scripts, liste figée des
  paquets. E:/DevCoreRuntime/releases/devcore-py31316-20261003/provenance.json
  SHA-256 a0b3b1405ff50bc02663d1d2f26a0cae2566601bdcd8c55e05d85dbf2bc41fc5.
  Dépendances seules : application testée depuis ce dépôt via PYTHONPATH,
  artefact DevCore autonome et figé à préparer ultérieurement.
- Nouvelle recette WAL : 2 écrivains + 2 checkpoints + 1 lecteur, compteur/ledger
  atomiques alpha/beta, intégrité et contenu exacts, checkpoint final, sauvegarde
  SQLite restaurée et relue. sqlite-vec 0.1.9 et schéma DevCore réels vérifiés.
- Premier passage : **52 réussites, 2 échecs en 56,33 s**. WAL refusait database
  is locked avec timeout 5 s, lots 120/FULL. Recette adaptée explicitement :
  timeout 30 s conforme à connect_db, 40 écritures/projet, pause 1 ms/transaction.
  Passage final ciblé **3 réussites en 15,83 s** : PASSIVE 80 commits/80 checkpoints,
  4 busy, 40 snapshots, 5,688 s ; TRUNCATE idem, 40 busy, 7,176 s. Total 55 cas
  distincts réussis dans ces passages ; échecs initiaux conservés, pas de charge
  saturée, d'équité ou de seuil interactif qualifié. Pas un reproducer du bug
  amont ni une preuve contre les pannes physiques.
- Traces dans C:/Users/Administrateur/AppData/Local/Temp/devcore-wal-qualification-0579181ae2274518b75f0f196e3b8268/ :
  tests.txt SHA-256 1fabc4bdaf986b7a2042b856b8cc7fc73b41cc698b69f6f4d4b32e23254a3eee ;
  wal-final.txt SHA-256 428438d68d6135d07d9fbbc95ba3b8ef35f2501605312e4ce81e275d63ff8b49 ;
  runtime.json SHA-256 8ac6770e783b23166d756ce3732e81f821666dcca2960cb62fd43d46a41b8f63.
- CI : gate SQLite inclut la recette WAL et l'extension, délai deux minutes ;
  YAML/AST/diff --check ciblé valides. Pas de CI distante ni tests HTTP/MCP complets
  sous ce nouveau runtime annoncés. Documentation/plan et fiche v29 mis à jour :
  **11 499/12 000 octets**, sans avertissement. Fins de ligne normalisées ;
  card_sha256 f49511170c129e82a791142ed1e805de162cb94b0fb0f1b01b362695dff172cb.
  Décisions inchangées. Ancien runtime/services conservés, pas de bascule, données
  actives/Dropbox/index préservés. Qualification des autres processus, charge,
  artefact/service Windows et critères globaux encore ouverts.

- Suite restauration/récupération NTFS sur le candidat : **35 tests réussis en
  237,57 s**, sans skip/échec. Racines temporaires avant imports/sous-processus,
  sources DELETE/WAL, révocations et arrêts de workers sur fixtures. Trace
  C:/Users/Administrateur/AppData/Local/Temp/devcore-runtime-recovery-fd8e3e017bf149229835ea9f213993eb/tests.txt,
  SHA-256 db32c4d6370315abdfa365df0a5e0c98fa0f089404a0a10bea84c8a6c5dffed8.
  Avec les 55 cas ci-dessus : **90 tests distincts réussis**, sans addition de
  passages répétés. Qualification applicative partielle, aucune activation.
  Automatisation conservée pour la suite du plan.
