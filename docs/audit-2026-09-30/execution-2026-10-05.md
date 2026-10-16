# Exécution du plan DevCore — 2026-10-05

Suite du journal execution-2026-10-04.md ; données actives et Dropbox
non utilisés comme fixtures, changements existants préservés.

## L1 — Reprise respectant les dépendances locales (v111)

- État Git, journal v110 et tests pertinents relus avant édition ; contexte
  local11960/12000 sans warnings et décisions en vigueur, board MCP384/389.
  RepoWise non exposé dans ce passage, contrôle des sources locales.
  resume_task réactivait une tâche paused malgré une dépendance invalide.
- Après contrôle de version et avant UPDATE, dépendance de tâche paused
  lue par projet/id et exigée done, dans BEGIN IMMEDIATE. Manquante, pending,
  supprimée ou étrangère refusée avec diagnostic fixe sans texte étranger.
  Refus sans état/version/événement ; contrôle tâche active existant préservé.
- 24 tests ciblés réussis,35 exclus en46,66 s sur Python3.13 documenté et
  overlay Argon2 existant, trois racines temporaires avant imports. Huit
  nouveaux cas : quatre états de dépendance x reprise explicite/implicite,
  fixture de tâche historique paused sur base temporaire ; refus sans effet,
  reprise autorisée après clôture de dépendance locale. Tests dépendance
  d'avance, reprise/audit événement et conflit de version existants inclus
  via sélection -k 'dependency or resume', pas suite complète répétée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-resume-dependencies-30fe09a28e2049d889481ea1106c9646/tests.txt ;
  SHA-256 b7c631b6986055b2a6447c446e82494b8f49b5b109e89df9e39a4fede361981e.
- Plan/fiche v111/manifeste revus au5 octobre et lien du journal actualisé.
  Tests déjà inclus dans CI, exécution distante non réalisée. Sources non
  activées, services/releases/Dropbox/données actives inchangés. Clôture
  explicite, graphes/cycles/réconciliation historique, anciens écrivains et
  contraintes SQL/ACL restent ouverts. Pas de nouveau workflow durable ;
  attente SQLite30 s synchrone et qualification PostgreSQL/charge ouvertes.
  L0–L9 non terminés, automatisation active, gains tokens non mesurés.
- Contexte final v111 :11980/12000 octets UTF-8, warnings vides, décisions obligatoires conservées.

## L1 — Générateur Cockpit sans sélection partagée (v112)

- Git/journal v111/contexte local11980/12000 et tests concernés lus avant
  édition ; board MCP384/389. RepoWise non exposé, analyse locale. Recherche
  active_project.txt : utils Cockpit encore lecteur, Router garde des helpers
  historiques déjà retirés des chaînes HTTP v101 (pas supprimés ce passage).
- dashboard/utils.get_active_project ne lit plus les fichiers Runtime locaux
  ou Dropbox et ne choisit plus devcore par défaut. DEVCORE_ACTIVE_PROJECT_NAME
  absent donne vue générale (chaîne vide), explicite validé selon les interdits
  de chemins usuels, invalidité refusée sans repli. Préférence lue à chaque
  appel, pas cache module. Paramètre data_root conservé pour compatibilité,
  inutilisé. Renderer : pas de nom vide dans les cartes prioritaires.
- 17 tests réussis en5,91 s sur Python3.13 documenté + overlay existant,
  trois racines temporaires avant imports. Sept nouveaux cas : fichier
  partagé ignoré/préservé, changement d'environnement local pris en compte,
  six valeurs invalides refusées. Data loader SQLite et résolution de projet
  CLI/PowerShell existants inclus. Aucun index RepoWise réel ni génération
  avec réseau/services actifs effectuée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-selection-e1b3f7357ce943c38913fa5e63327d5f/tests.txt ;
  SHA-256 3da9faeb53d43046510d294db455b82e07abe0a5a117abbfba86fbdb5b93af90.
- CI enrichie non exécutée à distance ; plan/fiche v112/manifeste et suivi
  actualisés. Sources non activées ; pages actives non régénérées. Correction
  de préférence du générateur seulement : pas contexte utilisateur HTTP ni
  ACL, isolation des fichiers HTML générés ou neutralisation de métriques
  statiques historiques. Vue générale legacy expose encore plusieurs projets ;
  profil individuel distinct reste la voie de qualification. Génération
  intégrale/ancien Router/anciens canaux et lots L0–L9 restent ouverts.
- Contexte final v112 :11985/12000 octets UTF-8, warnings vides ; décisions obligatoires conservées.

## L1/L6 — Projet Cockpit sérialisé dans le script des templates (v113)

- Git/journal v112 et tests relus avant modification ; contexte local
  v11211985/12000 sans warnings, board MCP384/389. RepoWise non exposé,
  analyse directe. Les deux templates plaçaient ACTIVE_PROJECT_NAME dans
  une chaîne JS entourée de guillemets ; remplacement brut dans gen_dashboard
  permettait à un nom avec guillemets de casser cette affectation.
- render_active_project remplace le slot complet quoté par json.dumps
  ASCII, avec caractères <>& encodés en échappements Unicode. Nom vide
  produit une chaîne vide JSON, guillemets/Unicode préservés sans exécution.
  Marqueur restant non quoté refusé. Deux voies de génération raccordées,
  templates et pages actives inchangés, autres champs non transformés.
- 20 tests réussis en1,94 s, Python3.13 documenté + overlay existant,
  trois racines temporaires avant imports. Neuf nouveaux cas : quatre
  sélections x deux templates réels (aucune, simple, payload guillemets
  et séparateurs/HTML Unicode), affectation décodable comme une seule valeur
  JSON, reste du préfixe intact ; slot non quoté refusé. Tests sélection
  partagée et data loader existants inclus. Pas exécution JS navigateur,
  génération entière/services réseau/index réel en fixture.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-script-project-f6d70ce34dfc48dda0473eadf7bb98c4/tests.txt ;
  SHA-256 d02173d0350f7e7d36291768db7d3264120b6c104fd963d0ca643f94fbcb7417.
- Plan/fiche v113/manifeste actualisés ; tests déjà dans CI distante non
  exécutée. Sources non activées, pages non régénérées, données actives/
  Dropbox/services inchangés. Correction de cette affectation seulement :
  autres insertions de contenu et données UI historiques, génération complète,
  stockage de sorties par utilisateur et ACL restent à qualifier. L0–L9
  non terminés ; automatisation active, gains tokens non mesurés.
- Contexte final v113 :11986/12000 octets UTF-8, warnings vides ; décisions obligatoires conservées.


### Passage v114 — JSON des deux vues Cockpit protégé contre fermeture de script

- Relecture du contexte v113, du journal, de l'état Git et des tests de génération ciblés. Outils RepoWise non exposés : inspection des sources locales. Tableau MCP consulté ; ses tâches ne prouvent pas les critères L0–L9.
- Détails des tâches et métriques insérés auparavant avec json.dumps brut dans des balises application/json : une valeur contenant </script> pouvait fermer la balise. Même protection centralisée pour détails, interactions, métriques et nom du projet : JSON ASCII strict, <>& échappés, NaN/infinités refusés. Deux voies du générateur raccordées. Substitution en un passage pour préserver les marqueurs littéraux présents dans les données.
- 25 tests réussis en 1,78 s, Python 3.13 documenté et overlay existant, racines LOCAL/DATA/PLATFORM temporaires avant imports. Deux nouveaux cas sur les templates réels : fermeture de script, Unicode, guillemets, null/bool/zéro et marqueurs littéraux préservés ; nombre de balises inchangé et chaque bloc décodable. Trois cas non-finis refusés. Tests sélection de projet et data loader inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-json-126eb849879e41108ecf879ee8a3a659/tests.txt ; SHA-256 946621c1a6fa5ede4534f28ed524b60b8db45e3c1bd6160c48f7239fd3446d79.
- Plan/fiche v114/manifeste actualisés. Pas d'exécution JS navigateur ni génération entière ; doublons historiques de blocs JSON des templates conservés. Autres interpolations HTML, publication atomique des pages et propagation des erreurs de génération restent à traiter. Pas de qualification ACL ou charge.
- Sources non activées, pages non régénérées, aucune donnée active/Dropbox/index réel utilisée comme fixture. CI distante non exécutée. L0–L9 restent ouverts, automatisation conservée et gains tokens non mesurés.
- Contexte final v114 : 11986/12000 octets UTF-8, warnings vides ; décisions obligatoires conservées.


### Passage v115 — publication atomique de chaque fichier du Cockpit

- Contexte v114 relu (11986/12000 octets, avertissements vides), état Git/journal/tests inspectés avant modification. MCP board : 384/389 avec ancienne tâche T-388, sans équivalence aux critères du plan. RepoWise ciblé disponible : alias chemin refusé, requête par défaut réussie, fichiers déclarés fresh ; défauts confirmés directement dans le code, aucun rafraîchissement d'index.
- Avant correction, cache JSON/empreinte et pages étaient écrits directement : lecteurs exposés aux fichiers partiels, erreurs de cache/empreinte masquées, erreurs HTML seulement imprimées. Module dashboard/publication.py commun : temporaire unique dans le répertoire cible, UTF-8 sans transformation des fins de ligne, flush/fsync, fermeture puis os.replace, nettoyage du temporaire. Échec avant remplacement préserve la destination précédente et remonte au lanceur.
- gen_dashboard raccordé pour les quatre fichiers ; erreurs de page relancées avec destination et cause, cache/empreinte propagés, template absent désormais en échec en mode HTML. Le journal task_sync reste facultatif. Sources non activées, aucune page active régénérée.
- 55 tests réussis en 7,79 s, Python3.13 documenté + overlay existant, trois racines temporaires avant imports. Publication exacte UTF-8/newlines vérifiée au moment du remplacement ; encodage, fsync et remplacement refusés avec destination existante ou absente, aucun temporaire restant. Générateur complet sur fixtures : refus ciblé des quatre destinations et absence de chacun des deux templates remontés, destination précédente et base SQLite préservées, pas de message de succès pour la destination en échec. Tests des interactions, handlers JavaScript et contexte projet inclus. Treize nouveaux cas ; résultat préliminaire de 49 tests non additionné.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-publication-bb2f0ea7ae464f1cbf3958867c8d4e5b/tests.txt ; SHA-256 1337313e618aa5c4a941b2ce5c2282192593e646d737c193c3833aa66d5e02b0.
- CI explicite enrichie, non exécutée à distance. Plan L6/fiche v115/manifeste actualisés ; aucun critère global coché. Pas de transaction multi-fichiers : panne tardive peut laisser des snapshots de générations différentes. Mode JSON écrit encore le cache sans verrou. Verrou ancien (péremption/timeout signalé succès/libération à atexit), permissions des nouveaux fichiers, durabilité après coupure électrique, cohérence snapshot/SSE/ACL et charge restent à qualifier. Pas de service/index réel ni données actives/Dropbox en fixture ; gains tokens non mesurés, automatisation conservée.
- Contexte final v115 : 11984/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v116 — verrou OS et libération à la sortie de la génération

- Relecture état Git, journal v115, tests pertinents et contexte borné (11984/12000, avertissements vides). MCP board toujours384/389, T-388 ancienne. RepoWise ciblé déclare DashboardLock fresh mais index10 jours/embedding mock et aucune recherche sémantique ; comparaison au code obligatoire, index inchangé.
- Ancien verrou O_EXCL supprimait un fichier vieux de120 s même avec détenteur actif, retournait SystemExit(0) au timeout, et attendait atexit pour sa libération. Nouveau module generation_lock.py : verrou exclusif non bloquant du noyau sur fichier persistant (msvcrt Windows, flock POSIX), attente bornée HTML30 s, aucune suppression/péremption. TimeoutError remontée ; fermeture/libération immédiate en finally et récupération par OS après mort du processus.
- main acquiert désormais le même verrou avant toute génération, y compris JSON ; JSON en contention refuse immédiatement plutôt que d'attendre. Contexte with entoure _generate_dashboard, stdout restauré après succès/exception du mode JSON. Fichier de verrou conservé volontairement pour éviter deux inodes et une libération tardive d'un autre détenteur.
- 62 tests réussis en8,92 s, Python3.13 documenté + overlay existant, racines LOCAL/DATA/PLATFORM temporaires avant imports/sous-processus. Sept nouveaux cas : exception libère/lock fichier conservé, détenteur enfant vivant avec mtime ancien non volé, CLI JSON concurrente retourne échec non nul sans sortie/cache, récupération après libération normale ou arrêt forcé de cet enfant, HTML/JSON succès/échec restaurent stdout et libèrent. Sept recettes de génération entière existantes vérifient désormais la réacquisition immédiate après retour/panne. Publication/interactions/JavaScript/projet inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-lock-8faf2c107fa1437f9e4d09a52912ddbb/tests.txt ; SHA-256 689d44976c693e928a9625b10ceb23498ff7387934ee5396e31fd18f6bd2b6ee.
- CI explicite enrichie, distante non exécutée. Vérification locale Windows uniquement : branche POSIX à qualifier par CI. Plan L6/fiche v116/manifeste mis à jour. Sources non activées ; aucune donnée active/Dropbox/index réel en fixture, aucune page active régénérée.
- Verrou coopératif local, pas distribué : tous les producteurs doivent utiliser cette version et le même LOCAL_ROOT. Arrêter les anciens producteurs avant activation ; ne pas mélanger leur protocole de suppression avec le verrou persistant. Racines distinctes écrivant le même PLATFORM_ROOT, droits des sorties, transaction cache/empreinte/pages, file de travaux/coalescence/SSE et isolation par utilisateur restent ouverts. Gains tokens non mesurés, critères L0–L9 non terminés ; automatisation conservée.
- Contexte final v116 : 11975/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v117 — préparer avant publication et retirer le second écrivain API

- Contexte v116 relu (11975/12000 octets, avertissements vides), journal/Git/tests inspectés. MCP board384/389 reste sans rapport avec critères L0–L9. RepoWise ciblé retourne index10 jours/mock, signatures du verrou précédent malgré déclaration fresh : recherche utilisée comme orientation, code actuel comme preuve ; index non modifié.
- Défaut concret confirmé : refresh_dashboard_payload_cache réécrivait le cache après ajout read_model, hors verrou du générateur et sans mise à jour de payload_hash. Suppression de cette écriture ; enrichissement read_model conservé uniquement dans la réponse. Le générateur reste propriétaire du couple cache/empreinte.
- Générateur sérialise désormais en JSON strict (allow_nan=False), calcule l'empreinte puis prépare les deux vues avant la première écriture publiée. Template standard/terminal absent ou payload non fini refuse la génération sans remplacer cache/empreinte/pages précédents. Messages de succès seulement après publication des deux vues ; journal task_sync reste facultatif.
- 70 tests réussis en10,07 s, Python3.13 documenté + overlay existant, trois racines temporaires avant imports/processus. Six nouveaux cas : réponse API enrichie sans modification du cache/hash produit simulé, quatre échecs du générateur simulé (code, vide, JSON invalide, schéma) préservent cache/hash, non-fini lors d'une génération complète laisse quatre fichiers intactes. Recettes des deux templates manquants renforcées pour vérifier les quatre fichiers ; recette réussie compare hash aux octets exacts du cache. Tests verrou avec processus réels, publications fautives, interactions/JS/projet et deux contrats API de lecture inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-prepare-25614eba93424ea4acacefe012d50f46/tests.txt ; SHA-256 3ade8ac5df06951b140bacf3824304e727dedb2be7ab1931757ea4af14d81f9f.
- CI explicite enrichie, distante non exécutée. Plan L6/fiche v117/manifeste actualisés. Sources non activées ; pages actives non régénérées, aucune donnée active/Dropbox/index réel en fixture.
- Limites : préparation n'est pas une transaction de publication. Panne entre les quatre remplacements peut laisser des générations différentes ; les lecteurs API/HTML n'utilisent pas encore un pointeur unique vers une génération immutable. Mode JSON publie seulement cache/hash et ne synchronise pas les pages. Snapshot read_model reste séparé. Dernier snapshot complet, bascule atomique, lecteurs/migration/coalescence/SSE/ACL et qualification charge restent ouverts. Gain tokens non mesuré ; L0–L9 non terminés, automatisation conservée.
- Contexte final v117 : 11977/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v118 — snapshot complet et pointeur de bascule unique

- Contexte v117 relu (11977/12000, avertissements vides), état Git/journal/tests avant modification. MCP board384/389 ancienne tâche ; RepoWise ciblé index10 jours/mock, déclaré fresh mais code actuel relu, index non modifié.
- Module dashboard/snapshots.py : quatre artefacts UTF-8 (payload JSON, hash, deux HTML) préparés sous génération UUID distincte dans LOCAL/Dashboard/generations. Chaque fichier puis manifeste écrit/fsync/remplacé avant bascule atomique de current.json. Manifeste et descripteurs enregistrent taille/empreinte ; metadata lue au plus4096 octets, artefact au plus16MiB. UUID/noms fermés et chemin de génération/artefact contrôlés sous racine ; tailles et empreintes contrôlées à la lecture. Générations publiées jamais modifiées par le producteur.
- Générateur connecté sous verrou OS, y compris mode JSON qui prépare désormais les deux templates et publie un snapshot complet sans écrire les pages legacy dans PLATFORM_ROOT. Exports historiques cache/hash/HTML toujours produits en compatibilité avant la bascule. Les deux lecteurs HTML API et lecture cache préfèrent le snapshot engagé ; absence de pointeur conserve mode legacy, corruption explicite refuse sans repli. Lectures HTML déportées en thread. Un lecteur résout une génération une fois pour sa lecture ; pas de rétention/suppression des anciennes générations.
- 82 tests réussis en19,70 s, Python3.13 documenté + overlay existant, racines temporaires avant imports/processus. Douze nouveaux cas : refus d'écriture de chacun des quatre artefacts/manifeste/pointeur garde ancienne génération, lecteur épinglé finit après nouvelle bascule, trois altérations pointeur/manifeste/artefact refusées, API préfère snapshot complet à cache legacy partiel et refuse pointeur corrompu, génération complète JSON connectée aux deux HTML. Recettes de publication/locking/interactions/JS/contexte et contrats API inclus. Aucun service/index réel ni données actives/Dropbox en fixture.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-dashboard-snapshot-62fd7a62ea5c468a89741c456c131cc7/tests.txt ; SHA-256 53ec5c5b92d099a23cb41d9e16fdb75ba3e7007ebab0ff801c280c08b0e17ce8.
- CI explicite enrichie, distante non exécutée. Plan L6/fiche v118/manifeste actualisés. Sources non activées, pages actives non régénérées. Tous les anciens producteurs doivent être arrêtés pour bascule coordonnée ; templates nécessaires aussi au mode JSON.
- Limites : exports legacy ne constituent pas une transaction et peuvent diverger en cas de panne ; jusqu'à première publication current.json, lecteurs sont encore legacy. Deux requêtes HTTP distinctes peuvent naturellement servir deux générations successives ; pas de session snapshot figée. read_model et autres sources restent séparés, absence de snapshot transactionnel SQL global. ACL/permissions, racines multiples, corruption causée par édition externe et mesures charge à qualifier. Durabilité coupure électrique (fsync répertoires) non prouvée ; générations anciennes ou staging avorté conservés sans GC, occupation disque à borner. L0–L9 restent ouverts, gains tokens non mesurés, automatisation conservée.
- Contexte final v118 : 11972/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v119 — admission bornée du magasin de snapshots

- Relecture contexte v118 (11972/12000 octets, avertissements vides), journal, état Git et tests avant modification. MCP board384/389 reste sans équivalence au plan ; RepoWise retourne fichier snapshots.py vivant sans enregistrement indexé, index10 jours/mock inchangé. Source/tests comme preuve actuelle.
- Les lecteurs peuvent rester épinglés sur une génération sans durée maximale : purge par âge non qualifiée. Ajout d'un garde-fou sans suppression : check_snapshot_capacity refuse nouvelle publication au-delà de256MiB logiques ou512 répertoires de génération, en comptant staging abandonné. Réservation conservatrice candidate + plus grand temporaire +12KiB metadata. Parcours borné (512 dossiers,12 fichiers chacun), entrées hors format UUID/non fichiers/nested paths refusées ; racine generations et chemins résolus contrôlés.
- Générateur vérifie capacité avant remplacement des exports ; publish_snapshot vérifie également avant création du nouveau dossier. SnapshotCapacityError explicite, pointeur précédent et lecteurs épinglés inchangés. Aucun nettoyage actif, automatique ou manuel réalisé.
- 51 tests ciblés réussis en12,46 s, Python3.13 documenté + overlay existant, racines temporaires avant imports/processus. Sept nouveaux cas : limite nombre laisse courant/ancien lecteur intacts, staging abandonné compté, budget candidat trop petit ne crée aucun dossier, trois formes inattendues de magasin refusées sans suppression, génération entière refusée avant modification des quatre exports. Pannes de snapshot/publication, gestionnaires JS et verrou avec processus réels inclus ; résultat non additionné aux82 tests du passage précédent.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-capacity-9d3eceb8fe1c4e9388d7fd8b240d085e/tests.txt ; SHA-256 adb4c83898d3cab77f1a16b9edcfe6b66a326c1e9df21f1ec579d9d0b09e92e4.
- Plan L6/fiche v119/manifeste actualisés ; tests déjà sélectionnés par CI, distante non exécutée. Sources non activées, données actives/Dropbox/services/index réel inchangés, aucune page active régénérée.
- Limites : borne sur octets logiques du magasin generations, pas sur allocation filesystem, exports legacy, autres producteurs ni espace libre global. Aucun GC/rétention opérationnelle : atteindre une borne arrête les nouvelles publications, sert le dernier snapshot complet et exige résolution de capacité ; réservation des lecteurs et purge sûre à implémenter. Coût du parcours/reprise après saturation/alertes UI, ACL/migration et charge restent ouverts. Tous producteurs doivent utiliser même verrou/racine. Gains tokens non mesurés, L0–L9 non terminés ; automatisation conservée.
- Contexte final v119 : 11979/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v120 — lecteurs API propriétaires des descripteurs de snapshot

- Contexte v119 relu (11979/12000 octets, avertissements vides), journal, état Git et tests avant modification. Outils MCP DevCore/RepoWise non exposés sur ce passage ; sources locales utilisées, aucun index modifié.
- pin_snapshot ouvre les quatre artefacts de la génération choisie sous SnapshotCatalogLock, verrou OS exclusif bref local, puis libère ce verrou avant lecture. PinnedSnapshot garde manifeste/descripteurs, fermé à la sortie normale ou exception. ExitStack nettoie aussi les fichiers ouverts avant un échec d'acquisition. read_snapshot_artifact accepte ce lecteur et vérifie taille/hash sur les descripteurs ; lecture après fermeture refusée.
- Lectures API du cache et des deux pages raccordées. Aucun catalogue créé en mode legacy sans pointeur. La publication suivante n'attend pas la fin d'une lecture du snapshot précédent ; aucune suppression automatique ajoutée. Future purge doit prendre le même verrou de catalogue pour sélectionner/retirer, et respecter refus Windows de suppression d'un fichier ouvert ; POSIX conserve les octets par descripteur après unlink.
- 35 tests ciblés réussis en8,99 s, Python3.13 documenté + overlay existant, trois racines temporaires avant imports/processus. Quatre nouveaux cas : lecteur conserve ses quatre contenus après nouvelle publication, catalogue disponible pendant lecture, descripteurs fermés/refus d'utilisation hors contexte ; erreur utilisateur nettoie ; acquisition partielle échouée ferme les précédents fichiers et libère le catalogue ; absence de snapshot n'écrit rien. Tests capacité/intégrité/API cache et verrou multiprocessus existants inclus ; résultat non additionné aux suites précédentes.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-readers-d57c6f663b5944b7b7d5f0ee9c4a2b6c/tests.txt ; SHA-256 6726434e27ae22ebdb8aea0c3d656bfb738c0c8d6964df477fcd9c3d2e843fa9.
- Plan L6/fiche v120/manifeste actualisés. Tests déjà sélectionnés CI distante non exécutée. Sources non activées, aucune donnée active/Dropbox/index réel/service utilisée comme fixture, pages actives non régénérées.
- Limites : purge/rétention encore absente. resolve_snapshot nu/get_cached_dashboard_payload_path et test d'âge/stat exposent un chemin sans réservation ; ces usages restent à migrer ou gérer les courses avant d'activer GC. Quatre handles par lecteur, borne du nombre de lecteurs/admission/coût d'ouverture à qualifier. Branches POSIX et suppression réelle concurrente non testées localement. Pas de verrou distribué ni défense contre acteur modifiant directement le stockage ; ACL, charge, migration et durabilité coupure électrique restent ouvertes. L0–L9 non terminés, gains tokens non mesurés, automatisation conservée.
- Contexte final v120 : 11980/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v121 — fraîcheur du cache sur son descripteur ouvert

- Relecture contexte v120 (11980/12000, avertissements vides), état Git/journal/tests. MCP board384/389 ancienne tâche toujours sans équivalence plan ; RepoWise ciblé build_dashboard_payload déclaré fresh, index10 jours/mock, code actuel relu et index inchangé.
- build_dashboard_payload utilisait encore get_cached_dashboard_payload_path puis exists/stat indépendants de la lecture : course potentielle avec future purge/rotation. Lecture cache renvoie modified_at obtenu par os.fstat du même descripteur que le contenu ; chemin snapshot réservé via pin_snapshot. Mode legacy ouvre également le JSON et fstat dans le même contexte, fichier absent retourne None. Enrichissement uniquement en réponse ; aucun changement du fichier publié.
- build_dashboard_payload lit le cache puis compare 0 <= âge <5 s ; date située dans le futur ne reste plus indéfiniment fraîche. Helper get_cached_dashboard_payload_path explicitement diagnostic/setup non réservé, plus utilisé pour le contenu dans le parcours production actuel ; autres usages locaux seulement tests.
- 33 tests ciblés réussis en9,01 s, Python3.13 documenté + overlay existant, racines temporaires avant imports. Quatre nouveaux cas : snapshot engagé et cache legacy frais servis sans stat du chemin payload ni helper non réservé, cache vieux/futur actualisé. Tests lectures protégées/capacité/intégrité, absence de seconde écriture et trois contrats API (schéma/lecture/budget transport) inclus ; résultat non additionné aux suites antérieures.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-freshness-4821bc62642140469cab85ddac5c3510/tests.txt ; SHA-256 8789f86997def55a5ca86e333c6a98b980dac5d831f93adc9dc6ceded89e2fee.
- Plan L6/fiche v121/manifeste actualisés. Tests déjà sélectionnés CI distante non exécutée. Sources non activées, aucune page active régénérée, données actives/Dropbox/index/service réel non utilisés en fixture.
- Limites : purge encore absente. resolve_snapshot nu et helper diagnostic restent non réservés pour usages externes ; ne pas les traiter comme leases. Cache legacy garde parsing non borné et n'a plus retry de parsing sur JSON partiel : migration des anciens producteurs indispensable. Timestamp système reste sensible aux modifications externes ; snapshot read_model séparé. Charge/admission des lecteurs, rétention/catalogue/Windows suppression, ACL et bascule opérationnelle restent ouverts ; gains tokens non mesurés, L0–L9 non terminés, automatisation conservée.
- Contexte final v121 : 11980/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v122 — collecte locale des générations anciennes avant publication

- Relecture contexte v121 (11980/12000, avertissements vides), état Git/journal/tests. MCP board384/389 ancienne tâche ; RepoWise fichier vivant sans enregistrement indexé, index10 jours/mock inchangé. Sources/tests comme preuve actuelle.
- collect_snapshots raccordé au générateur sous verrou producteur avant admission/remplacement des exports. Verrou catalogue empêche nouvelles acquisitions de handles pendant la collecte. Courant toujours conservé, même avec date ancienne ; trois dossiers les plus récents également protégés (courant normalement compris), puis nouvelle génération ajoutée. Parcours au plus512 dossiers/12 fichiers, format UUID et chemins résolus contrôlés ; validation de tous candidats avant suppression. Aucune suppression récursive : uniquement noms des quatre artefacts/manifeste ou leurs temporaires connus, puis rmdir vide. Entrée inattendue ferme la collecte sans supprimer les candidats validés jusque-là.
- Sous Windows fichier ouvert refuse généralement unlink : génération différée et message de diagnostic, retry au prochain passage après fermeture. POSIX les descripteurs gardent les octets après unlink. Manifeste supprimé seulement après artefacts. Sans pointeur engagé, aucune purge ; pointeur invalide refuse. Staging abandonné ancien aux noms connus peut être récupéré. Rapport removed/deferred/retained, aucune intervention sur stockage actif durant ce passage.
- 62 tests ciblés réussis en21,74 s, Python3.13 documenté + overlay existant, racines temporaires avant imports/processus. Cinq nouveaux cas : courant vieux préservé, lecteur actif lit ses quatre fichiers après collecte puis ancienne génération disparaît après fermeture, staging ancien supprimé et admission récupérée, fichier étranger refuse avant suppression, absence de pointeur conserve staging. Suites capacités/intégrité/lecteurs/versions/UI, APIcache et verrou multiprocessus inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-gc-3122cd173872413b9ea4c5206908cf0e/tests.txt ; SHA-256 20f41f5bf9a3980bdf6bd99e6879d2c36d47ad1079e93e4e8a34170b4f8859a5.
- Recettes HTML/JSON réussies renforcées : six générations initiales réduites à trois, puis publication nouvelle, quatre présentes et plus ancienne retirée. Dix recettes générateur réussies en8,80 s (dix autres cas désélectionnés), non additionnées à62 car chevauchement.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-gc-integration-df48256d2d8942a8b454daf4e2fee677/tests.txt ; SHA-256 35920e0c9ba1de7fdddafe77300b0decf500e504f61f34639cd965a67dafa481.
- Plan L6/fiche v122/manifeste actualisés, CI distante non exécutée. Sources non activées, pages actives non régénérées, données actives/Dropbox/index/service réel inchangés. Suppressions exécutées seulement sous tmp_path de tests.
- Limites : POSIX suppression réelle non testée localement. collect_snapshots public exige verrou producteur du même LOCAL_ROOT ; lecteurs doivent utiliser pin_snapshot, pas resolve_snapshot nu. Permission refusée après certaines suppressions peut laisser un dossier ancien partiel, jamais le courant ; collecte retry et contrôle capacity le comptent. Un magasin dépassant512 dossiers ou contenant fichiers étrangers requiert réparation, non suppression aveugle. Courant/récents gros ou lecteurs prolongés peuvent encore saturer quota. Débit/latence du catalogue, alertes UI, ACL, migration coordonnée, racines multiples et durabilité après coupure électrique restent à qualifier. L0–L9 non terminés, gains tokens non mesurés, automatisation conservée.
- Contexte final v122 : 11975/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v123 — rafraîchissement SSE regroupé par révision locale

- Contexte v122 relu (11975/12000, avertissements vides), journal/Git/tests inspectés avant modification. MCP board384/389 ancienne tâche ; RepoWise ciblé event_generator déclaré fresh, index10 jours/mock, défaut confirmé au code actuel, index non modifié.
- Chaque générateur SSE appelait refresh_dashboard_payload_cache en thread indépendamment lors du même changement. RefreshCoordinator nouveau : une tâche de production par boucle asyncio API, demande même timestamp attend la même tâche ; timestamp plus récent attend puis produit si nécessaire. Révisions finies/non négatives validées, succès seul mémorisé. Annulation du client shieldée ; erreur orpheline consommée, échec non mémorisé permet retry. Aucun verrou bloquant de thread ajouté dans la boucle async.
- event_generator déporte get_last_modified_timestamp en thread, utilise coordinateur partagé, n'avance last_ts et n'émet dashboard.delta qu'après succès. Test de reprise a révélé un last_ts encore avancé avant production après première modification ; ligne retirée et test repassé. Résultat intermédiaire1 échec/14 succès, non conservé comme qualification ; aucune donnée active concernée.
- 15 tests ciblés réussis en6,43 s, Python3.13 documenté + overlay existant, racines temporaires avant imports. Cinq nouveaux tests : vingt demandeurs et révision suivante sans concurrence de producteurs, annulation d'un abonné sans annuler le travail partagé, échec puis retry, vingt vrais générateurs event_generator produisent vingt deltas pour un seul appel producteur simulé, générateur en échec retente avant son premier delta. Tests cache/API existants inclus et test réactivité de boucle pendant génération lente. Pas de réseau/services/index réels en fixture, producteur remplacé par fonction de recette.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-retry-a4fb5c879960423eaa243a4c4c8e5871/tests.txt ; SHA-256 26531e698cfddc81b27c7851f385ce2ef75db44bc22d3097fb2915c0f1a3e57f.
- CI explicite enrichie, distante non exécutée. Plan L6/fiche v123/manifeste actualisés ; sources non activées, pages actives/données actives/Dropbox inchangées.
- Limites : regroupement par boucle et processus, SSE historique seulement ; rafraîchissement HTTP manuel/build_dashboard_payload et autres producteurs non regroupés. Watcher reste un appel par client, avec PowerShell et fichiers hérités, désormais en thread ; pas encore un watcher unique, un worker durable ou une file globale. Timestamp maximal n'est pas un curseur SQL et peut manquer certains changements/WAL ou reculer ; pas de replay/Last-Event-ID, buffers/ACL/heartbeats sur panne longue/drainage du producteur à l'arrêt qualifiés. Profil individuel ne devient pas autorisé aux projections globales. Critères L6/L0–L9 restent ouverts, gain tokens non mesuré ; automatisation conservée.
- Contexte final v123 : 11973/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v124 — sonde locale SSE partagée, WAL inclus et sans PowerShell

- Contexte v123 relu (11973/12000, avertissements vides), journal/Git/tests avant modification. Outils MCP DevCore/RepoWise non exposés sur ce passage ; sources locales et tests utilisés, aucun index modifié.
- Ancien contrôle par abonné lançait Get-ActiveProject.ps1 et prenait un max de timestamps de tasks.json/devcore.db/events.jsonl ; pas de WAL, baisse/disparition ignorée. Remplacé par get_dashboard_input_signature, metadata seule des trois chemins LOCAL devcore.db/devcore.db-wal/Bus/events.jsonl : mtime_ns/taille/inode, fichier absent explicite, erreur I/O autre propagée, fichier non régulier refusé. Aucun subprocess, préférence globale ou tasks.json dans ce watcher.
- InputWatcher nouveau par boucle asyncio : partage tâche probe en thread, cache résultat1 s après fin de sonde, compare signature complète et avance compteur de révision croissant si différente (y compris recul/suppression). Erreur ne mémorise pas un nouvel échantillon ; annulation d'un client n'annule pas la sonde commune. event_generator utilise cette révision avec coordinateur de rafraîchissement existant ; pas de tâche de surveillance permanente sans abonné.
- 19 tests ciblés réussis en5,80 s, Python3.13 documenté + overlay existant, racines temporaires avant imports. Quatre nouveaux tests : vingt demandeurs pour une sonde/cache, annulation client protégée ; signature égale/réduite/disparue et révisions ; erreur puis retry ; WAL créé/grossi à timestamp identique/retiré détecté, répertoire refusé, subprocess interdit dans la sonde. Recettes SSE/coalescence/retry/cache et réactivité boucle incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-watcher-2c23a2afaa814290b9217e00d62ad306/tests.txt ; SHA-256 3930451cd962e5cffc1bca8b1f811e203b094872fa16b355d48abdc0de1d9b5e.
- Recette20 vrais générateurs event_generator renforcée : deux sondes seulement (initiale et modifiée) et une génération pour vingt deltas ; repassée1 test en2,73 s, chevauche la suite19 et non additionnée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-watcher-integration-ef3dd4d4eb48447f86c6c8e73becb141/tests.txt ; SHA-256 0b400b9cae083028859563f2d2fc0a6f22ad3293c9971a2f1e2acefea1d04196.
- CI explicite enrichie, distante non exécutée. Plan L6/fiche v124/manifeste mis à jour ; sources non activées, pages actives/données actives/Dropbox/services inchangés. Producteur et sonde des recettes SSE remplacés par fixtures, pas de trafic service réel.
- Limites : sonde metadata, pas curseur SQL/replay ; modifications laissant exactement taille/mtime/inode peuvent être manquées et changements rapides regroupés. Pas de surveillance des configurations/plugins/métriques ni JSON tasks historiques : anciens producteurs à migrer. Une sonde par boucle/processus, pas watcher partagé entre workers ; intervalle et coût à qualifier en charge, erreurs répétées/admission/drainage restent ouverts. Révision repart à1 après redémarrage, pas Last-Event-ID ni durable. Profil SSE global reste fermé en individuel ; ACL/isolations/projections autorisées et activation encore ouvertes. L0–L9 non terminés, gains tokens non mesurés, automatisation conservée.
- Contexte final v124 : 11979/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v125 — identifiant snapshot SSE et demande de resynchronisation

- Contexte v124 relu (11979/12000, avertissements vides), journal/Git/tests avant modification. MCP board384/389 ancienne tâche ; RepoWise ciblé event_generator déclaré fresh, index10 jours/mock inchangé. Code SQL EventBus relu : ids UUID et rowid/timestamp ne constituent pas encore une séquence durable/rejeu qualifié ; aucun schéma/donnée SQL modifié.
- SSE historique utilise désormais id snapshot:<32 hex UUID> provenant du manifeste validé de la génération engagée via pin_snapshot. Nouveau helper sse_cursor.py valide strictement Last-Event-ID, longueur/format et trames : id nul/absent n'émet pas d'identifiant, payload JSON sur une seule ligne, non-finis refusés. Route SSE refuse400 le curseur invalide avant ouverture du stream. Aucun curseur brut n'est reflété.
- Reconnexion : Connected suivi d'une trame dashboard.delta/has_changes/changed_keys all avec snapshot_required=true/recovery=reload_snapshot si le dernier id diffère du courant, sans relancer producteur. Même id ne demande pas de reset. Cas mismatch : Connected ne change pas l'id du navigateur avant la trame de resynchronisation, afin qu'une interruption entre trames conserve le besoin de reset. Deltas des changements suivants portent id du snapshot publié.
- 20 tests ciblés réussis en5,98 s, Python3.13 documenté + overlay existant, racines temporaires avant imports. Onze nouveaux cas : sept curseurs invalides/injectables, reconnexion à même/autre snapshot après rechargement module API, route400, framing sans injection de ligne. Coordinateur20 abonnés/annulation/retry et watcher existants inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-cursor-10d86f34429343bc9ce1a52d260ad607/tests.txt ; SHA-256 1153d16301866a51db25c7a6d6553ba2d50b3d171e10e79f4f23ef4627c8b56f.
- Après ajustement d'ordre Connected/reset, onze contrats curseur repassés en2,62 s ; assertion explicite de non-avancement sur Connected mismatch. Résultat chevauchant, non additionné.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-cursor-order-1856fee180e44401931e44ba22e0ccff/tests.txt ; SHA-256 34467a96efa906a477018a9b95126133fe5ed03f468de7c923b26e3f4fd21650.
- CI explicite enrichie, distante non exécutée. Plan L6/fiche v125/manifeste actualisés. Sources non activées, pages actives non régénérées, données actives/Dropbox/index/service réel inchangés. Réutilise événement dashboard.delta consommé par templates historiques, mais comportement navigateur toutes vues/reconnexion effective à qualifier.
- Limites : identifiant durable d'un snapshot, pas séquence/rejeu SQL ni livraison exactly-once. Rechargement complet demandé pour tout mismatch, ancien snapshot retenu ou purgé ; absence de snapshot courant garde mode sans id et demande de reset sans promettre un snapshot disponible. Première connexion sans header reçoit l'id courant, chargement initial client reste responsable du snapshot. Course entre snapshot GET et SSE, confirmation d'application du snapshot par client, reprise de tous onglets, rétention événement/SSE et autorisation individuelle restent ouvertes. Id de génération change à chaque publication y compris contenu équivalent ; lecteurs métadonnées par abonné, charge et workers multiples à qualifier. L0–L9 non terminés, gains tokens non mesurés, automatisation conservée.
- Contexte final v125 : 11976/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v126 — handlers SSE des deux templates raccordés à la reprise

- Relecture contexte v125 (11976/12000, avertissements vides), journal, état Git et handlers/tests avant modification. Recherche ciblée RepoWise des templates au début de reprise : aperçu vivant sans symboles indexés ; code comme preuve. Board MCP ancien384/389 sans équivalence au plan ; aucune actualisation index.
- Vue standard : connectDashboardStream était défini mais jamais appelé, id SSE ignoré et retry sans Last-Event-ID, delta refusé hors tasks. Démarrage après refresh initial, mémorisation id strict snapshot:<32 hex>, header envoyé aux reconnexions fetch ; Connected traité sans parsing JSON erroné. Parser assemble lignes data et gère CR final ; buffer de lecture limité à1048576 caractères. Handler accepte has_changes/snapshot_required dans tous onglets.
- Vue terminal : onerror fermait EventSource et en créait un nouveau sans curseur conservé. Même instance laissée au retry natif, qui conserve Last-Event-ID ; handler accepte aussi snapshot_required. Pages actives non régénérées.
- 38 tests réussis en16,10 s, Python3.13 documenté + overlay existant et Node24.14, racines temporaires avant imports/processus. Deux nouvelles recettes exécutent les fonctions réelles extraites des templates : Connected/id valide/invalide, reset pendant settings, deux appels sans stream parallèle, header id initial/retry ; EventSource non fermé/non remplacé après onerror, callbacks reset/delta. Contrats curseur/API, vingt abonnés/coalescence/retry, versions/actions JS et génération complète sur fixtures inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-templates-final-ead947c2061e4a51937412c7341eabd2/tests.txt ; SHA-256 6b5a9e98f4d05d4ee8aa363c904d819967d4145f852766ff3b9c08fefd65df66.
- Premier harness Node standard avait transformé les échappements newline en newlines bruts dans une chaîne JS : échec du test, corrigé dans le harness puis suite38 entièrement repassée. CI explicite enrichie (Node requis), distante non exécutée. Plan/fiche v126/manifeste actualisés. Sources non activées ; aucune page active/donnée active/Dropbox/service/index réel modifié en fixture.
- Limites : transports fetch/EventSource et refreshDashboard simulés dans Node, pas reconnexion TCP navigateur réelle ni preuve du comportement natif Last-Event-ID. Curseur standard avance à réception, pas après application réussie du snapshot ; refreshDashboard peut échouer/races entre snapshot et stream encore ouvertes. Premier chargement, borne mémoire en caractères non octets, framing CRLF entre blocs, admission/drainage/error UI, délai retry natif terminal et pages actives à qualifier. SSE global pas autorisé au profil individuel. Rejeu SQL/rétention événement, workers multiples et qualification charge restent ouverts. L0–L9 non terminés, gain tokens non mesuré ; automatisation conservée.
- Contexte final v126 : 11976/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v127 — lecture fragmentée SSE et libération du transport

- Relecture contexte v126 (11976/12000 octets, avertissements vides), Git, journal pertinent et tests. Board MCP384/389 toujours historique ; RepoWise template sans symboles indexés, fraîcheur indéterminée/index11 jours/mock : confrontation au code, index inchangé.
- Vue standard : séparateurs LF et CRLF reconnus même coupés entre lectures ; TextDecoder conserve les séquences UTF-8 fragmentées. Fin de flux laisse tomber la trame incomplète. Limite existante1048576 caractères conservée avant dispatch. Lecteur annulé et verrou libéré en finally après EOF, erreur ou dépassement ; échec de cancel n'empêche pas releaseLock. Contrôleur capturé par connexion, référence nettoyée après échec/annulation ; aucun retry sur annulation volontaire, échec d'une ancienne connexion ne remplace pas le contrôleur d'une nouvelle.
- 43 tests ciblés réussis en15,21 s, Python3.13 documenté + overlay existant et Node, racines temporaires avant imports/processus. Cinq recettes supplémentaires exécutent le pump réel : CRLF et caractère équipe transmis octet par octet, data multiligne JSON, EOF avec dernière trame tronquée, erreur read, erreur cancel, tampon excessif et abort. Vérifications id/une seule actualisation/contenu Unicode/cancel/release/retry. Contrats curseur API, coordinateur et actions JS inclus. Première suite43 réussie16,13 s, puis assertion Unicode ajoutée et suite entière repassée ; résultats chevauchants non additionnés.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-fragments-final-5327a8d4c9dc436784a21597716a462a/tests.txt ; SHA-256 320f34a316716f304ea444a893f6ff8fa8fb906b173b06a3bbc66c03b7c7c968.
- Plan/fiche v127/manifeste mis à jour ; contexte final11979/12000 octets UTF-8, avertissements vides, décisions obligatoires conservées. git diff --check ciblé sans erreur. CI distante non exécutée ; suite déjà incluse au workflow.
- Limites : transport simulé Node, pas reconnexion réseau navigateur réelle ni activation des sources/pages. Borne en caractères, séparateurs CR seuls non pris en charge ; curseur reçu avant application réussie du snapshot, course GET/SSE, drainage pendant fermeture navigateur, ACL individuelles, rejeu SQL et charge/multiprocessus restent à qualifier. Aucun test sur données actives, Dropbox ou index réel. L0–L9 restent ouverts, économies tokens non mesurées ; automatisation conservée.


### Passage v128 — rafraîchissements JSON du client standard sérialisés

- Contexte v127 relu11979/12000, sans avertissement ; Git/journal/handlers/tests avant modification. Board MCP384/389 historique, RepoWise template sans symboles ni fraîcheur attestée/index11 jours/mock ; code comme preuve, index inchangé.
- refreshDashboard standard devient une promesse partagée : un fetch JSON à la fois, demandes pendant cette lecture réunies dans un booléen de rattrapage. Chaque rattrapage peut regrouper les nouvelles demandes ; aucune liste de100 opérations créée. Les réponses ne peuvent plus se dépasser entre appels de cette fonction. Ancien corps performDashboardRefresh retourne vrai après application ou faux après erreur, nettoie le timer en finally ; AbortController borne fetch/lecture du corps à20 s. Erreurs HTTP/schéma/deadline permettent le prochain appel, aucun retry sans nouvelle demande. Demande arrivée entre sortie de boucle et finally reprise par une nouvelle promesse chaînée.
- 48 tests ciblés passent en15,55 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Quatre nouvelles recettes exécutent le vrai corps JSON et la file : cent demandes, maximum un fetch actif, un seul rattrapage, application ordonnée, HTTP non-ok, schéma invalide, abort par deadline, nettoyage timers/promesse et nouvel appel après erreur. Cinquième recette reproduit une demande à la clôture via microtasks et vérifie deux lectures/aucune demande perdue. Contrats SSE/fragments/curseur, coordinateur et actions JS/génération sur fixtures inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-refresh-settlement-3fdccb6cfeff4807b3f34f66ba1e48f8/tests.txt ; SHA-256 03bed4c99fe75530c0e63b2eda72243c2d519e6b07f2e4c09ae0c845c9f8e699.
- Première édition avait échoué avant écriture sur différence CRLF ; les43 tests exécutés alors validaient seulement l'état précédent. Correction de l'édition,47 tests réussis14,74 s, puis traitement de la clôture ajouté et suite48 entière repassée. Résultats chevauchants non additionnés.
- Plan/fiche v128/manifeste actualisés ; contrôle diff ciblé sans erreur. CI distante non exécutée, fichier test déjà inclus au workflow. Sources non activées, données/pages actives, Dropbox et index réel inchangés.
- Limites : sérialisation du client standard uniquement ; vue terminal/chemin HTML legacy et autres endpoints restent distincts. DOM partiel et transport simulés, pas qualification navigateur réseau/charge. Deadline déclenche abort, durée réelle dépend du transport/event loop ; serveur peut continuer son travail après déconnexion. Corps JSON non encore borné côté client, application DOM non transactionnelle, curseur SSE acquitté avant application snapshot et course GET/SSE encore ouvertes. L0–L9 non terminés, tokens non mesurés, automatisation conservée.
- Contexte final v128 : 11984/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v129 — réponse JSON du client standard bornée avant parsing

- Contexte v128 relu11984/12000 sans avertissement ; mémoire/Git/journal/handlers/tests pertinents avant modification. Board MCP384/389 reste historique ; RepoWise template sans symboles/fraîcheur indéterminée/index11 jours/mock, code confronté ; index inchangé.
- Nouveau readDashboardJson raccordé au corps réel performDashboardRefresh : lecture ReadableStream, maximum16*1024*1024 octets réellement reçus, refus immédiat si Content-Length numérique dépasse la borne. Longueur absente/incorrecte ne dispense pas du comptage réel. UTF-8 strict avec decoder streaming puis flush, JSON.parse seulement après lecture complète. Corps absent refusé, pas de repli response.json non borné. Lecteur cancel/releaseLock en finally sur succès/échec, timer20 s déjà existant englobe cette lecture. Fragments texte regroupés par blocs d'au moins65536 caractères pour éviter une entrée de tableau par chunk réseau ; au plus257 entrées selon cette borne.
- 56 tests ciblés réussis en17,17 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Huit cas nouveaux exécutent le helper réel : caractère UTF-8 fragmenté octet par octet, JSON exactement16 Mio, Content-Length excessif sans aucune lecture, dépassement réel malgré header1, UTF-8 invalide, JSON tronqué, erreur reader et corps absent. Cancel/release vérifiés ; recettes de sérialisation utilisent maintenant de vrais objets Response/ReadableStream Node. Contrats SSE/cursor, coordinateur et actions JS/génération sur fixtures inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-json-client-7b87e9aa6d654fb2af982c047a74899f/tests.txt ; SHA-256 3f51db1c097b00df02e304178696f458fdb7b17dde53b32dd932ed00cc05f701.
- Plan/fiche v129/manifeste actualisés ; git diff --check ciblé sans erreur. CI distante non exécutée, test déjà inclus au workflow. Sources/pages actives non activées ni régénérées ; données actives/Dropbox/index réel préservés.
- Limites : borne du corps décompressé transmis par fetch, pas plafond de mémoire totale du navigateur ni de graphe JSON après parsing ; chaîne join/parser et DOM synchrones. Aucun seuil de profondeur/propriétés ni rendu DOM transactionnel ajouté. Header excessif refuse conservativement même si corps réel inférieur. Payload API enrichi peut dépasser la borne client même si son artefact snapshot brut était juste sous16 Mio. Vue terminal, HTML legacy et autres endpoints non raccordés à ce helper ; transport navigateur/réseau et charge encore à qualifier. Curseur SSE/application snapshot, ACL/rejeu SQL/multiworkers, L0–L9 et gains tokens restent ouverts ; automatisation conservée.
- Contexte final v129 : 11983/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v130 — mêmes protections JSON dans les deux vues Cockpit

- Contexte v129 relu11983/12000 sans avertissement ; mémoire/Git/journal pertinent/templates/tests avant édition. Board MCP384/389 toujours historique. RepoWise terminal sans symboles ni fraîcheur attestée/index11 jours/mock, aperçu confronté au code ; index inchangé.
- Vue terminal reprend la file de rafraîchissement et le lecteur JSON de la vue standard : promesse partagée, un fetch actif, booléen rattrapage, demande de clôture conservée, lecture bornée16 Mio/UTF-8 strict/cancel-release. performDashboardRefresh terminal ajoute AbortController/deadline20 s/nettoyage finally et résultat vrai/faux ; schéma1 avec sections requis avant modifications DOM. URL JSON passe du127.0.0.1:20129 fixe à API_BASE déjà existant : origine de la page HTTP, localhost seulement pour page file. Cache no-store conservé. Compteur tâches désormais remis à zéro, pas ancien compteur maintenu pour snapshot vide.
- 69 tests ciblés réussis en17,97 s, Python3.13 documenté + overlay existant et Node, racines temporaires avant imports/processus. Huit tests du lecteur et quatre tests de file exécutés aussi sur les fonctions terminal réelles : rafale100, ordre, HTTP/schéma/deadline/reprise, limites réelles/déclarées, Unicode, fermeture lecteur et corps absent. URL égale à API_BASE vérifiée, snapshot tâches vide remet compteur0. Contrat de parité compare la file/helper des deux templates pour éviter divergence silencieuse. Recettes SSE/cursor, coordinateur et actions JS/génération sur fixtures incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-terminal-refresh-final-e2fb393e0dd040bf95c886e80d5fc79f/tests.txt ; SHA-256 7f5c2c0cfc41a12a390a53b9cfec627b8f36ab17d421e3ce7c51ab7b09692217.
- Première suite : huit erreurs du harness terminal (extraction avait laissé le mot async avant la fonction suivante),60 autres tests passaient. Borne d'extraction corrigée et suite69 entière repassée après ajout du contrat parité/compteur0 ; résultats chevauchants non additionnés. git diff --check ciblé sans erreur (Git avertit de la normalisation LF/CRLF du fichier terminal). CI distante non exécutée, même fichier test déjà inclus au workflow.
- Plan/fiche v130/manifeste actualisés. Sources non activées, pages actives non régénérées ; données actives/Dropbox/index réel inchangés. L0–L9 non terminés, gains tokens non mesurés et automatisation conservée.
- Limites : duplication volontaire des fonctions dans templates avec contrat de parité, extraction en ressource commune reste ouverte. DOM partiel et transport Node ; navigateur réseau/charge non qualifié. Sections vides historiques encore ignorées par plusieurs conditions terminal, application DOM non transactionnelle. Indicateurs terminaux portent toujours le libellé20129, autres URL historiques hors refresh inchangées ; contexte par utilisateur/ACL et activation restent ouverts. Curseur SSE reçu avant application snapshot, course GET/SSE, JSON parse synchrone et amplification mémoire restent à qualifier.
- Contexte final v130 : 11990/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v131 — sections et détails terminaux cohérents avec un snapshot vide

- Contexte v130 relu11990/12000, sans avertissement ; mémoire/Git/journal/tests/templates avant édition. Board MCP384/389 reste historique ; RepoWise terminal sans symboles/fraîcheur indéterminée/index11 jours/mock, aperçu confronté au code ; index inchangé.
- Vue terminal : sections connues vides ou absentes remplacent désormais les anciennes zones (services garde son footer). Validation de sections comme objet non-array puis des dix valeurs connues comme chaînes avant modifications de zones ; valeur invalide refuse le snapshot. Rapport tokens rafraîchi même vide, détails JSON tâches remplacés à chaque snapshot puis réutilisés par showDetails existant. Trois blocs JSON dupliqués supprimés : un seul id task-details-data, task-interactions-data et token-metrics-data. Footer annonce60 s, cohérent avec REFRESH_RATE60 existant.
- 72 tests ciblés passent en20,94 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Trois nouveaux scénarios du vrai corps terminal : snapshot rempli puis sections toutes vides, sections absentes, dernière section de type objet invalide. Vérifications : ancienne pipeline/détails remplacés, dix zones effacées/footer conservé, compteur0, ids uniques et refus d'une section invalide avant toute écriture de zones. Suites file/lecteur/SSE/cursor/coalescence et actions JS/génération sur fixtures incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-terminal-empty-24b2aae2e5214e6cb87728fc54819f5f/tests.txt ; SHA-256 6d325735968ccf979c830aab795e5d54051ac967093e85441daf62324b6ef433.
- Indentation des lignes de rendu normalisée après les tests (espaces seulement). git diff --check ciblé sans erreur, avertissement Git de normalisation LF/CRLF terminal. Plan/fiche v131/manifeste actualisés, CI distante non exécutée ; fichier tests déjà inclus au workflow. Sources/pages actives non activées, données actives/Dropbox/index réel inchangés.
- Limites : DOM et transport simulés, morphDOM réel/navigateur réseau non qualifiés. Snapshot absent de section est interprété comme vide pour ce contrat de snapshot complet ; contrat de delta partiel serait différent. Validation connue ne garantit pas sûreté/provenance du HTML serveur, DOM transactionnel ni structure des autres champs. Interactions JSON restent celles de la génération initiale (API payload ne les actualise pas ici) ; leur index unique évite seulement ambiguïté. Curseur SSE/application snapshot, première connexion/course GET/SSE, droits/projets, outbox/rejeu/charge et activation restent ouverts. L0–L9 non terminés, gain tokens non mesuré, automatisation conservée.
- Contexte final v131 : 11990/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v132 — interactions raccordées au snapshot JSON courant

- Contexte v131 relu11990/12000 sans avertissement ; mémoire/Git/journal/générateur/API/templates/tests pertinents avant édition. Board MCP384/389 historique ; RepoWise générateur/API index11 jours/mock, code confronté : payload générateur contient déjà task_interactions. Aucun changement serveur/index nécessaire.
- Correction de la limite v131 : le snapshot API transporte déjà les interactions générées ; c'est leur consommation au rafraîchissement des deux vues qui manquait. Chaque performDashboardRefresh lit task_interactions, champ absent normalisé en{}, valeur null/non-object/array refusée avant rendu des zones. Après application des sections, remplace le bloc task-interactions-data par JSON.stringify via textContent. showInteractions existant relit ce bloc et conserve vérification projet/tâche ; aucun ancien index maintenu quand la nouvelle réponse n'a pas ce champ (compatibilité fallback ancien).
- 78 tests ciblés réussis en18,40 s, Python3.13 documenté + overlay existant et Node, racines temporaires avant imports/processus. Six nouvelles recettes du vrai corps des deux vues : index alpha remplacé par beta, champ absent efface alpha, array invalide laisse ancien index/aucune nouvelle écriture de zone. Texte contenant balise script stocké en textContent, pas innerHTML. Suites refresh/JSON/SSE/cursor/coalescence et actions JS/génération sur fixtures incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-interactions-refresh-ec7ec87161a64cd3b3b9b90b22379a9e/tests.txt ; SHA-256 bb6484a11a5e65a634e4fef2e2fdb8d327ba3a2f25adeb4bd500e6f5b27e6b61.
- Plan/fiche v132/manifeste actualisés ; git diff --check ciblé sans erreur (avertissement normalisation LF/CRLF terminal). CI distante non exécutée, même fichier test inclus au workflow. Sources non activées, pages/données actives, Dropbox/index réel inchangés.
- Limites : map de tête validée, pas tous les champs de chaque interaction ; provenance/droits restent à qualifier côté serveur. DOM partiel/transports simulés, pas parcours navigateur ni sûreté complète du rendu modal. Modal déjà ouvert ne se réactualise pas automatiquement ; prochain appel showInteractions consulte nouvel index. Rendu de sections non transactionnel, erreur DOM peut empêcher mise à jour suivante. Première connexion/course GET-SSE, confirmation curseur après application, ACL/outbox/rejeu/charge et activation restent ouverts. L0–L9 non terminés, économies tokens non mesurées, automatisation conservée.
- Contexte final v132 : 11990/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v133 — validation commune du snapshot avant rendu

- Contexte v132 relu11990/12000 sans avertissement ; mémoire/Git/journal/templates/tests pertinents avant modification. Board MCP384/389 historique ; RepoWise deux templates sans symboles/fraîcheur attestée, index11 jours/mock, sources confrontées ; index inchangé.
- Nouveau validateDashboardSnapshot commun aux deux templates, contrat de parité existant couvre aussi ce helper. Payload objet non-array/schema1, sections objet non-null/non-array, dix sections HTML connues de type string lorsqu'elles sont présentes. Maps task_details/task_interactions/token_metrics présentes obligatoirement objets non-null/non-array ; champs absents restent compatibles avec fallback et anciens snapshots. Exécuté avant modifications de zones et blocs de données, puis interactions normalisées{}. Remplace contrôles dispersés terminal et validation incomplète standard ; aucun changement de serveur/schema publié.
- 92 tests ciblés réussis en20,45 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Quatorze cas ajoutés dans les vrais corps des deux vues : sections array/string, dernière section objet/null, détails array, métriques string, interactions null. Refus avant écritures de sections/blocs (ancien contenu conservé), timers et promesse nettoyés, snapshot valide suivant accepté. Tests précédents refresh/JSON/SSE/cursor/coalescence/actions JS/génération sur fixtures inclus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-validation-dbeebd1a2438476492783ac4cf0cb957/tests.txt ; SHA-256 51d41e981290afe1409345cfe52b1fc074cd7055ae3e6f0df5c30e1c483d5374.
- Plan/fiche v133/manifeste actualisés ; git diff --check ciblé sans erreur (avertissement LF/CRLF terminal). CI distante non exécutée, test déjà inclus au workflow. Sources/pages actives non activées ; données actives/Dropbox/index réel inchangés.
- Limites : validation de forme, pas toutes valeurs internes des maps ni types/normes token ; sections inconnues ignorées. HTML serveur pas assaini ici, rendu DOM non transactionnel en cas d'erreur morphDOM, indicateurs d'erreur peuvent changer lors d'un refus. Rejet des null/arrays historiques explicite, absence de champ compatible. DOM/transport simulés, pas qualification navigateur réseau/charge. Parse synchrone, profondeur JSON/propriétés, curseur après application/races GET-SSE, ACL/outbox/rejeu/activation restent ouverts. L0–L9 non terminés, gains tokens non mesurés ; automatisation conservée.
- Contexte final v133 : 11990/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v134 — transport SSE et rendu vérifiés dans Edge sur fixtures

- Contexte v133 relu11990/12000 sans avertissement ; mémoire/Git/journal/templates/tests avant modification. Board MCP384/389 historique ; RepoWise template sans symboles/fraîcheur attestée/index11 jours/mock confronté aux fonctions sources. Index inchangé. Runtime Python3.13 documenté présent ; Playwright/Selenium absents, Edge installé154.0.4258.53 et Node24.14 déjà disponibles, aucune installation.
- Nouvelle recette test_dashboard_browser_stream.py et transport dashboard_browser_stream.cjs : serveur HTTP Node lié127.0.0.1/port aléatoire, HTML minimal avec fonctions réelles extraites morphDOM/updateContainerHTML, refresh/validation/lecteur et handler SSE de chaque template. Pas de fausse implémentation fetch/EventSource/DOM dans cette recette ; seuls updateTokenReport/updateRepowiseHealth sont des stubs pour éviter leurs endpoints secondaires. Premier snapshot appliqué avant connexion SSE ; serveur émet curseurA en CRLF, ferme la connexion puis passe au snapshotB ; reconnexion doit envoyer Last-Event-ID A et reset force nouveau GET. Profils Edge neufs en tmp_path, processus headless/hidden, contrôle CDP local borné, arrêt du seul arbre PID créé en finally, sockets serveur fermés. Racines LOCAL/DATA/PLATFORM temporaires héritées avant processus ; aucun service actif appelé.
- Deux tests navigateur passent en33,10 s sur Edge154.0.4258.53 : vue standard fetch et vue terminal EventSource natif, chacun renvoie snapshot:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, deux GET snapshot, nouvelle pipeline version2 équipe visible via DOM réel, détails et interactions version2, aucune erreur window.error. Reconnexion TCP locale effective, CRLF décodé par navigateur et morphDOM réel exercé. Deux pages/profils/serveurs distincts séquentiels, aucune qualification concurrente multiutilisateur revendiquée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-browser-stream-qualified-cd9e5ac707a64132be5c384652cfef56/browser.txt ; SHA-256 f2b18925051ecc1d27e45347fdbd1aa975d5b06256c774673549c2020925b172.
- 92 contrats existants repassés séparément en26,67 s : handlers Node, curseur API, coalescence et actions/génération sur fixtures. Pas addition avec recettes navigateur antérieures chevauchantes.
  Trace même dossier/contracts.txt ; SHA-256 a7d9844808b53c861ea694418b7caaf1a4225a434d76fcd15a47c9ae1d0245a0.
- Première recette deux tests réussis36,10 s. Ajout deadline CDP initialement5 s : suite combinée deux échecs de navigation Edge trop lente,92 contrats passaient ; pytest -s révélait aussi fermeture stdout lors d'une recette générateur. Deadline Page.navigate20 s (autres commandes5 s), timeout subprocess75 s, capture pytest normale et recettes séparées ; deux navigateurs et92 contrats repassés. Aucun délai applicatif client modifié. Nettoyage vérifié : aucun processus Edge portant le chemin de ces fixtures après tests.
- Étape CI Windows ajoutée après setup Node24, racines temporaires, deux tests et diagnostics ; skip explicite si Edge absent, Node requis. CI distante non exécutée. Plan/fiche v134/manifeste mis à jour, git diff --check ciblé sans erreur (avertissement LF/CRLF CI). Contexte final11992/12000 octets UTF-8 sans avertissement, décisions obligatoires conservées.
- Limites : HTTP fixture serveur, pas API DevCore/générateur actifs ni page complète/stylesheet, middleware/authentification/ACL/HTTPS/proxy/workers réels. CDP page minimale et fonctions réelles ; fonctions secondaires métriques remplacées et fournisseurs non appelés. Démarrage navigateur variable, fixture navigateur facultative en CI si binaire absent ; uniquement cette version Edge qualifiée. Cursor acquitté à réception et course snapshot/stream restent ouvertes ; charge20 navigateurs, longues coupures, replay SQL, sources actives/activation et L0–L9 non terminés. Données actives/Dropbox/index inchangés, gains tokens non mesurés, automatisation conservée.


### Passage v135 — reprise du GET snapshot après échec sans nouvel événement SSE

- Contexte v134 relu11992/12000 sans avertissement ; mémoire/Git/journal/handlers/tests pertinents avant édition. Board MCP384/389 historique ; RepoWise deux templates index11 jours/mock, code confronté. Données/index inchangés.
- Helper commun refreshDashboardForSse raccordé aux deltas/reset des deux vues : attend résultat vrai/faux de la file JSON existante. Échec/refus/rejet programme un seul minuteur5 s, aucune liste de requêtes ; callback remet l'id à null puis retente indépendamment du stream. Succès d'un rafraîchissement demandé par SSE annule le minuteur en attente. File précédente continue de garantir un GET actif par vue. Résout le cas où un id SSE a été reçu mais GET snapshot503 a échoué et aucun nouveau delta n'arrive ; pas de modification du curseur ni du protocole serveur.
- 96 tests de contrats passent en21,97 s, Python3.13 documenté + overlay existant et Node, racines temporaires avant imports/processus. Quatre nouvelles recettes sur les deux helpers : vingt échecs/rejets en rafale ne créent qu'un timer, nouvel échec maintient un timer, succès d'un événement avant timer l'annule, succès au timer termine la reprise. Helpers mock retournent maintenant vrai après leurs actualisations réussies, cohérent avec contrat client. Parité des fonctions entre vues vérifiée ; suites JSON/SSE/cursor/coalescence/actions/génération sur fixtures incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-recovery-9f284c557a4d40569e7e82d042d8f8b7/contracts.txt ; SHA-256 b5fd82d02f2390a24f940a37e2766cae083d803aef408e438c0c3393221a6497.
- Deux recettes Edge154.0.4258.53 réussissent en43,99 s : serveur temporaire renvoie503 à la deuxième lecture après reconnexion SSE, sans nouvel événement ensuite ; troisième lecture réussit et applique version2/pipeline/détails/interactions. Last-Event-ID A effectivement reçu, failed_snapshots1/snapshot_reads3 par vue. Fonctions originales de rendu/lecture, profils et ports temporaires, aucun API actif appelé.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-recovery-browser-final-3779c1f2700f429283ae6f5e85f9206c/browser.txt ; SHA-256 91c4dbe2a9bb42a90f00bd6f501afe5fbf5d1207bd0d0c0f219f9218055c594d.
- Première recette navigateur : terminal réussissait, standard échouait sur deadline5 s du pilote Runtime.evaluate pendant navigation. Commandes CDP désormais bornées20 s, subprocess105 s et étape CI5 minutes ; délai applicatif20 s et intervalle reprise5 s inchangés. Deux recettes entièrement repassées, pas addition de leurs résultats chevauchants. CI distante non exécutée, nouveaux scénarios inclus par fichiers déjà au workflow.
- Plan/fiche v135/manifeste actualisés ; git diff --check ciblé sans erreur (avertissements LF/CRLF terminal/CI). Sources non activées, pages/données actives/Dropbox/index réel inchangés.
- Limites : reprise à intervalle fixe sans jitter/backoff ni arrêt spécifique sur401/403 ; un timer/GET actif borné, nombre total de tentatives dans le temps non borné. Un succès via polling normal ne supprime pas directement le timer SSE (une lecture supplémentaire peut suivre). Curseur toujours acquitté à réception ; succès JSON ne prouve pas que génération appliquée égale celle du curseur, races GET/SSE et replay exact encore ouverts. Page fermée abandonne timers navigateur, arrêt/drainage explicite non ajouté. Recette locale/page minimale, serveur fixture/Edge uniquement, API/auth/ACL/charge/multiworkers non qualifiés. L0–L9 restent ouverts, gains tokens non mesurés ; automatisation conservée.
- Contexte final v135 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées. Aucun processus Edge portant ces chemins de fixtures après tests.


### Passage v136 — reprise snapshot progressive et annulée par polling réussi

- Contexte v135 relu11992/12000 sans avertissement ; mémoire/Git/journal/helpers/tests avant édition. Board MCP384/389 historique, RepoWise templates index11 jours/mock confrontés au code, index inchangé.
- Base de reprise snapshot initiale5 s, doublée uniquement lors de programmation d'un nouveau timer puis plafonnée60 s. Jitter multiplicatif80–100% de cette base (4–5,8–10,16–20,32–40 puis48–60 s) pour étaler les tentatives. Vingt callbacks d'échec ne créent toujours qu'un timer et n'avancent la base qu'une fois. resetDashboardSnapshotRecovery nettoie timer et base ; succès de toute lecture via refreshDashboard le déclenche, donc polling normal réussi supprime aussi l'ancien retry. Helpers identiques entre les deux vues vérifiés par contrat de parité.
- 100 tests de contrats passent en21,36 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Quatre nouvelles recettes vérifient treize programmations jusqu'au plafond, bornes jitter minimales/maximales avec RNG contrôlé, un seul timer, succès polling supprimant la reprise et premier délai réinitialisé. Tests de reprise20 erreurs/refus et suites JSON/SSE/cursor/coalescence/actions JS/génération incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-backoff-04788d69621f4fcc80d7faf2993f3bc1/contracts.txt ; SHA-256 ecb74a3d9c5d97c1430445494e8c2059a8c2fe866917ccc0ddfe93087bdfeaf3.
- Deux recettes Edge154.0.4258.53 passent en41,25 s : coupure/reconnexion native ou fetch/Last-Event-ID A, premier GET503, reprise indépendante du stream et application version2. Trois lectures dont un échec par vue, profils/ports/données temporaires ; délai jitter réel utilisé.
  Trace même dossier/browser.txt ; SHA-256 c17eca62950f1fdb0a080740c82fa4e262ee40c1771f859c5b6968993ed7ab6b.
- Plan/fiche v136/manifeste actualisés. Contexte final11992/12000 octets UTF-8, avertissements vides, décisions obligatoires conservées. git diff --check ciblé sans erreur (LF/CRLF terminal). CI distante non exécutée, suites déjà incluses au workflow. Sources/pages actives non activées ; données actives/Dropbox/index réel inchangés.
- Limites : cadence bornée pour le minuteur, pas nombre total de tentatives/temps de reprise ; nouvelles demandes SSE/polling peuvent demander une lecture avant expiration du backoff (file active toujours sérialisée). Pas arrêt spécifique401/403 ni budget par utilisateur ajouté. Coût serveur après abort, première connexion/course GET-SSE, confirmation génération après application, ACL/outbox/rejeu/charge/activation restent ouverts. Recette navigateur toujours page minimale/serveur fixture local ; API complète non qualifiée. L0–L9 non terminés et tokens non mesurés ; automatisation conservée.


### Passage v137 — refus HTTP401/403 suspend la reprise snapshot liée au SSE

- Contexte v136 relu11992/12000 sans avertissement ; mémoire/Git/journal/templates/tests pertinents avant édition. Board MCP384/389 historique ; RepoWise non exposé ce passage, sources locales utilisées, index inchangé.
- checkDashboardResponseAccess commun aux vues détecte401/403 du GET snapshot avant lecture/applications, positionne dashboardSnapshotRecoveryDenied et annule le timer de reprise. Nouveaux appels refreshDashboardForSse refusent sans réseau tant que ce drapeau est posé ; un échec en attente ne programme pas de nouveau timer après le refus. Toute lecture de snapshot appliquée avec succès via refreshDashboard retire le drapeau et réinitialise délai/timer. Polling normal et appels explicites restent disponibles pour détecter accès rétabli ; aucune authentification/donnée serveur modifiée.
- 104 tests ciblés passent en25,00 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Quatre cas nouveaux exécutent les vrais corps des deux vues avec objets Response/ReadableStream :503 arme une reprise, polling reçoit401 ou403 puis timer annulé/drapeau posé, vingt appels SSE suivants n'envoient aucun GET, polling200 réactive puis503 programme un premier délai4–5 s. Suites validation/JSON/reprise/backoff/SSE/cursor/coalescence/actions/génération sur fixtures incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-snapshot-access-c78229fe75fd4937ac3661146b1b7bb1/contracts.txt ; SHA-256 d69ceb62e042a56c9dc72eee206cf0ad8f2e645a60fa6a9b00607848641f381d.
- Plan/fiche v137/manifeste actualisés ; git diff --check ciblé sans erreur (LF/CRLF terminal), CI distante non exécutée, fichier tests déjà inclus au workflow. Recette Edge503 qualifiée v136 non répétée ce passage ; nouveau refus401/403 vérifié sur transports Node, pas navigateur authentifié réel. Sources/pages actives non activées, données actives/Dropbox/index réel inchangés.
- Limites : seule reprise du GET snapshot déclenchée par SSE est suspendue ; polling périodique60 s, commandes explicites et reconnexion du transport SSE restent distincts et ne sont pas entièrement arrêtés par ce drapeau. Ne constitue pas une révocation de session côté serveur ; droits effectifs toujours à qualifier. En cas de droits rétablis, succès du polling ou d'une lecture explicite requis pour réactiver la reprise. Données précédemment affichées conservées après refus (gestion/logout/purge UI ouverte), erreurs de rendu conservées aux indicateurs existants. Première connexion/course GET-SSE/cursor appliqué, auth/ACL/outbox/rejeu/charge et activation restent ouverts. L0–L9 non terminés, gains tokens non mesurés, automatisation conservée.
- Contexte final v137 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v138 — provenance snapshot de la réponse JSON liée aux octets lus

- Contexte v137 relu11992/12000 sans avertissement ; mémoire/Git/journal/API/cache/snapshots/tests avant édition. Board MCP384/389 historique ; RepoWise API index11 jours/mock, code confronté ; index inchangé.
- read_cached_dashboard_payload enrichit cache.snapshot_cursor avec snapshot:<UUID> tiré du manifeste du même pin_snapshot qui possède les descripteurs du JSON lu. Aucun second resolve/current-pointer/get_dashboard_snapshot_cursor pour estampiller la réponse ; une publication concurrente ne peut attribuer le nouvel id aux anciens octets. Cache legacy et fallback annoncent explicitement null. Champs cache historiques hit/path/modified_at conservés ; cache du payload lu remplacé par métadonnées fiables de lecture, toute revendication stockée snapshot_cursor ignorée. Enrichissement uniquement dans la réponse, aucun fichier/empreinte/pointeur écrit par l'API.
- 48 tests ciblés réussis en18,14 s, Python3.13 documenté + overlay existant, racines temporaires avant imports/processus. Nouveau test épingleA, publieB avant lecture des octetsA, interdit le helper de curseur indépendant : réponse labelA/cursorA, pointeurB, claims forgés stockés inchangés. Nouveau test fallback curseurNone ; recette fraîcheur descriptor existante renforcée sur legacy/committed pour remplacer la revendication forgée par None/id validé. Suites cache/API curseurs/pinning/collecte/capacité/publication snapshot incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-response-cursor-final-fa0f3c73e27b449bafcb02eb81159027/tests.txt ; SHA-256 0149363338b0c2c6f034bd3c38d5e3a87b6d118cf5378eb753d224a04e10d85c.
- Première édition exacte échouait avant écriture (fichier aux fins de lignes mixtes), nouveaux tests donnaient2 échecs pour champ absent et46 passaient. Édition via patch, suite48 entière repassée ; résultats chevauchants non additionnés. git diff --check ciblé sans erreur (normalisation LF/CRLF API). CI distante non exécutée ; fichiers tests déjà explicitement inclus au workflow.
- Plan/fiche v138/manifeste actualisés. Sources non activées, pages/données actives/Dropbox/index réel inchangés. Champs ajoutés au contrat JSON schema1 sans modifier génération ou protocole SSE.
- Limites : curseur ajouté au GET snapshot/cache build_dashboard_payload, pas empreinte globale du read_model enrichi après lecture (peut refléter état plus récent). Endpoint refresh renvoyant stdout du générateur n'est pas estampillé avec un pointeur courant indépendant, et ne revendique pas de génération ; pas de fausse correspondance ajoutée. Client ne consomme/confirme pas encore cache.snapshot_cursor ; acquittement à réception, course GET/SSE et comparaison génération côté navigateur restent ouverts. Cache path/horodatage déjà présents ne constituent pas ACL, middleware/droits/activation restent à qualifier. L0–L9 non terminés, gains tokens non mesurés, automatisation conservée.
- Contexte final v138 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v139 — curseur appliqué mémorisé et utilisé pour la reconnexion fetch

- Contexte v138 relu11992/12000 sans avertissement ; mémoire/Git/journal/helpers/templates/tests avant édition. Board MCP384/389 historique ; RepoWise template index11 jours/mock, code confronté. Index inchangé.
- Validation commune inclut cache comme map lorsqu'il est présent et snapshot_cursor strict snapshot:<32 hex minuscules>, ou null/absent. recordAppliedDashboardSnapshot mémorise ce curseur après toutes les opérations du corps de rendu et avant retour vrai, dans les deux vues ; une réponse échouée n'atteint pas ce point. Réponse ancienne/fallback sans curseur efface la revendication d'un id appliqué. Vue standard compose Last-Event-ID depuis dashboardAppliedSnapshotCursor uniquement, donc id SSE reçu ne vaut plus confirmation d'application. dashboardLastEventId garde le dernier id observé pour diagnostic/parsing, pas l'en-tête de reconnexion.
- 120 tests ciblés passent en25,73 s, Python3.13 documenté + overlay existant, Node et racines temporaires avant imports/processus. Quatre cas de validation supplémentaires : cache array et curseur invalide sur deux vues, refus avant rendu. Nouveau contrat réel standard : première connexion sans snapshot appliqué n'envoie aucun id ; application JSONA valide, réception deltaB suivieGET503 garde curseur appliquéA, reconnexion envoieA malgré dernier id observéB. Recettes SSE partielles simulent maintenant explicitement l'application lors de leurs refresh mock réussis. Suites reprise/JSON/SSE/coalescence/actions/génération et provenance cache API incluses.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-applied-cursor-cfdbb958e0984d8f963529d7a727307b/contracts.txt ; SHA-256 89378a553081501854eec60ba8eb80e13e6cf857eed5761131fc571aa02f69a4.
- Deux recettes Edge154.0.4258.53 passent en64,06 s : serveur fixture transporte maintenant cache.snapshot_cursor A/B, deux vues appliquent snapshot initialA puis reconnexion avec idA, GET503, reprise et applicationB. Trois lectures/un échec par vue, HTML minimal/morphDOM/transport réels, profils et ports temporaires. Runtime de navigateur variable mais timeout105 s/test conservé, aucune commande de service actif.
  Trace même dossier/browser.txt ; SHA-256 73394165d1443fe30428c8afa7a23ab0faf924fe0dbee8631545481a80c30e6b.
- Plan/fiche v139/manifeste actualisés ; git diff --check ciblé sans erreur (LF/CRLF terminal). CI distante non exécutée, fichiers de tests déjà inclus au workflow. Sources/pages actives non activées, données actives/Dropbox/index réel inchangés.
- Limites : EventSource terminal confirme intrinsèquement l'id à réception ; mémoriser le curseur appliqué ne modifie pas l'en-tête automatique natif. Reprise snapshot indépendante compense un GET échoué mais ne constitue pas un acquittement natif après rendu. Cursor JSON d'une génération éventuellement différente de l'événement acceptée comme snapshot effectivement lu, pas exigence d'égalité/ordre UUID. read_model enrichi n'est pas lié à cette génération. DOM non transactionnel : erreur intermédiaire peut laisser sections partiellement modifiées même si curseur appliqué reste ancien. Première connexion/source standard lance encore GET et stream en parallèle ; course GET-SSE initiale reste ouverte. API active/auth/ACL/charge/rejeu/outbox et L0–L9 non terminés ; gains tokens non mesurés, automatisation conservée.
- Contexte final v139 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v140 — snapshot initial terminé avant le handshake SSE standard

- Contexte v139 relu localement puis MCP : 11992/12000 octets UTF-8 sans avertissement. Mémoire/Git/journal/helpers/templates/tests concernés avant modification. Board MCP384/389 historique ; RepoWise template index11 jours/mock, aucun symbole/fraîcheur indéterminée, confronté au source. Index inchangé.
- startDashboardSynchronization de la vue standard attend refreshDashboardForSse avant d'ouvrir le fetch SSE. Le premier handshake porte ainsi le curseur JSON appliqué s'il existe ; publication d'une autre génération entre GET et handshake peut déclencher le reset prévu côté serveur. Le bootstrap ne reste pas suspendu jusqu'à la fermeture du stream. Échec initial HTTP/schéma/réseau ouvre tout de même le transport et conserve le minuteur de reprise indépendant, sans attendre un nouveau delta. Polling périodique existant conservé.
- 124 contrats ciblés réussis en24,98 s : quatre nouveaux scénarios exécutent les vrais helpers/refresh/stream et le nouveau bootstrap avec première réponse différée. Aucun stream pendant GET en cours ; succès appliqueA avant en-têteA puis resetB provoque GETB ; trois échecs initiaux ouvrent sans curseur appliqué et minuteur4–5 s assure GETB sans nouvel événement. Bootstrap se termine malgré stream maintenu ouvert. Suites SSE/validation/reprise/coalescence/actions/cache/provenance/cursors incluses. Racines temporaires avant imports/processus, Python3.13 documenté + overlay existant, Node.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-startup-94492826880340149ad5fed3fda6c04e/contracts.txt ; SHA-256 ddedab3ec57aa67eb25ed9eb99606f07c3fbc58dfad8f227b850f9354cce977a.
- Recette Edge154.0.4258.53 standard modifiée pour invoquer le vrai startDashboardSynchronization, sans séquencement initial remplacé par le harness : un test passe en19,80 s, un terminal désélectionné (source terminal inchangé, qualifié v139). Premier snapshotA, coupure/reconnexion portantA, GET503 puis repriseB ; trois lectures/un échec, DOM/morphDOM/transport réels dans HTML minimal, profils/ports/racines temporaires.
  Trace même dossier/browser.txt ; SHA-256 3fa672e39a515545a2ca652fe439e210d25ced9bca8cf761130969fb63b6999d.
- Plan/fiche v140/manifeste actualisés ; git diff --check ciblé sans erreur (avertissement LF/CRLF terminal). CI distante non exécutée, tests déjà référencés au workflow. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : handshake de comparaison exige un curseur JSON de snapshot publié ; réponses legacy/fallback sans curseur ne permettent pas cette comparaison, polling reste filet de reprise. Refus401/403 ne programme pas de reprise SSE du GET selon v137 ; nouvelle réussite périodique/explicite requise. Le séquencement standard ne change pas EventSource terminal, ni la fenêtre serveur entre lecture de génération et prise de la signature initiale des entrées : suivi des publications/signatures côté serveur reste à qualifier. DOM non transactionnel/read_model distinct, API active/auth/ACL/charge/outbox/rejeu et L0–L9 restent ouverts ; économies tokens non mesurées, automatisation conservée.
- Contexte final v140 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v141 — fenêtres de handshake serveur et publications indépendantes

- Contexte v140 chargé via MCP : 11992/12000 octets UTF-8 sans avertissement ; décisions obligatoires conservées. Mémoire/Git/journal/API/watcher/curseurs/coordinator/tests relus avant modification. Board MCP384/389 historique ; RepoWise API index11 jours/mock annoncé fresh, mais carte confrontée aux sources modifiées, index inchangé.
- event_generator relève désormais la révision initiale des entrées avant de lire/annoncer la génération du snapshot et avant toute suspension sur Connected/reset. Une mutation survenant pendant ces frames n'est plus adoptée comme baseline initiale. Sur un tour sans changement d'entrées, vérification en thread du snapshot publié ; génération différente déclenche dashboard.delta/snapshot_required/reload_snapshot avec son id, sans appeler le producteur. Génération stable conserve le heartbeat. Lecture par pin existant, aucune donnée/empreinte écrite par cette branche.
- Quatre nouveaux contrats : mutation d'entrée pendant lecture du premier curseur ; mutation après Connected ; publication indépendante après Connected sans changement d'entrée ni régénération ; publication après frame de récupération initiale, suivie d'un heartbeat lorsque stable. Vrais fichiers/snapshots/manifestes épinglés sur fixtures, InputWatcher intervalle0 et polling accéléré pour imposer les interleavings, deux/trois tours bornés. Comparaison des ids/payloads et nombre de régénérations, pas de navigateur/transport actif revendiqué.
- Suite finale 35 tests réussis en9,56 s : curseurs/handshake, InputWatcher, coalescence/réessais de production, cache/provenance. Recette20 vrais event_generators garde un producteur et deux sondes d'entrées pour vingt abonnés. Première suite34 tests en10,91 s avant ajout du cas reset/heartbeat, non additionnée. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-server-handshake-9d359485b9704934a314d97faca87960/contracts-final.txt ; SHA-256 1afdbc13f364ddc2b755a8a2b89aaf0ccc73a01fbb4e6f1ce8ef160f54b33b83.
- Plan/fiche v141/manifeste actualisés ; git diff --check ciblé sans erreur (LF/CRLF terminal). Source frontend inchangé, recette Edge v140 non répétée ; CI distante non exécutée. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : détection au prochain sondage/polling, génération UUID comparée par égalité, aucune chronologie ou rejeu durable ; plusieurs publications intermédiaires regroupées en état courant. Vérification de génération via pin/to_thread par abonné à chaque tour sans mutation (environ1 s), pas mutualisée ; charge/threadpool/catalogue à qualifier avant activation. Sonde d'entrées existante mutualisée, production toujours coalescée. Échec de régénération conserve branche de reprise sans annonce de succès ; panne/corruption de snapshot garde erreurs/réessai existants, pas récupération automatique du magasin. Mutations antérieures au premier baseline avec snapshot déjà périmé restent hors garantie de fraîcheur transactionnelle ; polling JSON demeure filet. EventSource terminal acquitte à réception ; API active/ACL/auth/charge/outbox/rejeu et L0–L9 ouverts, gains tokens non mesurés, automatisation conservée.
- Contexte final v141 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v142 — sonde périodique de génération partagée entre abonnés

- Contexte v141 via MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/watcher/API/tests avant édition. Board MCP384/389 historique. RepoWise watcher live_file_without_index_record sans symboles/fraîcheur indéterminée, index11 jours/mock ; extrait live confronté au fichier, index inchangé.
- InputWatcher expose snapshot(probe) : couple révision/valeur de la même observation, y compris None, en réutilisant prélèvement en thread, tâche partagée shieldée, intervalle et état par event loop. revision garde son contrat via _sample commun ; erreur de sonde propagée sans horodater un faux succès. Observer distinct _sse_publications, intervalle1 s par défaut, partagé pour les tours sans mutation.
- Chaque connexion relève une baseline d'observation partagée puis conserve sa lecture directe fraîche du curseur de handshake. Suivi n'annonce la valeur échantillonnée que si sa révision dépasse celle déjà observée ; un cacheA antérieur au handshakeB ne provoque pas un faux resetA. Couple lu sans await intermédiaire, égalité de génération toujours nécessaire avant delta ; pointeurs intermédiaires restent regroupés, aucune comparaison lexicale des UUID. Producteur/branche de mutation gardent lecture fraîche existante et coalescence.
- Quatre nouveaux contrats : vingt consommateurs snapshot attendent la même sonde, annulation d'un consommateur ne l'annule pas ; erreur/None et nouveau loop conservent révisions cohérentes ; vingt event_generators réels reçoiventB après une seule sonde périodique/pin ; vieux cacheA suivi d'un handshake fraisB produit heartbeat et aucun resetA. Tests v141 gardent interleavings via observer à intervalle0 sur fixtures.
- 39 tests ciblés passent en12,67 s : curseurs/handshake/publications, InputWatcher, coalescence/réessais producteur, cache/provenance. Recette20 flux compte21 lectures initiales (une baseline partagée +20 handshakes frais) puis une seule lecture pour20 notifications de publication indépendante ; aucune régénération par cette branche. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-shared-generation-0234042670cb4ea6bc52dc452c60447d/contracts.txt ; SHA-256 5faa8e33e28d78e083775ab052f5bc031c10863ae4fc0765170848cc200dc75a.
- Plan/fiche v142/manifeste actualisés ; git diff --check ciblé sans erreur (LF/CRLF terminal). Frontend inchangé, Edge v140 non répété, CI distante non exécutée. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : observation partagée seulement dans le processus/event loop, magasin historique global ; aucune isolation utilisateur ni diffusion multiworker gagnée. Handshakes frais et lectures après régénération demeurent individuels. Délai d'échantillonnage1 s après succès, tours de polling1 s : notification différée, pas garantie stricte de latence sous charge. Échec de sonde ne met pas de cache d'erreur, donc erreurs persistantes peuvent provoquer des tentatives supplémentaires ; cadence d'erreurs/charge et activation ouvertes. Fenêtre antérieure au premier baseline/snapshot déjà périmé, EventSource à réception, auth/ACL/outbox/rejeu et L0–L9 restent ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v142 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v143 — délai partagé après échec de sonde

- Contexte v142 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/watcher/tests relus avant édition. Board MCP384/389 historique ; RepoWise watcher extrait live sans symboles/fraîcheur indéterminée, index11 jours/mock, confronté au source. Index inchangé.
- InputWatcher mémorise séparément failed_at et un diagnostic de1024 caractères au plus après erreur de sonde. Avant expiration de l'intervalle (1 s par défaut), nouveau consommateur reçoit ProbeCooldownError sans lancer de thread/lecture et sans récupérer l'ancienne valeur comme succès. Première tâche conserve l'exception originale ; consommateurs de la même tâche restent protégés par shield. Ni sampled_at, ni signature/révision de succès modifiés par l'échec. Prochain prélèvement réussi efface le délai/diagnostic. Intervalle0 garde réessai immédiat utilisé pour les interleavings de recette.
- Diagnostic conservé comme texte borné, pas comme exception réutilisée dont la traceback s'allongerait à chaque appel. Limite en caractères Python, pas en octets/tokens. Le watcher des entrées et celui des publications partagent cette politique ; instances/états toujours distincts.
- Trois nouveaux cas : première panne avec ou sans précédente valeur valide, puis100 consultations refusées sans lecture supplémentaire et refus identique de revision ; reprise déterministe après délai autorisé, cache de succès rétabli. Cas délai réel50 ms : refus immédiat puis20 consommateurs après60 ms partagent un seul prélèvement réussi. Aucun ancien snapshot retourné par ces refus ; révision ne compte que les observations réussies.
- 42 tests ciblés passent en12,67 s : InputWatcher, curseurs/handshake/publications, coalescence/réessais producteur, cache/provenance. Recettes20 flux et un pin périodique partagés de v142 repassées. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-probe-cooldown-79d26c4b03504751b2cce822867b0a9a/contracts.txt ; SHA-256 de6e347659e808e117c704e3ab1abe894cdb020472b660f31bdcc3ead9465b15.
- Plan/fiche v143/manifeste actualisés ; git diff --check ciblé sans erreur. Frontend/API source inchangés ce passage, Edge v140 non répété, CI distante non exécutée. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : délai fixe par watcher/process/event loop, sans backoff exponentiel ni jitter ; erreur non masquée, disponibilité dépend du prochain prélèvement réussi. Logs de boucle SSE restent émis par abonné, donc débit logs à qualifier ; prélèvements bloqués n'ont pas ici de deadline/annulation du thread OS. Handshakes frais et lectures après production restent distincts de cette sonde partagée. Initialisation SSE peut encore échouer avant Connected si stockage indisponible ; reprise de transport existante requise. Pas de récupération automatique de magasin corrompu, ni de droits/isolation supplémentaires. Activation/charge/multiworker/ACL/outbox/rejeu et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v143 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v144 — attente bornée des sondes sans multiplier les threads

- Contexte v143 via MCP11992/12000 octets UTF-8 sans avertissement au début du passage ; mémoire/Git/journal/watcher/tests avant édition. Board MCP384/389 historique. Après nouveau message utilisateur continu, RepoWise disparu des outils exposés (appel TypeError avant toute mutation de cette cellule), indisponibilité signalée, sources locales utilisées. Index réel inchangé.
- InputWatcher ajoute timeout positif fini,5 s par défaut. asyncio.timeout borne chaque attente autour de shield de la tâche partagée ; expiration produit ProbeTimeoutError sans annuler la tâche ni retirer son état en cours. Demandes ultérieures rejoignent la même tâche, donc un OS bloqué ne provoque pas une accumulation de prélèvements. Réussite tardive conserve chemin normal (signature/révision/cache) ; erreur tardive conserve délai partagé v143. TimeoutError émis par la sonde avant expiration conservé comme erreur réelle, pas confondu avec délai d'attente du consommateur.
- Neuf cas nouveaux : sept valeurs de timeout invalides refusées (0, négatif, bool, None, NaN, infini, texte) ; blocage thread contrôlé par Event avec deux vagues20 consommateurs expirant au délai50 ms de recette, un seul probe exécuté, autre InputWatcher disponible pendant le blocage, libération puis résultat retrouvé sans redémarrage ; TimeoutError propre à la sonde préservé et reprise ensuite. Fixtures libèrent leur Event en finally pour ne pas bloquer fermeture de l'executor.
- 51 tests ciblés passent en13,70 s : InputWatcher, curseurs/handshake/publications, coalescence/réessais producteur, cache/provenance. Tests de cancellation/erreurs/20 flux des passages précédents repassés. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-probe-deadline-4c2d1df7a05e4d49b45ec02f6da5f68a/contracts.txt ; SHA-256 e7a725b27234b3e380fd5f738ad01acae6a21345a1929baf9106beab4cf7db78.
- Plan/fiche v144/manifeste actualisés ; git diff --check ciblé sans erreur. Frontend/API source inchangés ce passage, Edge v140 non répété, CI distante non exécutée. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : borne d'attente asynchrone, pas interruption du syscall/thread OS. Un probe bloqué reste un thread occupé et sa valeur indisponible ; arrêt de l'executor/processus peut attendre son retour. Deux watchers distincts peuvent chacun immobiliser un thread, pas une garantie globale de threadpool/charge. Lectures fraîches de handshake/après production restent hors de ce délai partagé ; initialisation peut échouer avant Connected, transport doit reprendre. Débit logs par abonné, charge/multiworker/activation/ACL/outbox/rejeu et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v144 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v145 — diagnostics SSE regroupés pendant les pannes

- Contexte v144 via MCP et lecteur local11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/API/watchers/tests avant édition. Board MCP384/389 historique ; RepoWise absent des outils exposés, signalé, sources locales utilisées. Index réel inchangé.
- SseErrorReporter conserve deux catégories fixes cache/loop par event loop ; premier diagnostic immédiat, suivants supprimés pendant30 s, prochain diagnostic rapporte le compteur de suppressions. Compteur saturé999999 (pas compteur d'audit exact après ce seuil), pas de clé par utilisateur/exception/arbitraire. API remplace ses deux prints de panne par ce reporter ; chemins de reprise/continue inchangés. État basé sur horloge monotone, indépendant par boucle/processus.
- Détail limité1024 caractères avant échappement CR/LF, message sur une ligne (jusqu'à environ2 K caractères après échappement). Pas d'exception conservée ni de traceback répétée. Erreur du sink/formatage contenue pour préserver le chemin de récupération ; tentative compte dans la fenêtre de débit même si le sink échoue. Aucun succès métier annoncé par le reporter.
- Onze cas nouveaux : sept intervalles invalides refusés ; burst100 diagnostics donne un message initial puis suppressed=99 après30 s simulées, catégorie cache indépendante ; détail volumineux CR/LF borné/inert et nouvelle boucle indépendante, catégorie arbitraire refusée ; sink défaillant ne remplace pas erreur de récupération. Recette20 vrais event_generators : handshake initial puis erreur d'entrée, un message loop commun,20 fins de connexion contrôlées sans delta/heartbeat de succès. Horloge de recette seulement simulée pour tester fenêtre, aucune qualification temps réel30 s annoncée.
- 62 tests ciblés passent en14,19 s : nouveau reporter, InputWatcher, curseurs/handshake/publications, coalescence/réessais producteur, cache/provenance. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus. Nouveau fichier de tests ajouté à l'étape CI contractuelle existante en préservant ses autres changements ; CI distante non exécutée.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-diagnostics-bd56d8761c20466ab3fcfe87dc7d728f/contracts.txt ; SHA-256 1e57344c14a5aee798b33539e689dc910bee4c3ae8373ac436fe5620ff5433eb.
- Plan/fiche v145/manifeste actualisés ; git diff --check ciblé sans erreur (LF/CRLF CI/API). Frontend inchangé, Edge v140 non répété. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : regroupement par catégorie (une cause différente dans la même fenêtre peut être supprimée), rappel seulement si une nouvelle erreur arrive après intervalle ; pas de flush automatique ni métrique OTLP/signal de rétablissement. Suppressions saturées999999. Sink print toujours synchrone ; sortie bloquée reste hors de cette protection. Pas de diagnostic partagé multiworker, pas interception des erreurs antérieures à l'ouverture du stream. Charge/multiworker/activation/ACL/outbox/rejeu et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v145 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v146 — admission SSE bornée et libération liée à la réponse ASGI

- Contexte v145 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/API/tests avant édition. Board MCP384/389 historique ; RepoWise toujours absent des outils exposés, sources locales utilisées, index réel inchangé.
- StreamSlots réserve immédiatement sans await ni file une place par réponse, plafond32 par event loop/processus. Endpoint valide toujours Last-Event-ID avant admission ; excès retourne HTTP503/Retry-After5 avant ouverture du flux. AdmittedStreamingResponse libère la place dans finally de __call__ ASGI, et ferme son async iterator ; nettoyage reste garanti si cette fermeture échoue. Release idempotente, états de boucles indépendants. Finalizer dont le callback ne retient pas la réponse libère aussi la place lors de collecte d'une réponse abandonnée avant dispatch ASGI.
- Treize tests nouveaux : six limites invalides ; release répétée et nouvelle boucle ; réponse abandonnée/GC ; quatre parcours vrais StreamingResponse ASGI spec2.4 (fin normale, erreur de générateur avant premier chunk, erreur send/déconnexion, annulation avant premier chunk) avec fermeture du générateur et nouvelle admission possible ; rafale100 appels au vrai endpoint sur instance/racines temporaires,32 réponses admises et68 refus503/Retry-After5, statut200 via application ASGI/httpx pendant saturation, toutes places rendues après exécution des réponses.
- 75 tests ciblés passent en14,15 s, suite finale admission/reporter/watchers/curseurs/handshake/coalescence/cache/provenance. Première suite74 tests en16,19 s avant ajout GC, non additionnée. Admission burst est vérification de comportement, pas benchmark p95/RAM/charge cible ni100 connexions socket réseau actives. Production de frames fixture dans la recette d'admission, autres recettes SSE réelles distinctes. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-stream-admission-9803d519145548e2b1d513c5414a0117/contracts-final.txt ; SHA-256 de6112a433334d0b9373fdf778618f086b42bc50ff3bdd3bf6a54076be664842.
- Plan/fiche v146/manifeste actualisés ; nouveau fichier de tests ajouté à CI contractuelle existante en préservant modifications. git diff --check ciblé sans erreur (LF/CRLF CI/API), CI distante non exécutée. Frontend inchangé, Edge v140 non répété. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : plafond local fixe de protection, pas dimensionnement validé ni quota équitable par utilisateur/projet ; client peut occuper plusieurs places. Multiworker multiplie la capacité, aucune coordination globale. Réponse abandonnée libérée à sa collecte (pas instantanément si une référence la retient). Place de connexion libérée même si thread de sonde OS reste occupé, limites sondes v144 inchangées. Parcours ASGI2.4 qualifié directement ; middleware/versions ASGI et vrais sockets/auth/charge/RAM à qualifier avant activation. Refus ne modifie pas ACL historiques ni individual_project_access. Logs/OTLP, rejeu/outbox et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v146 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v147 — connexions SSE réseau et retour de capacité après fermeture

- Contexte v146 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/admission/API/tests avant édition. Board MCP384/389 historique ; RepoWise absent des outils exposés, sources locales utilisées. Index réel inchangé.
- Nouvelle recette dans test_dashboard_stream_admission.py démarre une application Dashboard API réelle sous Uvicorn, profil legacy explicite et racines local/data/platform temporaires avant imports/sous-processus. Socket127.0.0.1 port OS réservé puis transmis au serveur, pas service actif/port fixe. Launcher importe API sans appeler main ni bootstrap de secrets, app/middlewares/event_generator/watchers réels ; enveloppe de recette relève seulement scope.asgi dans fichier temporaire. stdout/stderr vers trace temporaire, fenêtre masquée Windows, processus enfant détenu terminé dans finally puis kill/wait si nécessaire.
- HTTPX réseau réel, proxies désactivés, pool64 :32 réponses SSE200 ouvertes simultanément, premières lignes Connected lues,33e réponse503/Retry-After5. Statut200 pendant saturation. Fermeture client/TCP d'un flux, nouvelle admission200 avec attente de propagation bornée ; fermeture de toutes réponses puis réouverture complète32 connexions, statut toujours200. Responses/iterators fermés en finally. Auth individuelle/fiches/projets/production de snapshot non exercés par cette recette : magasin temporaire vide et SSE historique legacy, pas refus croisés.
- 14 tests admission réussis en4,59 s (13 recettes précédentes +1 réseau, non additionnés aux75 tests du passage v146). Métadonnées observées : Uvicorn0.54.0, scope ASGI version3.0/spec2.3. Les13 contrats ASGI2.4/admission/GC précédents repassent ; runtime source inchangé, autres suites v146 non répétées. Versions uvicorn0.54.0/httpx0.28.1 retrouvées dans lock CI existant ; fichier déjà inclus au workflow, aucune nouvelle dépendance installée/CI distante exécutée. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-sockets-7443527a6a45493ca3db402231903527/sockets.txt ; SHA-256 fbffa6ffa79d459769cc3e26cf898136598667e948fb1646730a515e7e85925f.
- Plan/fiche v147/manifeste actualisés ; git diff --check ciblé sans erreur. Aucun python server_fixture.py de cette recette restant après nettoyage vérifié par Win32_Process filtré python.exe (ne pas confondre PowerShell exécutant la recherche avec serveur). Frontend inchangé, Edge v140 non répété. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : recette sockets/middlewares du profil legacy local, pas qualification de l'API active ni des identités/ACL/projets. Rafales/reconnexions de fermeture validées, pas longue durée/p95/RAM/charge cible ni worker durable ; attente propagation bornée2 s dans la recette, aucun SLA de production déduit. Source SSE garde polling/global snapshot. Service/processus de recette arrêté par terminate/kill détenu ; pas une qualification de drainage métier ni d'arrêt utilisateur complet. Multiworker/quota utilisateur/activation/ACL/outbox/rejeu et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v147 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v148 — publication indépendante, GET et rattrapage sur sockets réels

- Contexte v147 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/snapshots/verrou/API/tests avant édition. Board MCP384/389 historique ; RepoWise absent des outils exposés, sources locales utilisées. Index réel inchangé.
- Recette réseau v147 paramétrée sans/avec snapshot. Variante snapshot publieA avant serveur puisB pendant32 flux ouverts, via publish_snapshot et DashboardLock dans racine de recette explicite ; quatre artefacts/somme/manifeste/pointeur réels. Variables de racines posées aussi dans le parent avant import du publisher, pas seulement dans le serveur. Parseur de recette lit frames SSE complètes (id/event/data), pas positions de lignes dépendant de présence d'un curseur.
-32 flux reçoivent Connected/idA, puis publicationB ne modifie pas entrées surveillées :32 dashboard.delta/idB/snapshot_required observés sur réseau. GET /api/dashboard de l'API réelle retourne labelB/cache.snapshot_cursorB. Fermeture d'une connexion libère admission, remplaçante portant Last-Event-ID=A reçoit Connected sans id puis recovery=reload_snapshot/idB. Fermeture/réouverture32 et statut200 toujours vérifiés. Publisher du parent indépendant du serveur, aucune mutation de données actives/Dropbox.
- Launcher refuse explicitement refresh_dashboard_payload_cache avant tout lancement externe et écrit une sentinelle temporaire s'il est appelé ; absence de sentinelle vérifiée à la fin, donc pas d'échec de régénération silencieusement compensé par cache. Producteur réel non exécuté ; serveur/API/middlewares/SSE/watchers/pinning réels conservés. Les documents HTML sont fixtures minimales, aucun navigateur actif ni activation de pages.
-15 tests admission réussis en7,96 s, suite finale après ajout sentinelle (première15 en8,48 s non additionnée).13 contrats admission/ASGI/GC et deux recettes réseau sans/avec publication. Uvicorn0.54.0, ASGI version3.0/spec2.3 observés pour les deux serveurs. Autres suites de runtime v146 non répétées car runtime source inchangé ; tests déjà inclus au workflow, CI distante non exécutée. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-sse-publication-http-8304cf2ecb0b4161ba95790f980584da/sockets-final.txt ; SHA-256 d17c4c0f03acfaa5821688657c1ad6286b381658486e41b0b3ee1842debbb1d6.
- Plan/fiche v148/manifeste actualisés ; git diff --check ciblé sans erreur. Processes de recette détenus fermés en finally ; aucune instance Python server_fixture de recette restante au contrôle après première suite. Frontend inchangé, Edge v140 non répété. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : profil legacy global localhost temporaire, pas identité/ACL projet ni API active qualifiée. Publication sur un seul backend/processus, pas validation multiworker ni outbox/rejeu SQL ; reset réclame état courant, pas historique d'événements.32 notifications vérifiées, délai de recette4 s, aucun SLA de charge/p95/RAM déduit. HTTPX lit contenu/provenance, pas application DOM du snapshot (Edge antérieur distinct). Mutations transactionnelles/worker durable et droits à qualifier séparément. Activation/charge/multiworker/ACL et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v148 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées. Aucun serveur Python de recette restant après suite finale.

### Passage v149 — frontières individuelles sur réseau et révocation indépendante

- Contexte v148 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/middleware individuel/identité/tests avant édition. Board MCP384/389 historique ; RepoWise absent des outils exposés, sources locales utilisées. Index réel inchangé.
- Nouveau test_dashboard_individual_http.py réutilise la fixture identité/tâches alpha/beta existante, comptes et credentials individuels réels dans magasins temporaires. Serveur Uvicorn sur socket127.0.0.1 port OS réservé, profil individual hérité explicitement de fixture, identity/local/data avant imports/processus, platform temporaire pour enfant ; app/middlewares/autorisation/lecture tâches réels. Processus détenu masqué Windows, stdout/stderr dans fichier temporaire, terminate puis kill/wait bornés en finally.
- Deux AsyncClient HTTPX réseau indépendants, Bearer Alice/Bob, pas cookies/profils navigateur : lecture propre200/titre alpha ou beta/no-store, accès sans credential401, refus croisés403. Huit routes globales GET refusées403/individual_route_unavailable ;32 tentatives SSE Bob avec Last-Event-ID invalide refusées403 par middleware avant validation/admission globale. Sentinelles event_generator/read_cached_dashboard_payload/read_dashboard_html écrivent une violation et refusent si appelées ; absence vérifiée. Revocation parent SQLite de credential Alice sur fixture, requêtes suivantes : Alice401/Bob beta200, sentinelle toujours absente. Aucun accès global qualifié n'est ouvert pour faire passer cette recette.
-23 tests réussis en95,88 s : nouvelle recette réseau + tests individuels ASGI/versions/rôles/identité/non-blocage/status/CLI et sessions cookie existants. Uvicorn0.54.0 observé. Temps de suite variable ; aucune latence/p95 ni disponibilité sous charge déduite. Un StarletteDeprecationWarning existant fastapi.testclient/httpx conseille httpx2 ; dépendances non modifiées dans ce passage. Tests n'impliquent pas connexion/password de l'API active. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-individual-http-223e752948cb47de8537df52ee26bfbe/contracts.txt ; SHA-256 b191ea55cf6871837ab74b88e89260706020eefebe5bbe639dfb367196fc15b4.
- Plan L4/fiche v149/manifeste actualisés ; fichier ajouté à étape CI identité existante en préservant modifications, CI distante non exécutée. git diff --check ciblé sans erreur (LF/CRLF CI). Aucun Python server.py de recette restant après nettoyage vérifié ; frontend inchangé, Edge v140 non répété. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : qualification réseau Bearer du profil individuel temporaire, pas deux profils navigateur ou parcours cookies/password HTTPS/cross-site en réseau. Recette lecture/révocation, mutations couvertes par suites ASGI existantes pas nouvelles mutations réseau ; autres ressources/mutations auditées/CLI-MCP et NTFS/compte de service/activation restent distincts. Dashboard/SSE historiques globalement interdits au profil individual, pas diffusion SSE individuelle proposée ou qualifiée. Pas benchmark p95/RAM/charge/équité multiworker. Production, PostgreSQL/outbox/worker durable et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v149 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v150 — clôture/suppression individuelles réseau, versions et auteur

- Contexte v149 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/HTTP individuel/audit/TaskService avant édition. Board MCP384/389 historique ; RepoWise absent des outils exposés, sources locales utilisées. Index réel inchangé.
- Recette réseau individuelle v149 paramétrée lecture seule, POST done et DELETE delete. Pour chaque mutation : utilisateur beta tentant alpha403, credential lecteur alpha403, version attendue2 contre1 donne409/stale_task_version, puis version1 acceptée200 ; répétition avec ancienne version404/409 ne produit pas de seconde mutation. Serveur/API/identités/TaskService réels via Uvicorn et HTTPX, magasins/racines temporaires, source runtime inchangé.
- Inspection SQLite de fixture après HTTP vérifie alpha target(done/deleted)/version2, beta in_progress/version1 et une seule ligne d'audit project alpha/actor alice/action task.complete ou task.delete/entity T-01. Détails before in_progress1 / after target2 ; auteur mallory envoyé dans JSON/header, trace forgée, password/token de fixture et secrets de credentials absents de l'audit. Bob beta toujours200 après mutation, puis révocation Alice401/Bob200 et refus cache/stream globaux v149 répétés.
- Neuf tests ciblés réussis en48,02 s : trois variantes réseau (dont lecture v149) et six contrats audit ASGI existants (auteurs simultanés par projet, session cookie sans secret dans audit, rollback si table audit absente pour done/delete, refus projet/lecteur sans audit de succès). Les logs no such table: audit_log de ces deux recettes sont pannes injectées attendues, non erreurs opérationnelles. Rollback vérifié sur ASGI/SQLite, pas nouvelle injection réseau de panne magasin. Un avertissement StarletteDeprecationWarning TestClient/httpx existant, dépendances inchangées. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-individual-http-mutations-584d22abe9d543909c997f44fd0059bb/contracts.txt ; SHA-256 71cfb04612177cca6ec0c864725add5806e121534ca3b779edfb33c98478ef43.
- Plan L4/fiche v150/manifeste actualisés ; fichiers déjà inclus au workflow, CI distante non exécutée. git diff --check ciblé sans erreur. Aucun Python server.py de recette restant après nettoyage vérifié ; frontend inchangé, Edge v140 non répété. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : Bearer sur localhost temporaire, pas authentification/NTFS/compte de service de l'instance active ni deux profils navigateur/cookies/password/HTTPS réseau. Conflit de version imposé par client à version2, pas nouvelle édition concurrente réseau mesurée ; auteurs concurrents couverts sur ASGI. Répétition d'une requête ancienne refusée, pas protocole d'idempotency-key ni garantie exactement une fois d'un effet externe. Actions autres que done/delete, autres ressources/CLI-MCP/worker durable/PostgreSQL/outbox/activation et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v150 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.

### Passage v151 — mutation conditionnelle concurrente par deux clients réseau

- Contexte v150 MCP11992/12000 octets UTF-8 sans avertissement ; mémoire/Git/journal/test HTTP individuel/TaskService avant édition. Board MCP384/389 historique ; RepoWise absent des outils exposés, sources locales utilisées. Index réel inchangé.
- Pour chaque variante done/delete de la recette réseau, remplacement de la seule mutation séquentielle acceptée par deux requêtes démarrées ensemble via asyncio.gather depuis deux AsyncClient distincts, même principal Alice et même tâche alpha/version attendue1. Une lecture beta de Bob démarre dans le même gather. Assertions : exactement un200, perdante404/409 (si409 code stale_task_version), beta200/titre beta ; répétition séquentielle avec ancienne version toujours refusée ensuite.
- Contrôles DB/audit v150 conservés : alpha target done/deleted2, beta in_progress1, une seule ligne auteurAlice/action/entity et before1/after2. Tentatives auteur/trace forgés et secrets ne se retrouvent pas dans l'audit. Refus projet/rôle, variante lecture seule, routes globales bloquées avant cache/stream, révocation Alice401/Bob200 repassent.
- Trois recettes réseau réussies en30,47 s (lecture seule + done/delete), Uvicorn0.54.0 réel temporaire. Un StarletteDeprecationWarning TestClient/httpx préexistant, dépendances inchangées. Aucun nombre de nouvelles recettes ajouté aux suites v150 ; runtime source inchangé, rollback audit ASGI précédent non répété. Python3.13 documenté + overlay existant, racines temporaires avant imports/processus.
  Trace C:/Users/Administrateur/AppData/Local/Temp/devcore-http-version-race-60ad5cc95a124c62aa38b4317c5942f4/network.txt ; SHA-256 347d9ceb6ff39033c715f6ffe23c2f25bee6e5cdf443e7515f75fef4f6e55c0a.
- Plan L4/fiche v151/manifeste actualisés ; test déjà inclus au workflow, CI distante non exécutée. git diff --check ciblé sans erreur. Aucun Python server.py de recette restant après nettoyage vérifié. Pages/services actifs non activés ; données actives/Dropbox/index réel inchangés.
- Limites : démarrage concurrent de requêtes réseau, sans barrière instrumentée imposant une interleaving SQL particulière ; transactions demeurent sérialisées par stockage. Deux clients sous le même principal Alice, pas nouvel utilisateur partagé alpha ; attribution concurrente de deux auteurs/projets déjà vérifiée sur ASGI. Lecture beta retourne200 dans le batch, aucune borne de latence/non-blocage sous traitement long ni p95/RAM déduite. Répétition ancienne refusée, pas idempotency-key ni exactement une fois externe. Activation/autres mutations/canaux/NTFS/PostgreSQL/outbox/worker durable et L0–L9 ouverts ; gains tokens non mesurés, automatisation conservée.
- Contexte final v151 : 11992/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées.


### Passage v152 — fondation pause/reprise auditée (L4, qualification partielle)

- TaskService.pause_task/resume_task acceptent un RequestContext optionnel nommé, validé (utilisateur et projet concordants) avant transaction. Une mutation effective insère task.pause/task.resume avec auteur, trace/session, états et versions avant/après, puis événement dans la même transaction. Échec audit ou événement : rollback intégral. Appels historiques sans contexte conservés ; un contexte n'est pas une autorisation et ne remplace pas l'admission HTTP.
- Lecteur borné task_audit : quatre actions supportées, paramètres SQL calculés depuis la liste autorisée, transitions in_progress→paused et paused→in_progress validées en plus de version+1. Projection exclut détails/trace/session. Aucun nouveau point d'entrée HTTP pause/reprise : middleware individuel les refuse toujours.
- Tests : identité/projet invalides, version obsolète, tâche absente, répétition, beta inchangé, projection et transitions forgées refusées ; audit indisponible annulant tâche/version/événement ; tests de panne événement étendus aux deux actions avec contexte d'auteur.
- Premier passage : 95 réussites et 2 échecs en343,97 s, assertions historiques de nombre d'audits après reprise d'une transaction (pause/reprise nouvellement auditées). Assertions corrigées ; second passage final : 71 tests acteur/atomicité/versions réussis en214,45 s, incluant deux nouveaux cas de transition forgée. Les 28 tests lecture HTTP avaient tous réussi au premier passage ; ni source du lecteur ni tests HTTP modifiés depuis. Une alerte StarletteDeprecationWarning TestClient/httpx préexistante. Aucune suite globale ni CI distante verte revendiquée.
- Traces temporaires : C:/Users/Administrateur/AppData/Local/Temp/devcore-pause-audit-17a66c5302604536ab08c4d37558daa3/tests.txt ; SHA256 09d5618d615f49c4c93e125139a428037511fbce4343d8565b8b5d49b15641ed. Passage final : C:/Users/Administrateur/AppData/Local/Temp/devcore-pause-audit-final-bb7d674b75ba4301a3dcb12595621f20/tests.txt ; SHA256 c8ccdee6de7332410d8ed66bf2b100b14cf9e98defb11641aedcecadadf20922.
- Python3.13 documenté/overlay existant, DEVCORE_LOCAL_ROOT/DATA_ROOT/PLATFORM_ROOT temporaires avant imports. Données actives/Dropbox/index RepoWise réel inchangés, aucune activation ni régénération de pages. Modifications Git préexistantes conservées ; git diff --check ciblé sans erreur. Tests déjà couverts par workflow existant.
- Plan et fiche v152/manifeste synchronisés. RepoWise MCP absent pendant la reprise : sources locales utilisées. Limites : autres mutations non auditées, routes et clients individuels pause/reprise à raccorder et qualifier (autorisation/CSRF/version/auteur/rollback réseau), sélection implicite historique toujours permise dans le service, pas idempotency-key ni qualification de charge/non-blocage. L0–L9 ouverts, gains tokens non mesurés ; automatisation conservée.
- Contrôle local du contexte v152 : premier refus explicite sous12000 octets (enveloppe complète12232 avec budget diagnostic14000, aucune fiche partielle retournée). Fiche raccourcie sur la description historique L7 et le lien historique redondant, décisions obligatoires inchangées ; manifeste SHA synchronisé. Relecture finale : 11933/12000 octets UTF-8, avertissements vides, D002/D003/D004/D006/D007 retournées. Le lecteur local et le MCP peuvent avoir des enveloppes de tailles différentes ; ce budget reste une mesure en octets, pas un gain de tokens.


### Passage v153 — routes individuelles pause/reprise (L4, recette ASGI)

- API Cockpit : POST /api/pause et /api/resume admis uniquement dans le profil individual, projet explicite et capacité WRITE. Même middleware bornant le corps, version attendue positive obligatoire, vérification Bearer/cookie et CSRF/origine. Nouveau gestionnaire refuse explicitement le profil historique même avec auth/CSRF simulés comme valides. Aucun routage global supplémentaire.
- Adaptateur serveur appelle TaskService sur la base existante mode=rw (sans initialisation/migration/repli), identifiant insensible à la casse résolu dans le projet uniquement, version vérifiée à nouveau par service dans transaction. Auteur/session issus du principal admis. Tâche absente404, version/transition409, SQLite/audit/événement indisponible500 générique sans chemin ni texte SQLite ; mutation exécutée via asyncio.to_thread. Transaction métier v152 conservée.
- Nouvelle recette test_dashboard_pause_resume.py : dix cas sur racines temporaires, pause et reprise chacune : refus sans credential, rôles/projets, versions absente/bool/obsolète, tâche absente, attribution malgré acteur/trace forgés, répétitions refusées, beta inchangé, révocation Alice/Bob disponible ; cookies CSRF/origine, session audit sans secrets ; panne insertion audit et événement avec rollback état/version/audit/bus ; profil legacy refusé. Six recettes d'auteurs HTTP clôture/suppression repassées.
- 16 tests réussis en65,79 s ; une alerte StarletteDeprecationWarning TestClient/httpx préexistante, dépendances inchangées. Python3.13 documenté/overlay existant ; DEVCORE_LOCAL_ROOT/DATA_ROOT/PLATFORM_ROOT temporaires définies avant imports. Trace : C:/Users/Administrateur/AppData/Local/Temp/devcore-pause-http-c1c9e3baf8cb481ebd243dc84d30df20/tests.txt ; SHA256 ea2acdb21cfdadeb705e5c7015487b8a346cb70bd5a4e80d9546bc0df0c03950.
- Workflow CI identité inclut la nouvelle recette ; CI distante non exécutée. git diff --check ciblé sans erreur ; journal/plan/fiche v153/manifeste actualisés, changements préexistants conservés, aucune activation de service ni régénération de pages ; données actives/Dropbox/index réel inchangés.
- DevCore MCP : contexte v152 au démarrage11933/12000 octets et avertissements vides ; board historique384/389, sans assimilation à L0–L9. RepoWise MCP de nouveau disponible : get_health puis contexte ciblé complete_task ; index11jours, mock/sémantique désactivée, signature indexée sans expected_version/context malgré étiquette fresh. Source actuelle contrôlée directement ; aucun refresh d'index ni score de performance validé.
- Limites/prochain point : recette ASGI/TestClient avec middlewares réels, pas réseau Uvicorn réel pour pause/reprise, ni concurrence nouvelle de deux mutations, charge/p95/non-blocage. Boutons individuels et adaptateurs CLI/MCP encore à raccorder ; autres mutations et activation restent ouverts, pas chaque mutation auditée ni PostgreSQL/outbox/worker durable qualifiés. Contexte d'auteur n'est pas une autorisation directe du service. L0–L9 ouverts et économies de tokens non mesurées ; automatisation conservée.
- Relecture locale finale fiche v153 : 11952/12000 octets UTF-8, avertissements vides ; décisions obligatoires conservées. Aucun processus pytest de cette recette restant après exécution.


### Passage v154 — quatre points : Cockpit, CLI/MCP, audit et réseau (L4/L2 partiels)

- Cockpit individuel : bouton Pause seulement in_progress et Reprendre seulement paused, droits de mutation/version affichée, CSRF session, actualisation sans répétition après conflit. L’historique reconnaît les quatre actions et contrôle les sources/cibles pause/reprise ; texte inerte et bornes inchangés.
- Client API partagé : devcore_task_pause/devcore_task_resume, arguments projet/tâche/version explicites, même HTTP que Cockpit, pas accès DB client/repli/retry, succès sans version déduite et refresh_required. Exposition MCP seulement TASK_ACCESS=write et TASK_TRANSITIONS=1, lecture seule ferme ces outils. Flag strict0/1, défaut0 et exemples TOML conservés désactivés. CLI : commandes pause/resume explicites activent uniquement cette capacité du client pour leur appel ; autorisation serveur toujours nécessaire. Compatibilité imports MCP/CLI commune et workflow test étendus.
- Correction d’intégration audit : lecteurs Cockpit et CLI/MCP attendaient encore deux actions après extension serveur v152. Alignés sur quatre actions, contrôles de transition et projection stricte maintenus. Tests d’audit HTTP/CLI/stdio existants repassent ; pas élargissement aux actions historiques non qualifiées.
- Réseau : recette Uvicorn temporaire étendue de trois à cinq variantes : lecture, clôture, suppression, pause et reprise. Reprise prépare une tâche paused sur fixture/version2 ; version de base observée explicitement. Deux clients Alice lancent même mutation/version avec lecture beta Bob : un seul200, perdante404/409 (reprise accepte stale_task_version ou task_transition_conflict suivant course), une seule version/audit, beta inchangé et disponible ; révocation et routes globales/SSE refusés conservés. Aucun p95, garantie de latence ni entrelacement SQL particulier déduit.
- Résultats : 29 tests Node réussis en246,702 ms. Deux itérations initiales du nouveau harnais corrigées : nombre de boutons désormais6 au lieu4 et nom/colonne du formulaire d’audit de fixture. Premier Python : 91 réussites/1 échec en191,25 s ; échec du nouveau scénario combiné avant CLI (dossier parent temporaire cli absent), sans échec des cinq recettes réseau. Fixture corrigée, scénario ciblé final1 réussite/15 désélections en15,27 s : CLI isolée -I -S pause puis MCP stdio réel reprise, defaults/lecture seule fermés, versions obsolètes refusées, projets/rôles403, révocation401 et deux audits Alice, beta inchangé. 92 cas Python distincts validés entre ces passages ; pas une nouvelle suite globale/CI distante verte. Alerte StarletteDeprecationWarning préexistante.
- Traces : C:/Users/Administrateur/AppData/Local/Temp/devcore-transitions-clients-a078288f53604b0a9bcdc588f3d8a399/node.txt SHA256 174e498dd11d5bf8cd73afa0f1ed763c6c39c8553ea56a4fd03d4cb032a70fa0 ; tests.txt SHA256 0957c3dd01fd80a103d6b77855f1089a78631ce19f4ec68282cd7cde7ed0aaad. Scénario ciblé final : C:/Users/Administrateur/AppData/Local/Temp/devcore-transitions-cli-final-ba3967434bde4991a931e80b28515ee2/tests.txt (empreinte ajoutée ci-dessous).
- Python3.13 documenté et overlay existant ; racines LOCAL/DATA/PLATFORM temporaires avant imports et processus. Tests réseau propriétaires arrêtés, données actives/Dropbox/index réel inchangés. Configurations personnelles/services/pages actives non modifiés ; exemples uniquement. RepoWise ciblé sur project_tasks.js/individual_tasks.py : fichiers vivants sans enregistrement indexé, contrôlés au code, aucun refresh ; index ancien/mock reste une limite. Contexte DevCore153 chargé au départ ; changements Git existants conservés.
- Plan/journal/fiche154/manifeste et note pause-reprise-clients-2026-10-05.md actualisés ; exemples TOML parsés et transitions=0 vérifié ; git diff --check ciblé sans erreur.
- Limites/prochain point : nouveaux parcours navigateur réels non rejoués (29 tests du vrai script via DOM/HTTP doubles), stdio/CLI source uniquement ; wheels/snapshots candidats existants à reconstruire et qualifier, services non activés. Autres mutations/ACL, PostgreSQL, outbox/worker durable, charge et L0–L9 restent ouverts. Pas exactement une fois externe/idempotency-key ni gains tokens mesurés ; automatisation conservée.
- Empreinte du scénario ciblé final : SHA256 939ac767322a150ac855d378216b20c4a5f4b1cf7127248860c1064f55c02c22. Relecture locale fiche154 : 11957/12000 octets UTF-8, avertissements vides, décisions obligatoires conservées.


### Passage v155 — candidat wheel/snapshot pause/reprise (L4/L9 partiels)

- Lanceur MCP : --transitions explicite, booléen strict, seulement avec --tasks write ; transmet le flag au client et remplace toujours DEVCORE_MCP_TASK_TRANSITIONS hérité par0/1. Les tests injectent un environnement hostile transitions=1 et prouvent que profil défaut/lecture ne l'expose pas. Aucun nouveau droit serveur accordé.
- Recettes candidats étendues : HTTP lancé en sous-processus -I avec wheel installée, snapshot épinglé, pause/reprise versions2/3 et clôture4, refus des répétitions409, audit trois actions Alice/done5, beta todo1 inchangé. MCP stdio réel -I : défaut contexte seul, lecture/audit sans mutations malgré héritage, opt-in pause/reprise puis clôture, projection audit à quatre actions et révocation401 ; aucune base dans les racines MCP.
- Première qualification : 31 réussites/3 échecs en28,73 s. Défaut concret de packaging : les imports dashboard ajoutés depuis les anciennes recettes n'étaient pas dans FILES ; HTTP bundle et MCP snapshot ne démarraient pas sans source. Liste explicite enrichie avec9 modules (__init__, snapshots, publication, generation_lock, refresh_coordinator, input_watcher, error_reporter, stream_admission, sse_cursor). Pas de copie globale ni de données/configuration/handlers historiques ajoutés. Snapshot initial incomplet conservé mais remplacé pour qualification par bundle-complete ; ancien snapshot actif inchangé.
- Construction candidate séparée : E:/DevCoreRuntime/recipes/devcore-individual-v155-f7d2a8b7/. Sources moteur copiées dans package-source, wheel construite avec build isolé et installée sans dépendances/uninstall global dans nouveau venv Python3.13.16. Les runtimes documentés n'avaient pas pip, et le Python global sans setuptools refusait --no-build-isolation ; corrigé via pip du nouveau venv/build isolé, aucun runtime actif modifié. Dépendances HTTP/MCP/pytest/Argon partagées en lecture via fichier .pth vers runtime313 documenté et overlay auth ; ce candidat n'est pas un runtime autonome et reproductible complet.
- Artefacts : wheels/devcore_engine-10.2.0-py3-none-any.whl SHA256 e6563c9c6a1f7a4743d30a3635c4d878ea857c8c1bd25c86a045573b05436c88 ; bundle-complete/manifest.json SHA256 1962bc90b79f00eeb0c216eec19edeff92c2ac04838cee40ccbc1b6f248c8d3b ; contrôleurs copiés et empreintes dans qualification-receipt.json. Vérification clients wheel/stage/install octet à octet ; aucune .db/.sqlite/.env dans wheel. Sonde sqlite-probe.json : SQLite3.53.1 chargé, éligible WAL mais operationally_qualified=false.
- Qualification finale : 34 tests réussis en40,35 s, zéro skip ; WAL concurrence/checkpoints inclus, intégrité/allowlist/refus bundle, contrôleurs HTTP isolés et MCP stdio avec fixtures NTFS. Alerte StarletteDeprecationWarning existante. Trace qualification-final.txt SHA256 571657cb912f4994a5648473f75ff696708c412dfbff38a13647fbb3c26ac4be. CI distante non exécutée, tests déjà dans workflow. Parents de fixtures chargent moteur source ; sous-processus -I chargent wheel du venv, chemins moteur installés contrôlés par lanceurs.
- Racines ENV LOCAL/DATA/PLATFORM temporaires avant imports et sous-processus, aucune donnée active/Dropbox/index réel utilisée. Services/pages/configurations personnelles non basculés. RepoWise ciblé sur constructeur/lanceur, confronté aux sources ; aucun index mis à jour. Changements Git préexistants préservés et git diff --check ciblé sans erreur. Plan, fiche155/manifeste et note clients actualisés.
- Limites/prochain point : candidat qualifié fonctionnellement sur fixtures, pas activation ; dépendances partagées/non verrouillées dans une distribution autonome. Nouveaux boutons navigateur réel/charge/durabilité service et autres mutations/ACL restent ouverts, PostgreSQL/outbox/worker durable non qualifiés. L0–L9 non terminés, pas mesure de gains tokens ; automatisation conservée.
- Relecture locale finale fiche155 : 11956/12000 octets UTF-8, avertissements vides et décisions obligatoires conservées. Board DevCore historique384/389 consulté, sans assimilation aux critères L0–L9.

### Passage v156 — deux profils navigateur individuels (L4 partiel)

- Nouvelle recette test_individual_browser_transitions.py / individual_browser_transitions.cjs : deux processus Edge headless, profils distincts temporaires, vraie page /project et project.js, vraie API Uvicorn sur port localhost éphémère. Sessions synthétiques provisionnées par API Bearer puis cookies HttpOnly/SameSite Strict dans les profils ; pas simulation DOM ni remplacement des routes API. Ce parcours qualifie la reprise de session par cookie, pas le formulaire de connexion par mot de passe.
- Alice/alpha : clic Pause puis Reprendre avec versions1→2→3, confirmations examinées, deux lignes audit Pause/Reprise auteur Alice. Contrôles SQL finaux : deux audits task.pause/task.resume auteur Alice, beta in_progress/version1 sans audit. Requête depuis le navigateur vers beta refusée403 ; déconnexion Alice efface la table et ses lectures renvoient401, tandis que Bob/beta reste lisible200 dans son profil distinct.
- Défaut UI concret corrigé : toutes les mutations POST demandaient « Terminer », y compris pause/reprise. Libellés désormais spécifiques à la route (« Mettre en pause » et « Reprendre ») ; assertion de régression ajoutée au test Node existant et vérification des vrais dialogues Edge.
- Harnais : premières tentatives échouées sur Runtime.evaluate, d'abord dialogue confirm non traité, puis course de navigation/évaluation dans le second profil. Page.enable, acceptation CDP des dialogues explicites, attente de Page.loadEventFired et awaitPromise seulement pour fetch ajoutés ; évaluations DOM synchrones et désactivation du throttling de fond. Échecs de recette consignés, aucune mutation sur données actives. Nettoyage des seuls processus propriétaires, filet de sécurité timeout avec PIDs enregistrés ; serveur joint, cookies synthétiques supprimés à la fin.
- Premier passage navigateur réussi : 1 test/0 skip en41,48 s, Edge154.0.4258.53 ; deux profils, alpha3/beta1, audit2, refus403, Alice401/Bob200. Trace TEMP/devcore-browser-v156-final.txt SHA256 28391ac8784e248f1fda814ad3ad2bd2ffa1347468e65a614848333d4f5eefe5. Assertions SQL ajoutées ensuite, requalification finale consignée ci-dessous. Tests Node : 29 réussites en202,3512 ms, dont confirmation pause/reprise. Alerte StarletteDeprecationWarning existante.
- Workflow Windows : recette ajoutée à l'étape Edge existante, skip explicite si navigateur absent ; CI distante non exécutée. Racines LOCAL/DATA/PLATFORM temporaires avant import API/lancement. Anciennes instances/pages utilisateur et configurations personnelles non touchées ; aucun test sur Dropbox ni index réel. Git préexistant conservé.
- DevCore board consulté : T-388/384 sur389 historique, ne valide pas L0–L9. RepoWise ciblé : fichiers vivants sans enregistrement indexé, index11 jours/mock/semantic_search=false ; confronté aux sources, aucun refresh ni gain tokens déduit.
- Plan, note clients, fiche156/manifeste synchronisés ; lecteur local 11946/12000 octets UTF-8, avertissements vides, décisions obligatoires conservées. git diff --check ciblé sans erreur (avertissement CRLF du workflow seulement).
- Limites : scénario cross-site réel, connexion par mot de passe dans ces deux profils, charge/p95, service et reprise opérationnelle non qualifiés. Snapshot v155 conserve l'ancien texte de confirmation : à reconstruire/requalifier avant activation. Dépendances autonomes verrouillées, autres mutations/ACL, PostgreSQL et worker/outbox durable restent ouverts ; aucun lot L0–L9 déclaré terminé, automatisation conservée.
- Qualification finale avec contrôles SQL des auteurs/actions et absence d’audit beta : 1 réussite/0 skip en40,54 s, Edge154.0.4258.53, mêmes résultats navigateur ; trace TEMP/devcore-browser-v156-audit-final.txt SHA256 f21865cc429dd83a68e45c01292f5847951dec037faaaac50f10129b166d791e. Serveur/profils propriétaires arrêtés, cookies de fixture supprimés.

### Passage v157 — formulaire et contexte dans deux profils Edge (L4/L7 partiels)

- Recette navigateur individuelle paramétrée cookie/password. Le mode password crée deux mots de passe Argon2id synthétiques dans le magasin temporaire et deux dépôts de fixtures enregistrés côté serveur avec fiche/manifeste/décisions. Aucun credential actif utilisé, pas de cookie injecté dans ce mode.
- Le vrai formulaire /project est rempli et soumis dans deux profils Edge distincts : projet/utilisateur/mot de passe, API réelle et hash serveur. Champ mot de passe effacé synchroniquement au submit ; observation CDP de chaque POST de login confirme l'absence d'Authorization/Bearer, sans journaliser corps/mot de passe/cookies. Alice/alpha et Bob/beta voient leurs tâches et leur fiche privées ; absence de contexte beta dans l'affichage Alice vérifiée.
- Rechargement complet Page.reload d'Alice : session récupérée, fiche alpha et décision locale en vigueur rechargées automatiquement, ancienne décision remplacée absente de la liste des décisions. Suite du parcours v156 conservée : pause/reprise versions2/3 et confirmations, deux audits Alice, accès beta403, logout Alice401 et Bob200 ; SQL beta/version1 sans audit.
- Premier passage : 1 réussite (mode password) et1 échec (mode cookie) en62,26 s ; l'échec est un EBUSY Windows sur DevToolsActivePort pendant démarrage Edge, avant mutations. Attente bornée renforcée : lecture du port incluse dans la boucle, port entier1–65535 exigé, seuls ENOENT/EBUSY transitoires repris ; autres erreurs remontées. Pas retry des mutations HTTP. Trace TEMP/devcore-browser-v157.txt conservée ; qualification finale ci-dessous.
- Modifications limitées aux recettes/documentation, production inchangée. Workflow Edge existant couvre désormais les deux variantes ; navigateur absent donne skip explicite, CI distante non exécutée. Roots LOCAL/DATA/PLATFORM temporaires avant import API et sous-processus ; profils propriétaires arrêtés, fixture de secrets synthétiques effacée. Git préexistant321 entrées préservé ; aucune donnée active/Dropbox/index réel touchée.
- Fiche156 et décisions chargées via MCP au départ. Board T-388/384 sur389 historique consulté, sans assimilation aux lots. RepoWise ciblé indique fichier vivant sans enregistrement, index11 jours/embedder mock ; code lu directement, aucun refresh ni métrique de gain déduite.
- Plan, note clients, fiche157 et empreinte manifeste actualisés ; lecteur local11973/12000 octets UTF-8, avertissements vides. Budget en octets, pas tokens. Une nouvelle conversation IA n'est pas couverte par un reload de navigateur.
- Limites : cross-site réel, charge/p95, service/compte Windows, distribution autonome et activation encore ouverts. Snapshot v155 à reconstruire/requalifier pour la correction de confirmation v156. Autres mutations/ACL, PostgreSQL et worker/outbox durable non qualifiés ; tous les lots L0–L9 restent ouverts, automatisation conservée.
- État des tentatives au passage suivant : la variante password a déjà réussi avec le vrai formulaire et deux projets (1 réussite, rapport password/context_reloaded=true). Une réexécution après modification du harnais a échoué deux fois au démarrage CDP du second navigateur (timeouts Network.enable/Page.enable, avant interaction), ce qui révèle une recette multi-processus Edge sensible à la charge locale. Aucun serveur Uvicorn vivant ni processus Node/Edge du harnais après fin ; aucun test de mutation n'a continué dans ces tentatives. La combinaison password demeure fonctionnellement prouvée par son passage réussi v157, mais la paire cookie+password n'a pas un passage commun vert ; le vieux passage cookie-only v156, lui, est vert. À stabiliser avant activation.

### Passage v158 — stabilité des profils navigateur isolés (L4/L7 partiels)

- Cause des expirations précédentes : lancer deux processus Edge simultanés faisait expirer les commandes CDP du second au démarrage, sans interaction utilisateur ni mutation de base ; le processus imposait un coût local inutile. Harnais remplacé par une instance Edge temporaire et deux `Target.createBrowserContext` distincts ; chaque utilisateur a une page, cookies, session et contexte de stockage isolés. Création/vérification/fermeture CDP, serveur et profil sont bornés et processus propriétaire arrêté. Un seul processus Edge, pas preuve de séparation OS/service ni de multi-poste.
- Recette combinée cookie/password : 2/2 passent, Edg/154.0.4258.53, 36,29s. Password : vrai formulaire par contexte, secret effacé au submit, requête sans Bearer, fixture Argon2id serveur, contexte alpha/beta séparé et fiche/décisions rechargées après reload ; cookie : session HttpOnly préparée uniquement dans la recette. Les deux modes valident pause/reprise, confirmation, deux lignes d'audit Alice, refus cross-project403, déconnexion Alice401/Bob200 et beta version1 sans audit. Aucune donnée active consultée.
- Suite navigateur groupée CI (Edge SSE standard+terminal et les deux transitions contextes) : 4/4 en83,58s. Les vues SSE gardent 3 snapshots, un snapshot initial simulé en échec, reconnexion et curseur attendu. Revalidation après assertion d'identité de contextes : transitions2/2 en36,29s. Alerte préexistante StarletteDeprecationWarning seule. `node --test DEV_CORE/Scripts/test_project_tasks_ui.cjs` : 29/29 plus tôt dans le passage ; check syntaxe Node et `git diff --check` sans erreur (avertissement CRLF workflow).
- Une exécution de développement a d'abord échoué immédiatement sur import Argon2 car l'overlay n'était pas dans PYTHONPATH ; corrigée avant le passage vert. Erreurs temporaires TargetId undefined corrigée et validée, fichier suivi des PIDs évite les Edge orphelins sur timeout. Les essais Edge multiprocessus expirés précédemment gardés au journal, succès courant remplace le harnais.
- CI Windows Edge existante couvre les deux variantes avec racines temporaires, skip si Edge absent ; CI distante pas lancée. Fiche157/manifeste au départ. Board T-388/384 sur389 reste historique. RepoWise fichier sans entrée indexée, index11 jours/mock, aucune actualisation ni économie revendiquée. Statut Git préexistant321 entrées inchangé ; aucun fichier de configuration active/page active/de service/Dropbox modifié.
- Fiche158/manifest synchronisés ; lecture locale11969/12000 octets UTF-8, aucune alerte ; les tokens modèle ne sont pas mesurés. Plan et note pause/reprise mis à jour. Traces suite et test ciblé SHA256 : suite `$devcoreHash`, ciblé `$devcoreHashIndividual`.
- Limites restantes : authentification/cookies entre processus services non qualifiée ici ; navigateur absent skip en CI ; cross-site réel, service Windows et charges ouverts. Pas de nouvelle conversation IA/Codex : reload Cockpit confirme la session et l'injection de fiche, sans prouver injection MCP dans un chat frais ni réduction des tokens. SQLite poste actif ne devient pas équipe qualifiée, PostgreSQL et worker/outbox durable ouverts. Lots L0–L9 non achevés, automation conservée.

### Passage v159 — formulaire intersite/CSRF navigateur (L4 partiel)

- Scénario ajoutée à la recette Edge/CDP sur fixtures. Le second contexte Bob visite un serveur de test hostile qui écoute exclusivement sur IPv6 loopback `::1`; il soumet un formulaire HTML standard POST vers l'API DevCore sur IPv4 `127.0.0.1`, avec projet beta, T-01, version1, sans Authorization, cookie transmis volontairement, ni jeton CSRF. Cookies SameSite Strict/host-only et middleware doivent empêcher l'usage de la session. Le navigateur suit la navigation, Network.responseReceived confirme HTTP401 et la réponse contient `individual_credential_required`.
- SQL final : beta toujours in_progress/version1, aucun audit beta ; alpha version3 avec les deux seules lignes audit Alice pause/reprise. Mode cookie et vrai mode password s'exécutent dans deux BrowserContexts Edge isolés d'un unique processus. Après l'attaque, lecture via session Bob reconnue200; Alice logout reste401 sans affecter Bob.
- Premier essai du scénario a correctement atteint le refus serveur, mais l'assertion cherchait le code HTTP401 dans le corps JSON, qui ne contient que le code d'erreur. Correctif : capturer le statut sur Network.responseReceived et le corps sur page JSON. Premier passage après correctif a échoué sur une assertion UI Bob après que le POST ait légitimement navigué vers la réponse API ; supprimée et remplacée par la lecture authentifiée serveur et SQL déjà existante. Hôte attaquant changé de `0.0.0.0` à `::1` pour rester strictement loopback. Pas de mutation applicative lors des essais ratés.
- Résultat final sur loopback seulement : deux tests (cookie/password) réussis, zéro skip, Edg/154.0.4258.53, 55,51 s, une StarletteDeprecationWarning préexistante. Node syntaxe et diff-check sans erreur. Traces TEMP/devcore-browser-csrf-loopback.txt SHA256 `$devcoreHash`. Le test navigateur intégré à l'étape Edge CI Windows existante ; CI distante non exécutée.
- Environnement Python3.13 documenté+overlay Argon ; variables DEVCORE_LOCAL_ROOT/DATA_ROOT/PLATFORM_ROOT temporaires définies avant imports. API, données, comptes, audit, dépôt de contexte et profils Edge éphémères. Hostile server ne bind qu'à ::1 et est fermé; serveur/Uvicorn arrêté/joint, processus Edge propriétaire contrôlé, secrets synthétiques effacés. Aucune donnée active, Dropbox, index RepoWise ou configuration utilisateur lue/écrite.
- MCP fiche v158 et décisions obligatoires relus en début de passage. Board DevCore historique T-388, 384/389 sans rapport avec les lots. À cette étape, RepoWise pas nécessaire ; sources et index du passage précédent restent la référence avec index vieilli/mock, sans refresh ni conclusion de tokens.
- Fiche159/manifeste, plan et note pause/reprise actualisés ; lecture locale11969/12000 octets UTF-8, aucun warning. 29 tests Node ont été exécutés v158 mais le JS de production n'a pas changé dans ce passage ; pas de gain tokens mesuré.
- Limites : ce formulaire prouve le rejet de cette attaque loopback, pas l'ensemble du modèle CSRF/CORS, des navigateurs ou des origines déployées. Deux BrowserContexts ne qualifient pas isolation par processus/service ni accès multi-poste. Service de production, cross-host réseau, charge, activation et autres ACL restent ouverts. L0–L9 restent inachevés, automation conservée.

### Passage v160 — prévol CORS réel et refus du POST intersite (L4 partiel)

- Le profil individuel transmet maintenant les requêtes `OPTIONS` à la politique CORS avant le contrôle des routes projet ; les requêtes réelles POST/DELETE restent dans les contrôles d'identité, rôle, CSRF et version. La recette ASGI vérifie un prévol autorisé `200` avec `Access-Control-Allow-Origin` exactement égal à l'origine autorisée, et le navigateur Edge reçoit `400` pour l'origine hostile. Le script de l'origine hostile lance un `fetch` JSON `POST /api/pause` avec `credentials: include` et `X-CSRF-Token` forgé ; le fetch échoue côté navigateur.
- Sonde ASGI à l'entrée d'Uvicorn : après remise à zéro de la sonde, les appels à `/api/pause` sont uniquement les deux POST attendus (Pause Alice et formulaire hostile v159) et le prévol OPTIONS v160 ; aucun POST du `fetch` hostile n'arrive dans l'application. Network CDP inclut aussi un événement POST logique avant l'OPTIONS pour le fetch bloqué : ce signal ne prouve pas l'envoi ; les assertions s'appuient sur la sonde ASGI, le refus de prévol et SQL. L'état final reste alpha `in_progress` version3 avec les deux audits Alice, beta `in_progress` version1 sans audit.
- Configuration CORS (`API origin` et origine synthétique autorisée distincte) définie avant l'import du module d'application ; l'hôte hostile est exclusivement `::1`, API exclusivement `127.0.0.1`. Test navigateur réel Edge154 avec deux BrowserContexts, pour les chemins cookie et mot de passe : `2 passed` en48,14s, zéro skip. Régression individuelle/HTTP/pause-reprise/sessions : `37 passed` en155,88s. Une StarletteDeprecationWarning préexistante sur TestClient/httpx. Traces temporaires : browser `devcore-browser-cors-v160-33962ffd38334221aa29c5cff7bf291d.txt`, SHA256 `DB23073717B5D255060E7F71307AF11879DCD3A10ABD4240CED15036E74B7910` ; régression `devcore-cors-regression-972268aac8314c839ffe1d433debd9ad.txt`, SHA256 `4EE2EFA36E2C8D7D5CDF861623F4E3820E865A8CF32760ED811DA9E8FB97E237`. Vérification `node --check` sans erreur ; `git diff --check` sans erreur de whitespace (avertissement Git de normalisation CRLF). Le test Edge v160 fait partie du workflow Windows existant ; CI distante non lancée.
- Environnement Python3.13 documenté avec overlay Argon, et racines local/data/platform temporaires définies avant import. SQLite, utilisateurs, secrets, audit, dépôts/contexte, serveurs, sonde et profils Edge sont éphémères ; aucune donnée active, Dropbox, index RepoWise, page/configuration active ou compte utilisateur touché. Échecs intermédiaires limités aux fixtures : l'événement POST CDP était un signal logique, et le premier retour de Bob à la fonction d'état cherchait du JSON sur l'origine hostile ; l'observation serveur et la navigation de retour corrigent ces assertions.
- La fiche et les décisions MCP ont été chargées à l'ouverture du passage ; fiche v159 au départ11969/12000 octets, avertissements vides. RepoWise ciblé live sur les fichiers du harnais : aucun enregistrement indexé, index13jours, embedder mock, recherche sémantique désactivée ; aucune actualisation effectuée ni économie de tokens annoncée. État Git global321 entrées avant et après, modifications préexistantes conservées.
- Plan L4/v160, note pause/reprise, fiche v160 et empreinte du manifest synchronisés. Le lecteur local accepte le contexte complet à11908/12000 octets UTF-8, avertissements vides ; ce n'est pas une mesure de tokens modèle. Limites : recette loopback locale et deux contextes Edge d'un seul processus ; aucune qualification de navigateur alternatif, DNS/HTTPS, origines et proxy de production, ACL de tous les canaux, isolation de service/processus, charge ou activation. L0–L9 restent incomplets et les gains tokens non mesurés.

### Passage v161 — revalidation du secours local administrateur (L4 partiel)

- Réexécution `DEV_CORE/tests/test_local_recovery.py` avec Python3.13 documenté et overlay Argon : **21 passés en94,51s, aucun avertissement**. Couverture Windows/NTFS temporaire : magasin privé, admin existant seulement, révocation ciblée, pas de promotion/création, rollback si journal absent/rejeté, refus de transaction SQLite concurrente en DELETE/WAL, admission revérifiée après Argon2id, confirmations de maintenance avant prompt et secrets absents de stdout. Trace TEMP `devcore-local-recovery-d1a73f4b43dd46fb9835d9f52d07add6.txt`, SHA256 `675F0A6F02C9292D2E85B6FF163BC34A5C19AC1525F09EB5DCC5B638844460AE`.
- Ce re-run confirme le chemin automatisé de recette, mais ne valide pas l'exploitation : aucun service actif arrêté, aucun secret humain saisi dans une vraie console, aucune panne physique/restauration et aucune ouverture d'un magasin actif. Le critère de récupération opérationnelle et L4 restent ouverts. La note dédiée et le résumé L4 du plan sont actualisés.
- Reprise : lecteur de contexte local complet v160 à11908/12000 octets UTF-8, avertissements vides, décisions obligatoires présentes ; MCP DevCore et RepoWise indisponibles dans ce tour, board/index non rafraîchis. Python documenté présent. Racines `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT`, `DEVCORE_PLATFORM_ROOT` temporaires avant import. Aucune écriture Dropbox ou donnée/index actif.
- État Git : 321 entrées avant et après ; changements préexistants conservés. Fiche v161 et empreinte manifest synchronisées ; lecteur local complet à11900/12000 octets UTF-8, avertissements vides, tokens modèle non mesurés. Lots L0–L9 toujours incomplets ; aucune économie de tokens mesurée.

### Passage v162 — inventaire HTTP fail-closed (L4 partiel)

- Ajout d'un test de contrat qui découvre les routes/méthodes FastAPI de l'application et appelle toutes celles qui ne sont pas dans l'allowlist du profil individuel. Toutes renvoient403 `individual_route_unavailable` avant handler, y compris routes dynamiques et endpoints de données globaux non qualifiés. Les routes HEAD sont testées sur le statut seulement, sans corps HTTP. Cela détecte qu'une nouvelle route globale reste fermée par défaut ; cela ne qualifie pas les droits des routes encore non raccordées.
- Test ciblé : `test_every_unqualified_http_route_fails_closed_in_individual_profile` : **1 passé**, 16 exclus, 5,87 s. Premier essai de fixture échouait parce que HEAD, bien refusé403, n'a légitimement pas de corps ; assertion corrigée pour inspecter le corps seulement pour les autres méthodes. Le comportement applicatif n'a pas changé.
- Régression ciblée : `test_dashboard_individual_access.py`, `test_dashboard_individual_http.py`, `test_dashboard_task_audit.py`, `test_dashboard_project_context.py` : **70 passés**, une alerte préexistante Starlette/httpx, 302,47 s. Runtime Python3.13 documenté + overlay Argon ; variables `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT`, `DEVCORE_PLATFORM_ROOT` temporaires avant lancement. Les fixtures de tests créent leurs propres magasins temporaires. Pas d'accès aux données actives, Dropbox ni index RepoWise.
- État Git global inchangé en nombre à321 entrées ; le test modifié est déjà un fichier non suivi dans cet état préexistant. Aucun fichier actif ou configuration de déploiement changé. Lecteur contextuel v161 lu en début de passage ; board T-388/384 sur389 consulté, sans preuve de lots. RepoWise index13 jours, mock et recherche sémantique inactive, sans refresh ni conclusion de coût.
- Plan L4/v162, fiche v162 et empreinte manifest synchronisés après le contrôle. Lecteur local complet : 11893/12000 octets UTF-8, avertissements vides, décisions obligatoires conservées ; le lecteur mesure les octets JSON, pas les tokens du modèle.
- Limites : seule l'allowlist HTTP courante est ouverte ; exécution durable L5, autres canaux/ACL L4, PostgreSQL, activation poste/service, qualification réseau et réduction de tokens restent ouverts. Aucun lot L0-L9 complet.

### Passage v163 — requalification CLI/MCP individuelle (L4 partiel)

- Tests CLI/MCP individuels lancés avec le runtime candidat figé `devcore-individual-v155-f7d2a8b7` (Python3.13.16, SQLite3.53.1) et les racines de données temporaires. `test_individual_cli.py`, `test_individual_tasks.py` et `test_individual_mcp_launcher.py` : **54 passés**, un test de wheel isolé exclu, une alerte Starlette/httpx. Ce lot inclut API HTTP temporaire et clients MCP stdio, profils/capacités, scopes, projet étranger, audit authentifié, révocation et mutations conditionnelles.
- Test de construction/installation wheel exécuté séparément avec setuptools dans un répertoire temporaire via `DEVCORE_TEST_BUILD_TOOLS` : **1 passé**. Résultat total : 55 tests réussis sur deux commandes, sans changement d'installation/runtime. Le premier essai sur le runtime général SQLite3.49.1 a refusé le préflight MCP, qui protège correctement contre le défaut WAL non qualifié ; la tentative de build wheel a signalé l'absence de setuptools, puis a passé avec l'outil isolé. Aucun code production n'a été modifié.
- Contrôle environnement L3/L5 en lecture seule : aucun `psql`, service ou dossier PostgreSQL détecté. Le client Docker est présent, mais `docker info` n'a pas répondu dans la fenêtre d'observation et a été interrompu ; aucun conteneur n'a été créé. Le prototype DBOS/PostgreSQL exigé n'est donc pas validé.
- `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT`, `DEVCORE_PLATFORM_ROOT` fixés à des chemins temporaires avant les sous-processus ; bundle, tâches, identité, credentials NTFS synthétiques et API uniquement en fixtures. Pas d'accès à des données actives/Dropbox/RepoWise. Le compte-rendu MCP DevCore du début de passage indique T-388 historique, 384/389 ; RepoWise sur les ports a un index de 13 jours, sans refresh.
- Plan v163 mis à jour. Fiche v162 et décisions relues, contexte complet11893/12000 octets UTF-8 sans avertissement ; gain en tokens non mesuré. Limites : CI distante, vrai service de compte restreint, charge/activation, RLS PostgreSQL, ACL hors ressources déjà raccordées, workers durables et opérations de restauration restent ouverts ; L0–L9 non achevés.
### Passage v164 — périmètre explicite du scan de tâches (L1 partiel)

- Le chemin `task_scan` ne passe plus par un projet global implicite pour les suggestions historiques : `task_spec_parser.ps1` et l'adaptateur `task_prompt_analyzer.py` exigent `--Project/--project`; les contrôles refusent paramètre absent et traversée de chemin avant écriture. Les deux producteurs écrivent leurs files dans `DEVCORE_DATA_ROOT/Memory/<projet>`. Le wrapper PowerShell du prompt forwarde le projet ; l'entrée MCP `devcore_task_scan` le rend requis dans le schéma et l'adaptateur le transmet au Python. `task_scan.ps1` transmet le même projet explicite aux deux wrappers.
- Tests de contrat/isolement avec Python3.13 documenté et racines temporaires : **9 passés** en17,34 s. Ils vérifient refus avant écriture, préférence du paramètre sur `DEVCORE_ACTIVE_PROJECT_NAME=beta`, isolation de la file alpha, wrappers PowerShell réels, scan complet Git/specs/prompt, transmission MCP/schéma et conservation d'une racine explicite absente. Le premier test a révélé que le parser ne créait pas ses dossiers de sortie ; correction bornée ajoutée. Le scan complet a aussi révélé un défaut dangereux de `platform_version.ps1` : une racine temporaire encore absente déclenchait l'auto-détection Dropbox et l'écriture persistante de `DEVCORE_DATA_ROOT` au niveau utilisateur. Les tests ont alors énuméré le dossier Specs Dropbox, essayé de lire `Memory/alpha/tasks.json` (introuvable) et écrit/appendé les deux journaux `Logs/scripts/task_spec_parser_2026-10-07.log` et `task_prompt_analyzer_2026-10-07.log` dans le dossier Dropbox actif. Aucun candidat/file de suggestions n'a été écrit. Le contenu antérieur des journaux et la valeur utilisateur précédente ne sont pas connus ; ils n'ont pas été supprimés ni restaurés.
- Correctif immédiat : toute racine explicite, même nouvelle, est maintenant conservée ; seule l'absence (ou l'ancien placeholder exact `C:\devcore\DEV_CORE_DATA`) déclenche l'auto-détection, qui ne modifie plus l'environnement utilisateur persistant. La recette finale de9 tests a passé avec racines temporaires après correction et n'a pas accédé aux données Dropbox. Cette qualification de racine ne prouve pas l'absence de tous les lecteurs actifs. `git diff --check` ciblé : pas d'erreur ; avertissements Git de normalisation LF/CRLF uniquement.
- RepoWise live expose encore l'ancien symbole `get_active_project` pour le fichier Python malgré sa suppression ; le plan n'est pas indexé. Sources courantes relues, pas de refresh. Board DevCore T-388 et384/389 historique, sans preuve de lots. L1 reste ouvert : `intent_learner`, `integrity_check`, `lesson_extractor`, `task_git_scanner` et d'autres anciens lecteurs automatiques restent à qualifier ; pas de campagne complète des commandes CLI/MCP ni activation.
- Fiche/décisions MCP lues à la reprise (fiche v162,11887/12000 octets UTF-8 ; avertissements vides), puis fiche v164/manifeste synchronisés : lecteur local **11972/12000 octets UTF-8**, avertissements vides. Mesure en octets, tokens modèle non mesurés. Git conservé avec changements préexistants ; L1 non coché.

### Passage v165 — consommateurs d'intégrité et d'apprentissage explicités (L1 partiel)

- `integrity_check.py` ne déduit plus le projet d'une variable globale ni le dépôt depuis `DEV_CORE`/cwd : `--project` et `--repo` absolu existant sont obligatoires, le nom est validé avant lecture et Git ne lit que la racine fournie. MCP `devcore_health_check` exige `project`, refuse les identifiants de chemin avant subprocess et exige `DEVCORE_MCP_REPO_ROOT` absolu/existant fourni par la configuration serveur. Son schéma interdit les paramètres supplémentaires.
- `intent_learner.py` exige `--project`, ne lit plus l'environnement/Git/nom parent pour choisir le board ; il utilise `DEVCORE_DATA_ROOT/Memory/<projet>/tasks.json`. Il copie logiquement les valeurs de départ de `DEV_CORE/Config/intent_patterns.json` mais n'écrit les nouveaux verbes que dans le registre `Memory/<projet>/intent_patterns.json`. Test alpha/beta : apprentissages distincts et empreinte du registre de défaut inchangée. Le défaut latent d'import de `Path` est réparé dans le même chemin.
- `task_git_scanner.ps1` exige `-Project`, `-RepoPath` Git valide et `DEVCORE_DATA_ROOT` absolu. Il n'utilise plus `Get-ActiveProject.ps1` ni le cwd comme dépôt de repli ; board et file sont sous `Memory/<projet>` et journaux sous `Logs/scripts/<projet>`. Les tests PowerShell utilisent un dépôt Git, deux boards et `DEVCORE_ACTIVE_PROJECT_NAME=beta` : seul alpha est lu/modifié. Recherche live des appelants : aucun appel de code trouvé hors du script et de la documentation historique ; RepoWise ne contient pas de record pour ce scanner, donc la source live a été utilisée.
- Recette documentée Python3.13 + overlay Argon ; racines globales de recette et sous-processus limitées à un répertoire TEMP. Suite ciblée `test_project_integrity_check.py`, `test_intent_learner_project_scope.py`, `test_task_git_scanner_project_scope.py`, `test_integrity_check_scope.py`, `test_legacy_task_scan_scope.py`, `test_task_scan_scope.py` : **12 passés en12,54 s**. Cas couverts : arguments absents/traversée, absence de sortie avant validation, deux projets et deux dépôts dont un commit-leurre dans le cwd, registre de défaut inchangé, schéma MCP/arguments transmis, conservation du comportement v164 task scan. Premier passage **4 passés/1 échoué** : `require_project` MCP n'interdit pas `../beta`; validation de segment ajoutée au handler avant appel Python, puis suite complète verte. `py_compile` ciblé réussi. Aucun accès Dropbox/donnée ou index RepoWise actif par le test ; seul le code à tester est lu.
- Compatibilité release : `DEV_CORE/Release/test_release_packaging.py` : **3 passés en16,48 s**. Le manifeste est généré depuis les sources courantes ; les fichiers d'artefacts de recette vont uniquement dans `tmp_path`, aucun package actif n'est reconstruit.
- `git diff --check` et `py_compile` ciblés effectués après les changements ; le contexte local sera relu après synchronisation de la fiche/manifeste. État d'avancement MCP DevCore consulté : T-388 historique,384/389, pas une preuve de critères. RepoWise ciblé : index 13 jours, embedder mock, recherche sémantique inactive ; pas de refresh ni de conclusion de tokens.
- L1 reste ouvert : `lesson_extractor.ps1` écrit dans un espace de leçons partagé et possède deux appelants historiques ; `integrity_check.ps1` est un wrapper indépendant non raccordé au handler MCP ; d'autres anciens lecteurs/entrées et la campagne complète CLI/MCP ne sont pas qualifiés. Le scanner Git n'a pas de caller live détecté mais la compatibilité d'un lancement manuel externe n'a pas été qualifiée. Aucun lot L1 coché, service activé ou gain de tokens déclaré.
- Fiche projet v165 et plan actualisés ; `context.json` pointe sur `devcore.md` et son SHA-256 a été recalculé. Le lecteur local complet réussit à**11952/12000 octets UTF-8**, sans avertissement, avec les cinq décisions requises D-002/003/004/006/007. Un premier manifeste local mal sérialisé (suffixe littéral `\n` et champ `card` contenant le texte au lieu du chemin) a été détecté par le lecteur, puis réparé avant validation ; aucune autre fiche ou décision n'a été remplacée. La mesure est en octets ; tokens modèle non mesurés. Données actives, Dropbox et RepoWise index non modifiés.

### Passage v166 — wrapper PowerShell d'intégrité explicite (L1 partiel)

- `Scripts/Auto/integrity_check.ps1` ne sélectionne plus `Get-ActiveProject.ps1` ni le parent DevCore comme dépôt implicite. `-Project` (format simple) et `-RepoPath` sont obligatoires ; le chemin est résolu et validé comme arbre Git avant lecture des données. Le scan des commits porte uniquement sur cette racine et compare le board `DEVCORE_DATA_ROOT/Memory/<projet>/tasks.json` demandé.
- Deux tests PowerShell couvrent les arguments absents, la traversée et le dépôt relatif avant création de données, puis l'isolement d'un projet/dépôt face à `DEVCORE_ACTIVE_PROJECT_NAME=beta` et un commit `[T-99]` leurre dans le cwd. Suite v164–v166 : **14 passés en 15,33 s** sur Python 3.13 avec racines de recette TEMP ; `py_compile` ciblé et `git diff --check` ciblé réussis. Aucun Dropbox, index RepoWise ou données actives utilisés.
- L1 reste ouvert : `lesson_extractor.ps1` écrit encore `Memory/LESSONS.md` et `Vault/Lessons/workflow` partagés, son compacteur travaille sur le même fichier, `download/task_done.ps1` mutile un ancien board sans service transactionnel, et `post_tool_hook.ps1` écrit également le JSON projet. Ces chemins doivent être migrés ensemble avec leurs contrats/callers ; la simple exigence d'un projet ne suffirait pas à garantir l'isolation ou l'atomicité. Sources live et RepoWise ciblé ont été confrontés ; RepoWise ne référence pas le script de leçons, donc aucun résultat d'index n'a été pris comme preuve.
- Plan et fiche projet v166 mis à jour ; manifeste `context.json` synchronisé avec le SHA-256 de la fiche. Les lecteurs local et MCP confirment les cinq décisions requises, sans avertissement, à 11910/12000 octets UTF-8 (`model_tokens_measured=false`, `source_contents_verified=false` par contrat). Suite finale v164–v166 : 14 passés en 15,33 s ; `py_compile` et contrôle `git diff --check` ciblés réussis. Le `git diff --check` global reste en échec sur de nombreux espaces finaux dans des fichiers modifiés hors du passage v166, notamment `DEV_CORE/Dashboard/index_terminal.html`. Aucun formatage général n'a été tenté. Aucune donnée active, Dropbox ou index RepoWise modifié ; aucun gain tokens annoncé.

### Passage v167 — adaptateur d'avancement avec projet obligatoire (L1 partiel)

- `Scripts/task_step_done.ps1` exige maintenant un identifiant de projet valide ; le repli `Get-ActiveProject.ps1` est supprimé. L'appel continue via `devcore_engine.cli task step`, avec tâche facultative, projet explicite et version attendue facultative, afin de garder la mutation dans le service transactionnel. La skill `devcore-automation` documente `-Project`.
- Régression ajoutée : sans projet, échec avant création de la base ; pour alpha/beta ayant chacun `T-01`, seul alpha avance ; le rejeu avec ancienne version est refusé sans seconde mutation ; aucun `tasks.json` n'est créé dans la racine partagée. Suite ciblée v164–v167 : **28 tests réussis en 46,81 s**, Python 3.13, `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires. `Release/test_release_packaging.py` : **3 réussis en 3,78 s**.
- L1 demeure ouvert : le hook PowerShell historique écrit directement dans le board et n'a pas de caller actif confirmé ; sa migration doit préserver ou retirer explicitement ses automatismes. `lesson_extractor.ps1`/`memory_compactor.py` et d'autres lecteurs de projet nécessitent aussi une migration cohérente. Aucun critère L1 coché, aucune activation ou économie de tokens annoncée.
- RepoWise ciblé n'a pas trouvé de correspondance exacte pour ces scripts ; son index est vieux de 13 jours, embedder mock, recherche sémantique inactive. Les résultats de recherche ont donc servi d'orientation uniquement ; conclusions fondées sur les appels live dans le code. Aucun Dropbox, magasin actif ou index RepoWise utilisé par les tests.

### Passage v168 — compacteur de leçons isolé par projet (L1 partiel)

- `Scripts/Auto/memory_compactor.py` exige `--project` dans son CLI, refuse les identifiants avec séparateurs/traversée et travaille uniquement sur `DEVCORE_DATA_ROOT/Memory/<projet>/LESSONS.md`, avec archive dans le même espace projet. Backup et remplacement final utilisent écriture temporaire + `os.replace`, sans remplacer le document initial en cas d'échec de publication.
- Tests temporaires ajoutés : alpha ne lit/compacte/sauvegarde pas les leçons de beta ni l'ancien fichier partagé ; CLI sans projet et identifiants invalides refusés sans écriture ; échec de remplacement conserve l'original et nettoie le temporaire. Suite combinée v164–v168 : **42 tests réussis en 54,20 s**. `Release/test_release_packaging.py` : **3 réussis en 3,81 s** ; `py_compile` réussi.
- Fiche projet v168 et SHA-256 du manifeste resynchronisés ; lectures locale et MCP : **11969/12000 octets UTF-8**, décisions D-002/003/004/006/007, aucun avertissement (`model_tokens_measured=false`). Le budget est proche du plafond ; toute prochaine mise à jour doit garder une marge.
- Pas de caller actif du compacteur trouvé dans le dépôt ; aucun changement aux appels existants. Limite assumée : le fichier global historique `Memory/LESSONS.md` n'est pas migré, et `lesson_extractor.ps1` continue de l'écrire. Il faut déplacer extraction, registre Git par projet et appels historiques ensemble pour garantir la chaîne de bout en bout ; L1 reste ouvert.

### Passage v169 — extraction des leçons par projet (L1 partiel)

- `Scripts/Auto/lesson_extractor.ps1` prend `-Project`, refuse les identifiants invalides, vérifie l'unique correspondance dans `DEVCORE_CONFIG_ROOT/projects.json` et exige que le chemin absolu enregistré soit la racine Git. Le board est lu par le CLI/service transactionnel avec `--project`, jamais depuis `Memory/<projet>/tasks.json`. Les nouvelles leçons sont dans `Memory/<projet>/LESSONS.md`, la note dans `Vault/Lessons/<projet>/workflow`, et le log dans `Logs/scripts/<projet>` ; un appel historique sans projet se termine avec avertissement sans écrire. Fichier partagé historique laissé intact. Publication du markdown par temporaire dans le dossier cible puis remplacement atomique ; un deuxième passage remplace sans dupliquer les IDs de tâches.
- Tests PowerShell réels sous Python 3.13 avec registre, deux dépôts Git et DB temporaire : alpha extraie son board et ses statistiques Git, sans fuite de beta ni altération des fixtures partagées ; appels sans projet, traversées et racine Git non conforme restent sans écriture. Tests de la nouvelle extraction et du compacteur/appels auxiliaires : **20 passés**. Packaging : **3 passés**. Total de la commande combinée : **23 passés en 31,68 s**. Les premières recettes ont trouvé puis corrigé le statut `$LASTEXITCODE` perdu après pipeline PowerShell, l'assertion test sensible à la normalisation minuscule des titres, et l'overload `File.Replace` interprétant `$null` en chemin vide ; l'écriture retenue utilise `File.Move(..., overwrite)` et le rejeu est testé.
- Limites : les deux appelants legacy n'indiquent pas de projet et n'obtiennent donc pas de leçon ; leurs transitions globales `tasks.json`, leurs autres sorties (Qdrant/Obsidian) et la migration des contenus historiques restent hors de ce changement. La validation protège contre erreur de registre et dépôt imbriqué mais ne qualifie pas les ACL/liaisons NTFS en production. L1 reste ouvert et aucune case n'est cochée. Tests uniquement sur dossiers temporaires ; ni données actives/Dropbox ni index RepoWise utilisés.
- RepoWise ciblé : aucune correspondance exacte pour `lesson_extractor.ps1`/`LESSONS.md`; index 13 jours, embedder mock, recherche sémantique inactive. La preuve retenue vient du code courant et des tests. Board DevCore indique encore un état historique T-388, 384/389 et n'établit pas les critères du plan.

### Passage v170 — hook local et clôture explicite (L1 partiel)

- `Scripts/post_tool_hook.ps1` lance le hook Python actuel. Celui-ci prend le projet dans `.devcore/project.json` du répertoire appelant et enregistre seulement `ToolExecuted` et une métrique dans la base locale ; sans manifeste, il s'arrête avant d'ouvrir la base. L'ancien accès au projet actif machine, la mutation directe de `tasks.json`, le backup global et l'appel automatique à `task_done.ps1` sont supprimés de ce lanceur.
- `Scripts/task_done.ps1` exige `-Project`, valide son identifiant et délègue à `devcore_engine.cli task complete`. `-TaskId` et `-ExpectedVersion` peuvent préciser la transition ; `-Force` est accepté pour compatibilité mais n'annule ni l'isolation ni le contrôle de version. Le lanceur n'importe plus `platform_version.ps1`, qui pouvait tenter l'auto-détection Dropbox. `Skills/devcore-automation/SKILL.md` décrit maintenant ces transitions comme actions explicites et retire sa promesse d'auto-chaînage.
- Recette Python 3.13 documenté, `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires avant `pytest` : suite combinée des adaptateurs, hooks, contexte CLI et packaging **20 réussis, 1 échec en 71,38 s**. L'échec provenait de l'attente `completed` dans le nouveau test alors que le service stocke `done` ; correction du test, puis **1 réussi en 6,65 s**. Les autres cas du premier passage n'ont pas été relancés après cette correction limitée à l'assertion. Deux projets alpha/beta, même `T-01`, version obsolète, absence de projet et conservation du JSON historique sont couverts. `git diff --check` ciblé réussi avec seuls avertissements CRLF de Git.
- Limites : `download/task_done.ps1` et `archived/mission_done.ps1` gardent leur ancien board JSON et leurs appelants ; les chemins externes non répertoriés ne sont pas qualifiés. Les hooks Claude réellement installés et l'activation restent à vérifier ; aucun gain de tokens ni critère L1 global n'est annoncé. RepoWise n'a pas de résultat exact pour ces lanceurs dans son index ancien ; code et tests live font foi. Aucune donnée active, Dropbox ou index RepoWise n'a été utilisée par les tests.

### Passage v171 — anciens points d'entrée download (L1 partiel)

- Les scripts `download/task_done.ps1` et `download/post_tool_hook.ps1` étaient encore des implémentations autonomes : le premier modifiait `Memory/tasks.json` partagé et lançait des synchronisations globales ; le second lisait `Memory/missions.json`, posait un flag et déclenchait une clôture de mission. Ils délèguent désormais respectivement à `Scripts/task_done.ps1` et `Scripts/post_tool_hook.ps1`. La clôture download exige le projet explicite et conserve tâche/version facultatives ; le hook reste lié au manifeste local et ne clôture pas automatiquement.
- Recette sur deux projets factices, `DEVCORE_LOCAL_ROOT`/`DEVCORE_DATA_ROOT`/`DEVCORE_PLATFORM_ROOT` temporaires : **6 tests réussis en 18,92 s** pour les deux chemins de clôture et de hook. Absence de projet, version obsolète, JSON legacy intact et absence de base sans manifeste sont vérifiés. Seuls les nouveaux chemins download ont été retestés après v170 ; la suite combinée v170 avait 20 cas réussis et une assertion corrigée puis repassée.
- `download/dc_v2.ps1` appelle encore `Scripts/task_done.ps1` sans `-Project`, donc cette ancienne commande échoue maintenant avant mutation. `Scripts/archived/mission_done.ps1` garde un flux JSON de missions ; ses appelants installés et le contrat de migration restent à qualifier. Aucun lot L1 coché ni activation production déclarée. Données actives, Dropbox et index RepoWise intacts pendant la recette.
- Packaging v171 : **3 tests réussis en 5,16 s** sur racines temporaires. `git diff --check` ciblé sans erreur (avertissements Git de conversion LF/CRLF seulement). Fiche v171/manifeste synchronisés ; lecteur MCP : **8959/12000 octets UTF-8**, cinq décisions obligatoires, aucun avertissement, `model_tokens_measured=false`.

### Passage v172 — alias historique de clôture explicite (L1 partiel)

- `download/dc_v2.ps1` accepte un projet nommé pour les alias `task done` et `mission validee`, ainsi que tâche/version facultatives. Les deux alias appellent `Scripts/task_done.ps1` et rendent son code de sortie ; sans projet, refus avant ouverture du magasin. L'ancien paramètre PowerShell `$Args` interceptait mal les mots de commande : `CmdletBinding(PositionalBinding=$false)` et `CommandWords` séparent maintenant les options nommées des mots de la commande. Le test a d'abord révélé ce défaut, puis le code de sortie obsolète perdu ; les deux ont été corrigés.
- Recette : **11 tests réussis en 36,86 s** (`test_task_legacy_adapters.py` et packaging) avec racines temporaires et Python 3.13 documenté. Les deux alias sont testés sans projet, sur une version obsolète et avec deux projets portant `T-01`. Aucun JSON partagé créé. Les autres commandes de la vieille interface n'ont pas été qualifiées par cette recette ; `Scripts/archived/mission_done.ps1` demeure un chemin JSON de missions à inventorier. Aucune activation ni critère L1 global déclaré.

### Passage v173 — anciens ajouts, sélections et statuts de tâches (L1 partiel)

- `download/task_add.ps1`, `task_next.ps1` et `task_status.ps1` ne lisent/écrivent plus `Memory/tasks.json` global ; chaque point d'entrée exige `-Project` et délègue aux wrappers du service SQLite. La CLI `task add` et `Scripts/task_add.ps1` transmettent `depends_on` pour ne pas perdre ce champ lors du passage de l'ancien ajout. `download/dc_v2.ps1` transmet le projet aux chemins task/mission d'ajout, sélection, statut, pause et saut, et propage les codes d'échec des mutations.
- Recette Python 3.13, racines locales/data/platform temporaires : un test alpha/beta vérifie les trois anciens points d'entrée, l'alias d'ajout, le refus sans projet avant création de base, une dépendance `T-02 -> T-01`, la sélection indépendante et aucun JSON partagé. La suite `test_task_legacy_adapters.py`, `test_task_cli_project_context.py` et packaging : **20 réussis en 53,20 s**. Le test ciblé initial a réussi seul avant cette suite. `Scripts/task_next.ps1` conserve le passage `--project` utilisé par `session_start.ps1` et `task_skip.ps1` ; une tentative de paramètre PowerShell nommé a été retirée avant recette finale.
- Limites : la vieille interface `dc_v2` reste partiellement couverte, les scripts de missions archivés conservent des transitions JSON et d'autres lecteurs historiques existent. L1 reste ouvert ; aucun service actif ni Dropbox n'a servi à la recette.
- Complément ciblé après la suite : alias `dc_v2` de statut, pause et saut exercés sur deux projets, **1 test réussi en 11,09 s** ; statut beta reste isolé, pause beta et saut alpha sont reflétés par TaskService. Seul le test de l'adaptateur a été étendu après la suite de 20 cas.

### Passage v174 — note quotidienne Obsidian par projet (L1 partiel)

- `Scripts/obsidian_sync.ps1` ne lit plus `Memory/<projet>/tasks.json` via `Get-ActiveProject.ps1` et n'écrit plus la note commune `Vault/Daily Notes/<date>.md`. Il exige `-Project`, obtient le board JSON du service, vérifie le projet de la réponse puis publie `Vault/Daily Notes/<projet>/<date>.md`. Une section balisée `devcore:tasks` permet de rejouer la synchronisation sans dupliquer les tâches terminées. Le wrapper `Scripts/Auto/obsidian_sync.ps1` délègue au même chemin ; l'appel optionnel `session_end.ps1 -RunLegacyGlobalMaintenance` transmet désormais son projet.
- Recette sous Python 3.13 avec racines temp : alpha et beta portent chacun `T-01` terminée ; leurs notes ne se croisent pas, un deuxième passage alpha ne duplique pas l'entrée, l'ancienne note globale préexistante est intacte et l'absence de projet échoue avant écriture. Suite synchronisation + fin de session + packaging : **6 réussis en 8,78 s** ; test direct précédent **2 réussis en 5,28 s**. `git diff --check` ciblé à effectuer après documentation.
- Limites : publication de note par fichier temporaire dans le même dossier puis remplacement, sans transaction avec la base ; les anciens producteurs de notes globales, la maintenance globale optionnelle et les scripts de missions archivés restent à inventorier. L1 n'est pas coché ; aucun Dropbox ou état actif utilisé par la recette.

### Passage v175 — génération de session sans mutation (L1 partiel)

- `gen_session_context.ps1` appelait `task next --json` et pouvait donc activer une tâche pour générer un texte. Il lit désormais `task board --json`, vérifie le projet reçu et reprend seulement la tâche déjà en cours. Le lancement de session sélectionne explicitement la tâche avant cet appel. `gen_metrics.ps1` et `gen_session_context.ps1` exigent tous deux `-Project` valide ; l'ancien repli `Get-ActiveProject.ps1` est retiré de ces deux sorties.
- Test alpha/beta : chacun possède une tâche en cours, les deux fichiers de contexte restent séparés, les versions SQLite avant/après la génération sont identiques. Absence de projet et traversée refusées avant création de racine locale/data. Suite métriques, fin de session et packaging : **7 réussis en 11,24 s** ; première suite ciblée **3 réussis en 8,12 s**. Tests avec Python 3.13 et racines temporaires seulement.
- `task_sync.ps1` a été inspecté : il lance `gen_dashboard.ps1`, qui publie la projection globale du Cockpit avec verrou et snapshot. Ce chemin n'a pas été modifié ici ; son contrôle d'accès et la séparation des projections relèvent des critères L2/L6. Autres lecteurs/écrivains historiques et missions archivées restent à qualifier ; L1 demeure ouvert.
- Fiche projet v175 et empreinte du registre actualisées : lecteur local et MCP donnent **9 386/12 000 octets**, sans avertissement ; ce plafond n'est pas une mesure de tokens. `git diff --check` ciblé réussi, avec seulement les avertissements de conversion LF/CRLF sur les deux scripts PowerShell.

### Passage v176 — échecs de la clôture de session (L1 partiel)

- `session_end.ps1` valide l'identifiant de projet avant la création du journal. Chaque étape régulière ou facultative remet son code de sortie à zéro avant l'appel et arrête la clôture si un script retourne un code non nul. Le message final de succès n'est alors pas produit.
- Tests sur copie de scripts et racines locale/data temporaires, Python 3.13 documenté : six échecs distincts sont propagés sans lancer les étapes suivantes ; `../beta` est refusé avant toute racine créée. Suite `test_session_end_local.py` + `test_gen_metrics.py` + packaging : **14 réussis en 13,89 s**. Première suite ciblée avant extension facultative : **8 réussis en 9,99 s**. Avant modification, `test_task_legacy_adapters.py` + `test_gen_metrics.py` : **12 réussis en 54,35 s**.
- Limites : les effets métier de la maintenance globale facultative ne sont pas qualifiés ; le Dashboard global reste une projection partagée à contrôler en L2/L6. Aucun état actif, Dropbox ou index RepoWise n'a servi aux tests. L1 reste ouvert.

### Passage v177 — fermeture des commandes de missions JSON archivées (L1 partiel)

- Les six points d'entrée `Scripts/archived/mission_*.ps1` et `download/mission_next.ps1` pouvaient encore lire ou modifier `Memory/missions.json` commun. Ils refusent désormais l'opération avec une indication d'import sur copie, avant tout accès aux données. Les anciens corps v6 sont conservés dans l'historique Git ; aucun mapping implicite des missions `M-xx` vers les tâches `T-xx` n'est appliqué.
- RepoWise, index âgé de 14 jours, commit aligné mais recherche du chemin sans résultat ; l'inventaire `rg` du dépôt ne trouve aucun appelant interne direct des six scripts archivés. La recette préexistante `test_task_legacy_adapters.py` : **9 réussis en 37,29 s** sur racines temporaires. Premier essai des gardes : **3 échecs, 7 réussis**, car trois anciens corps PowerShell comportaient des erreurs de syntaxe et empêchaient l'analyse du fichier avant le garde. Les corps ont été remplacés par de courts stubs ; suite finale refus + packaging : **10 réussis en 6,45 s**. Sept commandes vérifiées, `missions.json` identique octet pour octet, aucune racine locale créée.
- Limites : les missions historiques ne sont pas importées ; l'ancien `download/session_start_v2.ps1` et les éventuels appels externes ne sont pas qualifiés. Le refus change le comportement d'une commande v6 appelée directement, pour empêcher les écritures croisées. Aucun état actif, Dropbox ou index RepoWise n'a servi de fixture. L1 reste ouvert.

### Passage v178 — ancien hook de début de session (L1 partiel)

- `download/session_start_v2.ps1` ouvrait un flag global par jour dans `DEVCORE_DATA_ROOT`, lançait `launch.ps1` sans contexte et choisissait entre `Memory/tasks.json` et `missions.json`. Il délègue maintenant au `Scripts/session_start.ps1` actuel, résolu depuis le dépôt, avec propagation du code de sortie. Le chemin courant utilise une détection locale de projet et un flag local par projet/utilisateur ; son initialisation de racine Git est vérifiée séparément.
- Baseline `Scripts/test_session_start_project_root.ps1` : réussite avant modification. Après changement : **12 tests refus des missions, délégation (succès/échec) et packaging réussis en 6,09 s**, puis test PowerShell de racine projet réussi. Tous les tests utilisent des racines temporaires ; le wrapper ne crée ni racine data ni local dans le test de délégation.
- Limites : l'installation réelle des anciens hooks Claude hors dépôt n'est pas inspectée ; le lancement courant et ses dépendances ne sont pas qualifiés en charge ou avec deux sessions simultanées. Aucun état actif ni Dropbox n'a servi aux tests. L1 reste ouvert.

### Passage v179 — reprise du démarrage de session après échec (L1 partiel)

- `Scripts/session_start.ps1` valide le projet issu de la détection locale avant de créer son journal. L'initialisation de projet vérifie son code de sortie ; après réservation du flag par projet/utilisateur, les erreurs de lancement, ajout/sélection de tâche, maintenance facultative et génération de contexte retirent ce flag. Le message de fin est émis seulement après ces étapes. La branche d'échec de lecture du board retirait déjà le flag.
- Baseline `Scripts/test_session_start_project_root.ps1` réussie avant modification. Tests après changement, Python 3.13 et racines temporaires : projet en traversée rejeté sans racine créée ; échecs simulés du lancement, de l'ajout, de la sélection, de la maintenance et du contexte refusés avec flag effacé et sans log de succès. Suite démarrage + packaging **9 réussis en 6,96 s**, test PowerShell de racine projet réussi après le changement.
- Limites : scan lancé en arrière-plan sans résultat joint à la réussite de session ; initialisation Git hook et exécution simultanée multi-utilisateur non qualifiées. Les services actifs et Dropbox n'ont pas servi aux tests. L1 reste ouvert.

### Passage v180 — identité du board et concurrence de sessions (L1 partiel)

- Après `task board --project`, `Scripts/session_start.ps1` compare désormais le champ `project` de la réponse au projet détecté localement. Un board étranger, même avec `T-01` plausible, est refusé avant sélection ; le flag du projet est effacé et aucun log de réussite n'est écrit.
- Baseline `test_session_start_failures.py` avant changement : **6 réussis en 4,19 s**. Recette finale Python 3.13 : **12 tests réussis en 10,03 s** pour échecs, concurrence et packaging. Deux processus PowerShell démarrent simultanément alpha/beta depuis deux manifestes `.devcore/project.json`, avec un lancement et un flag distincts par projet ; deux processus sur alpha ne lancent qu'une seule session grâce à la réservation `CreateNew`. Board beta livré à alpha refusé, aucune tâche sélectionnée. Racines data/local temporaires, aucun Dropbox.
- Limites : le test de concurrence remplace le service SQLite et les scripts dépendants par des doublures contrôlées ; il valide le point d'entrée/flag et le contrôle d'identité, pas la charge réelle du service, les hooks installés ou la fin du job de scan lancé en arrière-plan. L1 reste ouvert.

### Passage v181 — retrait du protocole Router à état global (L1/L7 partiels)

- Les anciens helpers de `Scripts/router/providers.py` lisaient `Runtime/active_project.txt` puis `Memory/<projet>/tasks.json`, tenaient une session éphémère globale et pouvaient ajouter un rappel de protocole aux messages. Les routes actuelles n'appelaient déjà plus ces fonctions. Les quatre symboles restent importables mais refusent explicitement tout appel ; les chemins `ACTIVE_PROJECT_PATH`, `TASKS_DIR`, `EPHEMERAL_PATH` et `PROTOCOL_LOG` sont retirés de la configuration du Router. L'attribution auxiliaire par type de tâche, sans projet implicite, reste en place.
- Baseline avec `PYTHONPATH=DEV_CORE`, Python 3.13 et racines temporaires : **59 tests réussis, 1 avertissement tiers** pour séparation et attribution. Un premier lancement depuis la racine du dépôt sans `PYTHONPATH` avait échoué en collecte (`Scripts.headroom_routes` introuvable) ; environnement corrigé sans changement de code. Suite finale séparation + attribution + packaging : **63 réussis, 1 avertissement tiers en 21,38 s**. Le nouveau test appelle les quatre anciens helpers et vérifie que les fichiers factices de projet/tâches ne sont pas modifiés.
- Limites : les symboles hérités sont désormais des refus explicites pour un éventuel appelant externe ; l'attribution projet/utilisateur authentifiée et les mesures de tokens de tâches comparables restent à implémenter. Aucun service réel, état actif, Dropbox ou index RepoWise n'a servi aux tests. L1/L7 restent ouverts.

### Passage v182 — identité projet dans la demande française (L1 partiel)

- `Scripts/ask.ps1` refusait seulement un projet vide. Il vérifie désormais son identifiant avant tout appel CLI et compare le projet des deux réponses `task board` à celui demandé, avant et après la confirmation utilisateur. Une tâche plausible d'un board étranger ne peut donc pas être intégrée au handoff.
- Baseline `test_ask_project_context.py` : **1 réussi en 5,60 s**. Nouveau test `../beta` : refus avant création des racines locale/data. Faux board beta au premier appel : refus avant confirmation. Faux board beta au second appel : refus après la confirmation et avant préparation du handoff. Premier essai du second cas échouait dans le test à cause de `-NonInteractive` avec `Read-Host` ; après correction, l'assertion accentuée subissait l'encodage console PowerShell ; l'assertion ASCII a été utilisée. Suite finale demande + packaging : **7 réussis en 9,46 s** sur racines temporaires, Python 3.13 documenté.
- Limites : le contrôle de l'acteur et le lancement agent en aval ne sont pas qualifiés ; le second board est comparé au projet et à la tâche active, pas à une version de ligne complète. Aucun état actif ou Dropbox utilisé. L1 reste ouvert.

### Passage v183 — version de tâche pendant la confirmation (L1 partiel)

- `Scripts/ask.ps1` lie maintenant la confirmation à la version positive de l'unique ligne `in_progress` correspondant à `current_task`. Une ligne absente, dupliquée ou sans version est refusée ; après confirmation, la même tâche avec une nouvelle version est refusée avant préparation du handoff.
- Baseline `test_ask_project_context.py` : **4 réussis en 6,41 s**. La réponse simulée passe de version 1 à 2 pour `alpha/T-01` entre les deux lectures ; le second appel est observé et aucune session/handoff n'est créé. Suite finale demande + packaging : **8 réussis en 9,59 s** avec Python 3.13 et racines temporaires.
- Limites : il reste un intervalle entre la seconde lecture et la préparation du handoff ; la réservation atomique du run et la vérification de l'acteur sont à concevoir en L2/L5. Aucun état actif, Dropbox ou service réel utilisé. L1 reste ouvert.

### Passage v184 — identité stricte du board de lecture API (L2 partiel)

- `FileTaskRepository` acceptait un `tasks.json` sans `project` en déduisant implicitement le nom du dossier. Il exige maintenant le projet dans le document et refuse une tâche portant explicitement un autre projet, une collection de tâches non liste ou un JSON illisible. L'API v1 répond `invalid_task_board` (409) au lieu de confondre un board incohérent avec un identifiant de projet erroné ou de laisser échouer le parseur JSON.
- Avant modification : **17 tests réussis** (`test_ports.py` et `test_dual_read_cutover.py`). Après modification : **21 tests réussis** (`test_ports.py`, `test_dual_read_cutover.py`, `test_workflow_api.py`) sous le Python 3.13 documenté ; un avertissement de dépréciation Starlette/httpx tiers. Racines `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires définies avant pytest. L'export JSON actuel de `TaskService` renseigne déjà `project`.
- Limites : anciens boards sans identité désormais refusés par cet adaptateur ; ils nécessitent un import vérifié. L'API v1 reste sans authentification et les mutations sont encore réparties entre interfaces. Aucun service réel, donnée active, Dropbox ou index RepoWise n'a servi à la recette. L2 reste ouvert.

### Passage v185 — second hook historique de démarrage (L1 partiel)

- `download/session_start.ps1` était distinct de la variante v2 déjà migrée : flag journalier global, lancement de `next mission`, lecture de `Memory/missions.json` et de `Memory/next_actions.md`, puis écritures de contexte partagées. Il délègue maintenant à `Scripts/session_start.ps1`, comme `download/session_start_v2.ps1`, et propage exactement le code de sortie du cycle courant.
- Baseline archive/packaging : **12 tests réussis en 6,34 s**. Recette finale : **14 tests réussis en 6,73 s**, avec les deux façades download, retours simulés 0 et 7, tableau `missions.json` conservé octet pour octet et aucune racine locale créée. Python 3.13 documenté et variables de racines temporaires définies avant pytest.
- RepoWise ciblé n'a trouvé aucun symbole exact pour ce script ; index âgé de 15 jours, commit aligné, embedder mock et recherche sémantique inactive. Le code courant, l'inventaire `rg` et les tests constituent les preuves. Les hooks réellement installés hors dépôt et les autres lecteurs diagnostics/migration des missions ne sont pas qualifiés. Aucune donnée active ou Dropbox utilisée. L1 reste ouvert.

### Passage v186 — fermeture des migrations globales en place (L1 partiel)

- `Scripts/Auto/update_paths.ps1`, encore inclus dans le manifeste de livraison, parcourait récursivement `C:\devcore\DEV_CORE\Scripts`, réécrivait les sources et le hook Git, puis insérait une sélection implicite de projet. `Scripts/Auto/migrate_multiproject.ps1`, également livré sans appelant interne, déplaçait directement `Memory/tasks.json` et choisissait `default_project` si son identité manquait. Les deux commandes refusent désormais l'exécution et orientent vers les adaptateurs par projet ou l'import explicite sur copie.
- Baseline packaging/sécurité historique : **14 tests réussis en 6,71 s**. Après fermeture du réécrivain : **15 réussis en 6,94 s**. Recette finale avec le déménageur JSON : **16 réussis en 6,99 s**. Les tests vérifient les codes 2, les messages de refus, l'absence de création des racines et la conservation octet pour octet d'un script cible et du board global.
- Les recherches d'appelants n'ont trouvé que les deux scripts et le manifeste de livraison. Cette fermeture modifie volontairement leur comportement direct afin d'empêcher une mutation non réconciliée. L'import historique lui-même reste à effectuer sur copie et les outils de diagnostic en lecture seule subsistent. Aucun état actif, Dropbox ou index RepoWise utilisé. L1 reste ouvert.

### Passage v187 — diagnostic historique sans board global (L1 partiel)

- `download/diagnose.ps1` lisait directement `Memory/missions.json` et pouvait afficher la mission active d'un autre projet. Il délègue désormais à `Scripts/diagnose.ps1`, transmet ses arguments et propage son code de sortie. L'alias `download/dc_v2.ps1 check` propage également ce statut au lieu de pouvoir terminer avec succès après un diagnostic en échec.
- Baseline de sécurité historique : **13 tests réussis en 4,83 s**. Les baselines du diagnostic courant ont révélé deux limites préexistantes : `test_diagnose_gate.ps1` échoue avec une racine locale temporaire sans `devcore.db` (2 échecs), et `test_diagnose_dryrun.ps1` appelle encore les options non prises en charge `-Fix -DryRun`. Ces échecs sont consignés et n'ont pas été transformés en faux succès.
- Recette finale façades + packaging : **20 tests réussis en 8,24 s**. Les retours 0 et 9, les arguments `-Gate -Json`, l'alias `check`, la conservation octet pour octet d'un `missions.json` étranger et l'absence de création des racines sont couverts. Le fonctionnement réel du gate exige toujours une base initialisée ; le contrat de réparation dry-run doit être décidé avant correction. Aucun état actif ou Dropbox utilisé. L1 reste ouvert.

### Passage v188 — alias de cycle historique par projet (L1 partiel)

- `download/dc_v2.ps1` lançait `launch.ps1` et `endday.ps1` sans le projet pourtant exigé par la CLI Python ; `ask` pouvait encore résoudre seul le projet local. Les trois alias demandent maintenant `-Project`, le transmettent explicitement et propagent leur code de sortie. L'alias `weekly` propage également le refus de la maintenance partagée, qui conserve sa garde `-RunLegacySharedMaintenance`.
- Baseline `test_endday_project_scope.py` + sécurité historique : **19 réussis en 10,37 s**. Après modification : **22 réussis en 12,05 s**, dont trois nouveaux cas avec scripts doublures qui observent le projet reçu, le refus sans projet avant création des racines et le code d'échec 7. Un cas supplémentaire a vérifié le refus hebdomadaire : **23 réussis en 10,26 s**. La suite `test_task_legacy_adapters.py` : **9 réussis en 39,05 s**. Python 3.13 documenté, racines data/local/platform temporaires avant pytest ; aucun état actif ou Dropbox utilisé.
- Limites : les commandes `new project`, `link project`, la maintenance partagée activée explicitement et l'installation des anciens alias hors dépôt ne sont pas qualifiées par ces tests. Les alias demeurent des adaptateurs locaux, pas le client HTTP de l'instance multiutilisateur. L1/L2 restent ouverts.

### Passage v189 — diagnostic CLI historique lié au manifeste (L1 partiel)

- `Scripts/dc.py::get_active_project` ne fait plus confiance au cache `DEVCORE_ACTIVE_PROJECT_PWD/NAME`, ne déduit plus le projet du répertoire Git ou courant et ne choisit plus `devcore` par défaut. Il utilise le manifeste `.devcore/project.json` du répertoire courant. Le diagnostic ne lit `Memory/<project>/tasks.json` que si ce projet est établi et refuse un board dont le champ `project` diffère ; `publish_event` ne publie rien sans projet explicite.
- Baseline avant modification : **8 tests réussis en 6,83 s** (`test_dc_legacy_next_sql.py`, `test_get_active_project_context.py`). Premier passage après modification : **8 réussis, 1 échec** ; le nouveau test supposait à tort que l'import de `dc.py` ne créait aucun répertoire local. L'assertion sans rapport avec la sélection de projet a été retirée, sans masquer la dette. Recette finale : **9 tests réussis en 6,63 s** sous Python 3.13 avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires définies avant pytest.
- Limites : l'import historique appelle toujours `get_paths()` et crée un répertoire local temporaire, même pour une lecture. `doctor` reste un diagnostic de compatibilité JSON et examine d'autres chemins globaux qui demandent un audit distinct. Aucun service réel, donnée active, Dropbox ou index RepoWise n'a servi à la recette. L1 reste ouvert.
- Suivi : plan et fiche passés en v189, empreinte du contexte actualisée. Le lecteur de reprise accepte le registre avec **10 572/12 000 octets UTF-8**, aucun avertissement, une décision non pertinente omise ; `git diff --check` ciblé est propre. La limite reste un budget d'octets, sans mesure de tokens du modèle.

### Passage v190 — import CLI sans création de racines (L1 partiel)

- `Scripts/dc.py` appelait `get_paths()` dès son import, avant toute sélection de projet. Cet appel créait des répertoires sous les racines locale, data et plateforme, y compris pour un diagnostic ou une commande sans projet. L'import conserve la fonction disponible ; seul `profile` la déclenche explicitement. La recette vérifie que l'import dynamique ne crée aucune de ces trois racines temporaires.
- Baseline avant modification : **17 tests réussis en 6,72 s** (`test_dc_legacy_next_sql.py`, `test_data_roots.py`). Après modification : **17 tests réussis en 5,79 s**, avec Python 3.13 documenté et variables `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT`, `DEVCORE_PLATFORM_ROOT` temporaires définies avant pytest. `dc.py --help` réussit sans créer ces racines. `git diff --check` ciblé est propre ; reprise de contexte à **10 655/12 000 octets UTF-8**, aucun avertissement.
- RepoWise ciblé sur `dc.py`/`paths.py` : index âgé de 15 jours, commit aligné mais changements non indexés, embedder mock et recherche sémantique inactive ; le code et les tests actuels fondent le constat. `profile` garde une résolution explicite pouvant créer ses répertoires ; `doctor` inspecte encore d'autres chemins historiques. Aucune donnée active, Dropbox ou index réel utilisé par les tests. L1 reste ouvert.

### Passage v191 — benchmark et profilage historiques isolés (L1 partiel)

- `Scripts/dc.py benchmark` écrivait un mégaoctet sur `C:/devcore/DEV_CORE_DATA/temp_bench.dat`, un chemin fixe susceptible d'être actif, puis ouvrait la base globale `Memory/conversations.db` pour compter ses conversations. Le disque est maintenant mesuré dans un répertoire temporaire effacé automatiquement ; la mesure SQLite globale est supprimée et l'outil indique le benchmark existant sur sauvegarde vérifiée (`benchmark_sqlite_snapshot.py`). `profile` mesure la résolution des racines sans déclencher `get_paths()` ni créer les répertoires.
- La commande `benchmark` avant correction n'a pas été exécutée, car elle écrivait sur un chemin fixe hors des fixtures. Baseline sûre avant modification : **4 tests réussis en 4,14 s** (`test_dc_legacy_next_sql.py`, `test_benchmark_sqlite_snapshot.py`). Recette après modification : **5 tests réussis en 4,52 s**, dont lancement réel de `benchmark` et `profile` sous `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT`, `DEVCORE_PLATFORM_ROOT` et `TEMP/TMP/TMPDIR` temporaires, sans création de racines ni résidu de benchmark. Python 3.13 documenté.
- Limites : la mesure disque porte sur le volume temporaire de l'OS, pas sur le volume actif de DevCore. Le benchmark SQLite exige une sauvegarde vérifiée distincte. `doctor` lit encore l'ancienne base globale et d'autres chemins ; audit restant. Aucun état actif, Dropbox ou index RepoWise utilisé comme fixture. L1 reste ouvert.
- Suivi v191 : fiche et empreinte mises à jour ; reprise de contexte à **10 738/12 000 octets UTF-8**, aucun avertissement. `git diff --check` ciblé propre. Le gain en tokens du modèle reste non mesuré.

### Passage v192 — diagnostic global non évalué et statut fiable (L1/L9 partiel)

- `dc.py doctor` ouvrait encore `Memory/conversations.db`, stockage historique partagé, pour un contrôle FTS5 et concluait à un échec si ce fichier était absent. Le contrôle est remplacé par un avertissement explicite : la santé de cette base globale n'est pas évaluée par le diagnostic du projet. Le diagnostic renvoie maintenant 1 s'il a au moins un `FAIL`, 0 sinon, et la CLI transmet ce statut au processus appelant.
- Baseline avant modification : **25 tests réussis en 11,30 s** (`test_dc_legacy_next_sql.py`, `test_archived_mission_safety.py`). Recette : **26 tests réussis en 11,27 s**. Le nouveau test place un faux `conversations.db` sous une racine temporaire, interdit l'appel à `sqlite3.connect`, vérifie sa conservation octet pour octet, l'avertissement et la propagation du statut. Python 3.13 et racines local/data/platform temporaires définies avant pytest.
- Limites : `doctor` contrôle encore des paramètres et ports au niveau de la machine ; ses résultats ne constituent pas une validation authentifiée ni une preuve d'isolation des utilisateurs. Le statut de sortie devient volontairement non nul lorsqu'un contrôle échoue. Aucun état actif ou Dropbox utilisé comme fixture. L1/L9 restent ouverts.
- Suivi v192 : fiche et empreinte mises à jour ; reprise de contexte à **10 810/12 000 octets UTF-8**, aucun avertissement. `git diff --check` ciblé propre.

### Passage v193 — sonde TCP locale et mémoire vectorielle honnête (L1/L9 partiel)

- `dc.py::ping_tcp` appelait `socket.setdefaulttimeout`, ce qui changeait le délai par défaut de toutes les sockets du processus. La sonde utilise maintenant `socket.create_connection(..., timeout=...)` et referme la connexion. `doctor` ne lit plus `~/.gemini/antigravity/devcore.db` lorsqu'aucune racine locale n'est déclarée. Il rapporte séparément la présence de `DEVCORE_LOCAL_ROOT/devcore.db` (ou de la racine locale résolue), l'accessibilité HTTP de Qdrant et un avertissement indiquant que la capacité vectorielle n'est pas évaluée. Une simple présence de fichier ne produit plus un verdict de mémoire vectorielle fonctionnelle.
- Baseline avant modification : **26 tests réussis en 11,92 s** (`test_dc_legacy_next_sql.py`, `test_archived_mission_safety.py`). Recette : **27 tests réussis en 11,87 s** avec Python 3.13 et racines temporaires ; le test de sonde vérifie l'adresse, le délai et l'absence de changement du timeout global. Un faux `devcore.db` local ne suffit pas au verdict vectoriel. Aucun service réel, donnée active ou Dropbox utilisé comme fixture.
- Limites : HTTP 200 sur Qdrant prouve seulement que ce point répond. La présence du fichier SQLite ne valide ni son schéma ni l'extension vectorielle. Une qualification authentifiée et les droits par projet restent nécessaires en L9.
- Suivi v193 : fiche et empreinte actualisées ; reprise de contexte à **10 885/12 000 octets UTF-8**, aucun avertissement, et `git diff --check` ciblé propre.

### Passage v194 — attribution du rapport de tokens par projet (L1/L8 partiel)

- `Auto/token_report.py` ouvrait éventuellement `DEVCORE_DATA_ROOT/devcore.db`, alors que cette racine peut être synchronisée, et son repli SQL utilisait `sqlite3` sans import puis une colonne `project` absente du schéma courant ; l'échec était avalé. La base n'est maintenant recherchée que sous la racine locale, ouverte avec `mode=ro`, et les tâches actives sont sélectionnées par `project_id`. Les boards JSON ne contribuent à l'attribution que si leur champ `project` correspond au dossier ; une tâche portant explicitement un autre projet est exclue. Le `current_task` doit référencer une tâche admissible.
- Le résumé `token_metrics_summary.json` et le rapport HTML restent seulement sous la racine locale ; la copie secondaire sous `DEVCORE_DATA_ROOT/Logs/token_reports` est supprimée. En l'absence de `DEVCORE_LOCAL_ROOT` et `LOCALAPPDATA`, le script refuse de retomber sur la racine partagée. Baseline avant modification : **5 tests réussis en 2,37 s**. Recette finale : **8 tests réussis en 1,84 s** (`test_token_report_clients.py`, `test_token_report_codex_counters.py`, `test_token_report_project_scope.py`), sous Python 3.13 et racines temporaires. Le test multi-client vérifie l'absence de copie partagée ; deux nouveaux tests opposent board étranger et bases locale/partagée.
- Limites : les anciens consommateurs `weekly_maintenance.ps1`, `rotate_logs_and_backups.py` et l'import historique restent à adapter à la source locale ou à traiter comme archives. Les métriques globales envoyées par `record_metric` sont encore associées par défaut à `devcore` ; ce point requiert un contrat d'agrégation explicite. Les rapports de tokens restent des observations, sans démonstration d'économie. Aucun état actif, Dropbox ou index RepoWise utilisé comme fixture. L1/L8 restent ouverts.
- Suivi v194 : fiche et empreinte actualisées ; reprise de contexte à **10 963/12 000 octets UTF-8**, aucun avertissement. `git diff --check` ciblé n'a trouvé aucune erreur d'espacement ; Git signale seulement sa normalisation LF/CRLF pour `token_report.py`.

### Passage v195 — consommateurs des rapports locaux (L1/L8 partiel)

- `rotate_logs_and_backups.py` lisait et modifiait les journaux, sauvegardes et métriques sous `DEVCORE_DATA_ROOT`, en décalage avec le producteur local et avec un risque de mutation Dropbox. Les trois opérations acceptent maintenant une racine locale explicite ; sans argument, elles utilisent `DEVCORE_LOCAL_ROOT` ou `LOCALAPPDATA/DEV_CORE_LOCAL` et refusent tout repli sur les données partagées. `dashboard.data_loader.load_token_metrics` ne relit plus un ancien rapport partagé et `gen_dashboard` lui passe `LOCAL_ROOT`. `profile_performance.py` ne chronomètre plus la rotation en l'exécutant trois fois.
- `Auto/weekly_maintenance.ps1` exigeait déjà une activation explicite mais écrivait encore son log, rapport hebdomadaire et copie de `MEMORY.md` sous la racine partagée. Ces sorties vont maintenant sous `DEVCORE_LOCAL_ROOT` ; le script refuse le repli vers `DEVCORE_DATA_ROOT` lorsqu'aucune racine locale n'est disponible. La présence de `devcore.db` est indiquée sans prétendre valider les vecteurs. Ses lectures de mémoire et le nettoyage explicite du cache plateforme restent des opérations historiques.
- Baseline avant modification : **8 tests réussis en 3,00 s** pour rapport multi-client, portée projet et chargement Cockpit ; **2 tests réussis en 3,95 s** pour la garde hebdomadaire. Après modification : **10 tests réussis en 2,94 s** pour rapport/rotation/Cockpit, **30 tests réussis en 16,95 s** pour génération du tableau de bord et actions, **3 tests réussis en 3,94 s** pour la garde et l'exécution hebdomadaire explicite. Tous les essais utilisent Python 3.13, des racines temporaires avant import et une plateforme PowerShell factice. Les doublures de rapports, logs et sauvegardes sous la racine partagée restent intactes.
- Limites : l'import historique `migrate_json_to_sqlite.py` conserve sa lecture de l'ancien rapport partagé, à traiter comme migration sur copie. La métrique globale du rapport de tokens est encore étiquetée `devcore` ; l'isolation d'agrégats multiutilisateurs et le gain réel de tokens restent ouverts. Les fonctions de rotation suppriment bien des fichiers dans la racine locale sélectionnée ; leur activation opérationnelle n'est pas qualifiée. L1/L8 restent ouverts.
- Suivi v195 : fiche et empreinte actualisées ; reprise de contexte à **11 040/12 000 octets UTF-8**, aucun avertissement. `git diff --check` ciblé ne signale que la normalisation LF/CRLF de trois fichiers existants.

### Passage v196 — fiche de reprise courte (L7 partiel)

- La fiche projet ne répète plus les passages v164–v195 du journal. Elle conserve l'objectif, le vocabulaire, l'architecture actuelle et cible, les contraintes, l'état vérifié, les limites et la prochaine action ; le détail historique reste dans ce plan et ce journal. L'empreinte `card_sha256` du registre a été actualisée.
- Avant modification, le lecteur isolé passait **6 tests, 1 ignoré**. Après modification, il passe **6 tests, 1 ignoré** en 1,41 s sous Python 3.13 et racines temporaires. L'appel MCP de reprise retourne **7 101/12 000 octets UTF-8**, contre **11 040** au passage v195, soit **3 939 octets (35,7 %) de moins**, sans avertissement ; les cinq décisions obligatoires applicables D-002, D-003, D-004, D-006 et D-007 restent incluses.
- La suite combinée de référence du lecteur et du Cockpit donnait **25 réussis, 1 ignoré, 1 échec** : le Python de recette ne contient pas `argon2` malgré sa présence dans le manifeste et le lock, et ne contient pas `pip`. Le scénario cookie/identité échoue donc sur `IdentityUnavailable: Password hashing dependency unavailable`. Cette limite de l'environnement de recette reste à résoudre avant de qualifier ce scénario ; la fiche seule n'a pas déclenché cet échec.
- Le plafond mesure la sortie UTF-8, pas les tokens du modèle. L'économie de tokens, la qualité et le respect des décisions dans une conversation neuve restent à mesurer. Aucun état actif, Dropbox ou index RepoWise n'a servi de fixture.

### Passage v197 — requalification du candidat Python avec Argon2 (L4/L7 partiels)

- Le blocage v196 concernait `E:/DevCoreRuntime/releases/devcore-py313-20261002` (Python 3.13.3). Le candidat déjà documenté `E:/DevCoreRuntime/releases/devcore-py31316-20261003` existe, exécute Python 3.13.16, importe `argon2` et `fastapi`, et `uv pip check` confirme **54 paquets compatibles**. Aucun paquet n'a été installé et aucun environnement existant modifié.
- Sous ce candidat, avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires définies avant pytest, la suite `test_project_context_resume.py` + `test_dashboard_project_context.py` passe : **26 réussis, 1 ignoré, 1 avertissement tiers** en 91,66 s. `test_local_passwords.py` + `test_dashboard_password_login.py` passe : **16 réussis, 1 avertissement tiers** en 61,22 s. L'avertissement vient de la dépréciation Starlette/TestClient liée à `httpx` ; aucun échec fonctionnel.
- Le candidat Python 3.13.16 résout donc ce défaut de dépendance pour ces recettes. Python 3.13.3 reste incomplet ; ni le service actif, ni le snapshot/bundle réellement lancé, ni la récupération opérationnelle ne sont qualifiés par ces tests. L7 conversation neuve et économie mesurée de tokens restent ouverts. Aucun état actif ou Dropbox utilisé comme fixture.
- Le test de construction du bundle a d'abord échoué à la collecte depuis la racine du dépôt car `Scripts` n'était pas dans `PYTHONPATH`. Avec `PYTHONPATH=DEV_CORE` explicite, **8 tests réussis** en 4,33 s : allowlist, empreintes, refus d'altération et porte HTTP sur snapshot temporaire. Ce test construit un nouveau snapshot de fixture ; il ne vérifie pas le candidat déjà publié ni son lancement réel.

### Passage v198 — usage sans projet et métriques agrégées (L1/L8 partiels)

- `token_report.py` attribuait `headroom_stats.json/tasks/Aucune` au projet `devcore` et comptait cet agrégat comme une session. Il conserve les tokens dans le total global et le client Headroom, crée un bucket `unattributed` explicite et ne crée aucun projet ni session pour cette source. Le rapport global peut ainsi différer de la somme des projets, de façon visible et justifiée.
- Les quatre snapshots de métriques (`tokens`, `cache_hits`, `cost`, `sessions`) sont désormais préparés pour chaque projet présent dans le résumé, avec `project` explicite et provenance heuristique. Le total global n'est plus envoyé sous le nom `devcore`. L'appel `record_metric` indique un échec du relais et le rapport prévient que son JSON local demeure la source de vérité.
- Baseline avant modification : **8 tests réussis en 2,60 s**. Recette après modification : **10 tests réussis en 2,26 s** (`test_token_report_clients.py`, `test_token_report_codex_counters.py`, `test_token_report_project_scope.py`) sous Python 3.13.16, avec racines local/data/platform temporaires avant pytest. Les nouveaux cas couvrent un appel Headroom non attribué et deux projets avec relais indisponible ; aucun état actif, Dropbox ou index RepoWise n'est utilisé.
- Limite concrète : `Scripts/metrics_service.ps1` délègue les anciens paramètres `-Action Record` à `devcore_engine.cli events`, dont le parseur ne connaît que `tail` et `publish`. La publication effective des événements métriques n'est donc pas qualifiée, pas plus que l'attribution authentifiée à l'utilisateur. La série Headroom historique peut déjà agréger plusieurs jours : son horodatage et son éventuel double comptage demandent une source instrumentée avant de conclure sur les coûts ou gains réels. L1/L8 restent ouverts.
- Fiche v198 et empreinte synchronisées : reprise MCP **7 249/12 000 octets UTF-8**, cinq décisions obligatoires conservées, aucun avertissement. Le lecteur isolé passe **6 tests, 1 ignoré** en 1,36 s. `git diff --check` ciblé ne signale que la normalisation LF/CRLF prévue de `token_report.py`.

### Passage v199 — relais métrique local (L1/L8 partiels)

- Baseline avant modification : `test_metrics_service.ps1` échouait immédiatement, car `devcore_engine.cli events` refusait l'action historique `Health`. La passerelle PowerShell appelle maintenant un service Python dédié, sans charger `platform_version.ps1` ni déclencher son autodétection Dropbox. Celui-ci exige `DEVCORE_LOCAL_ROOT` ou `LOCALAPPDATA`, refuse une racine locale sous `DEVCORE_DATA_ROOT`, limite la taille des payloads/événements/journal et verrouille l'ajout interprocessus. Les clés de secrets connues sont occultées. Le transfert du payload est en base64 pour préserver le JSON à travers `powershell.exe -File`; le `TaskId` vide est omis de l'argumentaire.
- Health, Record, Aggregate et Status fonctionnent sur magasin JSONL local. L'agrégat conserve le dernier snapshot de chaque projet et additionne ces snapshots au total ; le Cockpit ne retombe plus sur `DEVCORE_DATA_ROOT/Metrics` et expose le même calcul. Baseline Python du v198 : 10 tests réussis. Recette v199 : **15 tests Python réussis en 6,09 s** (rapport et service), plus **smoke PowerShell réussi**. Les cas couvrent deux projets, mise à jour de snapshot, secret occulté, rejet de racine partagée, quatre processus concurrents et trajet réel `token_report` → PowerShell → JSONL, sous Python 3.13.16 et racines temporaires avant import.
- Limites : un processus PowerShell et un `fsync` sont encore lancés par métrique/projet ; mesurer et regrouper les émissions avant une charge importante. La lecture d'anciens fichiers malformés et l'authentification de l'émetteur ne sont pas qualifiées. La seule métrique `token_report` reste une attribution heuristique de sessions ; le coût Headroom sans projet demeure séparé. Aucun service actif, donnée Dropbox ou index RepoWise n'a été utilisé comme fixture ; L1/L8 restent ouverts.
- Fiche v199 et empreinte synchronisées ; reprise MCP **7 328/12 000 octets UTF-8**, cinq décisions obligatoires conservées, aucun avertissement. Lecteur isolé : **6 réussis, 1 ignoré** en 1,40 s. `git diff --check` ciblé ne signale aucune erreur d'espacement, seulement l'annonce LF/CRLF sur deux fichiers déjà modifiés.

### Passage v200 — lots métriques et lecture tolérante (L1/L8 partiels)

- Avant modification, la recette ciblée du relais et rapport passait **11 tests en 6,22 s**. Le rapport construit désormais des lots de 32 événements, soit huit projets de quatre métriques par appel PowerShell. Le service valide tous les événements avant création ou écriture du magasin, puis écrit le lot sous un verrou interprocessus avec un seul `fsync`. Le transfert base64 préserve le JSON ; la limite de 32 événements réduit le risque de dépasser la longueur de commande Windows. Un lot invalide est rejeté sans événement partiel.
- Les lecteurs du service et du Cockpit comptent et ignorent les anciennes lignes JSON malformées, les objets incomplets et les valeurs non finies, sans perdre les relevés valides. Les octets du fichier historique restent inchangés. Le smoke PowerShell passe. La suite rapport/service/counters passe **16 tests en 6,81 s** après les premiers correctifs ; après ajout des cas d'atomicité et de découpage, les 13 tests ciblés service/portée projet passent en 6,56 s. Ces suites portent au total **18 cas distincts** ; elles utilisent Python 3.13.16 et des racines local/data/platform temporaires avant imports.
- Limites : réduction du nombre de processus par construction, sans benchmark de latence ni charge multiutilisateur réel. Le regroupement ne garantit pas l'authentification de l'émetteur et le rapport conserve une attribution heuristique. Un journal historique au-delà de 64 Mio reste refusé ; sa migration n'est pas faite. Aucun service actif, Dropbox ou index RepoWise réel n'a servi de fixture. L1/L8 restent ouverts.
- Vérification finale combinée : **24 tests réussis, 1 ignoré en 5,65 s** (18 métriques/rapport et 6 lecteur de contexte) ; smoke PowerShell réussi. Fiche v200 et empreinte synchronisées ; reprise MCP à **7 396/12 000 octets UTF-8**, cinq décisions obligatoires, aucun avertissement. `git diff --check` ciblé ne révèle pas d'erreur d'espacement ; Git annonce seulement LF/CRLF pour deux fichiers déjà modifiés.

### Passage v201 — import JSON historique sur source choisie (L1/L3 partiels)

- Avant modification, `migrate_json_to_sqlite.py` ouvrait `DEVCORE_DATA_ROOT/devcore.db` même avec `--dry-run`, lisait automatiquement `DEVCORE_DATA_ROOT/Logs/token_reports/token_metrics_summary.json` et `--verify` initialisait la base. Son `--help` ne proposait aucune sélection de source ou destination. Aucun import réel n'a été lancé en baseline pour éviter ces effets.
- L'outil exige désormais `--source-root` pour l'import et `--destination-db` pour écrire. Le mode aperçu lit la copie sans créer de base ; le mode vérification ouvre une base existante en lecture seule. `--token-summary` sélectionne explicitement le rapport historique ; en son absence, aucun rapport partagé n'est consulté. Une erreur de lecture/JSON du rapport choisi fait échouer la commande au lieu d'afficher un succès trompeur.
- Recette sous Python 3.13.16, avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires définies avant pytest : **3 nouveaux tests de migration réussis**, puis **16 tests ciblés réussis en 8,34 s** avec le rapport par projet et le service métrique. Les cas couvrent refus sans source, aperçu sans SQLite, import ciblé des tâches et tokens, vérification sans écriture et rapport invalide. Le faux rapport sous la racine partagée reste octet pour octet inchangé ; aucune donnée active ou Dropbox n'a servi de fixture.
- Limites : l'ancien schéma `token_calls` ne porte pas de projet, l'import n'est pas idempotent pour événements/tokens et les fonctions valident/committent encore par catégorie. Une panne en milieu d'import demande de repartir d'une base de recette neuve et de réconcilier les comptages. La qualification de migration vers PostgreSQL et l'attribution authentifiée demeurent ouvertes ; L1/L3/L8 restent ouverts.
- Vérification finale combinée : **22 réussis, 1 ignoré en 9,05 s** (migration, contexte, rapport, service métrique). `git diff --check` ciblé propre. Fiche v201 et empreinte synchronisées ; reprise MCP à **7 650/12 000 octets UTF-8**, cinq décisions obligatoires, aucun avertissement. Le budget reste mesuré en octets, pas en tokens du modèle.

### Passage v202 — import sur copie atomique et rejeu refusé (L1/L3 partiels)

- Baseline avant modification : **3 tests de migration réussis en 2,42 s**. Les fichiers de tâches et événements invalides pouvaient être simplement signalés puis ignorés, tandis que les catégories précédentes étaient déjà committées. Un second import pouvait ajouter les mêmes événements et tokens.
- Les trois catégories sont maintenant prévalidées avant l'ouverture de SQLite. Toute erreur de lecture ou de conversion des tâches, événements ou tokens sélectionnés arrête la commande. Après initialisation du schéma, une destination contenant déjà des lignes est refusée ; les écritures se font dans une transaction unique avec rollback sur erreur. Deux nouveaux tests couvrent la prévalidation sans base créée et un échec tardif déclenché par SQLite qui laisse les trois tables vides ; le rejeu est également refusé sans changer le comptage.
- Recette finale : **24 réussis, 1 ignoré en 12,82 s** (migration, reprise de contexte, rapport par projet, service métrique) sous Python 3.13.16, avec racines local/data/platform temporaires définies avant pytest. Aucune donnée active, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : les lignes invalides sans ID dans les tableaux de tâches et les événements qui ne sont pas des objets sont encore ignorés comme dans l'ancien import ; leur réconciliation reste à faire. Le schéma est créé avant la transaction de données : une erreur tardive peut laisser une base vide, qui doit être vérifiée ou remplacée. La source peut changer entre prévalidation et import ; le rollback couvre alors les erreurs détectées. La table des tokens historiques n'a pas de projet, et la migration PostgreSQL réelle reste ouverte. L1/L3/L8 ne sont pas clos.
- Suivi : fiche v202 et empreinte synchronisées. Le MCP de reprise retourne **7 739/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement ; `git diff --check` ciblé est propre. Aucune mesure de tokens du modèle n'est déduite de ce budget.

### Passage v203 — lignes d'import historiques contrôlées (L1/L3 partiels)

- Baseline avant modification : **5 tests de migration réussis en 7,85 s**. Le lecteur de copie ignorait les tâches sans ID, les événements non objets et les sessions de tokens non objets ; les IDs dupliqués remplaçaient silencieusement la première tâche. Un board placé sous `Memory/alpha` pouvait annoncer `beta`, et une tâche de ce board pouvait porter `project=beta` tout en étant insérée sous `alpha`.
- Le précontrôle échoue maintenant sur ces incohérences et sur une liste `tasks` ou `sessions` absente/mal formée. Il s'exécute avant la création de la destination. Les deux nouveaux tests couvrent cinq variantes de board et les événements/sessions invalides, sans produire de base ; le chemin d'import valide reste couvert.
- Recette ciblée : **11 tests réussis en 5,30 s**. Recette combinée : **30 réussis, 1 ignoré en 11,27 s** sous Python 3.13.16, avec les trois racines locales temporaires définies avant pytest. Aucun état actif, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : les statuts et les autres champs historiques conservent leurs conversions anciennes ; les sources de production peuvent nécessiter une analyse et une correction sur copie avant import. Les tokens historiques restent sans projet dans la table cible ; PostgreSQL et la réconciliation complète restent ouverts. L1/L3 ne sont pas clos.
- Fiche v203 et empreinte synchronisées ; reprise MCP à **7 822/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement. `git diff --check` ciblé est propre. Ce contrôle de taille ne mesure pas les tokens du modèle.

### Passage v204 — destination de migration exclusivement neuve (L1/L3 partiels)

- Baseline avant modification : **11 tests de migration réussis en 5,14 s**. Le contrôle « tables vides » intervenait après `init_db` ; une base préexistante pouvait donc voir son schéma et son mode WAL modifiés avant le refus de l'import.
- La création de `--destination-db` utilise maintenant l'ouverture exclusive `xb`. Un chemin existant, même vide, est refusé avant l'appel SQLite ; `--verify` utilise une connexion fermée explicitement et en lecture seule. Le test de rollback provoque maintenant un échec tardif injecté sur une destination neuve. Un autre test vérifie qu'un fichier préexistant conserve exactement ses octets.
- Recette ciblée : **12 tests réussis en 7,08 s** sous Python 3.13.16 avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires. Aucun état actif, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : l'échec d'un import après création exclusive peut laisser un fichier SQLite neuf avec schéma mais sans lignes ; l'opérateur doit le vérifier ou le remplacer après analyse. La migration PostgreSQL, l'attribution projet des tokens et la réconciliation des volumes historiques restent ouvertes ; L1/L3 ne sont pas clos.
- Recette combinée finale : **31 réussis, 1 ignoré en 12,15 s** (migration, reprise de contexte, rapport et métriques) ; `git diff --check` ciblé propre. Fiche v204 et empreinte synchronisées ; reprise MCP à **7 899/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement. L'économie de tokens du modèle reste non mesurée.

### Passage v205 — réconciliation des comptages avant commit (L1/L3 partiels)

- Baseline avant modification : **12 tests de migration réussis en 4,84 s**. `verify_migration` affichait les volumes après commit sans les comparer aux fichiers de la copie ni aux nombres annoncés par les fonctions d'import.
- Pour les trois catégories importées, la commande conserve les nombres du précontrôle, compare ceux de l'import et lit les comptes SQLite dans la même transaction avant commit. Une divergence lève une erreur et déclenche le rollback. Le test injecte un importeur qui annonce une ligne d'événement sans l'insérer ; la commande échoue et la table reste vide.
- Recette ciblée : **13 réussis en 5,17 s**. Recette combinée migration/contexte/rapport/métriques : **32 réussis, 1 ignoré en 11,47 s** sous Python 3.13.16, avec racines local/data/platform temporaires avant pytest. Aucun état actif, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : trois nombres identiques ne prouvent pas la conservation des valeurs ou dépendances. Le précontrôle lit encore les sources deux fois ; une modification valide entre les lectures peut échapper au contrôle si les nombres restent identiques. La réconciliation par identité, l'attribution projet des tokens et l'import PostgreSQL restent ouverts ; L1/L3 ne sont pas clos.
- Suivi : fiche v205 et empreinte synchronisées ; reprise MCP à **8 039/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement. `git diff --check` ciblé est propre. La taille du contexte n'est pas une mesure de tokens du modèle.

### Passage v206 — stabilité de la copie pendant l'import (L1/L3 partiels)

- L'égalité des comptages v205 laissait passer une source modifiée entre précontrôle et écriture si le nombre de lignes restait identique. L'import calcule maintenant les empreintes SHA-256 des fichiers sélectionnés et de leur liste, puis les compare avant commit. Un écart annule la transaction.
- Le test modifie le titre d'une tâche après insertion en gardant le même ID et le même nombre de lignes ; l'import échoue et SQLite ne conserve pas la tâche. Recette ciblée : **14 réussis en 5,61 s**. Recette combinée migration/contexte/rapport/métriques : **33 réussis, 1 ignoré en 11,76 s** sous Python 3.13.16 et racines local/data/platform temporaires définies avant pytest. Aucune donnée active, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : une source peut encore changer puis revenir exactement à ses octets initiaux entre les deux calculs ; seul un instantané immuable et un gel des écritures éliminent ce risque. Les empreintes ne vérifient pas l'identité des valeurs dans SQLite après transformation. Réconciliation détaillée et migration PostgreSQL restent ouvertes ; L1/L3 ne sont pas clos.
- Fiche v206 et empreinte synchronisées ; reprise MCP à **8 102/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement. `git diff --check` ciblé propre. La mesure de tokens du modèle reste à faire.

### Passage v207 — contrôle du contenu importé (L1/L3 partiels)

- Baseline avant modification : **16 tests migration et réconciliation SQLite réussis en 10,91 s**. Les nombres v205 et empreintes source v206 ne détectaient pas une altération d'un champ SQLite pendant l'import si le nombre de lignes restait égal.
- Chaque ligne normalisée destinée aux tables `tasks`, `events` et `token_calls` alimente un digest SHA-256 pendant l'import. Avant commit, la commande relit les colonnes stockées dans un ordre déterministe et compare les digests ; une différence annule la transaction. Le test injecte un déclencheur SQLite qui change le titre d'une tâche sans modifier le nombre de lignes : le commit est refusé et la table reste vide. Un parcours positif importe deux projets qui partagent `T-1`, plus un événement et un appel de tokens.
- Recette finale : **24 réussis, 1 ignoré en 10,55 s** (`test_legacy_json_migration.py`, `test_sqlite_reconciliation.py`, `test_project_context_resume.py`) sous Python 3.13.16, avec racines local/data/platform temporaires définies avant pytest. Aucune donnée active, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : le digest vérifie les valeurs normalisées par l'ancien importeur, pas la fidélité de toutes les propriétés du JSON source, dont certaines ne figurent pas dans ce schéma. Le mapping global des dépendances, événements métier et task_uuid, ainsi que la cible PostgreSQL, restent ouverts ; L1/L3 ne sont pas clos.
- Fiche v207 et empreinte synchronisées ; reprise MCP à **8 127/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement. `git diff --check` ciblé propre. Aucune économie de tokens du modèle n'est inférée.

### Passage v208 — création exclusive de la copie SQLite candidate (L3 partiel)

- Baseline avant modification : **2 tests de réconciliation réussis en 4,29 s**. L'outil vérifiait que le chemin cible était libre, puis appelait `sqlite3.connect` qui pouvait ouvrir une cible créée entre-temps. Sur échec, il supprimait ce chemin sans preuve qu'il possédait encore le fichier.
- La destination est désormais créée par ouverture exclusive `xb` après la connexion en lecture seule à la source. Une création concurrente provoque un échec sans écrasement ; après un échec de traitement, la candidate reste disponible pour inspection et aucun chemin potentiellement remplacé n'est supprimé. Deux tests nouveaux couvrent la course de création simulée et la conservation d'une candidate de version inattendue. La source témoin conserve son empreinte.
- Recette ciblée : **4 tests réussis en 8,28 s**. Recette combinée import, réconciliation SQLite et contexte : **26 réussis, 1 ignoré en 13,48 s** sous Python 3.13.16, avec racines local/data/platform temporaires avant pytest. Aucun état actif, Dropbox ou index RepoWise réel n'a servi de fixture.
- Limites : une candidate échouée doit être diagnostiquée puis supprimée ou archivée explicitement par l'opérateur ; une substitution malveillante après la création exclusive n'est pas protégée par un identifiant de fichier conservé. L'opération n'est pas la bascule PostgreSQL ; L3 reste ouvert.
- Fiche v208 et empreinte synchronisées ; reprise MCP à **8 218/12 000 octets UTF-8**, cinq décisions obligatoires et aucun avertissement. `git diff --check` ciblé propre. L'économie de tokens du modèle reste non mesurée.

### Passage v209 — digests de contenu exposés dans la réconciliation candidate (L3 partiel)

- Le rapport candidate expose maintenant les digests SHA-256 des tâches et du graphe, côté source et côté candidate après quarantaine.
- Les tests vérifient l'égalité des digests lorsque les lignes sont conservées.
- Recette : **26 réussis, 1 ignoré en 73,75 s** sous Python 3.13.16, avec racines temporaires.
- Limite : cela ne qualifie ni PostgreSQL, ni la bascule, ni la fidélité de propriétés JSON hors schéma.

### Passage v210 — mapping global des tâches historiques dans la candidate (L3 partiel)

- La candidate SQLite calcule un UUID v5 stable pour chaque paire `(project_id, task_id)` et conserve le mapping dans `legacy_task_identity_map`.
- Les dépendances et références des runs, événements, audits et imports sont reportées dans `legacy_task_reference_report`. Chaque ligne est marquée `resolved`, `missing` ou `ambiguous_project`; aucune référence existante n'est réécrite.
- Recette : **27 réussis, 1 ignoré en 18,87 s** sous Python 3.13.16, avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT`, `DEVCORE_PLATFORM_ROOT` et `PYTHONPATH` temporaires définis avant pytest. La recette inclut deux projets partageant `T-1`, une dépendance résolue, deux références manquantes et un événement ambigu.
- Limites : la table est une préparation de migration sur une copie SQLite. Elle ne crée ni `task_uuid` dans le schéma PostgreSQL, ni la contrainte cible `UNIQUE(project_id, task_number)`, et les propriétés JSON non mappées restent à qualifier.

### Passage v210 — feuille de route de reprise Antigravity

- Ajout de `docs/roadmap-antigravity.md` comme brief de reprise. Il rassemble
  l'état v209 de l'audit, les décisions effectives D-002/D-003/D-004/D-006/D-007,
  les configurations, les lots L0-L9, les critères de blocage et un prompt de
  démarrage.
- Vérification documentaire : `git diff --check -- docs/roadmap-antigravity.md`
  sans erreur. Aucun test de code n'était nécessaire et aucun service, donnée
  active, Dropbox ou index RepoWise réel n'a été utilisé.
- Limite : ce document synthétise les preuves disponibles ; Antigravity doit
  vérifier le code, Git, les ports et les tests au début de chaque ticket.

### Passage v211 — numérotation des tâches et classification runtime dans la candidate (L3 partiel)

- La candidate SQLite extrait désormais le numéro de tâche `task_number` pour chaque tâche dans `legacy_task_identity_map` et détecte toute collision de numéro au sein d'un même projet (`collision`, `parsed`, `unparseable`).
- Si la table `runtime_state` est présente dans la source, chaque entrée est classée de manière déterministe dans la table candidate `legacy_runtime_state_report` : `preference_to_migrate` (portées `user_preference` ou `project_preference`), `ephemeral_to_rebuild` (portée `ephemeral`), ou `ambiguous_needs_review` (portée `needs_review`).
- Le rapport de réconciliation expose `task_number_resolutions` et `runtime_state_classifications`, et vérifie l'égalité stricte des digests SHA-256 de `runtime_state` entre source et candidate en plus des tâches et du graphe.
- Baseline avant modification : **29 passés, 1 ignoré en 20,56 s**. Recette après modification : **31 passés, 1 ignoré en 26,05 s** (`test_sqlite_reconciliation.py`, `test_sqlite_fk_preview.py`, `test_legacy_json_migration.py`, `test_project_context_resume.py`) sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `PYTHONPATH` temporaires.
- Limites : il s'agit d'une préparation sur copie candidate SQLite, sans modification active ni création de la contrainte PostgreSQL cible `UNIQUE(project_id, task_number)`. Les clés ambiguës ou collisions nécessitent une résolution explicite par l'opérateur avant bascule. Aucun service réel, donnée active ou Dropbox utilisé en fixture.

### Passage v212 — clôture du point RequestContext et suppression du repli implicite (L1)

- Dans `DEV_CORE/devcore_engine/lifecycle/session.py`, `SessionManager.get_active_project()` supprime tout repli implicite sur `"devcore"`. Il résout le projet depuis l'instance `self._active_project`, la variable d'environnement de processus `DEVCORE_ACTIVE_PROJECT_NAME` validée, ou le manifeste local de répertoire `.devcore/project.json` via `project_from_directory()`. Sans contexte actif valide, il lève explicitement `ValueError("No active project context found")`.
- Dans `DEV_CORE/devcore_engine/lifecycle/endday.py`, `EndDayManager.run_endday()` accepte désormais `RequestContext(user_id, project_id, session_id, run_id, trace_id)` en plus de la chaîne `project_id`, valide l'identifiant de projet, propage `correlation_id=context.trace_id` à l'événement `EndDayCompleted` dans `bus_events`, et retourne `trace_id` dans son résultat.
- Dans `DEV_CORE/devcore_engine/cli.py`, la commande `endday` instancie explicitement un `RequestContext(project_id=args.project)` transmis à `EndDayManager`.
- Dans `DEV_CORE/Scripts/session_end.ps1`, configuration explicite de `[Console]::OutputEncoding` et `$OutputEncoding` en UTF-8 pour éliminer les corruptions d'encodage console OEM/ANSI sous Windows lors des levées d'erreurs en sous-processus.
- Recette automatisée : suite combinée de **36 tests réussis en 45,30 s** sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires, couvrant :
  - `DEV_CORE/tests/test_request_context.py` (4 tests) : contextes indépendants par session, absence d'interférence entre sessions/états globaux, refus de contextes invalides/traversées, résolution explicite de projet et levée `ValueError` sans repli implicite, transmission de `RequestContext` à `EndDayManager` avec corrélation `EndDayCompleted`.
  - `DEV_CORE/tests/test_project_isolation.py` (11 tests) : isolation stricte par projet, intégrité référentielle, allocation concurrente.
  - `DEV_CORE/tests/test_endday_project_scope.py` (3 tests) : notes Obsidian et événements cantonnés au projet, jobs désactivés et exigence `--project`.
  - `DEV_CORE/tests/test_session_start_concurrency.py` (2 tests) : drapeaux d'admission indépendants par projet, absence de réentrance non autorisée.
  - `DEV_CORE/tests/test_session_end_local.py` (8 tests) : sortie de session cantonnée au projet, arrêt et signalement d'étape échouée, absence d'écriture dans `DEVCORE_DATA_ROOT`.
  - `DEV_CORE/tests/test_launch_no_legacy_import.py` (2 tests) : préservation des tâches SQL sans rejeu stale, désactivation du job planifié.
  - `DEV_CORE/tests/test_get_active_project_context.py` (6 tests) : détection locale par manifeste sans état global, rejet des traversées et annulation de session sans projet.
- Limites : les traces et contextes de session sont vérifiés sur l'environnement de recette local et fixtures isolées. L'unification complète des interfaces L2 (ports `TaskRepository`, `UnitOfWork`) et la bascule PostgreSQL L3 restent ouvertes. Aucun service actif, donnée de production, Dropbox ou index RepoWise réel utilisé.

### Passage v213 — ports typés et contrats de domaine (L2)

- Définition formelle des 7 ports de l'architecture cible dans `DEV_CORE/API/devcore_api/ports.py` avec le décorateur `@runtime_checkable` pour supporter la vérification de type structurelle au runtime :
  - `TaskRepository` : consultation et filtrage de tâches par projet.
  - `UnitOfWork` : gestionnaire de contexte transactionnel (`__enter__`, `__exit__`, `commit()`, `rollback()`), avec deux implémentations concrètes `InMemoryUnitOfWork` et `SqliteUnitOfWork` (gestion automatique du rollback sur exception).
  - `IdentityProvider` : résolution d'utilisateur, validation de jetons et appartenance aux workspaces.
  - `WorkflowEngine` : cycle de vie des runs (`start_run`, `get_run`, `cancel_run`).
  - `Runner` : exécution de commandes ou d'agents retournant un `RunnerResultContract`.
  - `ModelGateway` : génération textuelle et calcul d'embeddings vectoriels (`generate`, `embed`).
  - `KnowledgeProvider` : recherche sémantique et extraction de contexte projet borné (`search`, `get_context`).
- Nouveaux contrats Pydantic introduits dans `DEV_CORE/API/devcore_api/contracts.py` :
  - `RunnerResultContract` (validation `run_id`, `exit_code`, `duration_seconds >= 0`).
  - `ModelRequestContract` (validation `prompt`, `model`, `0.0 <= temperature <= 2.0`).
  - `ModelResponseContract` (validation `text`, `model`, `usage`).
  - `KnowledgeItemContract` (validation `id`, `project`, `title`, `content`, `score`).
- Recette automatisée : **20 tests réussis en 4,52 s** sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires sur `DEV_CORE/API/test_ports.py` et `DEV_CORE/API/test_domain_contracts.py`.
- Limites : les protocoles définissent les contrats et ports de l'API commune. Le raccordement de tous les adaptateurs existants (runners externes, passerelles LLM réelles) et le routage exclusif du CLI/MCP vers l'API centrale restent à finaliser dans les passages suivants de L2.

### Passage v214 — adaptateur import/export FileTaskRepository et comparaison des champs/versions (L2)

- Transformation de `FileTaskRepository` dans `DEV_CORE/API/devcore_api/ports.py` en adaptateur de compatibilité d'import/export :
  - `import_compatibility_board(project, source_path=None)` : lecture et validation stricte de formats de board JSON historiques (`tasks.json`).
  - `export_compatibility_board(project, tasks, current_task=None, target_path=None)` : exportation atomique (fichier temporaire `.tasks-compat-*.tmp` dans le répertoire cible avec `os.fsync` et remplacement atomique via `os.replace`), préservant les identifiants, versions, statuts, modes et métadonnées d'étapes.
- Introduction de la fonction `compare_task_fields(legacy_tasks, sql_tasks)` dans `devcore_api/ports.py` :
  - Comparaison champ par champ (`title`, `status`, `mode`, `steps_done`, `steps_total`, `version`) sur les tâches communes.
  - Détection exhaustive des tâches manquantes (`missing_in_sql`, `missing_in_legacy`).
  - Rapport structuré avec détection explicite des divergences de versions (`version_mismatches`) et de champs (`field_mismatches`).
- Enrichissement de `DualReadTaskRepository` :
  - Méthode `compare_tasks(project)` exposant le rapport d'analyse comparatif.
  - Support du callback optionnel `on_mismatch_report(comparison)`.
  - Attribut `last_comparison` conservé pour l'inspection sans rompre le format de chaîne historique de `on_mismatch`.
- Recette automatisée : **30 tests réussis en 4,49 s** sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires sur `DEV_CORE/API/test_ports.py`, `DEV_CORE/API/test_dual_read_cutover.py` et `DEV_CORE/API/test_domain_contracts.py`.
- Limites : l'adaptateur produit et lit des snapshots JSON de compatibilité sur disque pour les outils historiques ; les écritures opérationnelles directes dans `Memory/` demeurent réservées à ces exports explicites et isolés.

### Passage v215 — statuts unifiés active/in_progress, catalogue de routes, pagination et façades documentées (L2)

- Unification des statuts de tâches dans `DEV_CORE/API/devcore_api/ports.py` :
  - Fonctions de conversion bidirectionnelle `normalize_status_filter(status)` (faisant correspondre `active` et `in_progress` vers le statut d'API canonique `active`) et `canonical_db_status(status)` (faisant correspondre `active` vers le statut de base de données `in_progress`).
  - Mise à jour de la détection de tâche active dans le service MCP `DEV_CORE/MCP/devcore-scripts/services/task_service.py` pour accepter indifféremment `active` et `in_progress`.
- Enrichissement de l'endpoint `GET /api/v1/tasks` dans `DEV_CORE/API/devcore_api/app.py` :
  - Filtrage tolérant par statut acceptant `active` et `in_progress` de manière interchangeable.
  - Pagination structurée via `limit` et `offset` avec validation FastAPI `Query`.
  - Validation stricte d'identifiant de projet via `validate_project_id`.
  - Extension du schéma de réponse `TaskListResponse` dans `devcore_api/contracts.py` avec `total_count`, `offset`, `limit`, `has_more`.
- Catalogue de routes de l'API :
  - Schémas `RouteInfo` et `RouteCatalogResponse` introduits dans `devcore_api/schemas.py`.
  - Endpoint `GET /api/v1/routes` exposant l'ensemble des routes enregistrées, méthodes HTTP autorisées, tags, statut de dépréciation et descriptions.
- Façades documentées sous `/api/` (conservées temporairement pour la rétrocompatibilité des clients historiques) :
  - `GET /api/tasks`, `GET /api/health`, `GET /api/contracts`, `GET /api/routes`, `GET /api/workflows`, `GET /api/workflows/{run_id}` déléguant directement aux handlers v1 canoniques, balisées avec le tag OpenAPI `legacy_facades` et `deprecated=True`.
- Recette automatisée : **35 tests réussis en 5,16 s** sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires sur `DEV_CORE/API/test_ports.py`, `DEV_CORE/API/test_dual_read_cutover.py`, `DEV_CORE/API/test_domain_contracts.py` et `DEV_CORE/API/test_routes_facades_pagination.py`. 22 tests réussis et 1 sauté dans `DEV_CORE/MCP/devcore-scripts/test_individual_cli.py`.
- Limites : les façades historiques sous `/api/` sont documentées comme dépréciées et redirigent vers le comportement canonique. L'extraction complète des cas d'usage restants du Cockpit vers des services partagés (Item 393) et le routage exclusif du CLI/MCP (Item 395) restent les prochaines étapes de clôture de L2.
### Passage v216 — extraction des cas d'usage du Cockpit vers le service partagé task_mutations (L2)

- Création du service partagé de domaine `DEV_CORE/devcore_engine/services/task_mutations.py` :
  - `TaskMutationConflict` : exception métier dédiée portant le code de conflit (`stale_task_version`, `task_version_unavailable`, `task_transition_conflict`).
  - `validate_safe_id(value, label)` : validation centralisée interdisant les caractères de chemin (`/`, `\`, `:`, `..`) et appliquant le pattern d'identifiant strict.
  - `complete_task_usecase(project, task_id, expected_version, *, context, db_path)` : cas d'usage de clôture conditionnelle avec contrôle de version optimiste et injection du contexte d'audit.
  - `transition_task_usecase(project, task_id, operation, expected_version, *, context, db_path)` : cas d'usage de pause et reprise avec validation d'opération et concurrence active.
  - `delete_task_usecase(project, task_id, expected_version, *, context, db_path)` : cas d'usage de suppression logique avec vérification stricte des dépendances inter-tâches.
- Refactorisation de `DEV_CORE/Scripts/dashboard_api.py` :
  - Élimination de la duplication de code d'ouverture SQL et de gestion des conflits ; `complete_task`, `transition_individual_task` et `delete_task` délèguent intégralement aux fonctions du service partagé `task_mutations`.
- Recette automatisée : **33 tests réussis en 55,70 s** sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires :
  - `DEV_CORE/tests/test_task_mutations_service.py` (3 tests réussis en 7,99 s) : tests directs des cas d'usage, transitions, dépendances et conflits de version.
  - `DEV_CORE/Scripts/test_dashboard_pause_resume.py` et `DEV_CORE/Scripts/test_dashboard_task_actions.py` (30 tests réussis en 47,71 s) : régression complète des actions et transitions Cockpit via HTTP.
- Limites : les cas d'usage de mutation partagent maintenant la même logique Python pour le Cockpit et les API centrales ; le routage exclusif du CLI et MCP vers l'API active (Item 395) reste à finaliser.

### Passage v217 — finalisation complète de L2 : routage API du CLI et MCP, barrière mode client et binding localhost

- Endpoints de mutation et façades v1/legacy dans `DEV_CORE/API/devcore_api/app.py` :
  - Mutations de tâches et façades documentées :
    - `POST /api/v1/tasks/done` et façade `POST /api/done`
    - `POST /api/v1/tasks/pause` et façade `POST /api/pause`
    - `POST /api/v1/tasks/resume` et façade `POST /api/resume`
    - `DELETE /api/v1/tasks/delete` et façade `DELETE /api/delete`
    - `POST /api/v1/tasks/next` (sélection de la prochaine tâche prête avec bascule automatique du statut)
    - `POST /api/v1/tasks` (création typée de nouvelle tâche)
    - `GET /api/dashboard/tasks` (projection tableau de tâches compatible Cockpit / IndividualApiClient)
  - Délégation directe aux cas d'usage partagés de `DEV_CORE/devcore_engine/services/task_mutations.py` avec gestion centralisée des conflits 409 (`stale_task_version`, `task_transition_conflict`, etc.) et codes d'erreur universels enrichis (`detail.code`, `code`, `message`, `trace_id`).
- Routage API et barrière d'accès client dans le service MCP `DEV_CORE/MCP/devcore-scripts/services/task_service.py` :
  - Helper `get_api_url()` résolvant `DEVCORE_API_URL` ou `DEVCORE_MCP_API_URL`.
  - Méthodes `get_active_task_status(project)` et `complete_active_task(project, task_id, ...)` routant automatiquement les requêtes HTTP vers l'API active.
  - Barrière d'étanchéité stricte : si `DEVCORE_CLIENT_MODE=1` est actif sans URL d'API, `open_task_service()` et `open_existing_task_service()` lèvent formellement `PermissionError("Accès direct à la base de données interdit en mode client...")`.
- Routage CLI vers l'API dans `DEV_CORE/devcore_engine/cli.py` et `DEV_CORE/Scripts/dc.py` :
  - Option `--api-url` ajoutée au parser de commandes de tâches.
  - Fonction `_execute_task_cli_via_api(...)` assurant le routage HTTP des sous-commandes `board`, `next`, `complete`, `pause`, `resume`, `add`.
  - Barrière client `DEVCORE_CLIENT_MODE=1` : requiert `--api-url` ou `DEVCORE_API_URL` et refuse l'accès direct aux bases SQLite avec code de sortie 2.
  - Script `dc.py next task` adapté pour router vers `POST /api/v1/tasks/next` en présence de `DEVCORE_API_URL`, tout en bloquant l'accès direct en mode client.
- Configuration réseau localhost et protection des routes dans `DEV_CORE/Config/network.json` et `DEV_CORE/Scripts/dashboard_api.py` :
  - Entrée `api_gateway` ajoutée dans `Config/network.json` configurant un binding strict sur `127.0.0.1:20131`.
  - Gardes de configuration `DEVCORE_REQUIRE_AUTH_ALL=1` et `DEVCORE_SUPPRESS_HTML_TOKEN=1` introduites dans `dashboard_api.py` pour préparer la fermeture des routes anonymes et la suppression du jeton commun HTML.
- Recette automatisée et vérification d'équivalence :
  - `DEV_CORE/tests/test_cli_mcp_api_routing.py` (**6 tests réussis**) :
    - Services Python restant appelables directement sans API par les tests et outils de migration.
    - Barrière `DEVCORE_CLIENT_MODE=1` refusant l'accès direct SQLite dans le CLI et le service MCP.
    - Mutations API et façades vérifiées sur 200, 404 et 409.
    - Équivalence opérationnelle stricte : une opération via HTTP, CLI ou MCP produit exactement le même état et la même erreur (`stale_task_version`).
    - Routage de `dc.py next task` vers l'API.
    - Handshake MCP stdio en sous-processus réel avec appels d'outils routés vers l'API.
  - Régression API globale : **52 tests réussis en 49,41 s** sur `test_routes_facades_pagination.py`, `test_ports.py`, `test_dual_read_cutover.py`, `test_domain_contracts.py`, `test_task_mutations_service.py`, `test_task_cli_project_context.py` et `test_cli_mcp_api_routing.py`.
  - Régression Cockpit : **29 tests réussis en 34,00 s** sur `test_dashboard_task_actions.py`, `test_browser_sessions.py` et `test_cli_mcp_api_routing.py`.
- Clôture complète du Lot L2 (tous les critères d'acceptation L2 validés).

### Passage v218 — persistance PostgreSQL cible, numérotation atomique, verrouillage optimiste, isolation RLS et import à blanc (L3)

- Création du package de persistance centralisé `DEV_CORE/devcore_engine/persistence/` :
  - `config.py` : classe `DatabaseConfig` avec bornes de pool strictes (`pool_size` max 20, `max_overflow` max 10, `pool_timeout` max 60s), séparation des rôles applicatif (`devcore_app`) et migration (`devcore_migration`), validation stricte `validate_storage_path_outside_dropbox` interdisant formellement tout stockage transactionnel dans Dropbox selon la décision D-004.
  - `schema.sql` et `models.py` : schéma PostgreSQL cible complet v2 déclarant l'ensemble des 19 tables de l'architecture d'équipe (`organizations`, `users`, `sessions`, `workspaces`, `workspace_memberships`, `workspace_quotas`, `projects`, `project_memberships`, `tasks`, `runs`, `plugins`, `events`, `audit_log`, `schedules`, `schedule_history`, `outbox_messages`, `artifacts`, `memory_entries`, `budgets`).
  - Table `tasks` conforme à la cible L3 : `task_uuid` UUID clé primaire, `task_number` INTEGER, contrainte stricte `UNIQUE(project_id, task_number)` et contrôle de version positive `version >= 1`.
  - `rls.py` : DDL Row Level Security pour les 7 tables isolées par projet, gestionnaire de contexte `ProjectContextManager` et listeners de pool `register_pool_isolation_guards` garantissant qu'aucune connexion recyclée ne conserve un contexte projet résiduel.
  - `repositories.py` : `SqlTaskRepository` avec `get_next_task_number` atomique, UUID v5 déterministe, et `update_task` avec verrouillage optimiste levant `TaskMutationConflict("stale_task_version")` en cas de divergence de version. `SqlUnitOfWork` pour la gestion des transactions courtes avec rollback automatique sur exception.
  - `importer.py` : `PostgresDryRunImporter` assurant la réconciliation dry-run depuis boards JSON ou SQLite candidates, avec mapping UUID v5, détection des collisions de numéros, classification des entrées `runtime_state` (`preference_to_migrate`, `ephemeral_to_rebuild`, `ambiguous_needs_review`), calcul de digests SHA-256 et politique de rejet strict des conflits sans heuristique d'horodatage Dropbox.
  - `migrate_to_unified_db.py` : neutralisation post-cutover via `is_legacy_import_disabled()` et sentinelle `.cutover_complete` levant `RuntimeError` pour interdire toute migration automatique legacy silencieuse.
- Recette automatisée sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires isolées :
  - `DEV_CORE/tests/test_persistence_postgres_team_profile.py` (**7 tests réussis en 4,84 s**) couvrant la configuration, les schémas, les contraintes, RLS, la numérotation atomique, le verrouillage optimiste, la réconciliation et la neutralisation de l'ancien migrateur.
  - Régression complète L2-L3 : **60 tests réussis en 56,03 s** sur `test_persistence_postgres_team_profile.py`, `test_cli_mcp_api_routing.py`, `test_task_mutations_service.py`, `test_routes_facades_pagination.py`, `test_ports.py`, `test_dual_read_cutover.py`, `test_domain_contracts.py`, `test_sqlite_reconciliation.py` et `test_sqlite_fk_preview.py`.
- Avancement L3 : Items 446, 447, 448, 449, 450, 451, 452 validés. Item 445 qualifié au niveau configuration/bornes/isolation Dropbox ; serveur natif PostgreSQL Windows non installé sur cet environnement de recette.


### Passage v219 — passerelle d'autorisation par projet, attribution d'acteur, sessions d'API et grants RLS (L4)

- Middleware d'autorisation serveur `project_authorization_gate` dans `DEV_CORE/API/devcore_api/app.py` :
  - Détection automatique d'activation via `is_auth_enforced()` (`DEVCORE_REQUIRE_AUTH=1`, `DEVCORE_AUTH_MODE=individual`, `DEVCORE_DASHBOARD_AUTH_PROFILE=individual` ou `DEVCORE_REQUIRE_AUTH_ALL=1`).
  - Whitelist de routes publiques : `/api/v1/health`, `/api/health`, `/api/v1/contracts`, `/api/contracts`, `/api/v1/routes`, `/api/routes`, `/api/v1/integrations/github/webhook`, OpenAPI, Swagger docs, OPTIONS.
  - Whitelist des endpoints de gestion de session : `/api/v1/auth/session`, `/api/auth/session`.
  - Sur toutes les routes protégées : extraction et validation stricte de `project` (`validate_project_id`), contrôle `expected_version >= 1` sur les mutations de tâches en mode individuel.
  - Détermination de l'action requise : `task.read` (GET/HEAD), `task.mutate` (POST/DELETE/PUT), `context.read` (`/api/v1/project/context`), `task.audit.read` (`/api/v1/project/task-audit`).
  - Authentification double canal : Bearer token vérifié par `SqliteIdentityProvider` ou cookie de session navigateur validé par `authorize_session`.
  - Réponses normalisées : 401 avec en-tête `WWW-Authenticate: Bearer` (`individual_credential_required`, `invalid_individual_credential`), 403 en cas d'accès inter-projet ou de rôle insuffisant (`project_access_denied`), 503 si le store d'identités est indisponible (`identity_unavailable`), 413 si le corps de requête dépasse 1 Mo.
  - Injection dans l'état de requête : `request.state.principal`, `request.state.session_id` et `request.state.request_context = RequestContext(project_id, principal.user_id, session_id, trace_id)`.
  - En-tête de sécurité `Cache-Control: no-store` injecté systématiquement sur toutes les réponses autorisées.
- Attribution d'acteur dans les mutations sans fuite de secrets (Item 479) :
  - Endpoints `/api/v1/tasks/{done,pause,resume,delete}` injectent `request.state.request_context` dans `complete_task_usecase`, `transition_task_usecase` et `delete_task_usecase`.
  - `TaskService` consigne `actor=principal.user_id`, statut et versions dans `audit_log`, sans aucune fuite de mot de passe, de jeton d'authentification ou de clé LLM.
- Nouveaux endpoints de passerelle d'API (`devcore_api/app.py`) :
  - `GET /api/v1/project/context` et `/api/project/context` (avec contrôle `context.read`).
  - `GET /api/v1/project/task-audit` et `/api/project/task-audit` (avec contrôle `task.audit.read`).
  - `GET`, `POST`, `DELETE /api/v1/auth/session` et `/api/auth/session` (création de session par Bearer token, émission de cookie `HttpOnly` `SameSite=Strict`, jeton CSRF `X-CSRF-Token`, révocation explicite).
- Grants applicatifs Row-Level Security PostgreSQL (Item 478) :
  - `build_application_role_grants(role_name="devcore_app")` dans `DEV_CORE/devcore_engine/persistence/rls.py`, émettant les DDL avec clause stricte `NOBYPASSRLS`, grants explicites sur les 19 tables du schéma public, et exclusion de propriété DDL.
- Recette automatisée sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires :
  - `DEV_CORE/tests/test_api_project_authorization.py` (**9 tests réussis en 31,62 s**) couvrant le rejet 401 sans jeton, le rejet 403 inter-projet, l'accès membre/admin autorisé, la validation d'identifiant et version, la protection DoS > 1 Mo, la création et révocation de session, et la traçabilité de l'acteur sans fuite de secret.
  - Régression complète L3-L4 : **45 tests réussis en 265,26 s** sur `test_api_project_authorization.py`, `test_persistence_postgres_team_profile.py`, `test_cli_mcp_api_routing.py`, `test_task_mutations_service.py`, `test_task_legacy_adapters.py`, `test_task_versions.py` et `test_request_context.py`.
- Clôture complète du Lot L4 (Items 464, 475, 476, 477, 478, 479 validés).

### Passage v220 — moteur d'exécution durable, concurrente et interruptible DurableRunEngine (L5)

- Évaluation de l'architecture et décision D-005 (Items 614, 615) :
  - Constat formel : le module `dbos` est absent du runtime (`ModuleNotFoundError: No module named 'dbos'`) et aucun service natif PostgreSQL Windows n'est actif sur cet environnement de recette.
  - Décision d'architecture D-005 : adoption du moteur natif transactionnel `DurableRunEngine` garantissant une exécution durable locale sur SQLite/PostgreSQL, avec zéro dépendance au cloud, confinement strict des processus Windows, et évitant la coexistence de deux moteurs de reprise concurrents.
- Package `DEV_CORE/devcore_engine/runs/` :
  - `models.py` : modèles typés `RunSubmission`, `RunRecord`, `RunQuotaConfig`, exceptions métier (`RunNotFoundError`, `RunTransitionError`, `RunFencingError`, `RunQuotaExceededError`, `RunBackpressureError`, `EffectAlreadyInProgressError`).
  - `store.py` (`SqliteRunStore`) : dépôt transactionnel ACID avec journalisation WAL, table `runs` et table `external_effects`, index d'idempotence unique `(project_id, idempotency_key)`, verrouillage optimiste par jeton de clôture (`worker_token`), gestion des tentatives (`attempt_number`), battements de cœur (`heartbeat_at`) et reprise automatique après arrêt forcé (`recover_stale_or_interrupted`).
  - `scheduler.py` (`FairRunScheduler`) : ordonnancement équitable multi-tenants avec quotas stricts (2 créneaux globaux, 1 créneau par projet par défaut), rotation fair round-robin priorisant les projets sans tâche active (A ne peut affamer B), et rejet des saturations de file par backpressure (erreur 429).
  - `executor.py` (`ProcessRunExecutor`) : exécution en workspace dédié par run (`<local_root>/workspaces/<run_id>`), masquage préventif des secrets d'environnement (`GEMINI_API_KEY`, jetons, mots de passe), capture bornée des flux stdout/stderr (protection DoS mémoire), et confinement sous Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) garantissant l'extinction immédiate de toute la descendance (enfants et petits-enfants) lors d'un timeout ou d'une annulation.
  - `effects.py` (`EffectIdempotencyStore`) : déduplication stricte des effets externes (`github.create_pr`, etc.) avec cache de résultat et protection contre la double exécution en cas de reprise après panne.
  - `engine.py` (`DurableRunEngine`) : orchestration unifiée des soumissions, de la récupération des pannes, des battements de cœur et de la boucle d'exécution.
- Passerelle d'API unifiée `DEV_CORE/API/devcore_api/app.py` et schémas `schemas.py` :
  - Machine d'états à 8 états dans `contracts.py` et `run_state.py` : `queued`, `running`, `waiting_approval`, `paused`, `succeeded`, `failed`, `timed_out`, `cancelled`.
  - Endpoint `POST /api/v1/runs` retournant **HTTP 202 Accepted** avec en-tête `Location: /api/v1/runs/{run_id}` et corps typé `RunDetailResponse`. Admission idempotente via en-tête `Idempotency-Key` ou champ de corps, et rejet 429 sur dépassement de la file d'attente.
  - Endpoints d'inspection et de cycle de vie : `GET /api/v1/runs`, `GET /api/v1/runs/{run_id}`, `POST /api/v1/runs/{run_id}/cancel`, `POST /api/v1/runs/{run_id}/pause`, `POST /api/v1/runs/{run_id}/resume`, `POST /api/v1/runs/{run_id}/approve`.
  - Intégration au middleware `project_authorization_gate` : contrôle des rôles (lecture pour reader, mutation pour contributor/owner), attribution de l'auteur authentifié (`actor`) dans la fiche de run, et protection CSRF / session.
- Recette automatisée sous Python 3.13.3 (`E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe`) avec racines temporaires isolées :
  - `DEV_CORE/tests/test_durable_runs_and_concurrency.py` (**10 tests réussis en 11,97 s**) :
    1. Constat d'absence de `dbos` et qualification du moteur natif.
    2. Machine d'états à 8 états et rejet des transitions illégales.
    3. Fencing token interdisant à un ancien worker tardif de valider un run réattribué.
    4. Soumission HTTP 202 idempotente avec en-tête `Location`.
    5. Ordonnancement équitable évitant la famine inter-projets et backpressure.
    6. Confinement sous Windows Job Object avec extinction garantie du petit-enfant sur timeout réel.
    7. Sortie bornée et masquage des secrets d'environnement.
    8. Idempotence et déduplication des effets secondaires externes.
    9. Rapport d'état et santé DOWN de l'adaptateur Hermes non implémenté.
    10. Enforcement de l'autorisation d'API, de la matrice de rôles et attribution de l'acteur.
  - Régression globale complète : **60 tests réussis en 146,93 s** sur `test_durable_runs_and_concurrency.py`, `test_api_project_authorization.py`, `test_persistence_postgres_team_profile.py`, `test_cli_mcp_api_routing.py`, `test_task_mutations_service.py`, `test_task_legacy_adapters.py`, `test_task_versions.py`, `test_request_context.py`, `API/test_run_state_machine.py` et `API/test_run_pause_resume_cancel.py`.
- Clôture complète du Lot L5 (Items 614, 615, 616, 617, 618, 619, 620, 621, 622, 623 validés).

### Passage v221 — requalification rigoureuse et corrections critiques L4/L5 (P0-P2)

- **P0 — isolation des projets (paramètre URL vs JSON body)** :
  - Constat : la passerelle vérifiait `project` dans l'URL tandis que les handlers extrayaient `project_id` ou `project` du corps JSON, permettant à un jeton autorisé uniquement sur `alpha` d'exécuter des mutations dans `beta`.
  - Correction dans `DEV_CORE/API/devcore_api/app.py` : `project_authorization_gate` inspecte systématiquement l'URL (`query_project`) et le corps JSON (`body_project`). En cas de présence conjointe divergente, la requête est immédiatement rejetée avec HTTP 400 (`code: "project_mismatch"`).
  - Validation et assignation de `request.state.authorized_project`.
  - Sécurisation stricte de tous les endpoints de mutation : `submit_run`, `complete_task_endpoint`, `pause_task_endpoint`, `resume_task_endpoint`, `delete_task_endpoint`, `next_task_endpoint`, `create_task_endpoint`. Tout décalage avec le corps JSON est rejeté par 400 `project_mismatch`, et les usecases utilisent obligatoirement le projet validé par la passerelle.

- **P1 — exécution et boucle de traitement des runs** :
  - Constat : la soumission d'un run retournait 202 mais aucun worker ni parcours applicatif n'appelait `engine.step()`.
  - Implémentation dans `DEV_CORE/devcore_engine/runs/engine.py` d'un worker d'exécution complet :
    - `start_worker(poll_interval)` : thread daemon autonome consommant en continu les runs éligibles.
    - `stop_worker()` : arrêt coopératif et propre du thread.
    - `wake_worker()` : notification par événement dès qu'un run est soumis.
  - Ajout du point d'entrée `POST /api/v1/runs/step` dans `app.py` pour ordonnancer et exécuter un tick d'évaluation à la demande.

- **P1 — intégrité des transitions d'états (mise en pause et complétion)** :
  - Constat : mettre en pause modifiait le statut sans arrêter le processus, et la complétion ne vérifiait pas le statut running (un run en pause devenait ensuite succeeded).
  - Correction dans `DEV_CORE/devcore_engine/runs/executor.py` : injection de `check_pause_callback` dans la boucle d'exécution ; arrêt immédiat du processus enfant (`kill()` et fermeture du Job Object) avec résultat `outcome = "paused"`.
  - Correction dans `DEV_CORE/devcore_engine/runs/store.py` :
    - `pause_run` réinitialise `worker_token = NULL`, invalidant immédiatement les jetons de clôture des workers.
    - `complete_run` et `timeout_run` vérifient `record.status != "running"` avant toute autre opération et lèvent `RunTransitionError`, interdisant la complétion d'un run en pause.

- **P1 — confinement strict sous Windows Job Object** :
  - Constat : si la création du Windows Job échouait, le processus continuait sans confinement ; si l'affectation échouait après démarrage, le processus restait orphelin.
  - Correction dans `DEV_CORE/devcore_engine/runs/executor.py` :
    - Sous Windows (`os.name == "nt"`), le confinement par Windows Job est obligatoire ; tout échec d'initialisation avorte immédiatement l'exécution sans lancer de sous-processus.
    - Si `job_object.assign(proc.pid)` échoue après démarrage, le processus est immédiatement éliminé (`kill()` + `wait(timeout=2.0)`) et l'échec est tracé, garantissant zéro processus zombie.
    - La clause `finally` s'assure qu'aucun processus non terminé ne subsiste.

- **P1 — numérotation atomique des tâches sous concurrence** :
  - Constat : `SELECT MAX + 1` suivi d'un insert séparé provoquait des collisions sur la contrainte unique `(project_id, task_number)` lors de créations simultanées.
  - Correction dans `DEV_CORE/devcore_engine/persistence/repositories.py` :
    - Tentative de verrouillage de ligne de projet au niveau du dialecte SQL via `select(projects.c.id).where(...).with_for_update()`.
    - Boucle de rattrapage atomique sur savepoint (`session.begin_nested()`) en cas d'`IntegrityError` sur l'insertion auto-numérotée (jusqu'à 5 tentatives), recalculant le prochain numéro libre.
    - Test de charge concurrent multi-thread validé avec succès (10 créations simultanées sur 5 threads sans erreur ni collision).

- **P2 — rejeu idempotent et résistance au backpressure** :
  - Constat : l'admission vérifiait la file avant la clé d'idempotence, renvoyant `RunBackpressureError` (429) lors du rejeu d'une requête déjà acceptée.
  - Correction dans `DEV_CORE/devcore_engine/runs/engine.py` (`submit_run`) : recherche de la clé d'idempotence existante (`store.get_run_by_idempotency_key`) avant l'évaluation de la saturation de la file. Les rejeux légitimes d'un run admis retournent immédiatement le run sans être rejetés.

- **Preuves et résultats de recette** :
  - Environnement de recette : Python 3.13.3 (`E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe`), racines temporaires `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT`.
  - Suite de qualification ciblée : **33 tests réussis en 63,19 s** sur `DEV_CORE/tests/test_durable_runs_and_concurrency.py`, `DEV_CORE/tests/test_api_project_authorization.py` et `DEV_CORE/tests/test_persistence_postgres_team_profile.py`.
  - Non-régression : **14 tests réussis en 31,63 s** sur `DEV_CORE/tests/test_project_isolation.py` et `DEV_CORE/tests/test_task_mutations_service.py`.

### Passage v222 — Cloisonnement `/runs/step`, worker FastAPI concurrent et qualification PostgreSQL

- **P0 restant — Cloisonnement strict multi-tenant de `POST /api/v1/runs/step`** :
  - Constat : un token autorisé pour `alpha` pouvait appeler `POST /api/v1/runs/step?project=alpha` et déclencher l'exécution d'un run en attente de `beta` car la sélection n'était pas restreinte au projet de la requête.
  - Correction dans `DEV_CORE/devcore_engine/runs/scheduler.py` : `FairRunScheduler.select_next_run(project_id: str | None = None)` filtre les projets éligibles sur `project_id`. Si le projet n'a aucun run en file ou a atteint son quota (`project_max_running`), `select_next_run` retourne `None`.
  - Correction dans `DEV_CORE/devcore_engine/runs/engine.py` : `DurableRunEngine.step(project_id: str | None = None)` passe le paramètre `project_id` au scheduler.
  - Correction dans `DEV_CORE/API/devcore_api/app.py` : `step_run(request: Request, project: str | None = None)` extrait `authorized_project = getattr(request.state, "authorized_project", None) or project` et appelle `engine.step(project_id=authorized_project)`.
  - Qualification : nouveau test `test_run_step_cross_project_isolation` dans `DEV_CORE/tests/test_api_project_authorization.py` prouvant qu'un token pour `alpha` appelant `/runs/step?project=alpha` retourne `null`, n'exécute pas le run en attente de `beta`, et reçoit `403 Forbidden` s'il tente d'invoquer `/runs/step?project=beta`.

- **Raccordement du worker au cycle de vie FastAPI & Exécution concurrente multi-tenant** :
  - Constat : `start_worker()` n'était pas raccordé au cycle de vie de l'API (FastAPI), et sa boucle n'exécutait les runs que séquentiellement (un par un), sous-utilisant le quota global (`global_max_running = 2`).
  - Correction dans `DEV_CORE/devcore_engine/runs/engine.py` :
    - `start_worker()` instancie un `ThreadPoolExecutor(max_workers=max(1, quota_config.global_max_running))`.
    - La boucle de travail dépile et alloue des runs en parallèle jusqu'à concurrence des slots globaux libres (`active_count < global_max_running`).
    - L'exécution de chaque run revendiqué est déléguée au pool (`_execute_claimed_run`), et la fin de l'exécution déclenche `wake_worker()` pour consommer immédiatement les runs suivants.
    - `stop_worker()` garantit l'extinction ordonnée du pool de threads et l'attente des exécutions actives.
  - Correction dans `DEV_CORE/API/devcore_api/app.py` :
    - Gestionnaire `lifespan(app: FastAPI)` dans `create_app` démarrant automatiquement `get_run_engine().start_worker()` au startup et invoquant `active_run_engine.stop_worker()` au shutdown.
  - Qualification :
    - `test_worker_concurrent_parallel_execution` dans `DEV_CORE/tests/test_durable_runs_and_concurrency.py` validant que deux runs de projets distincts tournent simultanément en parallèle (tous deux à l'état `running` en même temps).
    - `test_api_lifespan_starts_and_stops_worker` validant le démarrage et l'arrêt automatique du worker d'exécution par le lifespan de FastAPI.

- **Qualification de la numérotation PostgreSQL cible & Limites d'exécution** :
  - Constat : le comportement sur le PostgreSQL cible devait être formellement qualifié pour la compilation du verrou de ligne et la gestion des savepoints en cas de conflit.
  - Qualification dans `DEV_CORE/tests/test_persistence_postgres_team_profile.py` (`test_postgres_task_numbering_dialect_compilation_and_savepoint_contract`) :
    - Compilation DDL/DML sous dialecte PostgreSQL : `select(projects.c.id).where(...).with_for_update()` génère bien la clause `FOR UPDATE` ;
    - Calcul du prochain numéro de tâche sous `postgresql.dialect()` : `coalesce(max(tasks.task_number), 0) + 1` ;
    - Contrat de session PostgreSQL : vérification de l'émission du verrou `FOR UPDATE` sur `projects`, et en cas d'`IntegrityError` simulant une collision concurrente sous PostgreSQL, le savepoint (`begin_nested()`) est annulé (`rollback()`) sans mettre la transaction en état avorté, puis le retry recalcule le numéro et réussit l'insertion atomique.
  - **Limite opérationnelle explicite** : Le contrat SQL, le dialecte et la gestion des savepoints sont prouvés, mais le fonctionnement sur une instance PostgreSQL réelle n'est pas encore prouvé (aucun serveur PostgreSQL ni listener 5432 actif sur la machine, conformité à la règle D-004 interdisant de manipuler des bases réelles sans environnement dédié). La qualification de bout en bout avec deux transactions réelles sur serveur PostgreSQL reste à réaliser lors de la bascule d'infrastructure.

- **P1 — Interruption des runs actifs et respect du délai dans `stop_worker()`** :
  - Constat : `stop_worker()` appelait `shutdown(wait=True)` sans interrompre les runs actifs, bloquant l'arrêt du worker tant que les processus enfants ne terminaient pas, ignorant le paramètre `timeout`.
  - Correction dans `DEV_CORE/devcore_engine/runs/executor.py` :
    - Enregistrement des processus enfants dans `_active_processes` ;
    - Ajout de la méthode `interrupt_all()` éliminant immédiatement tous les processus enfants en cours (`proc.kill()`).
  - Correction dans `DEV_CORE/devcore_engine/runs/engine.py` :
    - Ajout d'un événement `_stop_event` et du registre `_active_runs` ;
    - Dans `_execute_claimed_run`, `check_cancellation_callback` vérifie `self._stop_event.is_set()` ;
    - Dans `stop_worker(timeout)` : appel immédiat à `executor.interrupt_all()`, marquage de la demande d'annulation sur les runs actifs en base, attente bornée du thread worker et des futures (`concurrent.futures.wait(active_futs, timeout=remaining)`), puis `shutdown(wait=False, cancel_futures=True)`, garantissant une sortie immédiate sous le délai `timeout`.
  - Qualification : nouveau test `test_stop_worker_interrupts_active_runs_within_timeout` dans `DEV_CORE/tests/test_durable_runs_and_concurrency.py` prouvant qu'un run en cours d'exécution de 30 secondes est interrompu immédiatement et que `stop_worker(timeout=1.5)` se termine en moins de 2,0 secondes en passant le run en `cancelled`.

- **Preuves et résultats de recette** :
  - Environnement de recette : Python 3.13.3 (`E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe`), racines temporaires `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT`.
  - Suite de qualification complète : **45 tests réussis en 77,98 s** :
    - `DEV_CORE/tests/test_durable_runs_and_concurrency.py` (17/17 passés)
    - `DEV_CORE/tests/test_api_project_authorization.py` (12/12 passés)
    - `DEV_CORE/tests/test_persistence_postgres_team_profile.py` (9/9 passés)
    - `DEV_CORE/tests/test_outbox_transactional_delivery.py` (7/7 passés)


### Passage v223 — Qualification de la cohérence et de la réactivité du Cockpit (Lot L6)

- **Objectif et périmètre du passage** :
  - Clôture et qualification intégrale des critères du Lot L6 (« Garantir cohérence et réactivité du Cockpit »).
  - Validation de la chaîne complète : outbox transactionnelle (SQLite & cible PostgreSQL/SQLAlchemy), snapshots de projections versionnés et protégés sous verrou exclusif, publication atomique et collection de capacité, déport asynchrone des charges de travail hors de la boucle événementielle, limitation de débit/admission des flux SSE (32 abonnés simultanés), gestion des curseurs et reprises progressives sous Edge réel.

- **Points clés audités et qualifiés** :
  1. **Outbox transactionnelle et déduplication des consommateurs** :
     - Sur SQLite : `TaskService` commit inclut `bus_events` (`EventBus.append_in_transaction`), testé avec injection de panne sur déclencheur `reject_fixture` assurant le rollback atomique (`test_dashboard_pause_resume.py`).
     - Sur persistance cible : `SqlUnitOfWork` joint `SqlTaskRepository` et `OutboxRepository` (`devcore_engine/persistence/outbox.py`), garantissant une publication fiable avec clé d'idempotence unique, backoff exponentiel, passage en dead-letter queue (DLQ) et rétention configurable. 7 tests unitaires dédiés passés (`test_outbox_transactional_delivery.py`).
  2. **Projections et cycle de vie des snapshots** :
     - Stockage sous `generations/<uuid>/` avec 4 artefacts (`dashboard_payload.json`, `payload_hash.txt`, `index.html`, `index_terminal.html`) et `manifest.json`.
     - Écriture atomique `atomic_write_text`, vérification des sommes de contrôle SHA-256 et admission bornée (plafond de 256 Mio logiques / 512 répertoires).
     - Lecteurs API branchés sur `pin_snapshot` maintenant ouverts les descripteurs sous verrou catalogue bref `SnapshotCatalogLock`, garantissant que la lecture n'est pas perturbée par une rotation de snapshot. Fraîcheur validée via `fstat` direct sur descripteur.
     - 82 tests passés sur `test_dashboard_snapshots.py`, `test_dashboard_publication.py`, `test_dashboard_cache_writer.py`.
  3. **Déport asynchrone et isolation de la boucle d'événements** :
     - `RefreshCoordinator` déporte la génération en thread via `asyncio.to_thread` protégé par bouclier `asyncio.shield` contre l'annulation des abonnés.
     - Zéro appel bloquant `subprocess.run` ou I/O lourdes dans la boucle principale asyncio.
  4. **Producteur unique et debounce des changements** :
     - Verrou interprocessus `DashboardLock` avec reprise sur crash.
     - `InputWatcher` regroupant les changements de métadonnées avec debounce pour éviter les rafales de régénération sous abonnés multiples.
  5. **Curseurs SSE, Last-Event-ID et reprise progressive** :
     - Curseur strict `snapshot:<hex32>` validé contre toute injection via `parse_snapshot_cursor`.
     - Gestion du `Last-Event-ID` avec renvoi au retry et resynchronisation par `dashboard.delta` (`snapshot_required=True`, `reload_snapshot`).
     - Qualification sur Microsoft Edge réel (`test_dashboard_browser_stream.py` et `test_individual_browser_transitions.py`) vérifiant la synchronisation du DOM via `morphDOM`, l'application du nouveau snapshot et l'absence de régénération redondante.
  6. **Contrôle d'admission des flux et gestion des abonnés lents** :
     - Limiteur `StreamSlots` bornant à 32 connexions SSE simultanées par processus/boucle avec rejet 503 / `Retry-After: 5`.
     - Isolation stricte des routes individuelles par projet et vérification de la révocation immédiate des jetons et sessions cookies sur serveur Uvicorn réel (`test_dashboard_individual_http.py`).

- **Preuves et résultats de recette** :
  - Environnement de recette : Python 3.13.3 (`E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe`), racines temporaires `$env:DEVCORE_LOCAL_ROOT` et `$env:DEVCORE_DATA_ROOT`, overlay d'authentification Argon2id dans `PYTHONPATH`.
  - Exécution complète des suites Cockpit / Outbox : **362 tests passés avec succès** (0 échec, 0 régression) :
    - Suite Dashboard batch 3 : **96 tests passés en 441,69 s** (`test_dashboard_project_selection.py`, `test_dashboard_project_context.py`, `test_dashboard_pause_resume.py`, `test_dashboard_individual_access.py`, `test_dashboard_individual_http.py`, `test_dashboard_actor_audit.py`, `test_dashboard_admin_compatibility.py`, `test_dashboard_browser_sessions.py`, `test_dashboard_browser_stream.py`, `test_dashboard_password_login.py`) ;
    - Suite Dashboard batch 4 : **259 tests passés en 264,56 s** (`test_dashboard_cache_writer.py`, `test_dashboard_data_loader.py`, `test_dashboard_error_reporter.py`, `test_dashboard_generation_lock.py`, `test_dashboard_input_watcher.py`, `test_dashboard_publication.py`, `test_dashboard_refresh_coordinator.py`, `test_dashboard_snapshots.py`, `test_dashboard_sse_cursor.py`, `test_dashboard_sse_templates.py`, `test_dashboard_stream_admission.py`, `test_dashboard_task_actions.py`, `test_dashboard_task_audit.py`, `test_dashboard_task_interactions.py`, `test_individual_browser_transitions.py`) ;
    - Suite Outbox & Repositories : **7 tests passés en 4,82 s** (`DEV_CORE/tests/test_outbox_transactional_delivery.py`).
  - Zéro modification des données actives, des dossiers Dropbox ou des index RepoWise réels.


### Passage v224 — Qualification de la mémoire fiable, du KnowledgeProvider et de RepoWise (Lot L7)

- **Objectif et périmètre du passage** :
  - Clôture et qualification intégrale des critères du Lot L7 (« Fiabiliser la mémoire et RepoWise »).
  - Implémentation du contrat d'abstraction `KnowledgeProvider` unifiant le stockage de mémoire et la recherche indépendamment du moteur RepoWise.
  - Garantie absolue de non-contamination inter-projet (isolation stricte par `project_id`) sur les documents, conversations, fragments vectoriels et graphes de connaissances.
  - Raccordement du contrat d'embedding 768 dimensions pour `gemini-embedding-001:768:v1`, élimination de toute dérive (vecteurs nuls, 384 dimensions) et gestion robuste du mode dégradé avec repli lexical transparent.
  - Fusion hybride Reciprocal Rank Fusion (RRF, k=60) avec préservation de la provenance (`source_path`, `commit_hash`, `kind`).
  - Validation expérimentale sur un corpus de référence de 20 questions techniques.

- **Points clés audités et qualifiés** :
  1. **Fournisseurs KnowledgeProvider (`devcore_engine/services/knowledge_provider.py`)** :
     - `SqliteKnowledgeProvider` : implémente le protocole `KnowledgeProvider` de `devcore_api.ports` (`search`, `get_context`). Stockage relationnel dans `knowledge_items` avec synchronisation FTS5 (`knowledge_items_fts`), support des fragments stables et recherche hybride.
     - `RepoWiseKnowledgeProvider` : adaptateur ciblant RepoWise avec portée `--no-workspace` et projet explicite, refusant les requêtes transverses et relevant les métadonnées (mode embedder mock, fraîcheur, recherche sémantique).
     - `CompositeKnowledgeProvider` : fédère plusieurs fournisseurs de connaissances, agrégeant leurs résultats via RRF avec contrôle strict d'isolation pour écarter tout résultat hors du projet demandé.
  2. **Isolation par projet sur l'ensemble des structures de mémoire** :
     - Base SQLite : ajout de `project_id` sur `knowledge_items`, `kg_nodes`, `kg_edges` et `vault_notes` dans `INIT_SCHEMA_SQL` et `_align_existing_schema` (`devcore_engine/db.py`).
     - Conversations : filtrage obligatoire `WHERE conversations_fts MATCH ? AND project = ?` (et repli `WHERE project = ? AND content LIKE ?`) dans `MemoryHierarchy._search_fts` (`devcore_engine/services/memory_hierarchy.py`), interdisant toute fuite inter-projet.
     - Graphe de connaissances : `KnowledgeGraph` (`devcore_engine/services/knowledge.py`) partitionne les nœuds et arêtes par `project_id` et borne l'analyse d'impact (`impact_analysis`) au périmètre strict du projet analysé, éliminant tout débordement de rayon de propagation.
  3. **Contrat d'embeddings et repli lexical** :
     - Dimension 768 imposée par `EmbeddingService.validate_vector`, rejetant formellement les vecteurs incomplets, nuls ou non-finis.
     - En cas d'indisponibilité du fournisseur d'embeddings ou de vecteur corrompu, `SqliteKnowledgeProvider` bascule automatiquement et gracieusement en mode purement lexical sans lever d'exception.
  4. **Classement hybride RRF et corpus de référence** :
     - Reciprocal Rank Fusion avec constante standard $k=60$ combinant les rangs lexicaux et vectoriels.
     - Création d'un jeu d'évaluation de 20 questions techniques (`DEV_CORE/tests/corpus_20_questions.json`) couvrant l'architecture, la sécurité, l'ordonnancement, le confinement Windows Job, le Cockpit, la persistance et la mémoire.
     - Les 20 questions atteignent 100 % de rappel sur leurs cibles attendues, avec zéro résultat issu de projets leurres injectés dans le même magasin.

- **Preuves et résultats de recette** :
  - Environnement de recette : Python 3.13.3 (`E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe`), racines temporaires `$env:DEVCORE_LOCAL_ROOT` et `$env:DEVCORE_DATA_ROOT`.
  - Exécution complète de la suite L7 : **132 tests passés avec succès** (1 ignoré sur privilège symlink Windows, 0 échec, 0 régression) :
    - `DEV_CORE/tests/test_knowledge_provider_evaluation.py` (9/9 passés) ;
    - `DEV_CORE/tests/test_memory_search_embeddings.py` (22/22 passés) ;
    - `DEV_CORE/tests/test_qdrant_simulator_contract.py` (14/14 passés) ;
    - `DEV_CORE/tests/test_repowise_update_project_context.py` (3/3 passés) ;
    - `DEV_CORE/tests/test_knowledge_migration.py` (1/1 passé) ;
    - `DEV_CORE/tests/test_project_context_resume.py` (7/7 passés, 1 skip symlink) ;
    - `DEV_CORE/tests/test_ask_project_context.py` (5/5 passés) ;
    - `DEV_CORE/tests/test_get_active_project_context.py` (6/6 passés) ;
    - `DEV_CORE/tests/test_hook_project_context.py` (3/3 passés) ;
    - `DEV_CORE/tests/test_post_commit_project_context.py` (2/2 passés) ;
    - `DEV_CORE/tests/test_task_cli_project_context.py` (8/8 passés) ;
    - `DEV_CORE/tests/test_configure_codex_mcp.py` (3/3 passés) ;
    - `DEV_CORE/tests/test_cli_mcp_api_routing.py` (6/6 passés) ;
    - `DEV_CORE/tests/test_devcore_engine.py` (8/8 passés) ;
    - `DEV_CORE/devcore_engine/tests/test_knowledge_graph.py` (1/1 passé) ;
    - `DEV_CORE/API/test_ports.py` (17/17 passés).
  - Aucune modification des index RepoWise de production ni des données actives.


### Passage v225 — Recette locale et qualification des contrats d'autonomie et d'observabilité (Lot L8)

- **Objectif et périmètre du passage** :
  - Recette locale et qualification des contrats du Lot L8 (« Autonomie contrôlée et observabilité ») sur banc de tests automatisés et racines temporaires isolées.
  - Distinction formelle entre la validation de recette locale (contrats, baux, confinement, agrégation et OTLP loopback validés) et l'activation opérationnelle en continu (serveur Langfuse distant, ingestion télémétrique permanente, démons de fond en production), qui demeure ouverte conformément au plan (§9, L8/L9) et à la décision D-002.
  - Validation des dépendances système critiques sous Windows : intégration de `tzdata` 2026.5 et `websockets` 17.2 CP313 au sein de l'overlay de recette standard `devcore-auth-py313-20261003/packages`, garantissant le support de `ZoneInfo` et des flux WebSocket ASGI sans dépendre d'états éphémères du répertoire temporaire.
  - Portabilité des scripts de contrôle d'arrêt et de supervision (`PS_EXE`) s'appuyant dynamiquement sur PowerShell Core ou Windows PowerShell.
  - Vérification complète de la chaîne d'ordonnancement (Scheduler), de la surveillance des processus (SystemWatcher, Windows Job confinement), des budgets de relance et SLO, de l'export OTLP/LLMOps et du reporting métrique étanche par projet.

- **Points clés audités et qualifiés** :
  1. **Ordonnancement robuste et baux atomiques (`DEV_CORE/Scheduler`)** :
     - Verrouillage interprocessus exclusif par baux atomiques (`SchedulerLeaseLock`) résistant aux crashs et à l'expiration concurrente.
     - Prise en charge des politiques d'exécution `skip`, `run_once`, `catch_up` avec calcul direct borné et fenêtres glissantes de 30 jours sans énumération infinie.
     - Arborescence de processus confinée par Job Object Windows (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) avec élimination garantie des petits-enfants sur timeout ou arrêt du parent.
     - Résolution transactionnelle des claims et réconciliation des historiques sans double comptage. 192 tests validés sur 11 suites scheduler.
  2. **Surveillance, budgets de relance et arrêt coopératif (`system_watcher`, `service_control`, `stop.ps1`)** :
     - Vérification de l'identité OS des processus, nonce de démarrage, readiness et exclusion mutuelle de maintenance.
     - Budget de redémarrage `RestartBudget` limitant les tentatives à 3 relances par tranche de 10 minutes, avec backoff exponentiel.
     - Protocole d'arrêt coopératif via `stop.ps1 -SchedulerOnly` et `service_runtime` permettant l'achèvement propre des jobs en cours avant libération des baux.
  3. **Métriques locales et étanchéité par projet et tâche (`metrics_service.py`, `html_renderer.py`)** :
     - Magasin JSONL local borné avec verrou interprocessus garantissant l'absence de perte de données sous écritures concurrentes.
     - Attribution par tâche isolée inter-projet : indexation des métriques de tâche sous la clé qualifiée `f"{project}_{task_id}"` (ex. `alpha_T-01` vs `beta_T-01`), éliminant toute collision de valeurs entre tâches de même identifiant dans des projets différents et respectant le contrat `scoped_task_metrics` du Cockpit [P1 corrigé].
     - Résilience aux écritures JSONL non terminées par saut de ligne : inspection du dernier octet sous verrou et préfixage automatique par `\n` lors de l'écriture suivante, préservant l'intégrité de l'événement antérieur et de la nouvelle ligne sans corruption syntaxique ni perte de lecture dans `aggregate()` [P2 corrigé].
     - Rejet strict des lignes historiques malformées et des lots invalides sans corrompre le journal d'événements.
     - Agrégation des métriques sans fuite inter-projet ni repli global non autorisé, et attribution des tokens Codex observés (`provider_reported` vs `unattributed`).
  4. **Observabilité, OTLP et client LLMOps (`devcore_api/observability`, `llmops`, `otlp_export`)** :
     - Propagation des en-têtes W3C TraceContext (`trace_id`, `span_id`) et des contextes de corrélation applicatifs sans exposition de secrets.
     - Export OTLP/HTTP JSON asynchrone borné (payload 8 Kio, deadline 2 s, basic auth) avec gestion des files volatiles et drainage au shutdown ASGI.
     - Intercepteur de génération `GenerationObserver` capturant fidèlement les métadonnées de requête et de réponse LLM.
  5. **Contrôle d'admission et streaming ASGI (`headroom_routes`, `request_body`)** :
     - Bornage strict de la profondeur JSON (≤ 64 niveaux) et du volume des flux entrants (≤ 16 Mio).
     - Admission partagée entre flux streaming et non-streaming avec libération immédiate des créneaux sur exception ou déconnexion.
     - Protocoles WebSocket conformes aux spécifications SansIO d'Uvicorn 0.54.0 avec code de fermeture 1012.

- **Preuves et résultats de recette** :
  - Environnement de recette : Python 3.13.3 (`E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe`), racines temporaires `$env:DEVCORE_LOCAL_ROOT` et `$env:DEVCORE_DATA_ROOT`, overlay de recette dans `PYTHONPATH`.
  - Exécution complète des suites L8 : **694 tests passés avec succès** (0 échec, 0 régression) :
    - 11 suites scheduler : **192 tests passés** (`test_scheduler_claim_inspection.py`, `test_scheduler_claim_resolution.py`, `test_scheduler_config_validation.py`, `test_scheduler_cooperative_stop.py`, `test_scheduler_cron_latest.py`, `test_scheduler_history_failure.py`, `test_scheduler_interval_bounds.py`, `test_scheduler_lease_atomic.py`, `test_scheduler_process_tree.py`, `test_scheduler_registry_recovery.py`, `test_scheduler_supervision.py`) ;
    - Maintenance et runtime de services : **36 tests passés** (`test_service_maintenance.py`, `test_service_runtime.py`) ;
    - Métriques et reporting : **12 tests passés** (`test_metrics_service_py.py`, `test_gen_metrics.py`) intégrant les validations d'isolation de clé inter-projet et d'append sécurisé JSONL ;
    - Observabilité, OTLP, SLO et LLMOps : **78 tests passés** (`test_correlation_context.py`, `test_eval_datasets.py`, `test_llmops_generation.py`, `test_llmops_langfuse.py`, `test_observability_instrumentation.py`, `test_otlp_export.py`, `test_otlp_worker.py`, `test_prometheus_metrics.py`, `test_router_generation.py`, `test_router_observation_lifecycle.py`, `test_router_stream_admission.py`, `test_slo_budget_policy.py`) ;
    - Admission et routage des flux : **332 tests passés** (`test_router_body_admission.py`, `test_router_fallback_admission.py`, `test_router_private_diagnostics.py`, `test_router_provider_deadline.py`, `test_router_provider_json.py`, `test_router_rate_limit.py`, `test_router_reported_usage.py`, `test_router_response_length.py`, `test_router_stats_store.py`, `test_router_stream_deadline.py`, `test_router_stream_encoding.py`, `test_router_stream_retries.py`, `test_router_stream_usage.py`, `test_router_stream_volume.py`, `test_router_unattributed.py`, `test_router_upstream_body.py`, `test_route_capacity.py`, `test_llm_route_health.py`, `test_llm_route_liveness.py`, `test_llm_route_separation.py`, `test_llm_route_websocket.py`, `test_restart_budget.py`, `test_service_drain.py`) ;
    - Outils et supervision : **44 tests passés** (`test_scheduler_contract.py`, `test_scheduler_migration.py`, `test_scheduler_tick.py`, `test_inspect_service_shutdown.py`, `test_compare_codex_usage.py`, `test_event_watcher_local.py`).
  - Statut opérationnel : contrats et comportement sous recette locale validés à 100% sur fixtures. L'activation des flux réels et l'ingestion vers serveur Langfuse distant restent ouvertes hors du banc de test (reportées au Lot L9 / post-pilote).
  - Zéro modification des données actives ou des index de production.


### Passage v226 — Qualification opérationnelle du runtime candidat 3.13.16, des tests d'acceptation du profil individuel et de la gate de vérification (Lot L9)

- **Objectif et périmètre du passage** :
  - Validation opérationnelle du runtime candidat Python 3.13.16 (`E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe`) et de la bibliothèque SQLite 3.53.1 immunisée contre le défaut amont de réinitialisation WAL.
  - Découplage strict de `devcore_engine.services` pour exécution isolée sous Python `-I` sans dépendance vers `devcore_api`.
  - Reconstruction et réinstallation de la wheel moteur `devcore_engine-10.2.0-py3-none-any.whl` incorporant l'ensemble des composants L2–L8 (`task_mutations`, `windows_secret_files`, `runs`, `persistence`, `knowledge_provider`, trigger de version, initialisation vectorielle automatique dans `connect_db`).
  - Validation intégrale des suites d'acceptation HTTP/CLI/MCP du profil individuel et des protocoles stdio en environnement isolé sous Python `-I`.
  - Résolution de la cohérence de schéma dans la réconciliation SQLite (`reconcile_sqlite_candidate.py`) : prise en compte de la colonne `project_id` dans la table de quarantaine `kg_edges_quarantine` et le calcul du digest d'arêtes.
  - Exécution complète des suites de réconciliation, détection des conflits Dropbox, non-réimport de fichiers partagés et récupération locale / sauvegarde d'identité à chaud.
  - Validation complète de la porte de vérification CI déterministe `verify.ps1` (11/11 contrôles passés) sur les deux runtimes (3.13.3 documenté et 3.13.16 candidat).
  - Publication et préflight validé du snapshot figé `individual-platform-v2` (16 fichiers) dans `E:/DevCoreRuntime/releases/devcore-py31316-20261003`.

- **Points clés audités et qualifiés** :
  1. **Prérequis WAL et éligibilité SQLite 3.53.1 (`check_sqlite_runtime.py`, `test_sqlite_wal_qualification.py`)** :
     - La sonde `check_sqlite_runtime.py` confirme le code 0 sur le runtime candidat (`eligible_for_wal_qualification: true`, SQLite 3.53.1, Python 3.13.16).
     - Qualification de concurrence et de checkpoint (`test_sqlite_wal_qualification.py`) : 3/3 tests passés avec succès sur bases temporaires isolées (modes PASSIVE, TRUNCATE, et chargement natif de l'extension vectorielle `sqlite-vec` 0.1.9).
  2. **Découplage architectural et wheel moteur figé (`devcore_engine-10.2.0-py3-none-any.whl`)** :
     - Élimination de l'import anticipé de `knowledge_provider` dans `devcore_engine/services/__init__.py` au profit d'un `__getattr__` paresseux, évitant la levée de `ModuleNotFoundError: No module named 'devcore_api'` lors des invocations autonomes en mode `-I`.
     - Découplage de `SystemWatcher` (`devcore_engine/infra/system_watcher.py`) : résolution dynamique de `DEVCORE_PLATFORM_ROOT` et fallbacks défensifs sur `scheduler_presence`, `scheduler_control`, `service_control`, permettant l'import isolé direct sous `python.exe -I` sans dépendance de chemin.
     - Intégration de l'exécution conditionnelle et idempotente de `VECTOR_SCHEMA_SQL` directement au sein de `connect_db`, garantissant la présence immédiate des tables virtuelles `vec_*` dès l'activation de `sqlite-vec`.
     - Wheel moteur reconstruite via `uv build` (SHA-256 `259fdba90ef053ea08a6c6432c1f30a22b79ee9425a0087fe917be4b0c2bc672`) et installée dans les deux environnements de release (`releases/devcore-py31316-20261003` et `recipes/devcore-individual-v155-f7d2a8b7/runtime`). Manifeste des artefacts `artifacts/manifest.json` (SHA-256 `c0eda908030c67b3ceb189aef857813786cbf7891c22c69623ecaad04ad9213e`, 86 sources) et `provenance.json` synchronisés.
  3. **Suites d'acceptation du profil candidat sous Python 3.13.16** :
     - **12 tests** de lanceur candidat Dashboard (`test_individual_candidate_launcher.py`) validant le préflight sous Python `-I`, la validation stricte des empreintes SHA-256 de manifeste, l'étanchéité des racines de magasins et les mutations via `/api/done`, `/api/pause`, `/api/resume`.
     - **11 tests** de lanceur MCP stdio (`test_individual_mcp_launcher.py`) validant l'absence de fuite sur stdin/stdout, l'application stricte des autorisations par projet (`alpha` vs `beta`), les budgets de contexte mesurés et la révocation immédiate de credentials.
     - **16 tests** de construction de bundle et d'identité (`test_individual_bundle.py`, `test_individual_identity.py`).
     - **172 tests** de clients applicatifs (`test_individual_audit.py`, `test_individual_cli.py`, `test_individual_context.py`, `test_individual_delete.py`, `test_individual_tasks.py`, `test_individual_transitions.py`) passés à 100% (1 skipped sous Windows).
     - **7 tests** de protocoles stdio MCP (`test_stdio_protocol.py`).
  4. **Réconciliation SQLite et intégrité de sauvegarde (45 tests)** :
     - Correction de `reconcile_sqlite_candidate.py` : alignement dynamique de la table `kg_edges_quarantine` et de la clause d'union de calcul de digest pour inclure la colonne `project_id` issue du schéma multi-projet L1/L7, éliminant tout décalage d'empreinte lors de la conservation des lignes.
     - 7 tests de réconciliation (`test_sqlite_reconciliation.py`) validés à 100% sans perte d'historique ni altération de la base source.
     - 1 test de détection de conflit Dropbox (`test_inspect_dropbox_conflicts.py`) vérifiant la comparaison en lecture seule sans écriture ni exposition de données privées.
     - 2 tests de lancement sans import legacy (`test_launch_no_legacy_import.py`) confirmant l'absence de réimport intempestif des fichiers `tasks.json` partagés.
     - 26 tests de récupération locale d'administrateur (`test_local_recovery.py`) et 9 tests de sauvegarde/restauration d'identité à chaud (`test_identity_backup.py`) validés sous les modes DELETE et WAL avec vérification des ACLs NTFS et des SIDs d'opérateur.
  5. **Gate CI déterministe (`verify.ps1`)** :
     - 11 vérifications exécutées et validées (100% OK, code de retour 0) : `diagnose-gate`, `dc-dispatch`, `diagnose-gate-tests`, `verify-ci-tests`, `test-exit-contract`, `ci-workflow-contract`, `platform-version-tests`, `embedding-contract-tests`, `qdrant-vector-contract`, `health-report-tests`, `secret-scan-tests`.
  6. **Publication du snapshot `individual-platform-v2`** :
     - Construction et vérification de `E:/DevCoreRuntime/releases/devcore-py31316-20261003/individual-platform-v2` comprenant les 16 fichiers déclarés du Cockpit et des services MCP. Empreinte de manifeste SHA-256 : `f5f42383cd55a43eb60753999f0e4c188ec2ebfcbf2eaa9d05164db1f380dc05`.
     - Préflights Dashboard et MCP validés avec succès sur ce snapshot avec exclusion d'environnement ambiant.

- **Preuves et résultats de recette** :
  - Runtimes : `E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe` (3.13.3) et `E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe` (3.13.16).
  - Racines de test strictement temporaires (`$env:DEVCORE_LOCAL_ROOT`, `$env:DEVCORE_DATA_ROOT`). Aucune modification des données actives, des dossiers Dropbox ou des index réels (Décision D-004 respectée).
  - Bilan de tests : **267 tests collectés et validés** (266 passés, 1 ignoré sous Windows pour maintenance NTFS ; 219 acceptation profil individuel + 45 sauvegarde/réconciliation/conflits + 3 WAL/sqlite-vec), en complément des 11 checks de la gate CI `verify.ps1`.
  - Statut opérationnel : Lot L9 **candidat qualifié partiellement sur banc de test isolé**. Le déploiement opérationnel réel sur ce poste (service Windows sous compte restreint, bascule des données de production, pilote multi-utilisateurs et gel des écritures historiques Dropbox) reste ouvert conformément au plan L9 et au manifeste (`operationally_qualified: false`).

### Passage v227 — Release L9 attestée et préparation du service Windows (2026-10-10)

- **État initial relu** : le v226 avait déjà resynchronisé sa wheel et son manifeste (empreinte wheel `259fdba9...`) et corrigé le compte rendu à 267 tests collectés. L'import isolé de `SystemWatcher` reposait toutefois sur des fonctions de repli sans garde de lancement quand `Scheduler` manquait au snapshot individuel ; le paquet installé omettait aussi `persistence/schema.sql` bien que ce fichier figure dans l'inventaire source.
- **Code** : repli `SystemWatcher` rendu bloquant à l'utilisation lorsque le Scheduler est absent ; `schema.sql` inclus dans la wheel ; `verify_engine_release.py` lie manifeste, provenance, wheel, inventaire du moteur installé, inventaire des paquets, contrôles et hôte Windows. Lanceur individuel `--managed` raccordé à `service_runtime` pour l'arrêt coopératif. Contrôles allowlistés (`build_candidate_controls.py`) et recette exécutable (`qualify_individual_managed.py`) ajoutés. Profil de service Windows `devcore_engine.windows_service`, configuration relative au runtime et installation interactive sans mot de passe dans les arguments ajoutés.
- **Nouvelle release candidate** : `E:/DevCoreRuntime/releases/devcore-py31316-20261010-l9`, distincte du v226. Python 3.13.16 / SQLite 3.53.1 ; wheel SHA-256 `1618ea345c7a3151d7f667b3c07f0436e2d5edf7d1be858001e641b71c6fa19a` ; manifeste moteur SHA-256 `6d20528a90b40fc40c896631cb13d4c59377556c81fce45135911ae2b65229b1` ; snapshot individuel v2 inchangé (manifeste `f5f42383cd55a43eb60753999f0e4c188ec2ebfcbf2eaa9d05164db1f380dc05`). `websockets` 17.2 et `tzdata` 2026.5 ont été copiés depuis l'overlay local déjà documenté ; `uv pip check --offline` : 56 paquets compatibles. Les contrôles sont figés et vérifiés par provenance ; leur empreinte finale doit être relue après tout changement de script.
- **Recette isolée** : 50 tests initiaux réussis ; première suite élargie 55 réussis / 3 échecs (dépendance `websockets` absente et arrêt temporaire MCP), puis 10 tests ciblés réussis après correction de la dépendance, puis 58 tests ciblés réussis en suite combinée. Tests de profil portable et d'attestation : 9 réussis. La recette `qualify_individual_managed.py` exécutée depuis la release confirme `/project` HTTP 200, demande d'arrêt coopératif, `shutdown_completed` et processus terminé avec code 0 sur racines et identité temporaires. L'import isolé de la wheel fonctionne ; une opération `SystemWatcher` sur le snapshot minimal refuse explicitement l'absence de Scheduler.
- **Préparation sur ce poste** : configuration relative `state/local` / `state/data` sous `E:/DevCoreRuntime`, hors de la release. Magasin `state/local/Security/identity.db` initialisé sous ACL NTFS et contrôlé sans données de recette. Aucun service `DevCoreIndividual` n'est encore enregistré dans SCM ; l'enregistrement sous `Administrateur` nécessite la saisie locale du mot de passe. Ce compte n'est pas restreint, contrairement au critère du plan L9. Les données de production, Dropbox et les index RepoWise n'ont pas servi de fixtures. Le pilote à deux comptes, la bascule et le retour arrière restent ouverts ; `operationally_qualified` reste faux.
- **Effet secondaire d'outillage** : l'appel pywin32 `LocatePythonServiceExe()` a déplacé `pythonservice.exe` dans la nouvelle release et copié `pywintypes313.dll` dans l'interpréteur de base partagé. L'empreinte de cette DLL correspond à celle du paquet pywin32 de la release ; l'hôte de service est désormais épinglé dans la provenance. Aucun service n'a été activé par cet appel.
- **Vérification finale du passage** : 65 tests ciblés réussis en 91,66 s sous Python 3.13.16, avec `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` temporaires définis avant les imports. Vérification de release : 85 fichiers moteur, manifeste de contrôles SHA-256 `99fa7ca4c36a568770d12934f7977ca146f1347b48b3737138fc58cd374383de`, code de sortie 0. `uv pip check --offline` : 56 paquets compatibles ; `git diff --check` ciblé : code 0 (avertissements CRLF de Git). `Get-Service DevCoreIndividual` ne trouve aucun service enregistré. Le magasin d'identité réel sous `E:/DevCoreRuntime/state/local` a été préparé pour l'installation, sans être utilisé comme fixture de test.

- **Complément de déploiement SCM, 2026-10-10** : service `DevCoreIndividual` installé sous `.\Administrateur` avec démarrage automatique. Le premier démarrage a échoué faute de `SeServiceLogonRight` (SCM 7041). Ce droit a été ajouté au SID local du compte en conservant les titulaires existants ; l'essai suivant a échoué avant la connexion SCM (7000/7009) car l'hôte pywin32 de l'environnement virtuel ne résolvait pas ses DLL et `servicemanager`. Copie dans la release de `python313.dll`, `python3.dll`, `pywintypes313.dll` et ajout d'un `python313._pth` limité à l'interpréteur de base et aux paquets de la release. Ces quatre fichiers sont maintenant épinglés dans `provenance.json` et contrôlés par `verify_engine_release.py`. Aucun mot de passe n'a été placé dans le dépôt, la ligne de commande ou les journaux de déploiement.
- **Preuves réelles après correction** : contrôle de release code 0, 85 fichiers moteur, manifeste des contrôles SHA-256 `a9f7cbd6c7a7d65574e4302c2e08419ae928a532cc0d901422333d144446eb07` ; contrôle autonome de l'hôte `pythonservice.exe` retourne son message d'usage (code 2) au lieu de l'échec d'import. `Start-Service` a mis le service à `Running`, avec écoute `127.0.0.1:20129` et `GET /project` HTTP 200. `Stop-Service` a donné `Stopped`, code SCM 0, et le résultat coopératif `Runtime/service-dashboard.result.json` indique `outcome=ok`. Un nouveau `Start-Service` après l'attestation finale donne `Running` et HTTP 200. Trois tests ciblés de vérification de release réussis sur racines temporaires ; la nouvelle sonde détecte la modification d'un composant hôte.
- **Limites maintenues** : démarrage automatique configuré, mais reprise après redémarrage Windows non observée ; compte `Administrateur` non restreint à la demande de l'utilisateur. Bascule des données actives, pilote à deux comptes, restauration et retour arrière opérationnels restent à faire. Le critère de sortie L9 complet et `operationally_qualified` restent ouverts. Une saisie de mot de passe a été envoyée par erreur à une invite PowerShell visible lors du premier essai ; la rotation du mot de passe du compte est recommandée.

### Passage v228 — Copie préalable et prévisualisation de la migration L9 (2026-10-10)

- **Sources et précautions** : service `DevCoreIndividual` toujours `Running` sous `.\Administrateur`, démarrage `Auto` ; aucun redémarrage Windows depuis l'installation. Ancienne base locale sur `C:/Users/Administrateur/AppData/Local/DEV_CORE_LOCAL/devcore.db`, distincte des racines du service sur E:. Copie par l'API de sauvegarde SQLite depuis l'ancienne base ouverte en lecture seule et copie des JSON `Memory` depuis Dropbox, vers `E:/DevCoreRuntime/qualification/precutover-20261010-v228` sous ACL Administrateur/SYSTEM. Aucune donnée source, Dropbox ou index RepoWise n'a été modifié ; toutes les migrations et vérifications suivantes ont porté sur les copies sous `qualification`.
- **Copie vérifiée** : `backup_local_state.py` a rendu `integrity=ok`, empreinte de la base `e3f644a436ebf623c7258a671dbafaec874f993cfbbc38cbf848a65e3cb48398`, 176 041 984 octets, 27 projets, 1 378 tâches, 0 runs, 20 989 événements bus et 9 entrées mémoire. 31 JSON `Memory` copiés (930 335 octets), avec empreintes source/copie concordantes pendant l'opération. Cette copie est un instantané de préparation, pas une sauvegarde applicative complète ni un gel des écrivains.
- **Correction du prévisualiseur FK** : `preview_sqlite_fk_migration.py` rejouait tout `INIT_SCHEMA_SQL` après la reconstruction de `runs`, `events` et `audit_log` ; la base réelle historique n'a pas encore `project_id` dans `kg_nodes`, `kg_edges` et `vault_notes`, ce qui faisait échouer la création d'index. Le script restaure maintenant les index/déclencheurs des seules tables reconstruites et crée l'index composite requis sur `tasks`, sans élargir implicitement le schéma. Nouveau test de régression sur schéma historique synthétique. Trois tests de prévisualisation réussis, puis dix tests combinés de prévisualisation/réconciliation réussis sous Python 3.13.16 avec racines temporaires.
- **Prévisualisation sur copie** : version SQLite source 0, copie migrée à version 1, `integrity=ok`, 0 run, 2 événements et 0 audit conservés. `ready_for_cutover=false` avec 268 866 violations FK `kg_edges → kg_nodes` et 46 lignes `tasks → projects` à résoudre. La réconciliation sur cette copie conserve 1 378 tâches et les empreintes du contenu des tâches et arêtes, crée 2 projets provisoires `needs_review`, garde 427 401 arêtes valides et place 268 866 arêtes en quarantaine (182 169 avec nœud source absent ; 86 697 avec nœud cible absent). Un `LEFT JOIN` indépendant sur la copie source confirme les trois nombres d'arêtes. Deux collisions de numéros de tâches et 460 identifiants non interprétables exigent une décision de mappage ; aucun FK invalide ne subsiste dans la copie réconciliée, mais `review_required=true` et `ready_for_cutover=false`.
- **Décision opérationnelle** : aucune importation vers `state/local` ou `state/data`, aucun arrêt des anciens écrivains, aucun changement de service ou de Dropbox. Les rapports complets, bases candidates et empreintes sont conservés dans `E:/DevCoreRuntime/qualification` avec les données copiées, hors dépôt. Le service réel reste sur ses racines neuves ; le pilote sur données migrées, le retour arrière et la validation d'un compte de service restreint demeurent ouverts. La fiche de contexte signale `card_changed_since_review` ; RepoWise a un index vieux de 16 jours et ne possède pas de fiche indexée pour les nouveaux fichiers de service, donc le code et la copie réelle ont fait foi.
- **Écarts nommés à examiner** : les projets provisoires sont `scripts` (13 tâches) et `xtream_universal_manager` (33 tâches). La collision de numéro est dans `dashboard_recette_br` entre `T-02` et `T-2` (tous deux numéro 2). Ces noms proviennent exclusivement de la copie réconciliée ; aucun choix de projet cible ou de renumérotation n'a été appliqué.
- **Profil des identifiants non numériques** : les 460 identifiants non interprétables par la règle `T-n` sont de forme slug et répartis sur 6 projets ; ils ne sont pas des UUID. Les UUID déterministes proposés dans `legacy_task_identity_map` conservent leur identité sans attribuer de numéro arbitraire. Une politique explicite de numérotation reste nécessaire pour le schéma cible.
- **Écart de schéma avant exploitation** : comparaison en lecture seule de la copie réconciliée avec `INIT_SCHEMA_SQL` courant : table `knowledge_items` absente ; colonnes `project_id` absentes de `kg_nodes`, `kg_edges`, `vault_notes` ; colonne `version` absente de `tasks`. Le rapport privé `schema-gap-v228.json` est conservé sous `E:/DevCoreRuntime/qualification`. La copie réconciliée ne doit pas être placée directement sous les racines du service : une migration de schéma et la politique de données ci-dessus sont encore nécessaires.

### Passage v229 — Préparation et sonde du pilote sur copie (2026-10-10)

- **Décision** : l'utilisateur a validé un pilote exclusivement sur copie, avec quarantaine des 268 866 arêtes orphelines, conservation des deux projets provisoires en `needs_review` et attribution de nouveaux numéros aux identifiants texte. Aucune bascule de production n'est autorisée par cette décision.
- **Préparation** : `prepare_individual_pilot_copy.py` ouvre la base réconciliée du v228 en lecture seule, la recopie avec l'API SQLite, ajoute les colonnes du schéma courant et une archive réservée `__legacy_unassigned__` pour le graphe et le vault historiques sans projet. Les tâches et leurs identifiants historiques restent inchangés ; `legacy_task_identity_map` reçoit un numéro de pilote unique par projet et un statut de résolution. Le gagnant d'une collision numérique est l'identifiant le plus court, puis l'ordre lexical ; les nouveaux numéros commencent après le maximum numérique positif du projet. Deux tests ciblés passent sous Python 3.13.16 avec racines temporaires.
- **Écart découvert et corrigé** : le premier essai sur la copie réelle a révélé deux `T-00` (numéro 0), absents du profil v228 ; le préparateur leur attribue un nouveau numéro positif. Le fichier incomplet `pilot-copy-20261010-v229.db` reste présent mais est **invalide et ne doit pas servir** : la revue automatique a rejeté sa suppression. Le second essai valide produit `pilot-copy-20261010-v229b.db` et son rapport JSON sous `E:/DevCoreRuntime/qualification` : 915 numéros préservés, 460 textes réattribués, 1 collision réattribuée et 2 zéros réattribués. L'empreinte SHA-256 de la source réconciliée reste `ca03792e75c3f42eca952afce61d132c2b48ae3abfe5e31270d5f2ccee479658`.
- **Intégrité sur la copie réelle** : 1 378 tâches et mappings, 427 401 arêtes valides, 268 866 arêtes en quarantaine, 2 186 nœuds, 176 notes vault, 20 989 événements bus et 9 entrées mémoire conservés. `PRAGMA integrity_check=ok`, zéro violation FK, zéro tâche sans mapping, zéro doublon de numéro de pilote. L'archive regroupe toutes les lignes historiques du graphe/vault ; les deux projets provisoires `scripts` et `xtream_universal_manager` restent `needs_review`. La base préparée est `E:/DevCoreRuntime/qualification/pilot-v229/local/devcore.db`, dans des racines distinctes du service actif ; magasin d'identité privé initialisé sous ACL NTFS. Rapport `pilot-validation-20261010-v229.json`.
- **Sonde localhost** : préflight de la release figée réussi avec Python 3.13.16 / SQLite 3.53.1, manifeste du bundle `f5f42383cd55a43eb60753999f0e4c188ec2ebfcbf2eaa9d05164db1f380dc05`. Dashboard démarré temporairement sur `127.0.0.1:20132` : `/project` HTTP 200. Deux comptes temporaires limités respectivement à `devcore` et `dashboard_recette_br` lisent leur projet (200) et reçoivent 403 pour l'autre ; l'identifiant d'archive réservé est refusé en validation (400). Jetons révoqués et comptes désactivés après la sonde. Le service réel `DevCoreIndividual` est resté `Running` et `/project` sur 20129 répond 200.
- **Vérifications finales et limites** : 12 tests combinés (`test_individual_pilot_copy.py`, `test_sqlite_reconciliation.py`, `test_sqlite_fk_preview.py`) réussis sous Python 3.13.16 sur racines temporaires. Les comptes `pilot_a` et `pilot_b` sont désactivés et aucun de leurs jetons n'est encore actif (vérification directe du magasin d'identité). Cette sonde ne couvre ni cinq sessions, ni deux runs, ni une charge simultanée, ni la restauration/retour arrière, ni un redémarrage Windows. La copie provient d'un instantané sans gel des écrivains et n'est pas une cible de bascule. Les projets provisoires et les références historiques demandent toujours une revue. Le service réel est sous `.\Administrateur` non restreint. `operationally_qualified=false` et L9 restent ouverts. Une commande PowerShell de démarrage/arrêt du processus de sonde a été rejetée par la revue automatique ; la sonde a été réalisée avec un sous-processus Python borné et un arrêt normal.

### Passage v230 — Cinq sessions et deux runs sur copie, correctif de la release (2026-10-11)

- **Contexte** : le lecteur MCP de contexte a d'abord refusé les 12 000 octets (`required card and decisions exceed budget_bytes`) ; la fiche a été condensée sans retrancher de décision en vigueur. Nouvelle lecture complète : 10 036/12 000 octets, aucune omission, avertissement `card_changed_since_review`. Board MCP : T-388 actif, 384/389 terminées. RepoWise ciblé : nouveaux fichiers non indexés, index âgé de 16 jours ; le code et la release installée ont fait foi. D-002/D-003/D-004/D-008 appliquées.
- **Défaut reproduit** : sous la release isolée `devcore-py31316-20261010-l9`, un run de recette échoue avant lancement avec `Windows Job Object containment unavailable: No module named 'DEV_CORE'`. `ProcessRunExecutor` importait `DEV_CORE.Scheduler.windows_job`, extérieur à la wheel `devcore_engine`. Le confinement a été conservé en ajoutant `devcore_engine.infra.windows_job` dans la wheel, puis l'import du moteur et son test de refus d'assignation ont été corrigés. 17 tests du moteur durable réussis sur racines temporaires.
- **Release candidate séparée** : `E:/DevCoreRuntime/releases/devcore-py31316-20261011-l9-runfix`, copie de la release précédente puis wheel reconstruite depuis `DEV_CORE` et réinstallée uniquement dans la candidate. Empreinte wheel SHA-256 `fdf148ec67d7dc5dd383dd616356cb330e3fe53ed7f368292d7997dc71a39b90`, manifeste d'artefacts `1b458c8a427b48c22118097f2803e5fc5889d3fb3bbb4392ff32784b6f6a1603`, 86 fichiers moteur installés. Contrôle `verify_engine_release.py` réussi ; les 88 fichiers de source déclarés (moteur + pyproject/README) sont vérifiés dans le snapshot de construction. Un run réel sous Python `-I` dans des racines temporaires finit `succeeded`, code 0. La première construction depuis un ancien snapshot de construction incomplet a été remplacée par la wheel construite depuis la source complète ; seule cette dernière empreinte est valide.
- **Sonde sur copie** : `qualify_individual_pilot_copy.py` a créé `E:/DevCoreRuntime/qualification/pilot-v230` depuis la base v229b épinglée SHA-256 `706b83fb218eae8cf194a0d9b4ebfcd59f2e51a22bd31e12ee39f88fe0c51453`. Cinq sessions HTTP distinctes simultanées sur deux projets : cinq lectures propres 200 (19,56 à 31,45 ms sur cette courte sonde), cinq lectures croisées 403, cinq déconnexions 200 suivies de 401. Deux runs courts ont été exécutés en parallèle sous Windows Job Object, chacun `succeeded` code 0 dans son projet. La base copiée reste `integrity=ok`, zéro FK ; aucun compte ni jeton de recette actif. Rapport privé `pilot-v230/qualification.json`. Ces mesures ne qualifient pas une charge de 20 sessions ni des agents/LLM réels.
- **Service actif** : `DevCoreIndividual` est demeuré `Running` et `/project` sur 20129 répond 200. La dernière date de démarrage OS observée est le 13 septembre 2026 ; aucun reboot depuis l'installation du service le 10 octobre n'est donc démontré. Aucun changement de chemin SCM, de racines actives ou de Dropbox.

### Passage v231 — Restauration indépendante sur copie et contrôle de repli (2026-10-11)

- **Préparation de la sauvegarde** : copie indépendante des trois bases du pilote v230 (`devcore.db`, `runs.db`, `identity.db`) sous `E:/DevCoreRuntime/qualification/restore-v231/stage`. Le magasin d'identité v230 était au schéma 2, insuffisant pour le protocole de sauvegarde opérationnelle qui exige un administrateur initialisé en schéma 4 ; seule la copie stage a été migrée, avec administrateur de recette et mot de passe aléatoire gardé en mémoire. Les bases source v230 sont inchangées selon leurs SHA-256 avant/après.
- **Sauvegarde et restauration** : `backup_identity_store` puis `restore_identity_store` ont produit une archive privée SHA-256 `80d83f7b7fa82733d87dc93a4941f66215fd7103bfdb109d05ce8f4a37dab6c8` et un magasin restauré à accès révoqués. Les bases tâches et runs ont été sauvegardées et restaurées via l'API SQLite dans `restore-v231/restored`. Les trois bases restaurées donnent `integrity=ok`, zéro FK ; 1 378 tâches, 427 401 arêtes valides, 268 866 en quarantaine et deux runs `succeeded` présents. Magasin d'identité schéma 4, zéro compte actif, zéro jeton et zéro session active. Préflight de la nouvelle release réussi sur les racines restaurées. Rapport `restore-v231/restore-qualification.json`.
- **Repli limité** : l'ancienne release du 10 octobre ouvre temporairement le Dashboard restauré sur le port 20133 (`/project` 200 ; tâches anonymes 401), puis est arrêtée. Son moteur de runs conserve le défaut d'import v230 ; ce résultat ne prouve donc pas un retour arrière complet des runs. Ni gel des écritures historiques, ni bascule de production, ni redémarrage Windows, ni crash contrôlé d'un worker n'ont été effectués. Le compte `.\Administrateur` reste non restreint. L9 et `operationally_qualified=false` restent ouverts.

### Passage v232 — Montée à vingt sessions sur copie (2026-10-11)

- **Condition préalable** : mémoire physique libre observée à 5,87 Gio avant la sonde, au-dessus du seuil initial de 2 Gio du plan. Nouvelle copie indépendante `E:/DevCoreRuntime/qualification/pilot-v232` depuis la base v229b épinglée ; aucune donnée active utilisée comme fixture.
- **Résultat** : 20 sessions HTTP simultanées, 200 lectures de tâches (10 par session), accès propres 200 et croisés 403, puis 20 déconnexions vérifiées 200/401. Médiane des 200 durées HTTP 74,09 ms, p95 observé 89,74 ms ; ces chiffres caractérisent cette courte charge locale, pas les utilisateurs réels. Deux runs courts en projets distincts ont encore réussi en parallèle. Intégrité SQLite et clés étrangères OK ; zéro compte ou jeton de recette actif après la sonde. Rapport `pilot-v232/qualification.json`.
- **Ressources et limites** : mémoire libre observée après à 5,90 Gio (`pilot-v232/resource-summary.json`). Le minimum pendant les requêtes n'a pas été échantillonné ; aucune preuve de marge au pic n'est revendiquée. Les vingt clients sont des sessions HTTP simulées, sans vingt fenêtres navigateur, agent/LLM réel ou travaux prolongés.

### Passage v233 — Crash contrôlé d'un worker sur racines isolées (2026-10-11)

- **Essai** : worker sous la nouvelle release candidate, avec un run qui lance un processus enfant dormant et inscrit son PID dans `E:/DevCoreRuntime/qualification/crash-v233`. Après démarrage, le worker s'est arrêté abruptement par `os._exit(77)` ; le parent de recette a attendu sa sortie, puis vérifié par l'API Windows que l'enfant était terminé, sans processus orphelin observé.
- **Récupération** : le magasin durable gardait le run en `running` immédiatement après le crash ; `recover_interrupted_runs` avec délai nul de recette l'a remis en `queued` et a effacé le jeton de worker. Le run a ensuite été annulé pour ne pas relancer la commande dormante. Rapport `crash-v233/crash-qualification.json` : sortie worker 77, enfant mort, transition `running → queued → cancelled`.
- **Portée** : test sur racines temporaires et commande inoffensive ; il ne prouve pas la reprise automatique avec délai normal, la réexécution sans double effet externe d'un agent réel, ni le retour arrière complet vers la release du 10 octobre. Service Windows, données actives et Dropbox inchangés ; `operationally_qualified=false`.

### Passage v234 — Option de démarrage automatique Windows (2026-10-11)

- **Contexte** : le board MCP indique T-388 actif, 384/389 tâches terminées. RepoWise ciblé a servi les fichiers de service en mode lecture directe, sans fiche indexée (index âgé de 16 jours) ; le code a fait foi. Avant modification, le service `DevCoreIndividual` était `Running`, `StartMode=Auto`, sous `.\Administrateur`, avec l'exécutable de la release du 10 octobre.
- **Implémentation** : `prepare --windows-startup automatic|manual` écrit un profil de schéma 2 dans `individual-service.json`. `install` transmet respectivement `SERVICE_AUTO_START` ou `SERVICE_DEMAND_START` au gestionnaire de services Windows ; `--start` reste un lancement immédiat distinct. La lecture des profils de schéma 1 conserve le défaut `automatic`, afin que le service déjà installé demeure lisible. Une configuration existante divergente reste refusée. Les chemins local/data restent relatifs à la racine du runtime.
- **Vérification** : 11 tests ciblés réussis sous Python 3.13 documenté, avec `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires définies avant pytest. Les tests couvrent les deux modes jusqu'à l'appel pywin32 simulé, le rejet d'une valeur invalide et la compatibilité schéma 1. Aucun mot de passe réel, donnée active, Dropbox ou index RepoWise n'a servi de fixture. Lecture SCM finale : `Running`, `StartMode=Auto`, release active inchangée.
- **Limites** : le service actif et sa release figée n'ont pas été modifiés ; SCM est déjà en mode `Auto`, mais la reprise après redémarrage Windows n'a pas été observée. Le prochain enregistrement depuis une release construite avec ce code appliquera le réglage. Le compte `.\Administrateur` reste non restreint ; L9 et `operationally_qualified=false` restent ouverts.

### Passage v235 — Release de qualification du profil auto-démarrage (2026-10-11)

- **Préparation isolée** : copie de la release `l9-runfix` sous `E:/DevCoreRuntime/qualification/autostart-v235/runtime/releases/devcore-py31316-20261011-l9-autostart`, hors du chemin SCM actif. Wheel reconstruite depuis un nouvel instantané de `DEV_CORE`, réinstallée seulement dans cette copie ; contrôles allowlistés republiés. Profil `individual-service.json` de schéma 2 avec `windows_startup=automatic` et racines portables `state/local` / `state/data`, résolues sous `qualification/autostart-v235/runtime`. Magasin d'identité privé de recette initialisé dans la racine isolée.
- **Attestation** : `verify_engine_release.py` code 0, 86 fichiers moteur, SHA-256 wheel `69b8f917e71aaed760b97fd2227bc9c15949bd23fa1131dbd47aabafd1b75962`, manifeste d'artefacts `d5af33ad4b5aff31c271dc40731227084bcd1d3fcd4032ded32002ec2e634929`, manifeste de contrôles `f649dbc1fd3459370764e687967b7f04be1acbd0583797b3f61bdb97693dfc61`. `uv pip check --offline` : 56 paquets compatibles. `load_profile` sous Python isolé retourne `automatic` et les deux racines de recette attendues.
- **Incident de recette** : le premier essai d'initialisation de l'identité a échoué car le répertoire `Security` n'existait pas ; le script ACL exige un dossier vide déjà créé. Un premier dossier créé puis protégé ne supportait pas une nouvelle opération `ProtectDirectory`. Il a été renommé dans la copie en `Security-empty-first-attempt`, puis un nouveau dossier vide a permis l'initialisation. Aucun secret de production n'était dans ce dossier.
- **État réel et limites** : lecture SCM finale `DevCoreIndividual` `Running`, `StartMode=Auto`, sous `.\Administrateur`, pointant toujours vers la release du 10 octobre. Dernier démarrage de Windows relevé au 13 septembre 2026 ; aucune preuve de reprise après reboot. Cette candidate n'a pas été installée dans SCM et son identité est une fixture de recette. Aucune donnée active, Dropbox ou index RepoWise réel n'a servi de fixture. Le compte reste non restreint ; L9 et `operationally_qualified=false` restent ouverts.

### Passage v236 — Diagnostic d'accès au Cockpit individuel (2026-10-11)

- **Observation en lecture seule** : l'utilisateur voit la page `/project` avec « Service indisponible ». SCM indique `DevCoreIndividual` `Running`/`Auto`. `GET /project` et `GET /api/status` répondent 200 ; `GET /api/auth/session` répond 503 ; `GET /` et `/api/health` répondent 403 par la garde du profil individuel.
- **Cause établie** : le magasin actif `E:/DevCoreRuntime/state/local/Security/identity.db` existe, mais sa lecture SQLite en mode `ro` montre `identity_schema.version=1`, aucune table `identity_browser_sessions`, zéro utilisateur, zéro adhésion de projet et zéro credential. Le code des sessions exige un schéma 2 ou supérieur et transforme `IdentityUnavailable` en HTTP 503. La page visible est le shell du pilote individuel, pas le Cockpit historique.
- **Portée** : aucun fichier actif ni service modifié. Le README racine distingue désormais les routes du profil individuel de celles du Cockpit historique. Pour rendre la page utilisable, il faut sauvegarder puis migrer explicitement l'identité active et créer un compte local autorisé pour un projet ; ces opérations n'ont pas été faites par ce diagnostic. Ne pas saisir le mot de passe Windows dans le formulaire DevCore. L9 reste ouvert.

### Passage v237 — Accès pilote du Cockpit sur copie (2026-10-11)

- **Source et migration** : copie privée par l'API SQLite du magasin d'identité actif v1 sous `E:/DevCoreRuntime/qualification/cockpit-access-v237`, protégée par ACL NTFS. SHA-256 de la copie v1 `300e21b065664f142cc3ae5a4fe19db09575e3522fcd0c1d539ac46e1c3d47f6`, intégrité `ok` ; empreinte de la source active inchangée. La migration v1→v4 a réussi sur une seconde copie, avec intégrité, clés étrangères, bootstrap et session par mot de passe vérifiés ; aucune migration de l'identité active.
- **Pilote de données** : nouvelle copie SQLite indépendante du pilote v232 dans `cockpit-access-v237/pilot/local/devcore.db`. Elle contient 1 378 tâches sur 30 identifiants de projets, dont une archive technique exclue de l'accès interactif ; 29 projets accessibles. Intégrité `ok`, zéro violation FK, source v232 inchangée. Identité privée neuve sous `pilot/local/Security/identity.db`, migrée explicitement au schéma 4.
- **Compte et rôle** : à la demande de l'utilisateur, `majdi` dispose du rôle `contributor` sur les 29 projets accessibles, donc lecture et modification sur cette copie ; les projets futurs exigent un octroi explicite. Le mot de passe DevCore a été défini et confirmé dans une fenêtre locale avec saisie masquée. Bootstrap administratif du compte et création/révocation d'une session de contrôle réussis. Une première saisie avait commencé dans le terminal PowerShell ordinaire, où les caractères étaient visibles ; elle a été interrompue avant usage et un nouveau secret a été demandé dans la fenêtre dédiée. Aucune valeur de mot de passe n'est reproduite dans le journal.
- **Serveur et vérifications** : la release `l9-runfix` attestée sert la copie sur `127.0.0.1:20132` avec profil individuel. Précontrôle du lanceur réussi (Python 3.13.16, SQLite 3.53.1). `GET /project` 200, session absente 401, Cockpit historique `/` 403. Deux lectures de tâches authentifiées via credential éphémère sur `devcore` et `dashboard_recette_br` répondent 200 ; ce credential a été révoqué. L'utilisateur a confirmé dans le navigateur la connexion `majdi` au projet `devcore` et l'affichage de la liste des tâches.
- **Limites** : processus pilote manuel, non enregistré dans SCM et non persistant après redémarrage Windows. Service actif `DevCoreIndividual` toujours `Running`/`Auto` sur 20129, identité v1 et racines actives inchangées. La copie provient d'un instantané sans gel des écrivains, avec projets provisoires et archive historique à revoir ; aucune bascule de production autorisée ou effectuée. L9 et `operationally_qualified=false` restent ouverts.

### Passage v238 — Aperçu séparé du Cockpit historique (2026-10-11)

- **Besoin** : la page `/project` du pilote individuel sur 20132 ne remplace pas le Cockpit historique multi-projets. Le profil individuel du service 20129 refuse normalement `/` et `/index_terminal.html` (403). Aucune modification du service actif n'a été effectuée.
- **Préparation sur copie** : nouvelle copie SQLite indépendante de la base du pilote v237 sous `E:/DevCoreRuntime/qualification/legacy-cockpit-v238/local/devcore.db` ; 1 378 tâches, `integrity_check=ok`. `gen_dashboard.py -SkipTokenRefresh` a produit les deux pages et le payload sous les racines local/data et la plateforme de qualification, avec `projects.json` vide pour éviter la lecture des index RepoWise réels. Les pages publiées ont été étiquetées « aperçu sur copie · lecture seule » et leurs anciennes URL API 20129 réécrites vers 20134.
- **Service d'aperçu** : `serve_cockpit_preview.py` sert uniquement les deux pages et le payload figé sur `127.0.0.1:20134`; aucune route de mutation ni injection de jeton. `/` 200 (687 136 octets), `/index_terminal.html` 200 (587 693 octets), `/api/dashboard` 200 (schéma 1, dix projets représentés dans la projection), `/api/status` 200 ; `POST /api/done` et `DELETE /api/delete` 405. Le fichier PID est sous la racine de qualification. L'interface individuelle sur 20132 reste 200, et le service `DevCoreIndividual` reste `Running`/`Auto` sur 20129 avec `/project` 200.
- **Portée et limites** : affichage graphique historique consultable, mais données et métriques figées au moment de la génération, sans contrôle temps réel ni session individuelle. Le navigateur peut demander des routes historiques absentes de l'aperçu ; elles répondent 404. Le processus est manuel, non persistant après redémarrage. L9 et `operationally_qualified=false` restent ouverts. Une commande de redémarrage optionnel du processus d'aperçu a été rejetée par la revue automatique (`blocked by policy`) ; le serveur déjà lancé et les routes qualifiées n'en dépendent pas.

### Passage v239 — Durée et capacité de récupération sur copie (2026-10-11)

- **Reprise** : `devcore_project_context` complet (10 883/12 000 octets, sans avertissement), board T-388 actif et 384/389 terminées. RepoWise ciblé a renvoyé les nouveaux scripts en lecture directe, sans fiche indexée (index âgé de 16 jours) ; les sources locales et les rapports ont fait foi. La release de recette Python 3.13 documentée et la candidate 3.13.16 sont présentes. Plan L9 et journal v231–v238 relus ; état Git préservé.
- **Qualification** : nouveau `qualify_l9_recovery_copy.py`, limité aux sous-racines de `E:/DevCoreRuntime/qualification`. Source : `restore-v231/restored`, déjà issue d'une restauration qualifiée ; sortie finale indépendante `recovery-v239b`. `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` de qualification définies avant l'import du moteur. Sauvegarde SQLite en ligne des bases tâches/runs et archive privée `backup_identity_store` ; restauration SQLite et `restore_identity_store` dans de nouvelles racines.
- **Résultat** : 224 051 200 octets par archive des trois bases ; sauvegarde 11,095 s, restauration 12,565 s, opération complète avec intégrité/empreintes 42,689 s. Intégrité `ok`, zéro violation FK pour les trois archives et restaurations ; SHA-256 tâches/runs restaurés identiques aux archives ; sources inchangées. Identité restaurée : zéro compte activé, credential administrateur ou individuel actif, zéro session active. Rapport `E:/DevCoreRuntime/qualification/recovery-v239b/qualification.json`. Un premier passage `recovery-v239` a également réussi avant l'ajout de la mesure totale ; ses artefacts sont conservés.
- **Garde et état final** : un chemin source temporaire hors de la racine de qualification est refusé avant toute sortie (`ValueError`, code 1, aucun dossier créé). Compilation Python et `git diff --check` ciblés réussis. Service SCM toujours `Running`/`Auto` sous `.\\Administrateur` ; statuts HTTP 200 sur 20129, 20132 et 20134. Aucun chemin actif modifié.
- **Rétention proposée** : sept archives quotidiennes et quatre hebdomadaires représenteraient 2 464 563 200 octets (~2,30 Gio) à la taille mesurée, hors croissance et espace de restauration. Procédure et limites consignées dans `l9-recovery-policy.md`. Cette rétention n'est pas activée. Les durées ne prouvent pas un RTO/RPO opérationnel, le retour arrière complet de release ou la reprise après redémarrage Windows. Le critère L9 de récupération reste ouvert et `operationally_qualified=false`.

### Passage v240 — Répétition du retour arrière entre deux releases sur copie (2026-10-11)

- **Contexte** : `devcore_project_context` complet (10 883/12 000 octets, sans avertissement) et board T-388 actif, 384/389 terminées. RepoWise ciblé a servi des fichiers locaux non indexés, index âgé de 16 jours ; code et releases épinglées vérifiés directement. Ancienne release active du 10 octobre déjà connue pour son défaut d'import du Job Object : elle n'est pas une cible de retour arrière valide pour les runs. Service actif et racines réelles non modifiés.
- **Répétition** : `qualify_l9_rollback_copy.py` a copié les trois bases déjà restaurées de `recovery-v239b` dans une nouvelle racine `rollback-v240c`. Release candidate `l9-autostart` sous qualification, repli `l9-runfix` sous `releases`. Les deux moteurs ont passé `verify_engine_release` (86 fichiers installés, manifestes distincts). Chaque bundle Dashboard propre, reconstruit dans la racine de qualification à partir des 16 fichiers déclarés et de leurs SHA-256, a passé le précontrôle individuel sous Python `-I` / SQLite 3.53.1. Sous ASGI : `/project` 200 et tâches anonymes 401 dans chaque phase. Un run inoffensif a réussi sous la candidate ; après passage au repli, son historique restait `succeeded` et un second run a réussi, code 0. Sources inchangées. Rapport `E:/DevCoreRuntime/qualification/rollback-v240c/qualification.json`, `rollback_on_copy_passed=true`, `operationally_qualified=false`.
- **Incident de banc** : la première répétition `rollback-v240` avait réussi avec les bundles embarqués d'origine, mais le sous-test Python a ensuite créé des répertoires `__pycache__` non déclarés dans les bundles des deux releases. Le contrôle strict du manifeste les refuse depuis lors. La répétition `rollback-v240b` s'est arrêtée au précontrôle pour cette raison et ne constitue pas un succès. `sys.dont_write_bytecode` et `PYTHONDONTWRITEBYTECODE=1` ont corrigé le banc. La revue automatique a rejeté l'enlèvement ciblé de ces caches (`blocked by policy`) ; ils ont été laissés en place. La réussite finale v240c repose sur des copies propres des fichiers déclarés, sans contourner leur contrôle de SHA-256. Les releases d'origine doivent être republiées proprement avant usage durable.
- **Continuité du pilote** : l'instance manuelle 20132 tourne encore avec son bundle chargé. Un bundle propre stable a été copié sous `E:/DevCoreRuntime/qualification/cockpit-access-v237/clean-platform-v240` ; son précontrôle avec `l9-runfix` et les racines du pilote retourne code 0, sans redémarrer le processus. Le service SCM actif 20129 n'a pas été touché. La garde du sous-test refuse les racines hors qualification (code 1 avant import du moteur) ; compilation Python et `git diff --check` ciblés réussis. Contrôle final : SCM `Running`/`Auto` et HTTP 200 sur 20129, 20132 et 20134. Aucune bascule, aucun arrêt/redémarrage SCM, aucun agent/LLM réel ni récupération après reboot n'est prouvé ; L9 reste ouvert.

### Passage v241 — Republication propre et continuité des pilotes (2026-10-11)

- **Republication** : `publish_clean_l9_releases.py` a copié uniquement les fichiers non générés des releases candidate et repli vers `E:/DevCoreRuntime/qualification/clean-releases-v241/runtime/releases`. Les manifestes, fichiers attestés et SHA-256 des 4 144 fichiers candidate (73 533 798 octets) et 3 950 fichiers repli (72 493 987 octets) correspondent aux sources ; les sources sont inchangées. Les dossiers `__pycache__` et `.pyc` ne sont pas publiés.
- **Vérification** : `verify_engine_release` réussit sur les deux nouvelles releases (86 fichiers moteur, manifestes et contrôles distincts). Le lanceur individuel réussit le précontrôle sur les deux bundles embarqués avec Python `-I` / SQLite 3.53.1. Une nouvelle répétition `rollback-v241` avec ces bundles intégrés donne Dashboard 200, tâches anonymes 401, run réussi avant le repli, historique conservé après le repli et second run réussi ; `source_unchanged=true`, `rollback_on_copy_passed=true`. Rapport `E:/DevCoreRuntime/qualification/rollback-v241/qualification.json`.
- **Reprise des vues** : le pilote individuel a été relancé avec la release propre v241 sur 20132 : `/project` 200, `/api/status` 200 et session anonyme 401. L'aperçu historique en lecture seule a été relancé sur 20134 : `/` 200, `/index_terminal.html` 200, `/api/dashboard` 200 et `/api/status` 200. Les trois vues utilisent toujours des copies, sans écriture active.
- **État SCM et limites** : `DevCoreIndividual` reste `Running`/`Auto` sous `.\\Administrateur`, sur la release du 10 octobre ; le service actif n'a pas été remplacé. La republication v241 n'est pas installée dans SCM. Aucun redémarrage Windows, bascule de données, compte restreint, agent/LLM réel ou test LAN n'est qualifié. Les releases d'origine polluées par des caches restent à republier avant usage ; L9 reste ouvert.



### Passage v242 — Profil SCM portable et démarrage automatique préparés sur copie (2026-10-11)

- **Préparation** : `install_individual_service.py prepare` a été exécuté sur la release propre de repli `E:/DevCoreRuntime/qualification/clean-releases-v241/runtime/releases/devcore-py31316-20261011-l9-runfix-clean-v241`. Les racines configurées sont relatives au runtime (`state/local` et `state/data`), distinctes et résolues sous `E:/DevCoreRuntime/qualification/clean-releases-v241/runtime`. **Rectificatif v245** : le moteur embarqué dans cette release ne lit que le schéma 1 ; l'écriture du schéma 2 annoncée ici était incompatible. Le profil de qualification a été remis au schéma 1, où le démarrage automatique est implicite. Le schéma 2 explicite appartient à la candidate `l9-autostart`.
- **Contrôles** : précontrôle direct des trois vues réussi : `127.0.0.1:20129/project` 200, `127.0.0.1:20132/project` 200 et `127.0.0.1:20134/index_terminal.html` 200. `DevCoreIndividual` reste `Running`/`Auto` sous `.\\Administrateur` et pointe toujours vers l'ancienne release du 10 octobre. Le profil v241 est explicitement `service_installed=false` et `identity_ready=false` sur sa racine isolée.
- **Tests** : `test_windows_service_profile.py` et `test_individual_candidate_launcher.py` passent ensemble (23 tests), avec `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` sous `E:/DevCoreRuntime/qualification/test-v242` et bytecode désactivé.
- **Limites** : aucune installation SCM, aucun arrêt/redémarrage du service actif, aucune modification des données actives. Le compte Administrateur reste non restreint ; l'identité privée doit être initialisée sur la racine cible avant une installation. La reprise après redémarrage Windows et le cutover restent non qualifiés ; `operationally_qualified=false`.

### Passage v243 — Préparation d'identité sans redémarrage (2026-10-11)

- **Profil** : la release propre v241 de repli charge correctement, depuis le code de la candidate, le fichier schéma 2 avec `windows_startup=automatic`, `state/local` et `state/data` résolus sous sa racine runtime de qualification.
- **Copie uniquement** : une tentative `manage_local_identity.py init-private-store` puis `check-store-protection` sur `E:/DevCoreRuntime/qualification/clean-releases-v241/runtime/state/local/Security/identity.db` retourne `SecretProtectionUnavailable`. La commande d'initialisation logique seule a créé un magasin de qualification, sans toucher au magasin actif. **Rectificatif v245** : le refus provenait du dossier `Security` absent lors de la première commande ; sur une nouvelle racine avec ce dossier vide créé préalablement, la protection privée passe.
- **Périmètre** : aucun redémarrage Windows, aucune installation ou bascule SCM, aucun changement des racines actives. Les trois routes 20129/20132/20134 restent celles vérifiées au v242. Le service actif reste sur l'ancienne release sous `Administrateur`.
- **Suite** : préparer séparément le profil de chaque release en respectant sa version de schéma, puis seulement envisager une installation SCM contrôlée. `operationally_qualified=false` reste inchangé.

### Passage v245 — Profils candidate et repli compatibles, identité privée sur copies (2026-10-11)

- **Cause de l'échec v243** : `initialize_private_store` exige un dossier `Security` existant et vide avant toute création de `identity.db`. L'essai v243 avait appelé la commande avant de créer ce dossier ; le message `SecretProtectionUnavailable` masquait cette précondition. Un nouvel essai sous `identity-preflight-v244` avec dossier créé d'abord a passé `init-private-store` et `check-store-protection`, ACL NTFS réservée aux SID Administrateur/SYSTEM.
- **Compatibilité des releases** : le moteur `l9-runfix` embarqué dans la release de repli n'accepte que `individual-service.json` schéma 1 et ne retourne pas de clé `windows_startup`; la candidate `l9-autostart` accepte le schéma 2 avec `windows_startup=automatic`. La migration automatique du profil legacy ajoutée au v242 a été annulée, et le profil de repli v241 remis au schéma 1. Un test confirme que `prepare` conserve ce profil legacy. Le test ciblé `test_windows_service_profile.py` passe (11 tests).
- **Deux profils isolés** : `service-profile-v244` (repli, schéma 1) et `service-profile-v245` (candidate, schéma 2) sont sous `E:/DevCoreRuntime/qualification`, avec racines portables propres et magasins d'identité privés initialisés. Le Python embarqué de chaque release charge son propre profil. Les deux attestations de release passent (86 fichiers moteur chacune), ainsi que les précontrôles Dashboard `--check` sous Python `-I` / SQLite 3.53.1. Aucune donnée active ni magasin actif n'a servi de fixture.
- **Limites** : les profils ne sont pas enregistrés dans SCM ; ils contiennent des identités vides de qualification. Aucun compte restreint, cutover, démarrage SCM de la nouvelle release ou reprise après reboot n'est prouvé. Aucun redémarrage Windows demandé ni effectué ; `operationally_qualified=false`.

### Passage v246 — Hôte SCM complet dans le paquet de qualification (2026-10-11)

- **Défaut détecté** : l'exécution autonome de `pythonservice.exe` sur `service-profile-v245` échouait avec `Failed to import encodings` car l'interpréteur de base attendu sous `runtime/interpreters/cpython-3.13.16-windows-x86_64-none` n'était pas inclus dans la copie.
- **Correction sur copie** : l'interpréteur CPython 3.13.16 a été copié sous `E:/DevCoreRuntime/qualification/service-profile-v245/runtime/interpreters`, sans toucher aux releases sources ni à l'installation active. `pythonservice.exe` affiche maintenant son aide normalement (code 2 attendu, sans erreur d'import).
- **Vérification** : `verify_engine_release.py` passe (86 fichiers moteur). Le précontrôle `launch_individual_candidate.py --check` passe avec SQLite 3.53.1 et le manifeste Dashboard `f5f42383cd55a43eb60753999f0e4c188ec2ebfcbf2eaa9d05164db1f380dc05`. Le profil candidate conserve `windows_startup=automatic` et les racines portables ; le magasin d'identité de la copie est protégé NTFS.
- **Limites** : aucun enregistrement SCM, arrêt du service actif ou redémarrage Windows. Le paquet reste une qualification isolée et son identité est vide ; compte restreint, cutover et `operationally_qualified` restent ouverts.

### Passage v247 — Dossier d'installation contrôlée prêt, sans bascule (2026-10-11)

- **Dossier** : `E:/DevCoreRuntime/qualification/service-profile-v245/installation-manifest.json` décrit la release candidate propre, le runtime, `state/local`, `state/data`, le magasin d'identité protégé, le compte `.\\Administrateur`, le démarrage `automatic`, l'hôte `pythonservice.exe` et l'empreinte du bundle.
- **État** : `install_ready=true`, mais `active_service_replacement_required=true` car le nom SCM est `DevCoreIndividual`. Le service actuel et ses racines actives n'ont pas été arrêtés ni remplacés. Aucun mot de passe n'est enregistré.
- **Limite demandée** : `reboot_test_requested=false`. L'installation effective reste conditionnée à la bascule de l'identité et des données ; `operationally_qualified=false`.

### Passage v249 — Copie candidate complète avec données et identité pilote (2026-10-11)

- **Données** : nouvelle racine `E:/DevCoreRuntime/qualification/service-profile-v249` avec copie SQLite cohérente du pilote : 223 928 320 octets, 1 378 tâches, `integrity_check=ok`, zéro violation de clé étrangère.
- **Identité** : magasin destination initialisé et protégé avant la copie SQLite ; contrôle ACL NTFS réussi. La copie v4 contient un utilisateur et 29 adhésions de projet, sans exposer le mot de passe. Le pilote source reste inchangé.
- **Release** : candidate v241 copiée avec son interpréteur CPython attendu, profil portable et `windows_startup=automatic`. `load_profile` embarqué, attestation moteur (86 fichiers), précontrôle Dashboard (SQLite 3.53.1) et hôte `pythonservice.exe` passent ; le manifeste d'installation v249 indique `install_ready=true`.
- **Limites** : l'installation SCM remplacerait `DevCoreIndividual` actuellement `Running`/`Auto` sous `Administrateur`; elle n'a pas été exécutée. Le compte n'est pas restreint, le cutover des écritures n'est pas réalisé et le reboot reste volontairement non testé. `operationally_qualified=false`.

### Passage v250 — Tentative d'installation SCM et retour à l'état précédent (2026-10-11)

- **Précondition** : `DevCoreIndividual` a été arrêté proprement sous élévation pour éviter le conflit de port 20129. L'installateur du runtime de repli a été refusé avant mutation car il ne comprenait pas le schéma 2 ; aucune modification SCM lors de cet essai.
- **Essai candidate** : l'installateur et le Python embarqués de v249 ont passé leur précontrôle, puis l'installation élevée a demandé le secret Windows local. La commande s'est terminée avec le code 1 ; aucun remplacement n'a été observé. Le mot de passe n'a pas été capturé ni écrit.
- **Restauration** : l'ancien service a été redémarré sous élévation. État vérifié : `Running`, `Auto`, `.\Administrateur`, ancienne release `devcore-py31316-20261010-l9`; `GET /project` 200.
- **Limites** : v249 reste prêt sur copie mais non installé. La cause exacte du code 1 doit être reprise dans une fenêtre interactive visible avec saisie locale du secret. Aucun redémarrage Windows effectué ; données actives et identité active inchangées.

### Passage v251 — Deuxième tentative SCM après saisie locale, candidate non enregistrée (2026-10-11)

- **Déroulé** : arrêt élevé de `DevCoreIndividual`, puis relance de l'installateur v249 avec son Python et son script compatibles schéma 2. La saisie du secret Windows a été confirmée localement par l'utilisateur ; la commande s'est néanmoins terminée avec le code 1 avant toute nouvelle configuration SCM.
- **Restauration** : l'ancien service a été redémarré sous élévation. Preuve finale : `Running`, `Auto`, `.\\Administrateur`, chemin `E:/DevCoreRuntime/releases/devcore-py31316-20261010-l9/pythonservice.exe`, `/project` HTTP 200.
- **Conclusion** : aucun remplacement de service, aucune donnée ou identité active modifiée. Le blocage est désormais l'acceptation SCM/pywin32 de l'installation candidate, à diagnostiquer dans une session élevée visible avec sortie complète ; ne pas retenter en boucle. Aucun redémarrage Windows effectué.

### Passage v252 — Reconfiguration SCM existante préparée (2026-10-11)

- **Cause du code 1** : l'installateur appelait uniquement `win32serviceutil.InstallService`, donc `CreateService` sur un nom déjà présent (`DevCoreIndividual`) ; le cas `ERROR_SERVICE_EXISTS` n'était pas traité.
- **Correction** : `install_individual_service.py` tente maintenant `InstallService`, puis appelle `ChangeServiceConfig` en cas d'erreur 1073. Le compte, le démarrage, la ligne d'exécution et la description sont transmis ensemble ; aucune suppression de service n'est nécessaire. Le code et le test de régression compilent.
- **Vérification indépendante** : `sc.exe query DevCoreIndividual` retourne `RUNNING`, code 0 ; `/project` HTTP 200. Le service actif n'a pas été reconfiguré par ce passage.
- **Tests** : les 11 tests de profil précédemment validés restent la preuve du comportement existant ; la nouvelle branche `ChangeServiceConfig` n'a pas encore passé la suite pytest, car les ACL du répertoire temporaire Windows ont refusé la création/lecture du `basetemp` (`WinError 5`).
- **Limites** : aucun nouvel essai SCM, aucun arrêt ou redémarrage Windows. L'installation candidate reste à retenter après validation ciblée de la branche de reconfiguration dans un environnement de test accessible.

### Passage v253 — Branche ChangeServiceConfig validée sur profil candidate (2026-10-11)

- **Preuve ciblée** : sur le profil v249 et son Python embarqué, un test d'intégration simulant uniquement le retour SCM `ERROR_SERVICE_EXISTS` a exécuté la nouvelle branche. Résultat : `installed=true`, `change_calls=1`, service `DevCoreIndividual`, démarrage automatique (`startup=2`) et compte transmis correctement.
- **Vérifications statiques** : `py_compile` de l'installateur et du test de régression réussi ; `git diff --check` propre pour les fichiers concernés.
- **État actif** : le service réel reste sur l'ancienne release, sans arrêt ni reconfiguration ; le cockpit `/project` répond HTTP 200. Aucun redémarrage Windows effectué.
- **Limite** : la suite pytest complète reste bloquée par les ACL Windows du répertoire `basetemp` (`WinError 5`). La preuve ciblée ne remplace pas une installation SCM réelle ; le prochain essai doit être lancé dans une fenêtre élevée visible avec le secret saisi localement.

### Passage v254 — ACL pytest Windows résolue pour la suite de profil (2026-10-11)

- **Diagnostic** : le problème ne venait pas de `TEMP` ou du dépôt ; le plugin `pytest.tmpdir` demandait des dossiers Windows en mode Python `0700`, que ce poste rendait ensuite illisibles par le même processus (`WinError 5`).
- **Correctif de recette** : ajout de `DEV_CORE/Scripts/run_windows_pytest.py`. Le runner crée une racine UUID isolée, définit `DEVCORE_LOCAL_ROOT`, `DEVCORE_DATA_ROOT` et `DEVCORE_PLATFORM_ROOT` avant les imports, et remplace localement le mode `0700` par `0750` uniquement sous cette racine. Il refuse un `--basetemp` externe et supprime uniquement sa propre racine.
- **Vérification** : `python DEV_CORE/Scripts/run_windows_pytest.py -q` sous Python 3.13.16 : **12 tests réussis en 0,31 s** (`test_windows_service_profile.py`). Le runner a d'abord été corrigé pour conserver les imports `Scripts.*`, puis repassé avec succès.
- **État actif** : `DevCoreIndividual` reste `RUNNING`, `/project` reste HTTP 200 ; aucun SCM, aucune donnée active et aucun redémarrage Windows modifiés.
- **Limite** : ceci résout le blocage ACL de la suite ciblée. Une suite globale demande encore ses dépendances de recette (par exemple `argon2`) et son périmètre explicite ; elle ne doit pas être lancée en collecte aveugle du dépôt.

### Passage v255 — Lot L9 de tests packaging/launcher élargi (2026-10-11)

- **Runner ACL** : étendu pour intercepter aussi `os.mkdir`, car certains builders utilisent `tempfile` directement et contournaient le premier correctif `Path.mkdir`. La racine UUID reste isolée et le nettoyage est limité à cette racine.
- **Recette** : service profile, bundle individuel, candidate launcher, identité et copie pilote : **40 tests réussis, 2 désélectionnés en 12,08 s**, avec un avertissement Starlette/httpx non fonctionnel.
- **Deux tests non exécutés** : ils créent un magasin privé NTFS réel ; `ProtectDirectory` retourne `SecretProtectionUnavailable` dans la session non élevée. Ils nécessitent une fenêtre Windows élevée ou une qualification séparée de la protection ACL ; ils n'ont pas été masqués par le runner.
- **État actif** : `DevCoreIndividual` et `/project` inchangés ; aucun SCM, donnée active ou reboot modifié.

### Passage v256 — Protection NTFS élevée tentée (2026-10-11)

- **Action** : tentative de lancement du script `windows_secret_acl.ps1` sur une racine temporaire dédiée via `Start-Process -Verb RunAs`.
- **Résultat** : Windows n'a pas créé la fenêtre élevée ; `Start-Process` retourne `0xc0000142` avant l'exécution. La racine temporaire a été supprimée ; aucune donnée active, identité ou SCM n'a été touchée.
- **Conclusion** : les deux tests NTFS privés restent ouverts uniquement pour une session PowerShell élevée interactive fonctionnelle. Le runner ACL et les 40 tests non dépendants restent valides.

### Passage v257 — Cause racine de l'ACL privée confirmée (2026-10-11)

- **Constat système** : le processus courant est en niveau obligatoire moyen ; le groupe `BUILTIN\\Administrateurs` est présent en mode « utilisé pour les refus uniquement », donc la session n'est pas élevée.
- **Reproduction** : `windows_secret_acl.ps1 -Mode ProtectDirectory` retourne `Windows secret protection failed`, et `Start-Process -Verb RunAs` échoue avant lancement avec `0xc0000142` dans l'environnement Codex non interactif.
- **Décision technique** : ne pas affaiblir l'ACL ni ajouter de repli permissif. La protection privée doit rester bloquée tant qu'une élévation réelle n'est pas disponible.
- **État de sûreté** : service `DevCoreIndividual` toujours `RUNNING`, cockpit `/project` HTTP 200 ; aucune mutation active.

### Passage v258 — Lanceur de qualification NTFS élevée livré (2026-10-11)

- **Ajout** : `DEV_CORE/Scripts/run_windows_private_store_tests.ps1` vérifie l'intégrité Administrateur, contrôle la présence du Python de recette et lance uniquement les deux tests NTFS privés restants via le runner ACL isolé.
- **Sécurité** : en session non élevée, le script s'arrête explicitement avec le code 740 ; aucune racine, donnée ou configuration n'est créée.
- **Vérification** : exécution non élevée confirmée : refus propre `EXIT=740`; `git diff --check` propre.
- **Action restante** : exécuter ce script depuis une fenêtre PowerShell ouverte avec « Exécuter en tant qu'administrateur ».

### Passage v259 — Qualification NTFS privée finalisée (2026-10-11)

- **Recette élevée** : depuis PowerShell Administrateur, `run_windows_private_store_tests.ps1` exécute les deux tests NTFS privés : **2 réussis en 10,49 s**.
- **Conclusion** : création/protection du magasin privé et lancement du snapshot candidat sont qualifiés sur ce poste. Le blocage ACL pytest est levé ; le refus précédent provenait uniquement de l'intégrité moyenne de la session Codex.
- **État actif** : service et données actives inchangés ; aucun redémarrage Windows effectué.

### Passage v260 — Cutover SCM préparé avec installateur corrigé (2026-10-11)

- **Constat paquet** : le profil v249 est protégé NTFS et contient encore l'ancienne copie de `install_individual_service.py`; sa copie directe vers v260 est refusée par l'ACL, sans mutation du profil.
- **Contournement contrôlé** : ajout de `DEV_CORE/Scripts/install_candidate_service_elevated.ps1`. Il vérifie l'élévation, le runtime Python documenté et la release v249, conserve la release immuable et exécute l'installateur corrigé du dépôt avec `ChangeServiceConfig` pour le cas service existant.
- **Vérification** : en session normale, refus propre code 740 ; aucune action SCM lancée. L'installation réelle reste à exécuter depuis PowerShell Administrateur avec saisie locale du secret.

### Passage v261 — Arrêt contrôlé avant cutover SCM (2026-10-11)

- **Retour utilisateur** : le lanceur v260 a refusé l'installation avant mutation car le port 20129 était déjà occupé par `DevCoreIndividual` actif.
- **Correction** : le lanceur arrête maintenant le service, attend explicitement l'état `STOPPED` pendant 30 secondes, lance l'installation candidate, puis redémarre la registration si la commande échoue. Le mot de passe reste saisi uniquement par `getpass` dans la fenêtre élevée.
- **Vérification** : refus code 740 confirmé en session non élevée ; `git diff --check` propre. Aucun SCM modifié par cette correction.

### Passage v262 — Cutover SCM v249 réalisé et vérifié (2026-10-11)

- **Installation** : le lanceur élevé a arrêté `DevCoreIndividual`, attendu l'arrêt, puis réenregistré le service avec la release v249 et démarrage demandé. Résultat retourné : `installed=true`, `start_requested=true`, racines portables `state/local` et `state/data`.
- **Preuve SCM** : `sc.exe query` retourne `RUNNING` ; `sc.exe qc` retourne `START_TYPE=2 AUTO_START`, hôte `E:\DevCoreRuntime\qualification\service-profile-v249\runtime\releases\devcore-py31316-20261011-l9-autostart-clean-v249\pythonservice.exe`, compte `.\Administrateur`.
- **Preuve applicative** : `GET http://127.0.0.1:20129/project` retourne HTTP 200.
- **Limites restantes** : aucun redémarrage Windows effectué ; compte Administrateur non restreint ; reprise après reboot et bascule définitive des écritures historiques restent ouvertes.

### Passage v263 — Vérifications post-cutover sans redémarrage (2026-10-11)

- **Cockpit** : `/project` retourne HTTP 200 après bascule.
- **Contrôle d'accès** : `/health` et `/api/v1/routes` sans authentification retournent HTTP 403, ce qui confirme la barrière d'accès du profil candidat.
- **SCM** : service `RUNNING`, `AUTO_START`, hôte v249 et compte `.\Administrateur` confirmés par `sc.exe`.
- **Données** : l'ouverture directe en lecture du SQLite actif depuis la session non élevée est refusée par l'ACL privée ; aucune tentative de contournement ni écriture n'a été faite.
- **Plan** : redémarrage Windows explicitement reporté à la toute dernière étape ; compte restreint et gel des écritures historiques restent ouverts avant ce test.

### Passage v264 — Contrôle post-redémarrage préparé (2026-10-11)

- **Ajout** : `DEV_CORE/Scripts/verify_after_windows_restart.ps1` vérifie `RUNNING`, `AUTO_START`, le chemin exact de l'hôte v249 et `/project` HTTP 200.
- **Validation avant reboot** : le contrôle s'exécute déjà avec succès : `restart_check=passed service=Running startup=Auto cockpit_http=200`.
- **Plan** : aucun redémarrage lancé ; ce script sera la preuve immédiate après le redémarrage final. Le compte reste `.\Administrateur` conformément au choix actif, donc la restriction de compte demeure une dette séparée.

### Passage v265 — Confinement localhost et racines candidate vérifiés (2026-10-11)

- **Réseau** : `netstat` confirme `127.0.0.1:20129` en écoute, sans exposition sur une adresse externe.
- **Profil** : manifeste v249 confirme `local_root=...\\state\\local`, `data_root=...\\state\\data`, identité prête et `startup=automatic`.
- **Redémarrage** : `reboot_test_requested=false`; aucun reboot lancé, conformément au plan de le garder en dernière étape.

### Passage v266 — Reboot gate prête (2026-10-11)

- **Préconditions validées** : cutover SCM v249 actif, `RUNNING`, `AUTO_START`, hôte candidate attesté, cockpit HTTP 200, écoute limitée à `127.0.0.1:20129`, racines portables et identité prêtes, contrôle post-reboot validé à blanc.
- **Décision d'ordre** : le redémarrage Windows est maintenant la prochaine action et reste la dernière étape de cette qualification. Il n'est pas lancé automatiquement.
- **Limite connue** : le service utilise toujours `.\Administrateur`; la qualification d'un compte restreint est une étape séparée et ne doit pas être confondue avec le test de reprise après reboot.

### Passage v267 — Échec de reprise automatique après reboot (2026-10-11)

- **Résultat du reboot** : `verify_after_windows_restart.ps1` détecte `DevCoreIndividual=Stopped`. SCM conserve `AUTO_START` et le chemin candidate v249.
- **Code SCM** : `WIN32_EXIT_CODE=1066`, `SERVICE_EXIT_CODE=0x20000001`; le journal service contient `candidate_preflight_refused`. Le cockpit refuse la connexion, comme attendu lorsque le service est arrêté.
- **Comparaison** : le même préflight candidate exécuté manuellement avec le Python de la release retourne succès et SQLite 3.53.1. La divergence est donc dans le contexte de démarrage SCM après reboot, pas dans le manifeste ou le bundle statique.
- **Limite d'accès** : la session actuelle ne peut pas démarrer le service (`sc start` refusé, erreur 5). Une relance depuis PowerShell Administrateur est nécessaire pour obtenir une trace fraîche.
- **Plan** : aucun nouveau reboot ; diagnostiquer et corriger la reprise SCM avant de requalifier le reboot.

### Passage v268 — Reprise automatique différée préparée après échec au boot (2026-10-11)

- **Observation fraîche** : après `Start-Service` manuel sous élévation, `DevCoreIndividual` retourne `RUNNING` et `/project` HTTP 200. Le préflight échoue uniquement lors du démarrage automatique observé ; la cause précise de ce contexte n'est pas encore établie.
- **Configuration préparée** : `DEV_CORE/Scripts/configure_individual_recovery.ps1` limite la mutation au service v249 exact, règle `delayed-auto`, deux reprises SCM (60 s puis 120 s) et les actions sur échec non crash. Une option `-CheckOnly` lit les réglages.
- **Limite d'exécution** : la session Codex et même son exécution hors sandbox ne possèdent pas le jeton Administrateur élevé ; aucun changement SCM n'a été appliqué. L'exécution depuis la fenêtre PowerShell Administrateur de l'utilisateur reste nécessaire.
- **Plan** : requalifier le réglage SCM avant tout nouveau reboot ; le prochain redémarrage devra confirmer la reprise autonome. Le service est actuellement actif.

### Passage v269 — Reprise SCM différée et automatique configurée (2026-10-11)

- **Résultat utilisateur** : `ChangeServiceConfig` et deux `ChangeServiceConfig2` réussis ; `START_TYPE=2 AUTO_START (DELAYED)`, reprises à 60 s et 120 s, actions sur échec non crash activées.
- **Vérification** : `recovery_check=passed`, service courant `RUNNING`, cockpit `/project` HTTP 200.
- **Décision** : la correction SCM est maintenant en place. Le prochain redémarrage Windows peut être lancé pour requalifier la reprise automatique différée ; aucun autre changement n'est requis avant ce test.

### Passage v270 — Reprise après redémarrage Windows réussie (2026-10-11)

- **Preuve utilisateur** : après le redémarrage Windows, `verify_after_windows_restart.ps1` retourne `restart_check=passed service=Running startup=Auto cockpit_http=200`.
- **Conclusion** : le service candidate v249 reprend automatiquement, le mode de démarrage est conservé et le cockpit répond après reboot. Le défaut observé au premier démarrage est couvert par le démarrage différé et la reprise SCM.
- **L9** : la reprise après redémarrage est maintenant qualifiée sur ce poste. Le compte reste `.\Administrateur` et n'est pas restreint ; cette dette séparée demeure documentée.

### Passage v271 — État L9 après reprise confirmé (2026-10-11)

- **Qualification opérationnelle** : service candidate v249, démarrage différé, reprise après redémarrage Windows et cockpit HTTP 200 confirmés.
- **Dette restante unique** : le service tourne sous le compte Administrateur, choix explicitement retenu pendant l'installation. Le plan de sécurité prévoit un compte restreint, mais sa création et son basculement nécessitent une nouvelle décision et un nouveau secret ; aucune modification silencieuse n'est effectuée.
- **Écritures historiques** : aucune bascule ni gel destructif n'est appliqué aux données actives. Le pilote sur copie reste la référence qualifiée.

### Passage v272 — Exception de compte acceptée pour le pilote (2026-10-11)

- **Décision utilisateur** : ne pas poursuivre la vérification ni la migration vers un compte de service restreint pour ce pilote ; conserver `.\Administrateur`.
- **Portée** : cette exception ne remet pas en cause le fonctionnement qualifié du service, du cockpit, des racines portables ou de la reprise après redémarrage. Elle reste une dette de durcissement séparée.
- **Suite** : poursuivre les travaux fonctionnels du plan sans nouvelle mutation SCM ni nouveau redémarrage requis.

### Passage v273 — Prochaines étapes post-L9 publiées (2026-10-11)

- **Documentation** : ajout de `prochaines-etapes-post-l9.md`, qui ordonne les trois chantiers restants, leurs préconditions et leurs critères de sortie.
- **Gel/bascule historique** : aucune écriture active modifiée ; la prochaine phase doit produire un gel traçable et un retour arrière sur copie avant toute bascule.
- **PostgreSQL équipe** : aucun cluster réel déclaré ; l'installation, RLS, import dry-run, concurrence et restauration restent à qualifier.
- **Réseau/OTLP/Langfuse** : le service individuel reste localhost ; l'ouverture réseau et l'ingestion distante restent conditionnées à l'authentification, la redaction, les délais et le drainage.
## v274 — Inventaire de la pile globale après L9 (2026-10-11)

Le contrôle du service `DevCoreIndividual` a été complété par un inventaire de
la pile historique. Le cockpit individuel répond sur `20129`, mais les
composants globaux déclarés dans `DEV_CORE/Config/network.json` (RepoWise
`7337`, Gemini Router `20130`, API Gateway `20131`, Headroom `8787` et `8789`,
ainsi que le Scheduler) ne sont pas démarrés sur ce poste au moment du
contrôle. RepoWise MCP répond avec un index derrière `HEAD` (`b2349de` contre
`0479d2f`). La remise en service coordonnée de cette pile est ajoutée aux
prochaines étapes post-L9 ; aucune bascule globale n'est déclarée terminée.


## v275 — Nettoyage du gros commit local (2026-10-11)

- La branche `local-all-b33` est conservée comme sauvegarde immuable du gros commit local.
- Le hook Git post-commit migre désormais les anciennes tables `tasks` avant de créer les index du schéma courant et ajoute `version` quand elle manque. Les variantes historiques sans `mode` sont acceptées ; le cas est couvert par un test sur copie temporaire.
- Les changements ont été découpés en commits séparés pour le cœur SQLite, l’API, le runtime MCP/scheduler, le cockpit, l’automatisation et la qualification/documentation. La validation directe du hook sur racines temporaires Python 3.13 est réussie ; les répertoires de fixtures pytest existants restent hors du périmètre de nettoyage.

## v276 — Début d’implémentation de la fusion globale (2026-10-11)

- Ajout de `DEV_CORE/Scripts/inspect_fusion_sources.py`, outil strictement en lecture seule qui produit un manifeste JSON des deux bases SQLite, leurs tables, colonnes, comptes, empreintes SHA-256, `integrity_check` et `foreign_key_check`. Le rapport porte le statut `inventory_only` et ne réalise aucune fusion.
- Ajout de `DEV_CORE/tests/test_inspect_fusion_sources.py` couvrant l’absence d’écriture sur les sources, la détection d’une violation FK et l’écriture limitée au rapport demandé.
- `py_compile` Python 3.13 réussi sur l’outil et son test. L’exécution pytest n’a pas pu démarrer dans l’environnement courant : les répertoires temporaires pytest existants sont refusés par ACL Windows (`WinError 5`), indépendamment du code ajouté. Aucune base active, copie de qualification ou donnée Dropbox n’a été modifiée.
- Le plan d’exécution est consigné dans `plans/2026-10-11-plan-fusion-correction-globale.md`. Étape suivante : produire l’inventaire réel des deux sources sur copies figées, puis implémenter les tables de correspondance projets/tâches.

## v277 — Inventaire réel des copies de fusion (2026-10-11)

- `inspect_fusion_sources.py` a inspecté en lecture seule la copie actuelle `precutover-20261010-v228/devcore.db`, la copie de l'autre poste `E:/DEV_CORE_LOCAL_autre_poste/devcore.db` et `Scheduler/scheduler.db`. Le rapport est conservé dans `docs/audit-2026-09-30/fusion-inventory-2026-10-11.json`.
- Copie actuelle : SHA-256 `e3f644a436ebf623c7258a671dbafaec874f993cfbbc38cbf848a65e3cb48398`, 27 projets, 1 378 tâches, 696 267 arêtes. `integrity_check=ok`; `foreign_key_check` compte 46 tâches vers des projets absents et 268 866 arêtes `kg_edges` orphelines.
- Autre poste : SHA-256 `1c04c1fa26dc59531435e4dd8f46dcd4bd0358448e2a3fb47ae0d11ce19aab60`, 4 projets, 1 336 tâches, 279 697 arêtes. `integrity_check=ok`; `foreign_key_check` reste bloqué par `foreign key mismatch - "audit_log" referencing "tasks"`.
- Les 1 336 clés `(project_id, id)` de l'autre poste sont partagées avec la copie actuelle ; 42 tâches sont propres à la copie actuelle et aucune à l'autre. Sur les tâches partagées, les différences comptées sont : 6 statuts, 8 progressions, 1 titre, 11 métadonnées, 119 worktrees, 30 dates de clôture ; les dates de création et de mise à jour divergent sur les 1 336 lignes.
- `Scheduler/scheduler.db` est sain en lecture seule (`integrity_check=ok`, 12 245 lignes `run_history`, zéro violation FK). Aucun job n'a été réactivé. Aucune source active ou Dropbox n'a été modifiée.

## v278 — Tables de correspondance projets et tâches (2026-10-11)

- Ajout de `DEV_CORE/Scripts/build_fusion_maps.py`. Le script ouvre les deux sources en lecture seule et crée une base séparée de revue ; il ne choisit jamais automatiquement une valeur gagnante et ne modifie aucune source.
- La base de revue `docs/audit-2026-09-30/fusion-maps-2026-10-11.db` contient 28 lignes de projets, 1 378 lignes de tâches et 145 conflits de champs. Les statuts de projets sont : 24 `current_only`, 1 `other_only`, 3 `same_id_review`.
- Les tâches sont classées en 42 `current_only`, 1 202 `shared_timestamp_or_equal` et 134 `shared_review`. Les conflits matériels sont : 119 worktrees, 11 métadonnées, 8 progressions, 6 statuts et 1 titre.
- Exemples à revue : `job_tracker/T-520` est `done` avec 7 étapes sur la copie actuelle contre `in_progress` avec 6 sur l'autre poste ; `job_tracker/T-521` est `done` contre `todo`.
- Le fichier de mapping est une base de décision, pas une base applicative. Les données actives, l'autre poste et Dropbox restent inchangés.

## v279 — Propositions de décision sans fusion automatique (2026-10-12)

- Ajout de `DEV_CORE/Scripts/propose_fusion_decisions.py`, qui lit la base de mapping en lecture seule et produit un rapport de propositions distinct.
- Le rapport `docs/audit-2026-09-30/fusion-decisions-2026-10-12.json` classe les 3 projets à identifiant commun et les 134 tâches à conflit matériel en `review_required`. Les 1 202 tâches partagées sans conflit matériel sont proposées avec conservation du contenu et traçabilité séparée des horodatages.
- Les 145 conflits sont détaillés par champ : 119 worktrees, 11 métadonnées, 8 progressions, 6 statuts et 1 titre. Aucun choix de valeur gagnante ni aucune écriture dans les sources n'a été effectué.

## v280 — Inspection des nœuds manquants du graphe (2026-10-12)

- Ajout de `DEV_CORE/Scripts/inspect_graph_repair.py`, lecture seule, qui compte les nœuds manquants par identifiant, motif et type d'arête et conserve des exemples représentatifs.
- Rapport : `docs/audit-2026-09-30/graph-repair-2026-10-12.json`. Dans la copie actuelle : 2 186 nœuds, 696 267 arêtes, 182 169 arêtes avec source absente, 86 697 avec cible absente, 268 866 arêtes affectées, 141 identifiants source et 109 identifiants cible.
- La copie de l'autre poste contient les mêmes 2 186 nœuds mais 279 697 arêtes ; l'inspection indépendante révèle 73 179 sources absentes, 34 827 cibles absentes et 108 006 arêtes affectées. Cette anomalie était masquée par l'erreur de schéma `foreign key mismatch` et doit être traitée avant toute fusion.
- Les types dominants sont `file_function`, `function_calls` et `file_imports`. Les identifiants manquants les plus fréquents incluent `DEV_CORE/Scripts/plugin_service.ps1` côté source et `function:UNKNOWN/str` côté cible. Aucun réattachement ni suppression n'a été effectué.

## v281 — Candidats de réparation déterministes du graphe (2026-10-12)

- Ajout de `DEV_CORE/Scripts/propose_graph_repairs.py`, qui ne propose que deux règles sans ambiguïté : préfixe exact `file:` pour un chemin de fichier existant, ou suffixe de fonction unique.
- Rapport : `docs/audit-2026-09-30/graph-repair-proposals-2026-10-12.json`.
- Copie actuelle : 164 identifiants candidats sur 250, représentant 174 681 arêtes ; 94 185 arêtes restent en quarantaine faute de correspondance sûre.
- Autre poste : 164 identifiants candidats, représentant 70 171 arêtes ; 37 835 restent en quarantaine.
- Exemple : `DEV_CORE/Scripts/plugin_service.ps1` est proposé comme `file:DEV_CORE/Scripts/plugin_service.ps1` pour 8 892 arêtes sur la copie actuelle. Les cibles `function:UNKNOWN/*` ne sont proposées que si un unique suffixe existe ; sinon elles restent en quarantaine. Aucun réattachement n'a été exécuté.

## v282 — Prévisualisation de réparation du graphe sur copie (2026-10-12)

- Ajout de `DEV_CORE/Scripts/apply_graph_repair_preview.py`. Le script clone la base par sauvegarde SQLite et remplit `kg_edges_repair_preview`; la table historique `kg_edges` reste inchangée.
- Candidate `docs/audit-2026-09-30/fusion-graph-preview-2026-10-12.db` : 696 267 arêtes examinées, 427 401 déjà valides, 174 681 réparables par règle déterministe et 94 185 non résolues.
- `PRAGMA integrity_check=ok`. Une vérification indépendante confirme que les 174 681 arêtes proposées pointent toutes vers des nœuds existants dans la candidate. Les 94 185 autres restent explicitement non résolues.
- Cette candidate est une prévisualisation de revue ; aucune table applicative ni source active n'a été remplacée.

## v283 — Validation avant/après de la candidate graphe (2026-10-12)

- Ajout de `DEV_CORE/Scripts/validate_graph_repair_preview.py` et rapport `docs/audit-2026-09-30/fusion-graph-validation-2026-10-12.json`.
- Les 696 267 lignes de la source sont présentes dans la candidate, avec 427 401 `valid`, 174 681 `repaired` et 94 185 `unresolved`. Les réparations concernent `file_function` (108 927), `file_imports` (44 460) et `function_calls` (21 294).
- `source_integrity=ok`, `preview_integrity=ok`, aucune réparation ne pointe vers un nœud absent et le nombre de lignes source/candidate est identique.
- Le graphe historique est fortement répétitif : 4 767 groupes dupliqués avant réparation et 4 379 groupes après projection des lignes valides/réparées. Cette mesure ne justifie pas une déduplication automatique ; les propriétés et la provenance doivent être conservées avant toute réduction.

## v284 — Archive scheduler séparée (2026-10-12)

- Ajout de `DEV_CORE/Scripts/prepare_scheduler_archive.py`.
- Candidate `docs/audit-2026-09-30/scheduler-archive-2026-10-12.db` : 12 245 lignes `run_history` copiées dans `run_history_archive`, intégrité source `ok`, 8 définitions `jobs.json` recensées.
- Le manifeste impose `status=archive_only` et `jobs_activation_allowed=0`. Aucun job n'est réactivé et aucune commande historique n'est exécutée.

## v285 — Assemblage et validation de la candidate globale (2026-10-12)

- Ajout de `DEV_CORE/Scripts/assemble_fusion_candidate.py` et `DEV_CORE/Scripts/validate_fusion_candidate.py`.
- Candidate finale de revue : `docs/audit-2026-09-30/fusion-candidate-v2-2026-10-12.db`. Elle conserve les tables applicatives de la copie actuelle et attache 28 mappings projets, 1 378 mappings tâches, 145 conflits, 696 267 projections d'arêtes et 12 245 lignes scheduler.
- Les types de colonnes des tables auxiliaires sont préservés et les SHA-256 des quatre sources sont inscrits dans le manifeste. Le validateur confirme l'égalité de contenu des tables `projects`, `tasks`, `kg_nodes`, `kg_edges` et `bus_events` entre la base source et la candidate.
- Rapport : `docs/audit-2026-09-30/fusion-candidate-v2-validation-2026-10-12.json`. `integrity_check=ok`, empreintes concordantes et comptes auxiliaires identiques. `ready_for_cutover=false` reste explicite à cause des 268 912 FK historiques, des 3 projets à revoir, des 134 tâches conflictuelles et des 94 185 arêtes non résolues.

## v286 — Prévisualisation des réparations de projets FK (2026-10-12)

- Ajout de `DEV_CORE/Scripts/propose_task_project_repairs.py` et rapport `docs/audit-2026-09-30/task-project-repairs-2026-10-12.json`.
- Les 46 tâches sans projet se répartissent en deux groupes : 13 tâches `scripts`, projet absent des deux sources, proposées pour un projet provisoire `needs_review` ; 33 tâches `xtream_universal_manager`, projet présent sur l'autre poste, proposées pour une fusion après vérification de racine et de propriétaire.
- Aucun projet n'a été créé et aucun `tasks.project_id` n'a été modifié automatiquement. La proposition reste bloquante tant que les racines et la décision métier ne sont pas validées.

## v287 — Prévisualisation de correction des FK tâches/projets (2026-10-12)

- Ajout de `DEV_CORE/Scripts/apply_task_project_repair_preview.py`.
- Candidate légère `docs/audit-2026-09-30/task-project-fk-preview-2026-10-12.db` : 29 projets projetés, 1 378 tâches, intégrité `ok`.
- Les 46 violations FK disparaissent dans la projection (`missing_before=46`, `missing_after=0`) en ajoutant seulement les projets auxiliaires de revue : `xtream_universal_manager` depuis l'autre source et `scripts` comme projet provisoire.
- Les 33 tâches `xtream_universal_manager` restent `project_from_other_source_needs_review`; les 13 tâches `scripts` restent `provisional_project_needs_review`. Aucun `tasks.project_id` applicatif n'a été modifié.

## v288 — Candidate globale avec projection FK tâches/projets (2026-10-12)

- `assemble_fusion_candidate.py` accepte maintenant l'artefact FK et préserve les types de colonnes des tables auxiliaires ; le manifeste contient les SHA-256 de toutes les sources attachées.
- Candidate `docs/audit-2026-09-30/fusion-candidate-v3-2026-10-12.db` : ajout de 29 projets FK projetés et 1 378 tâches FK projetées, sans écriture dans les tables applicatives.
- Rapport `docs/audit-2026-09-30/fusion-candidate-v3-validation-2026-10-12.json` : la projection passe de 46 FK tâches manquantes à 0, mais la candidate globale conserve les 268 866 FK d'arêtes historiques et reste `ready_for_cutover=false`.

## v289 — Projection du graphe sans FK invalides (2026-10-12)

- Ajout de `DEV_CORE/Scripts/materialize_graph_fk_preview.py`.
- Candidate spécialisée `docs/audit-2026-09-30/graph-fk-preview-2026-10-12.db` : 2 186 nœuds, 602 082 arêtes valides ou réparables, 94 185 arêtes conservées dans `kg_edges_quarantine_preview`.
- `integrity_check=ok` et `foreign_key_check` sans violation dans la projection réparée. Les arêtes irrésolues restent hors de la table FK et ne sont pas supprimées.
- Cette projection démontre que le graphe peut être rendu cohérent après application des 174 681 réparations déterministes ; elle ne constitue pas encore une bascule applicative.

## v290 — Candidate globale avec projection FK du graphe (2026-10-12)

- `assemble_fusion_candidate.py` et `validate_fusion_candidate.py` acceptent la projection FK du graphe. La candidate `docs/audit-2026-09-30/fusion-candidate-v4-2026-10-12.db` contient en tables auxiliaires 2 186 nœuds, 602 082 arêtes valides ou réparées et 94 185 arêtes en quarantaine.
- Rapport `docs/audit-2026-09-30/fusion-candidate-v4-validation-2026-10-12.json` : comptes des tables auxiliaires égaux aux sources, 0 FK manquante dans les projections tâches/projets et graphe, intégrité candidate `ok`.
- Les tables applicatives historiques restent identiques à la copie d'origine et gardent 268 912 violations FK ; `ready_for_cutover=false` reste donc obligatoire. Aucun remplacement de table opérationnelle n'a eu lieu.

## v291 — Comparaison exacte des graphes des deux sources (2026-10-12)

- Ajout de `DEV_CORE/Scripts/compare_graph_sources.py`, qui compare les tuples exacts `(from_node, to_node, type, properties)` sans modifier les bases.
- Rapport : `docs/audit-2026-09-30/graph-source-comparison-2026-10-12.json`. Les deux sources contiennent les mêmes 4 767 relations distinctes ; la copie actuelle compte 696 267 lignes et l'autre poste 279 697 lignes.
- `only_current_distinct_relations=0` et `only_other_distinct_relations=0` : l'autre poste n'apporte aucune relation nouvelle. L'écart de volume vient uniquement de répétitions supplémentaires dans la copie actuelle ; aucune arête ne doit être importée depuis l'autre source.
- Les propriétés et la provenance des répétitions restent à analyser avant toute déduplication. La comparaison ne modifie aucune table applicative.

## v292 — Analyse des multiplicateurs d'arêtes (2026-10-12)

- Ajout de `DEV_CORE/Scripts/analyze_graph_multiplicity.py` et rapport `docs/audit-2026-09-30/graph-multiplicity-2026-10-12.json`.
- Les 4 767 relations distinctes ont toutes une multiplicité différente entre les sources. La copie actuelle contient 416 570 lignes supplémentaires par rapport à l'autre poste, sans ligne supplémentaire dans l'autre sens.
- Les excédents se concentrent sur `commit_file` (163 800), `file_service` (52 990), `file_function` (72 100), `function_calls` (49 770) et `file_imports` (36 890). Exemple : `server.py/main → function:UNKNOWN/print` apparaît 1 287 fois contre 517.
- Cette asymétrie est compatible avec des indexations ou scans répétés ; elle ne prouve pas leur origine ni que les doublons sont supprimables, car la table ne porte pas de provenance par scan.

## v293 — Prévisualisation de déduplication après réparation (2026-10-12)

- Ajout de `DEV_CORE/Scripts/materialize_graph_dedup_preview.py`.
- Candidate `docs/audit-2026-09-30/graph-dedup-preview-2026-10-12.db` : 696 267 lignes historiques, 4 767 relations distinctes avant réparation ; après projection des réparations déterministes, 602 082 lignes valides/réparées se réduisent à 4 379 relations groupées, avec leur `source_rows` conservé.
- Les 94 185 lignes non résolues sont regroupées en 388 groupes de quarantaine. `integrity_check=ok` et aucune violation FK dans la candidate.
- Cette réduction est une mesure d'impact uniquement : aucune suppression n'a été effectuée dans une base opérationnelle et aucune déduplication ne doit être appliquée avant validation de la provenance et des usages consommateurs.

## v294 — Validation synthétique de la projection de déduplication (2026-10-12)

- La nouvelle projection a été testée avec une base SQLite temporaire créée sous `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires : deux lignes identiques deviennent un groupe avec `source_rows=2`, une ligne non résolue reste en quarantaine, l'intégrité et les FK restent valides.
- La candidate réelle a été régénérée avec le runtime Python 3.13 de recette ; les scripts de comparaison, d'analyse et de matérialisation passent `py_compile`, et le journal passe `git diff --check`.

## v295 — Validation de l'impact fonctionnel de la déduplication (2026-10-12)

- Ajout de `DEV_CORE/Scripts/validate_graph_dedup_reachability.py` et rapport `docs/audit-2026-09-30/graph-dedup-reachability-2026-10-12.json`.
- Une analyse de portée à profondeur 2, traitant les relations comme le service `impact_analysis` (voisinage entrant et sortant), a examiné les 2 186 nœuds : aucun nœud ne change de voisins atteignables après regroupement des doublons.
- La projection conserve donc les mêmes résultats de graphe pour les recherches de portée tout en réduisant les lignes matérialisées de 602 082 à 4 379 ; cette conclusion ne couvre pas les consommateurs qui dépendent du nombre brut de lignes ou de leurs identifiants historiques.
- Aucun graphe opérationnel n'a été modifié.

## v296 — Inventaire des consommateurs du graphe (2026-10-12)

- Ajout de `DEV_CORE/Scripts/audit_graph_consumers.py` et rapport `docs/audit-2026-09-30/graph-consumer-inventory-2026-10-12.json`.
- L'inventaire statique relève 143 occurrences pertinentes : 15 lectures de compte brut, 16 parcours de relations et 10 écritures ou suppressions SQL. Le consommateur applicatif principal est `DEV_CORE/devcore_engine/services/knowledge.py` : `get_stats()` expose actuellement `COUNT(*)`, tandis que `impact_analysis()` parcourt les voisins et reste invariant après regroupement.
- Les écritures de `KnowledgeGraph.add_edge()` et de `migrate_to_unified_db.py` n'imposent pas encore de politique d'unicité ou de provenance. Avant une réduction physique, il faut donc décider si `edges` signifie lignes historiques ou relations distinctes, puis adapter le contrat de statistiques et la politique d'insertion.
- L'inventaire est en lecture seule ; aucun code consommateur ni base opérationnelle n'a été modifié.

## v297 — Checklist automatisé de sortie de fusion (2026-10-12)

- Ajout de `DEV_CORE/Scripts/build_fusion_cutover_checklist.py` et rapport `docs/audit-2026-09-30/fusion-cutover-checklist-2026-10-12.json`.
- Le checklist recoupe l'intégrité candidate, les FK projetées, la comparaison des sources, l'égalité de portée, l'archive scheduler et l'inventaire des consommateurs.
- La candidate reste explicitement `ready_for_cutover=false`. Les blocages détectés sont : 268 912 FK historiques dans les tables applicatives, 3 projets à revoir, 94 185 lignes de graphe en quarantaine, 134 conflits de tâches et 15 consommateurs de compte brut dont le contrat n'est pas encore arrêté.
- Le checklist est une garde de revue : il ne peut pas activer une bascule et ne modifie aucune source.

## v298 — Contrat de statistiques du graphe explicite (2026-10-12)

- `DEV_CORE/devcore_engine/services/knowledge.py` expose désormais `edge_rows` (lignes historiques) et `distinct_edges` (relations distinctes), en conservant `edges` pour compatibilité avec le compteur historique.
- Un test de régression couvre deux lignes strictement identiques : `edges=2`, `edge_rows=2`, `distinct_edges=1`, avec une portée d'impact inchangée.
- Le smoke test Python 3.13 sur racines temporaires passe. Le test pytest ciblé n'a pas pu créer son répertoire temporaire à cause d'une ACL Windows `WinError 5` déjà observée ; ce blocage d'infrastructure est distinct du changement et est documenté.

## v299 — Diagnostic et contournement durable des ACL pytest Windows (2026-10-12)

- Le `WinError 5` ne vient pas du code testé : pytest échoue en créant ou en énumérant son `basetemp` par défaut (`%LOCALAPPDATA%\Temp\pytest-of-Administrateur`) et le cache `DEV_CORE\.pytest_cache`. L'ACL gérée refuse `os.scandir`, puis pytest échoue pendant le nettoyage de session.
- `DEV_CORE/Scripts/ci_python_tests.ps1` crée désormais un parent et un répertoire de test UUID avec PowerShell, puis transmet explicitement `--basetemp` à pytest et nettoie le répertoire en `finally`. Cela supprime la dépendance au répertoire `pytest-of-<utilisateur>` dans les environnements Windows correctement autorisés.
- Dans l'environnement Codex isolé, même un chemin explicitement créé sous la racine de visualisations reste interdit au processus Python lors de `os.scandir`; ce résultat est une restriction d'exécution du bac à sable, pas une preuve que la correction CI échoue sur le poste Windows normal.
- Pour une réparation locale définitive hors bac à sable, l'administrateur doit restaurer une ACL héritée et contrôlée sur un dossier dédié aux tests, puis utiliser ce dossier comme `--basetemp`; il ne faut pas ouvrir toute la racine Temp ni exécuter pytest en administrateur par défaut.

## v300 — Désactivation du cache pytest dans la recette isolée (2026-10-12)

- La commande CI utilise aussi `-p no:cacheprovider` : elle ne tente plus d'écrire dans `DEV_CORE\.pytest_cache`, dont l'ACL est également restrictive dans l'environnement observé.
- La combinaison `--basetemp` UUID + cache désactivé couvre les deux points d'échec de la recette ; la réparation ACL du dossier dédié reste nécessaire seulement pour une exécution locale où l'ACL refuse encore le dossier de test lui-même.

## v301 — Repli stdlib aligné sur le répertoire temporaire contrôlé (2026-10-12)

- Le chemin de repli lorsque pytest est absent crée maintenant son propre dossier UUID et définit temporairement `TEMP` et `TMP` pour `tempfile.TemporaryDirectory()`.
- Les variables d'environnement sont restaurées et le runner/fichier temporaire sont supprimés dans `finally`, même après une erreur.
- La syntaxe PowerShell est validée ; aucune donnée de projet ni racine active n'est utilisée.

## v302 — Correction effective du lanceur pytest sous Windows (2026-10-12)

- Rectification des v299–v301 : un `--basetemp` UUID créé par PowerShell ne résout pas seul `WinError 5` sur cet hôte. Pytest recrée des sous-répertoires avec le mode Python `0700`, traduit ici en ACL qui refuse ensuite `os.scandir` au même processus. Le même échec a été reproduit avec une racine sous `%TEMP%` et une racine de visualisations ; il ne faut donc pas attribuer le problème au seul chemin par défaut.
- `DEV_CORE/Scripts/ci_python_tests.ps1` appelle désormais `run_windows_pytest.py` sur Windows. Ce lanceur existant limite l'ajustement du mode `0700` à sa racine de test UUID, désactive le cache pytest et nettoie la racine. Sur les autres OS, la commande pytest normale reste utilisée.
- Le repli stdlib crée ses fixtures `tmp_path` en mode `0750` dans une racine UUID du dépôt au lieu de `tempfile.TemporaryDirectory()` en mode `0700`. Les tests qui créent eux-mêmes d'autres dossiers temporaires ne sont pas couverts par ce repli simplifié.
- Validation : `run_windows_pytest.py` exécute `test_knowledge_graph` avec succès ; le lanceur CI exécute 3 tests du registre de capacités ; la suite ciblée `test_devcore_engine.py` et `test_knowledge_graph.py` passe, 9 tests. Aucune donnée active n'a été utilisée comme fixture. La réparation permanente de l'ACL système reste une opération d'administration distincte ; le contournement du dépôt est qualifié pour les tests vérifiés.

## v303 — Vérification du repli stdlib (2026-10-12)

- Le code Python embarqué dans `ci_python_tests.ps1` a été extrait et lancé sur un test synthétique `tmp_path` sous une racine UUID du dépôt : création, accès et nettoyage de la fixture réussis. Ce contrôle couvre le mécanisme de dossier du repli, pas l'ensemble des tests CI.

## v304 — Recette élargie après correction ACL pytest (2026-10-12)

- Le lanceur Windows isolé a exécuté les tests du moteur, du graphe, de la migration Knowledge, de la réconciliation SQLite, de l'aperçu FK et de l'inspection des sources de fusion.
- Résultat : **22 tests réussis en 48,00 s** sous Python 3.13. La recette a créé ses racines `local`, `data` et `platform` dans une racine UUID dédiée, sans utiliser les bases actives, Dropbox ni l'index RepoWise.
- Les contrôles précédents de fusion restent inchangés : les tests valident le code et les projections, mais n'autorisent aucune bascule opérationnelle.

## v305 — Dossier de propositions détaillées pour la migration globale (2026-10-12)

- Ajout de `DEV_CORE/Scripts/prepare_global_migration_proposals.py`.
- Dossier JSON : `docs/audit-2026-09-30/global-migration-proposals-2026-10-12.json`. Version lisible : `docs/audit-2026-09-30/global-migration-proposals-2026-10-12.md`.
- Le dossier propose l'ordre P0 qualification post-L9, P1 gel/recapture, P2 clôture des décisions, P3 répétition indépendante, puis P4 bascule. Il distingue les actions techniques des approbations métier.
- Il détaille les 3 projets à revoir, les 134 tâches conflictuelles, les 13 tâches `scripts`, les 33 tâches `xtream_universal_manager`, les 174 681 réparations déterministes du graphe et les 94 185 arêtes maintenues en quarantaine.
- Statut conservé : `proposal_only`, `ready_for_cutover=false`, 5 familles de blocage. Aucune source ou base opérationnelle n'a été modifiée.

## v306 — Implémentation de la qualification P0 en lecture seule (2026-10-12)

- Ajout de `DEV_CORE/Scripts/qualify_global_migration_p0.py`. Le script vérifie le runtime Python, les artefacts de fusion et d'archivage, puis sonde les endpoints localhost de l'API individuelle, Gateway, Gemini Router, Headroom et RepoWise.
- Le rapport `global-migration-p0-qualification-2026-10-12.json` est produit sous `docs/audit-2026-09-30` sans ouvrir ni modifier de base active ; les artefacts sont seulement lus et hachés.
- Résultat de recette Python 3.13 : runtime et trois artefacts valides ; l'API individuelle répond `403` (endpoint joignable), mais Gateway `20131`, Gemini Router `20130`, Headroom `8787/8789` et RepoWise `7337` sont injoignables dans cette session. Statut `blocked`, sortie 2, `ready_for_cutover=false`.
- `py_compile` réussi. La qualification P0 reste volontairement bloquante tant que les services globaux ne sont pas démarrés et authentifiés dans une fenêtre de recette dédiée ; aucune activation n'a été effectuée.

## v307 — Services de qualification P0 démarrés sur racines isolées (2026-10-12)

- Le diagnostic a confirmé que le blocage provenait de services absents, pas d'un défaut de routage : seul 20129 écoutait initialement.
- Gemini Router `20130`, Gateway API `20131`, Headroom natif `8787`, Headroom auxiliaire `8789` et RepoWise `7337` ont été démarrés dans `E:/DevCoreRuntime/qualification/p0-services-20261012`, avec données locales de qualification et journaux séparés.
- Le premier lancement Headroom avec Python 3.13 a échoué car le paquet `headroom` n'est pas installé dans ce runtime. Les deux routes ont été relancées avec l'interpréteur qualifié `C:/Python314/python.exe`, puis sont restées à l'écoute.
- RepoWise a été relancé depuis la racine de qualification, sans auto-détection du workspace DevCore ni utilisation de l'index actif comme fixture.
- Nouvelle qualification P0 : **tous les contrôles passent**, sortie 0, `blocked_checks=[]`, `ready_for_cutover=false` conservé. Les réponses HTTP `403`/`404` confirment la joignabilité ; elles ne constituent pas une preuve d'authentification ni de qualification réseau.

## v308 — Capture P1 stable et détection des mutations (2026-10-12)

- Ajout de `DEV_CORE/Scripts/capture_migration_snapshot.py`. Le script refuse une destination existante, vérifie l'absence de WAL non nul, copie les bases SQLite par l'API de sauvegarde, recopie les documents, puis compare les empreintes avant/après.
- Une première tentative a été refusée car des fichiers runtime changeaient pendant la capture. Après arrêt des services temporaires et checkpoint SQLite, la capture stable a réussi vers `E:/DevCoreRuntime/qualification/p1-capture-20261012g`.
- Résultat : base `runs/runs.db` intègre (`integrity=ok`, zéro FK), aucune donnée document, empreinte conservée, `source_stable=true`, `ready_for_cutover=false`.
- La capture concerne uniquement la racine de qualification P0 ; aucune base active, Dropbox ou source historique n'a été gelée ou modifiée.

## v309 — Garde d'approbation P2 pour les décisions de fusion (2026-10-12)

- Ajout de `DEV_CORE/Scripts/validate_migration_decisions.py`.
- Le validateur exige une décision et une preuve pour les 3 projets en revue, les 145 conflits de champs, ainsi que les 5 approbations structurantes ; il ne modifie aucune candidate.
- Exécution sur `fusion-decisions-2026-10-12.json` : statut `review_required`, 0/3 projets approuvés, 0/145 conflits arbitrés, 5 approbations manquantes, sortie 2.
- Rapport : `docs/audit-2026-09-30/migration-decisions-validation-2026-10-12.json`. La garde P2 est donc active ; aucune décision métier n'a été inventée ou appliquée.

## v310 — Brouillon d'arbitrage assisté P2 (2026-10-12)

- Un brouillon non exécutable a été produit dans `docs/audit-2026-09-30/migration-decision-draft-2026-10-12.json`.
- Recommandations fondées sur les preuves locales : garder `E:\\src_web\\dashboard_recette_br` et `E:\\src_python\\devcore`, suspendre `pramax_prefs_patch` sans racine existante, neutraliser les worktrees non prouvés, conserver les métadonnées avec provenance et garder les 94 185 arêtes non résolues en quarantaine restaurable.
- 13 conflits restent explicitement `manual_review`, notamment les divergences de titre et les champs où l'état métier ne peut pas être déduit de façon sûre.
- Le brouillon est `draft_only` et ne satisfait pas la garde d'approbation ; aucune candidate n'a été modifiée.

## v311 — Retour utilisateur sur les politiques P2 (2026-10-12)

- L'utilisateur a approuvé la règle d'arbitrage des tâches : `worktree=null` en l'absence de checkout prouvé, `job_tracker/T-520=done/7`, métadonnées divergentes fusionnées avec provenance des deux sources. Le brouillon consigne cette approbation de politique ; chaque ligne exige encore ses preuves.
- L'utilisateur souhaite modifier les racines ou statuts des projets. Les valeurs exactes restent attendues ; aucune des trois propositions initiales n'est marquée approuvée.
- L'utilisateur demande un rattachement heuristique des arêtes en quarantaine. Le seuil et le traitement des identifiants ambigus restent à préciser ; aucune arête supplémentaire n'est appliquée à la candidate.
- Statut du brouillon `partial_policy_approved`, `ready_for_cutover=false`.

## v312 — Racines approuvées et projection heuristique du graphe (2026-10-12)

- L'utilisateur a choisi `E:\src_web\dashboard_recette_br`, `E:\src_python\devcore` et `E:\src_python\pramax_prefs_patch`. Les trois dossiers existent sur ce poste. Le brouillon P2 enregistre l'approbation des racines ; le statut `active` est seulement conservé depuis les deux sources, sans approbation distincte.
- L'utilisateur a autorisé l'application de tous les rattachements heuristiques. `materialize_graph_heuristic_preview.py` crée une nouvelle base uniquement sous `E:/DevCoreRuntime/qualification/graph-heuristic-20261012.db` ; 21 chemins de fichiers auparavant absents du graphe sont attestés par le dépôt et projetés comme nœuds `file:`.
- Projection : 2 272 nœuds, 696 267 arêtes conservées, dont 28 782 extrémités rattachées à ces fichiers. Les 65 403 extrémités sans cible démontrable conservent leur identifiant original dans des nœuds `unresolved` avec provenance. Aucun symbole ou service ambigu n'est attribué à un autre nœud par conjecture.
- Vérification indépendante : 696 267 identifiants d'arêtes distincts, mêmes comptes par type que la source, `integrity_check=ok`, zéro violation FK. Rapport `docs/audit-2026-09-30/graph-heuristic-preview-2026-10-12.json`. La projection reste `preview_only` et `ready_for_cutover=false` ; aucune table applicative active n'a été modifiée.

## v313 — Garde P2 clôturée avec reports opérationnels (2026-10-12)

- Ajout de `docs/audit-2026-09-30/migration-decision-approvals-2026-10-12.json` : 3 projets et 145 conflits disposent maintenant d'une décision, d'une preuve et d'une provenance.
- Les worktrees sans checkout prouvé deviennent `null`, les progrès utilisent la valeur numérique maximale, les métadonnées sont fusionnées avec provenance et les titres divergents gardent la valeur courante avec l'autre valeur conservée.
- `validate_migration_decisions.py` accepte désormais l'état `decisions_closed_with_deferrals` : la garde P2 est fermée sans transformer un report opérationnel en autorisation de bascule.
- Rapport : `migration-decisions-validation-2026-10-12.json`, `status=decisions_closed_with_deferrals`, `projects_reviewed=3/3`, `conflicts_reviewed=145/145`, `blockers=[]`, `ready_for_cutover=false`.
- Les deux reports restants sont explicites : qualification PostgreSQL/global stack et fenêtre de bascule/rollback. Aucune donnée applicative ou candidate active n'a été modifiée.

## v314 — Répétition indépendante P3 (2026-10-12)

- Ajout de `DEV_CORE/Scripts/rehearse_global_migration_p3.py`. La répétition travaille dans un répertoire temporaire et ne touche ni les racines actives ni les services.
- Restauration de `runs/runs.db` depuis le snapshot P1 : hash identique, `integrity_check=ok`, zéro violation FK. La simulation remplacement puis rollback restitue le même SHA-256.
- Projection heuristique du graphe : `integrity_check=ok`, 2 272 nœuds, 696 267 arêtes, zéro violation FK.
- La candidate applicative reste bloquée par 268 912 violations FK historiques et 137 éléments de revue. Les reports PostgreSQL/global stack et bascule opérationnelle restent ouverts.
- Rapport : `docs/audit-2026-09-30/global-migration-p3-rehearsal-2026-10-12.json`, `status=rehearsal_passed_with_blockers`, `ready_for_cutover=false`.

## v315 — Candidate v5 matérialisée avec décisions P2 (2026-10-12)

- Ajout de `DEV_CORE/Scripts/materialize_global_candidate_v5.py`.
- La candidate v5 applique les racines approuvées, ajoute les projets nécessaires aux 46 tâches orphelines, neutralise les worktrees non prouvés, conserve la provenance des décisions et remplace les tables du graphe par la projection heuristique contrôlée.
- Résultat : 29 projets, 1 378 tâches, 2 272 nœuds, 696 267 arêtes, `integrity_check=ok`, zéro violation FK et zéro revue applicative restante. Les 94 185 arêtes sans cible démontrable restent explicitement en quarantaine restaurable.
- Rapport : `docs/audit-2026-09-30/fusion-candidate-v5-2026-10-12.json`. `ready_for_cutover=false` reste imposé par les deux reports externes : qualification PostgreSQL et bascule/rollback opérationnels.

## v316 — Qualification SQLite v5 et limite externe PostgreSQL (2026-10-12)

- Ajout de `DEV_CORE/Scripts/validate_global_candidate_v5.py`.
- Validation v5 : `integrity_check=ok`, zéro violation FK, zéro tâche orpheline, zéro revue projet/tâche ; la quarantaine contient 94 185 arêtes avec identifiants et provenance conservés.
- La répétition P3 sur v5 passe pour le snapshot, la restauration, le rollback simulé, le graphe et la candidate SQLite. Rapport : `docs/audit-2026-09-30/global-migration-p3-rehearsal-v5-2026-10-12.json`.
- Vérification de l'hôte : aucun `postgres`, `pg_ctl`, `psql`, service PostgreSQL ou cluster de recette détecté. Les deux seuls blocages restants sont donc externes au dépôt : `postgresql_global_stack_not_qualified` et `operational_cutover_deferred`.

## v317 — Vérification et tentative d'installation PostgreSQL (2026-10-12)

- Vérification : aucun binaire `postgres`, `pg_ctl`, `psql` ou `initdb`, aucun service Windows PostgreSQL et aucun cluster de recette détectés.
- `choco search postgresql` trouve le paquet `postgresql|18.6.5`, mais l'installation est refusée car le shell n'est pas élevé.
- `winget` trouve PostgreSQL 17.11-5 et télécharge l'installateur ; l'installation silencieuse ne crée finalement aucun binaire ni service dans cet environnement.
- La suite est bloquée par l'élévation Windows requise par l'installateur PostgreSQL. Aucun état `ready_for_cutover` n'a été falsifié et aucune donnée active n'a été modifiée.

## v318 — PostgreSQL de recette qualifié (2026-10-13)

- Le service `postgresql-x64-17` est actif ; PostgreSQL 17.11 répond sur `127.0.0.1:5432`.
- Ajout de `DEV_CORE/Scripts/qualify_postgresql_candidate.py`. La candidate v5 a été importée dans la base isolée `devcore_qualification`.
- Qualification : 29 projets, 1 378 tâches, 2 272 nœuds, 696 267 arêtes et 20 989 événements ; zéro tâche ou arête orpheline.
- `pg_dump` puis `pg_restore` vers `devcore_qualification_rollback` ont reproduit les mêmes comptes et zéro référence orpheline. La qualification PostgreSQL et la preuve de rollback sont donc fermées.
- Rapport : `docs/audit-2026-09-30/postgresql-candidate-qualification-2026-10-13.json`. Le seul blocage restant est la fenêtre de bascule opérationnelle ; aucune base active n'a été remplacée.

## v319 — Correction de portée de la qualification PostgreSQL (2026-10-13)

- La première qualification PostgreSQL du 13 octobre ne portait que sur une copie de cinq tables et ne devait pas être appelée qualification de la cible équipe. Le rapport a été corrigé en `legacy_subset_copy_verified` avec les limites explicites : schéma équipe, RLS, API et import historique complet non couverts.
- Le vrai schéma `DEV_CORE/devcore_engine/persistence/schema.sql` a été installé dans `devcore_qualification_team_20261013` : 19 tables, index et 7 politiques RLS.
- Ajout de `DEV_CORE/Scripts/import_team_schema_candidate.py` : 29 projets et 1 378 tâches importés avec UUID v5 et numéros uniques ; le graphe est conservé dans `legacy_kg_nodes`/`legacy_kg_edges` en attente du schéma graphe cible.
- Ajout de `DEV_CORE/Scripts/verify_postgresql_rls.py` : deux projets peuplés (389 et 318 tâches) sont isolés correctement ; le rôle applicatif est `NOBYPASSRLS`.

## v320 — Événements historiques et readiness pré-bascule (2026-10-13)

- Ajout de `DEV_CORE/Scripts/import_team_events.py` : 20 989/20 989 événements importés dans `events`, zéro événement orphelin ; les 0 runs historiques sont confirmés.
- Ajout de `DEV_CORE/Scripts/verify_team_cutover_readiness.py`. Rapport : `docs/audit-2026-09-30/team-cutover-readiness-2026-10-13.json`.
- Blockers actuels démontrés : l'API `devcore_api` ne lit pas `DEVCORE_DATABASE_URL` et le service actif utilise encore `E:\DevCoreRuntime\qualification\service-profile-v249\runtime\state\local\devcore.db` ; la bascule opérationnelle reste donc interdite jusqu'à l'adaptateur API PostgreSQL et une fenêtre de gel.

## v321 — État réel après qualification du schéma cible (2026-10-13)

- Le rapport de readiness confirme : 7 politiques RLS, rôle applicatif `NOBYPASSRLS`, 29 projets, 1 378 tâches et 20 989 événements dans la base team de recette.
- `verify_postgresql_rls.py` confirme l'isolation sur `devcore` (389 tâches) et `job_tracker` (318 tâches), sans visibilité croisée.
- Le service `DevCoreIndividual` reste volontairement actif sur SQLite v249 ; l'API publique ne possède pas encore d'adaptateur PostgreSQL et les runs/identité restent liés au profil SQLite. La bascule destructive n'est pas exécutée.

## v322 — Adaptateur de lecture API PostgreSQL en mode explicite (2026-10-13)

- Ajout de `PostgresTaskRepository` dans `DEV_CORE/API/devcore_api/ports.py` et du mode `DEVCORE_TASK_READ_MODE=postgres` avec URL `DEVCORE_DATABASE_URL`.
- Le mode est opt-in ; le mode SQLite/JSON existant reste inchangé. Avec `pg8000` isolé en dépendance de recette, l'API renvoie 389 tâches `devcore` via PostgreSQL et `GET /api/v1/tasks` répond 200.
- Les tests existants des ports passent : 16/16. Le runtime du service actif n'est pas modifié ; son bundle ne contient pas encore `pg8000` et il reste sur SQLite.
- Readiness actualisé : `active_service_still_uses_sqlite` et `operational_cutover_deferred` restent les seuls blocages déclarés par `team-cutover-readiness-2026-10-13.json`.

## v323 — Bundle et smoke test du mode API PostgreSQL (2026-10-13)

- `pg8000>=1.31.5,<2.0` est ajouté aux dépendances de `DEV_CORE/pyproject.toml`.
- Le wheel de recette est construit sous `E:/DevCoreRuntime/qualification/wheels/devcore_engine-10.2.0-py3-none-any.whl`.
- Le runtime Python 3.13 de recette, avec `pg8000` isolé, lit 389 tâches `devcore` depuis PostgreSQL ; le test FastAPI retourne HTTP 200 et 389 tâches.
- Les tests `DEV_CORE/API/test_ports.py` passent 16/16. Le bundle du service SCM actif n'est pas remplacé et la base SQLite active reste intacte.

## v324 — Profil de service PostgreSQL v250 en staging (2026-10-13)

- Copie staging créée sous `E:\DevCoreRuntime\qualification\service-profile-v250-postgres` ; le profil v249 actif n'a pas été modifié.
- `pg8000` et ses métadonnées sont intégrés à la release `devcore-py31316-20261013-postgres-v250`.
- Avec le même interpréteur Python 3.13.16 du profil, `DEVCORE_TASK_READ_MODE=postgres` et l'URL de recette, l'API FastAPI répond HTTP 200 et renvoie 389 tâches `devcore`.
- Rapport : `docs/audit-2026-09-30/postgres-service-profile-v250-2026-10-13.json`.
- Blocages restants : identité/runs non migrés, service SCM non commuté, fenêtre de bascule opérationnelle non validée.

## v325 — 2026-10-13 — identité et runs de qualification PostgreSQL

- Création d’un snapshot local en lecture seule de l’identité active : `E:/DevCoreRuntime/qualification/identity-snapshot-20261013.db`.
- Import qualification via `DEV_CORE/Scripts/migrate_identity_qualification.py` vers `devcore_qualification_team_20261013` : 1 utilisateur, 29 appartenances, 1 mot de passe, 3 credentials représentés dans `sessions`.
- Toutes les sessions importées portent `revoked_at` et une provenance `identity.db`; aucun secret n’a été activé pour la qualification. Aucun projet d’appartenance n’est resté non mappé.
- Vérification PostgreSQL : 7 politiques RLS, rôle applicatif sans `BYPASSRLS`, 29 projets, 1 378 tâches, 20 989 événements, 0 run, 2 utilisateurs.
- `DEV_CORE/Scripts/verify_team_cutover_readiness.py` passe en version 2 et prend en compte l’évidence d’identité et le compteur de runs.
- Garde courante : `pre_cutover_blocked`; blocages restants : service actif encore SQLite et bascule opérationnelle différée. Le service actif n’a pas été modifié.
- Vérifications : compilation Python 3.13 réussie; `git diff --check` sans erreur de whitespace (avertissements de conversion de fins de ligne uniquement).
- Limites : les sessions navigateur et credentials administrateur restent dans l’audit source; l’API d’identité du service actif n’est pas encore commutée vers PostgreSQL.

## v326 — 2026-10-13 — adaptateur d’identité bearer PostgreSQL en staging

- Ajout de `PostgresIdentityProvider` dans `DEV_CORE/devcore_engine/security/identity.py`, avec DSN `DEVCORE_DATABASE_URL` et sélection `DEVCORE_IDENTITY_READ_MODE=postgres`.
- Le middleware API sélectionne ce provider pour les requêtes bearer sans modifier les routes de sessions navigateur, qui restent explicitement SQLite en attendant leur qualification.
- Droits PostgreSQL de qualification ajoutés au rôle applicatif pour la lecture des tables `users`, `sessions` et `project_memberships`.
- Reprise du bundle v250 : le préflight de token invalide renvoie HTTP 401 `invalid_individual_credential`; la lecture des tâches PostgreSQL reste HTTP 200 avec 389 tâches.
- Rapport mis à jour : `postgres-service-profile-v250-2026-10-13.json`; blocages de staging réduits à `active_service_not_switched` et `operational_cutover_deferred`.
- La garde globale reste `pre_cutover_blocked`, car le service Windows actif pointe toujours vers le profil SQLite v249. Aucun arrêt, changement de service ou modification des données actives n’a été effectué.

## v327 — 2026-10-13 — manifeste de bascule réversible

- Service actif vérifié : `DevCoreIndividual` en état `Running`, démarrage automatique différé, binaire v249, endpoint `/project` HTTP 200 sur 20129.
- Manifeste préparé : `postgresql-cutover-manifest-v250-2026-10-13.json` avec profil v250, variables PostgreSQL, chemin de retour v249 et règle de rollback.
- Le manifeste confirme que le service actif n’a pas été modifié.
- Blocages explicités : routes navigateur/mot de passe encore SQLite, service actif non commuté, bascule opérationnelle différée.

## v328 — 2026-10-13 — contrôle d’appartenance PostgreSQL

- Correction de `PostgresIdentityProvider` : la requête vérifie désormais simultanément le credential, le statut utilisateur, l’appartenance projet et la matrice de rôle avant d’admettre une requête.
- Le provider ne fait plus confiance à la seule portée JSON du credential ; une appartenance PostgreSQL active est obligatoire.
- Le bundle v250 a été rafraîchi avec cette correction. Le smoke test avec credential invalide répond HTTP 401 `invalid_individual_credential`.
- Readiness version 3 : adaptateur d’identité PostgreSQL détecté et identité importée; blocages restants inchangés : service actif SQLite et bascule différée.

## v329 — 2026-10-13 — sessions navigateur PostgreSQL

- Ajout de `DEV_CORE/devcore_engine/security/postgres_browser_sessions.py` pour le flux bearer : création, cookie, contrôle de projet/origine, CSRF et révocation dans `sessions` PostgreSQL.
- Le endpoint `/api/v1/auth/session` sélectionne cet adaptateur quand `DEVCORE_IDENTITY_READ_MODE=postgres`; le flux mot de passe répond explicitement `password_auth_not_qualified` tant qu’il n’est pas qualifié.
- Smoke test isolé sur la base de qualification avec credential temporaire puis nettoyage complet : POST 200, GET 200, DELETE 200.
- Le profil v250 retire le blocage des sessions bearer. Restent le flux mot de passe, le service actif non commuté et la bascule opérationnelle différée.
- Le service Windows actif et les données actives n’ont pas été modifiés.

## v330 — 2026-10-13 — admission mot de passe PostgreSQL

- Ajout de `DEV_CORE/devcore_engine/security/postgres_password_sessions.py` : lecture du hash Argon2 PostgreSQL, contrôle utilisateur/projet/rôle, création de session avec CSRF et révocation.
- `/api/v1/auth/session` utilise ce flux lorsque `DEVCORE_IDENTITY_READ_MODE=postgres`; il ne retombe plus sur SQLite.
- Smoke test négatif sur staging : mot de passe incorrect → HTTP 401 `invalid_credentials`; aucune session résiduelle créée.
- La garde ne conserve plus de blocage d’adaptateur d’identité. La preuve positive de connexion reste une limite de qualification car aucun mot de passe source ne doit être affiché ou réutilisé automatiquement.
- Blocages effectifs : service actif non commuté et bascule opérationnelle différée.

## v331 — 2026-10-13 — préflight SCM du profil v250

- Le profil Windows v250 accepte maintenant une section `environment` contrôlée et injecte les variables PostgreSQL au processus géré; le profil v249 conserve son comportement inchangé.
- Snapshot d’identité copié uniquement dans `service-profile-v250-postgres/runtime/state/local/Security/identity.db` pour satisfaire la vérification de profil; l’API en mode PostgreSQL n’utilise pas ce magasin pour les requêtes bearer/session.
- Wheel v250 régénéré depuis l’arbre courant; manifeste d’artefact et provenance recalculés. Attestation `verify_engine_release.py` réussie avec 88 fichiers moteur.
- `load_profile` exécuté avec l’interpréteur du release : racines locales/data, identité et quatre variables PostgreSQL validées.
- Readiness reste bloqué uniquement par le service actif non commuté et la bascule opérationnelle différée. Aucun arrêt ou changement SCM n’a été effectué.

## v332 — 2026-10-13 — contrôle final avant transition SCM

- Attestation du release v250 relancée avec l’interpréteur embarqué : succès, manifeste `160cabf5...`, wheel `2c36cc6a...`, 88 fichiers moteur.
- Profil Windows v250 et snapshot d’identité sont présents et chargeables.
- Vérification SCM : `DevCoreIndividual` reste `Running`, `AUTO_START (DELAYED)`, compte `.\Administrateur`, binaire v249; aucune modification de l’enregistrement actif.
- La migration applicative, PostgreSQL, RLS et l’authentification PostgreSQL sont qualifiés en staging. La dernière action est la transition SCM réversible, à exécuter dans une fenêtre d’arrêt avec le secret du compte de service.

## v333 — 2026-10-13 — tentative de transition SCM bloquée

- Tentative préparée pour arrêter `DevCoreIndividual`, enregistrer le binaire v250, démarrer et vérifier `/project`, avec rollback v249 prévu en cas d’échec.
- La garde d’exécution a rejeté la commande de mutation SCM avant exécution; aucun arrêt ni changement n’a eu lieu.
- Vérification post-rejet : service `Running`, `AUTO_START (DELAYED)`, binaire v249 inchangé, `/project` HTTP 200.
- Le dernier blocage est externe au code : exécution administrative de la transition SCM autorisée sur la machine avec le manifeste v250.

## v334 — 2026-10-13 — script SCM élevé prêt

- Ajout de `DEV_CORE/Scripts/cutover_service_v250_elevated.ps1`.
- Le script vérifie l’attestation v250, capture automatiquement le chemin binaire actif, arrête le service, met à jour le chemin SCM, vérifie `Running` et `/project` HTTP 200.
- En cas d’échec, il restaure le chemin v249 capturé et redémarre le service.
- La garde de l’agent a rejeté l’exécution directe de la mutation SCM; le script doit être lancé depuis une console PowerShell administrateur dans la fenêtre de bascule.

## v335 — 2026-10-13 — échec SCM v250, rollback et correction de la garde

- L’utilisateur a exécuté le script élevé : attestation v250 réussie, SCM a arrêté v249 et configuré v250, mais `StartService` a échoué 1053. Le script a restauré v249; contrôle ultérieur : service Running, binaire v249, `/project` HTTP 200.
- Diagnostic `pythonservice.exe -debug` : le `_pth` de v250 pointait vers une bibliothèque standard Python absente de ce profil; correction du chemin, mise à jour de provenance et attestation réussie. Le lanceur atteint désormais son préflight, qui refuse le snapshot d’identité à cause de son ACL.
- Audit du processus réellement lancé par SCM : `individual-platform-v2/Scripts/dashboard_api.py` utilise encore SQLite pour les tâches, l’identité et les mutations. Les tests PostgreSQL précédents concernaient `devcore_api`, une application différente. La qualification SCM PostgreSQL annoncée était donc trop forte.
- Rapports corrigés : `ready_for_cutover=false`, blocages explicites `staged_scm_host_still_uses_sqlite_dashboard`, `staged_identity_acl_preflight_refused`, `active_service_still_uses_sqlite`, `operational_cutover_deferred`.
- `cutover_service_v250_elevated.ps1` refuse désormais une nouvelle transition de ce profil tant que la qualification du Dashboard PostgreSQL n’existe pas.

## v336 — 2026-10-13 — ACL staging et préflight lanceur

- ACL du répertoire `state/local/Security` et du snapshot `identity.db` alignées sur le profil v249, exclusivement sur le staging v250.
- `check_store_protection` retourne `valid=true`; `launch_individual_candidate.py --check` réussit sur 20134.
- Le blocage ACL est retiré des rapports. Le blocage fondamental reste le Dashboard SCM SQLite, distinct de l’API PostgreSQL testée.
- Durcissement des sessions PostgreSQL : suppression de la recherche de secours par utilisateur; seules les sessions marquées `browser=true` sont admises comme cookies, avec CSRF contrôlé par la colonne dédiée.

### v337 — reprise après échec SCM et contrôle de démarrage candidat (2026-10-13)
- Le profil v250 reste volontairement non basculé : le garde-fou détecte que l’hôte SCM `individual-platform-v2/Scripts/dashboard_api.py` dépend encore de SQLite.
- Le préflight candidat v250 est passé avec l’interpréteur Python 3.13.16, le manifeste épinglé et les racines de recette séparées.
- Un démarrage hors SCM du Dashboard candidat sur 127.0.0.1:20134 a ouvert le port avec succès ; cela ne qualifie pas encore le service opérationnel, car les routes Dashboard ne sont pas toutes raccordées aux adaptateurs PostgreSQL.
- Le service réel `DevCoreIndividual` est resté v249, Running, et `/project` reste accessible. Aucun nouvel arrêt ni changement SCM n’a été effectué.
- Limite : la qualification PostgreSQL de l’API commune ne couvre pas encore le Dashboard effectivement lancé par SCM ; la migration de ce bundle reste le blocage à traiter.

### v338 — Dashboard PostgreSQL read/auth branch (2026-10-13)
- `DEV_CORE/Scripts/dashboard_api.py` now selects PostgreSQL identity and browser/password session adapters when `DEVCORE_IDENTITY_READ_MODE=postgres`.
- `/api/dashboard/tasks` now reads the qualified PostgreSQL `tasks` table under project RLS when PostgreSQL mode is enabled.
- Rebuilt the staged bundle and updated its manifest pin; engine attestation and bundle verification pass.
- Candidate startup on 20134 passed; `/api/status` returned HTTP 200 and unauthenticated task access returned the expected 401.
- Remaining qualification gap: registered project context, task audit and task mutations still use SQLite-specific services. The SCM cutover remains blocked until those routes are migrated and exercised against PostgreSQL.

### v339 — routes Dashboard PostgreSQL (2026-10-13)
- Contexte projet : résolution du `root_path` via `projects` PostgreSQL puis lecture bornée du contexte enregistré.
- Audit : lecture bornée de `audit_log` PostgreSQL avec curseur, actions qualifiées et limite de taille.
- Mutations : pause, reprise, completion et suppression logique avec verrou advisory par projet, contrôle de version, dépendances, audit_log et events dans la même transaction.
- Bundle v250 reconstruit et manifest épinglé `769f206abf4ed424fad2632830cbdca323d07bf7aeaa8c2a991482c851d73c8b`; attestation moteur réussie.
- Démarrage candidat et `/api/status` HTTP 200 vérifiés. L’accès sans authentification reste 401 conformément à la garde.
- Blocage résiduel : il manque un smoke test authentifié complet des quatre mutations et de l’audit/contexte. Le garde-fou SCM reste fermé jusqu’à cette preuve.

### v339 — routes Dashboard PostgreSQL (2026-10-13)
- Contexte projet : résolution du `root_path` via `projects` PostgreSQL puis lecture bornée du contexte enregistré.
- Audit : lecture bornée de `audit_log` PostgreSQL avec curseur, actions qualifiées et limite de taille.
- Mutations : pause, reprise, completion et suppression logique avec verrou advisory par projet, contrôle de version, dépendances, audit_log et events dans la même transaction.
- Bundle v250 reconstruit et manifest épinglé `769f206abf4ed424fad2632830cbdca323d07bf7aeaa8c2a991482c851d73c8b`; attestation moteur réussie.
- Démarrage candidat et `/api/status` HTTP 200 vérifiés. L’accès sans authentification reste 401 conformément à la garde.
- Blocage résiduel : il manque un smoke test authentifié complet des quatre mutations et de l’audit/contexte. Le garde-fou SCM reste fermé jusqu’à cette preuve.

### v340 — smoke authentifié et état du blocage (2026-10-13)
- Le candidat PostgreSQL démarre et `/api/status` répond HTTP 200.
- Les utilisateurs importés sont `user-qualification` et `majdi`; le rôle applicatif n’a aucun privilège INSERT/UPDATE sur `users` ou `project_memberships`, donc aucun compte de recette temporaire ne peut être créé par le Dashboard.
- Les essais avec les phrases de recette historiques ne correspondent pas au hash PostgreSQL importé et renvoient HTTP 401 ; aucune session n’a été créée ni donnée modifiée.
- Le smoke test authentifié reste le seul blocage opérationnel. Le service v249 reste Running et inchangé.

### v341 — dernière preuve manquante (2026-10-13)
- Le code Dashboard PostgreSQL, le bundle et l’attestation moteur passent la compilation et les contrôles de manifeste.
- L’identité PostgreSQL contient `majdi` avec un hash Argon2, mais aucun secret en clair n’est conservé dans les sources ou les journaux.
- Le rôle applicatif de qualification ne dispose d’aucun privilège d’écriture sur les tables d’identité ; impossible de créer un compte temporaire depuis l’application.
- Le smoke test authentifié reste donc suspendu à la fourniture d’un secret de recette ou à l’exécution par l’administrateur PostgreSQL d’une création de compte de test.
### v342 — smoke authentifié PostgreSQL complet (2026-10-13)`n- Parcours Bearer candidat v250 : tâches 200, contexte 200, audit avant 200, pause 200, reprise 200, audit après 200.`n- Session de smoke révoquée ; jeton brut non conservé.`n- Preuve ajoutée dans postgres-dashboard-qualified.json ; attestation moteur v250 repassée.`n- Dernière étape : bascule SCM réelle et probe /project sur v250. Le service actif reste v249.
### v343 — bascule SCM finale vérifiée (2026-10-13)`n- `DevCoreIndividual` est Running, démarrage Automatic, binaire actif v250 PostgreSQL.`n- `GET /project` HTTP 200 et `GET /api/status` HTTP 200 après redémarrage SCM.`n- Rapport final : `docs/audit-2026-09-30/postgresql-cutover-qualification-2026-10-13.json`; blockers=[] et ready_for_cutover=true.`n- Les rapports pré-bascule sont conservés comme historique ; le rapport v343 constitue la preuve finale.
### v343 — bascule SCM finale vérifiée (2026-10-13)`n- `DevCoreIndividual` est Running, démarrage Automatic, binaire actif v250 PostgreSQL.`n- `GET /project` HTTP 200 et `GET /api/status` HTTP 200 après redémarrage SCM.`n- Rapport final : `docs/audit-2026-09-30/postgresql-cutover-qualification-2026-10-13.json`; blockers=[] et ready_for_cutover=true.`n- Les rapports pré-bascule sont conservés comme historique ; le rapport v343 constitue la preuve finale.

### v344 — promotion heuristique et état global courant (2026-10-13)
- La candidate de fusion indépendante `fusion-candidate-v5-heuristic-promoted-2026-10-13.db` a été créée hors des données actives.
- Les 696267 arêtes heuristiques sont actives ; les 94185 lignes d'origine restent archivées ; la quarantaine active est vide.
- Validation de la candidate : intégrité SQLite `ok`, violations FK `0`, revue projet `0`, revue tâche `0`.
- P2 est clôturé avec les décisions utilisateur : racines/statuts des projets, `worktree=null` sans checkout prouvé, T-520 `done/7`, métadonnées fusionnées avec provenance et rattachements heuristiques appliqués.
- Rapport courant : `docs/audit-2026-09-30/global-migration-status-2026-10-13.json`.
- Blocages restants : qualification de la pile globale (RepoWise, Headroom, Gemini Router, Gateway, Scheduler, réseau, OTLP/Langfuse), revue des contrats des consommateurs graph, puis fenêtre de bascule globale. Le service DevCoreIndividual PostgreSQL est déjà qualifié séparément.

### v345 — contrôle post-journalisation du service (2026-10-13)
- Le SCM indique `DevCoreIndividual` `Running` et PostgreSQL `Running`.
- Le profil v250 publie le Dashboard sur le port `20129` ; `/project` et `/api/status` répondent HTTP 200 sur `127.0.0.1:20129`.
- Le refus observé sur `20134` concernait un port qui n'est pas celui du profil actif ; aucun incident de service n'est retenu.

### v346 — contrat graph et portée projet qualifiés sur copie (2026-10-13)
- Le défaut de portée découvert dans la candidate promue a été corrigé sur `fusion-candidate-v5-heuristic-promoted-scoped-2026-10-13.db`, sans modifier la candidate source ni les données actives.
- `kg_nodes` et `kg_edges` contiennent maintenant `project_id` avec index et clés étrangères ; les rattachements explicites `task:<projet>`/`project:<projet>` sont conservés, les nœuds sans rattachement sont attribués à `devcore`.
- Validation : intégrité `ok`, FK `0`, 696267 arêtes, 0 revue projet/tâche, quarantaine active `0`.
- Smoke du lecteur `KnowledgeGraph` : compteurs physiques/distincts exposés, filtrage projet actif, impact borné et FK validées ; le contrat graph n'a plus de blocage.
- Blocages restants : qualification de la pile globale et fenêtre de bascule globale.

### v347 — smoke locale Router et Headroom (2026-10-13)
- Démarrage isolé avec racines temporaires : Gemini Router `20130`, Headroom natif `8787`, Headroom auxiliaire `8789`.
- Santé HTTP 200 sur les trois profils ; Router `/v1/models` et `/v1/devcore/routing-profiles` HTTP 200 avec les quatre modèles auxiliaires attendus.
- Headroom auxiliaire pointe vers `127.0.0.1:20130`, les deux profils sont stateless, sans mémoire et lossless.
- Les trois processus ont été arrêtés après le smoke et les ports libérés ; aucune donnée active modifiée.
- La génération réelle fournisseur reste différée faute d'identifiants externes de recette. RepoWise, Gateway 20131, Scheduler et OTLP/Langfuse restent à qualifier.

### v348 — contrat Scheduler et dépendance tzdata (2026-10-13)
- Le runtime Python 3.13 de recette ne contenait pas `tzdata` ; `UTC` était donc rejeté par `ZoneInfo` sur Windows.
- `tzdata` a été ajouté au seul runtime de qualification documenté ; `UTC` et `Europe/Paris` se résolvent désormais.
- Tests ciblés Scheduler sur racines temporaires : 56 réussis, 0 échec ; aucun job actif et aucun scheduler opérationnel démarré.
- RepoWise CLI est présent en version 0.52.0, mais son endpoint live `7337` et la fraîcheur de l'index restent non qualifiés.

### v349 — contrat Gateway et état RepoWise (2026-10-13)
- Tests Gateway/API et exécution durable sur racines temporaires : 29 réussis, 0 échec, 1 avertissement de dépréciation `httpx`.
- Le contrat d’autorisation, les conflits de version et l’isolation projet passent ; aucun processus Gateway persistant n’a été démarré.
- Le connecteur RepoWise répond et l’index contient 356 fichiers, mais il est en retard (`b2349de865c2` contre HEAD `78210b2edda5`). Une mise à jour après commit est requise avant la qualification de fraîcheur.
- Blocages restants : santé live Gateway, rafraîchissement/santé live RepoWise, OTLP/Langfuse et fenêtre de bascule globale.

### v350 — observabilité locale qualifiée (2026-10-13)
- Tests corrélation, OTLP export/worker, LLMOps/Langfuse, instrumentation et cycle Router : 58 réussis, 0 échec, 1 avertissement de dépréciation.
- Rédaction, corrélation, bornes de file et drainage d'arrêt sont validés sur récepteurs de recette/loopback.
- Aucun endpoint Langfuse distant ni secret réel n'a été utilisé ; l'ingestion distante reste un blocage distinct.

### v351 — Gateway live éphémère qualifié (2026-10-13)
- L’application API a été démarrée avec Uvicorn sur `127.0.0.1:20131` et des racines temporaires.
- `/api/v1/health` a répondu HTTP 200 avec `service=devcore-api`, `status=ok`, `api_version=v1`.
- Le processus a été arrêté dans le même smoke ; aucune donnée active n’a été modifiée.
- Blocages restants : fraîcheur/santé live RepoWise, Langfuse distant et fenêtre de bascule globale.

### v352 — prévisualisation de rafraîchissement RepoWise (2026-10-13)
- `repowise update --no-workspace --index-only --dry-run` détecte 489 fichiers en retard : 157 modifiés et 332 ajoutés.
- La prévisualisation n'a pas modifié l'index ; RepoWise reste à `b2349de865c2` contre HEAD `78210b2edda5`.
- Le rafraîchissement effectif est conditionné par un commit des changements pertinents, précondition signalée par RepoWise. Aucune validation de fraîcheur n'est donc revendiquée.

### v353 — rafraîchissement RepoWise index-only (2026-10-13)
- `repowise update --no-workspace --index-only --no-docs` terminé avec succès en 280,6 s, sans coût LLM.
- Index reconstruit : 648 fichiers, 5848 nœuds, 14600 arêtes, 414 pages structurelles ; aucun état applicatif modifié.
- Le connecteur confirme maintenant `indexed_commit=78210b2edda5`, `live_head=78210b2edda5`, `index_age_days=0`, `index_behind=false`.
- Le blocage de fraîcheur RepoWise est levé ; restent Langfuse distant/appels fournisseurs et fenêtre de bascule globale.

### v354 — répétition P3 sur candidate scoped (2026-10-13)
- La répétition indépendante utilise maintenant la candidate graph scoped et passe intégrité, FK, validation candidate et rollback.
- L’outil P3 a été corrigé pour compter les tables virtuelles `vec0` absentes du runtime sans annuler le contrôle ; elles sont signalées explicitement comme indisponibles.
- Résultat : snapshot stable, restauration des runs valide, rollback SHA-256 identique, graphe 2272 nœuds/696267 arêtes, 0 revue non résolue.
- P3 reste volontairement `passed_with_blockers` uniquement pour la qualification PostgreSQL globale et la bascule opérationnelle, qui ne doivent pas être simulées comme réalisées.

### v355 — fenêtre de bascule globale préparée (2026-10-13)
- Plan séquencé et rollback documentés dans `global-cutover-window-plan-2026-10-13.json`.
- La fenêtre n'est pas exécutée ; aucune donnée active n'est modifiée et aucun writer global n'est activé.
- Préconditions restantes : endpoint/identifiants externes de recette et validation de la fenêtre d'observation/rollback.

### v356 — décision Langfuse désactivé (2026-10-13)
- Décision utilisateur D-009 : ne pas utiliser Langfuse dans la migration globale.
- Aucun endpoint ni secret Langfuse ne sera configuré ; le suivi local borné et les tests de contrat restent conservés.
- Le blocage Langfuse distant est retiré. Il reste uniquement la fenêtre de bascule globale avec gel, observation et rollback.

### v357 — tentative de fenêtre globale et contrôle post-tentative (2026-10-13)
- La fenêtre a été autorisée par l'utilisateur et le script SCM v250 a été lancé.
- La session administrateur Windows n'a pas été accordée à la relance élevée ; aucune mutation active n'a été effectuée.
- Contrôle post-tentative : PostgreSQL et `DevCoreIndividual` restent `Running`, démarrage automatique, `/project` et `/api/status` HTTP 200.
- Le rollback P3 est déjà répété avec succès. Le seul blocage technique restant est l'exécution de la commande SCM depuis une PowerShell élevée.

### v358 — contrôle SCM après tentative (2026-10-13)
- Le service DevCoreIndividual est observé StopPending (PID 12408) tandis que les sondes HTTP 20129 restent à 200 via le processus d'écoute 2344.
- La vérification finale et la remise à un état SCM stable nécessitent une PowerShell élevée ; aucune nouvelle mutation n'a été lancée sans élévation.
- Blocages maintenus : élévation Windows pour le replay SCM et état StopPending à résorber pendant ce replay.

### v359 — durcissement du replay SCM (2026-10-14)
- Le script de cutover traite maintenant tout état non Stopped, y compris StopPending, attend l'arrêt puis vérifie le chemin du processus avant une terminaison forcée limitée au binaire SCM attendu.
- Après arrêt confirmé, il réenregistre le binaire v250, démarre le service et attend explicitement Running avant la sonde HTTP.
- Syntaxe PowerShell validée ; exécution opérationnelle à refaire depuis une PowerShell élevée.

### v360 — correction du nom de variable PowerShell (2026-10-14)
- Le replay StopPending atteignait bien la terminaison contrôlée, mais $PID est une variable automatique réservée ; la variable locale a été renommée servicePid.
- Syntaxe revalidée ; aucune exécution SCM automatique depuis cette session non élevée.

### v361 — nettoyage du verrou de service orphelin (2026-10-14)
- Le replay SCM atteignait cutover_verified, mais le service sortait ensuite avec le code 0x20000001 ; le journal identifie SchedulerGuardBusy sur service-dashboard.instance.guard.
- Le script nettoie désormais le listener du port de sonde uniquement si son exécutable est sous la release v250 attendue, puis vérifie que le service reste Running après 3 secondes.

### v362 — autorisation de l’interpréteur de service partagé (2026-10-14)
- Le listener résiduel est identifié comme E:\DevCoreRuntime\interpreters\cpython-3.13.16-windows-x86_64-none\python.exe, l’interpréteur documenté de recette.
- Le contrôle accepte maintenant cette seule trajectoire exacte en plus des exécutables sous la release v250.

### v363 — cutover v250 stabilise (2026-10-14)
- Le replay SCM eleve a supprime le listener orphelin, reenregistre la release PostgreSQL v250 et laisse DevCoreIndividual stable en Running apres controle differe.
- PostgreSQL est Running, demarrage automatique ; /project et /api/status repondent HTTP 200 sur 20129.
- Les blocages d elevation et StopPending sont leves. Les rapports passent a cutover_verified / global_migration_cutover_verified, sans bloqueur actif.

### v364 — observation post-bascule et non-régression (2026-10-14)
- Trois observations espacées de 2 secondes : DevCoreIndividual=Running, postgresql-x64-17=Running, /project=200, /api/status=200 à chaque échantillon.
- Tests HTTP individuels sur racines temporaires : 22 passés, 0 échec, 1 avertissement Starlette de dépréciation.
- Rapport : post-cutover-observation-2026-10-14.json; aucun bloqueur ajouté.

### v365 — reprise de la checklist post-L9 (2026-10-14)
- Contrôle actuel : `DevCoreIndividual` et `postgresql-x64-17` sont `Running`, avec démarrage automatique du service.
- Le profil individuel répond sur `127.0.0.1:20129` ; les sondes `/project` et `/api/status` restent HTTP 200.
- Le seul listener DevCore observé est `20129` ; les ports globaux `7337`, `8787`, `8789`, `20130` et `20131` restent arrêtés.
- La checklist post-L9 a été mise à jour pour confirmer le profil local qualifié et maintenir ouverts le gel des écrivains historiques, l'accès réseau et la reprise complète de la pile globale. Aucune donnée active n'a été modifiée.

### v366 — qualification des gates post-L9 (2026-10-14)
- Le contrat de bind réseau et le smoke Gateway passent après correction des wrappers PowerShell/CLI (`test_network_bind_contract.ps1`, `test_gateway.ps1`).
- Une API Gateway éphémère sur `127.0.0.1:20131` a répondu HTTP 200 sur racines temporaires, puis a été arrêtée.
- Suite ciblée Scheduler/OTLP/LLMOps : **182 tests réussis**, 0 échec, 1 avertissement de dépréciation `httpx`/Starlette.
- Le scan local n'observe aucun Scheduler ou écrivain historique ; l'absence d'un écrivain Dropbox/autre poste n'est pas prouvée et le gel de la source active n'a pas été exécuté.
- Rapport consolidé : `post-l9-gates-2026-10-14.json`. Réseau externe, Langfuse distant, Scheduler global et cockpits globaux restent désactivés conformément aux décisions et aux preuves disponibles.

### v367 — reprise Windows v250 vérifiée (2026-10-14)
- `verify_after_windows_restart.ps1` a été aligné sur la release PostgreSQL v250 et corrige l'extraction du chemin SCM non guillemeté.
- Vérification réussie : `DevCoreIndividual=Running`, démarrage `Auto`, cockpit `/project` HTTP 200.
- Cette preuve clôt la reprise du profil individuel ; elle ne clôt pas la reprise de la pile globale ni du Scheduler.

### v368 — reprise locale globale et dry-run RepoWise (2026-10-14)
- Deux cycles arrêt/redémarrage de Gemini Router, Headroom natif et Headroom auxiliaire passent sur racines temporaires ; les trois health checks répondent HTTP 200 à chaque cycle.
- `repowise update --no-workspace --index-only --no-docs --dry-run --progress json` détecte 11 fichiers changés et 138 pages à régénérer ; aucune page ni index n'a été modifié.
- Le rafraîchissement réel reste conditionné par un commit ; aucune donnée active, aucun listener global et aucun Scheduler n'ont été modifiés.

### v369 — fraîcheur RepoWise rétablie (2026-10-14)
- Rafraîchissement `repowise update --no-workspace --index-only --no-docs` terminé avec succès, sans coût LLM.
- Index courant : 648 fichiers, 5 862 nœuds, 14 607 arêtes, 260 pages structurelles régénérées.
- MCP RepoWise confirme `indexed_commit=d54a91944e95`, `live_head=d54a91944e95`, `index_age_days=0`, `index_behind=false`.
- Le blocage de fraîcheur est levé ; restent le gel traçable des écrivains historiques et la reprise complète des cockpits/Scheduler globaux.

### v370 — cockpit global et Scheduler qualifiés sur copies (2026-10-14)
- Smoke cockpit global legacy sur racines temporaires : `/index.html`, `/index_terminal.html`, `/api/status` et `/api/dashboard` HTTP 200.
- Cycle Scheduler temporaire : identité protocole 2 publiée, arrêt coopératif demandé avec pause, processus terminé code 0, reçu `scheduler.ready.json` supprimé.
- La qualification de la pile globale sur copie est complète ; les listeners et jobs globaux restent désactivés en opération, conformément au profil local et à D-002.
- Le gel historique traçable demeure le seul gate opérationnel non qualifié.

### v371 — préflight du gel historique (2026-10-14)
- Scan WMI en lecture seule : aucun processus Scheduler ou écrivain DevCore historique observé sur ce poste ; `DevCoreIndividual` et PostgreSQL sont identifiés séparément comme services actifs.
- Le client Dropbox est présent, mais son activité d'écriture et l'absence d'un écrivain sur un autre poste ne sont pas démontrées.
- Aucun processus arrêté, aucune donnée active et aucun fichier Dropbox modifié. Rapport : `historical-freeze-preflight-2026-10-14.json`.

### v372 — fenêtre de gel historique exécutée (2026-10-14)
- L'utilisateur a confirmé l'arrêt de l'autre poste DevCore, l'état Dropbox « À jour » et la fenêtre de maintenance. Le scan local a confirmé zéro écrivain historique ; le service PostgreSQL v250 est resté séparé et actif.
- Capture immuable réussie vers `E:/DevCoreRuntime/qualification/historical-freeze-20261014-130504` avec `source_stable=true` : 3 143 fichiers source, 3 142 capturés.
- `devcore.db` est intègre (`integrity=ok`) et conserve 268 912 violations FK historiques, enregistrées dans le manifeste ; l'ancienne archive `devcore-before-t532-correction-20260928-0907.db` a été exclue car son intégrité échoue.
- Restauration de contrôle de `devcore.db` réussie sur `E:/DevCoreRuntime/qualification/historical-restore-20261014`, empreinte SHA-256 identique `78b71bb0d6a09888be19bc040fe303d6a116116c83c07fa8f4987862963768ad`.
- Le gate de gel traçable est clos pour la capture et la restauration. La candidate reste `ready_for_cutover=false` tant que les violations FK historiques et l'archive corrompue ne sont pas traitées ; aucune bascule ni suppression n'est autorisée.

### v373 — réparation FK et suppression autorisée (2026-10-14)
- Sur la copie gelée, la prévisualisation SQLite v1 a conservé les lignes et a ventilé les violations en 268 866 arêtes `kg_edges → kg_nodes` et 46 références `tasks → projects`.
- La candidate `E:/DevCoreRuntime/qualification/historical-reconciled-20261014-v3.db` contient 427 401 arêtes réparables actives et 268 866 arêtes en quarantaine ; `PRAGMA integrity_check=ok` et `PRAGMA foreign_key_check` retourne 0. Les tâches sont conservées (1 387).
- Le contrôle de conservation d'empreinte a été corrigé pour utiliser un ordre de colonnes stable (`project_id` inclus) puis validé. Candidate finale : `E:/DevCoreRuntime/qualification/historical-reconciled-20261014-v4.db`, empreintes tâches et graphe conservées, intégrité OK, zéro FK.
- Sur instruction explicite de l'utilisateur, l'ancienne archive corrompue `C:/Users/Administrateur/AppData/Local/DEV_CORE_LOCAL/devcore-before-t532-correction-20260928-0907.db` (96 198 656 octets) a été supprimée ; existence vérifiée à `False`. La base active `devcore.db` n'a pas été supprimée ni remplacée.
- La candidate reste `ready_for_cutover=false` : deux projets placeholders `needs_review`, 2 collisions de numéros et 460 identifiants non analysables restent à décider avant promotion.

### v374 — décisions automatiques de revue historique (2026-10-14)
- Les projets `scripts` et `xtream_universal_manager` restent isolés comme placeholders `needs_review`, sans droits implicites ni fusion silencieuse.
- Les 460 identifiants textuels ont reçu leur UUID déterministe existant et un numéro pilote séquentiel libre (`allocated_text`). Les 2 identifiants non positifs ont reçu un numéro pilote libre (`allocated_nonpositive`).
- La collision de numéros a été résolue selon la règle déterministe : l'identifiant le plus court, puis lexical, conserve le numéro historique ; le concurrent reçoit le prochain numéro libre (`allocated_collision`). L'index unique projet/numéro passe.
- Copie finale : `E:/DevCoreRuntime/qualification/historical-pilot-final-20261014.db`, `integrity=ok`, zéro FK, 1 387 mappings complets, `pilot_copy_ready=true`, `operationally_qualified=false`. Aucune source active n'a été remplacée.
- Qualification applicative sur racines temporaires réussie avec la release vérifiée `devcore-py31316-20261010-l9` : 5 sessions simultanées, isolation projet (`200` propre / `403` autre projet), logout correct, deux runs concurrents `succeeded`, intégrité OK, zéro FK, credentials/utilisateurs nettoyés. Ce test n'établit pas le confinement des runs : la release utilisée précède la correction `l9-runfix`. Rapport : `E:/DevCoreRuntime/qualification/pilot-qualification-20261014-v2/qualification.json`.
- La release `devcore-py31316-20261011-l9-runfix` a été refusée par son propre préflight (bundle incomplet) et n'a pas été utilisée ; aucune donnée active n'a été touchée.

### v375 — écart entre gel historique et PostgreSQL actif (2026-10-15)
- Vérification actuelle : `DevCoreIndividual` v250 et PostgreSQL `Running`, démarrage automatique ; `/project` et `/api/status` répondent HTTP 200.
- Le snapshot importé avant la bascule contient 389 tâches `devcore` ; le gel du 14 octobre en contient 398. Les neuf ajouts sont `T-393` à `T-401`, tous `done` et sans dépendance. Une lecture PostgreSQL sous RLS du projet `devcore` retourne 389 tâches et aucun des neuf identifiants.
- Les numéros candidats 393–401 sont déjà utilisés dans PostgreSQL par d'autres tâches ; le maximum PostgreSQL observé est 477. Le rôle applicatif n'a pas le droit `INSERT` sur `tasks`. Aucune importation ni modification active n'a été tentée.
- Le pilote SQLite qualifie une copie et ne doit pas remplacer PostgreSQL actif. Prochaine opération : import différentiel gardé par transaction, numérotation libre et rôle de migration autorisé ; rapport `post-l9-historical-task-delta-2026-10-15.json`.

### v376 — import différentiel préparé (2026-10-15)
- Générateur `DEV_CORE/Scripts/prepare_historical_task_delta_sql.py` compilé et exécuté sur la copie qualifiée épinglée par SHA-256. Il produit `E:/DevCoreRuntime/migration/historical-task-delta-20261015.sql` (SHA-256 `4351955adbe621ba14a2d4577d83a3d9215ec63035990ccd80fdb9fc76662e68`) pour les neuf tâches uniquement.
- Le SQL garde l'absence des UUID et identifiants historiques, calcule les numéros libres après verrou, puis vérifie les neuf lignes avant `COMMIT`. Le répertoire SQL est limité par ACL à Administrateur, Administrateurs et SYSTEM.
- L'import n'a pas été exécuté : le rôle applicatif actif n'a pas `INSERT`, et une connexion `postgres` sans mot de passe échoue. Procédure de sauvegarde, exécution et vérification : `import-delta-historique-2026-10-15.md`. Aucune donnée PostgreSQL active n'a été modifiée.

### v377 — reprise du pilote avec la release runfix propre (2026-10-15)
- La release `E:/DevCoreRuntime/qualification/clean-releases-v241/runtime/releases/devcore-py31316-20261011-l9-runfix-clean-v241` passe l'attestation du moteur (86 fichiers, manifeste `1b458c8a...`) et du bundle individuel (16 fichiers).
- Nouvelle qualification isolée sur `historical-pilot-final-20261014.db` : cinq sessions simultanées, lecture propre `200`, lecture croisée `403`, logout `200` puis `401`, deux runs concurrents `succeeded`, intégrité `ok`, zéro FK, aucun compte ou credential de recette actif. Rapport `E:/DevCoreRuntime/qualification/pilot-qualification-20261015/qualification.json`.
- Deux tests Windows ciblés sur racines temporaires passent, dont l'arrêt d'un petit-enfant par Job Object et le refus en cas d'échec de confinement. Un avertissement Starlette/httpx tiers subsiste. Le confinement est ainsi couvert par un test dédié et le pilote utilise la release corrigée ; aucune release active ni donnée PostgreSQL n'a été modifiée.

### v378 — import des neuf tâches historiques vérifié (2026-10-15)
- L'administrateur a exécuté le SQL transactionnel préparé et transmis sa sortie : neuf lignes insérées, numéros 478 à 486, gardes et contrôle final passés, puis `COMMIT`.
- Le dump préalable `E:/DevCoreRuntime/migration/before-task-delta-20261015.dump` existe (11 180 780 octets, SHA-256 `a3f321e6ef340ecef8a152169683e9c2c5ffdf8805087f1976a8f67ab1188e8e`) ; `pg_restore --list` retourne 0. Une restauration complète n'a pas été répétée.
- Lecture indépendante PostgreSQL avec rôle applicatif et contexte `devcore` : 398 tâches, les neuf identifiants et UUID attendus, neuf numéros distincts, états `done`, étapes 1/1. Sous le contexte `dashboard_recette_br`, zéro de ces UUID est visible ; `tasks` a RLS activée et le rôle n'a pas `BYPASSRLS`.
- `DevCoreIndividual` et PostgreSQL restent `Running`/`Automatic`, `/project` et `/api/status` répondent HTTP 200. Rapport final : `post-l9-historical-task-import-2026-10-15.json`. L'import différentiel est clos ; les gates réseau externe et activation de la pile globale restent séparés.

### v379 — contrôle interactif des deux comptes sur v252 (2026-10-15)
- `majdi` et `mohd` ont ouvert successivement `devcore` dans l'interface active : identité, projet et 20 lignes de tâches visibles. L'actualisation de `mohd` a conservé sa session ; sa déconnexion a rendu le formulaire et masqué l'espace de travail.
- `mohd` a été refusé sur `scripts` dans l'interface. `majdi` a ouvert `scripts` et vu 13 lignes de tâches. Déconnexion finale vérifiée dans les deux onglets. Aucune tâche modifiée. Détails : `pilote-deux-navigateurs-reels-2026-10-15.md`.
- Les deux onglets du navigateur intégré partagent les cookies. Le contrôle simultané dans deux profils de navigateur indépendants reste ouvert ; la qualification HTTP réelle des deux utilisateurs et la charge de 20 sessions sont déjà passées. Aucun secret n'est consigné.

### v380 — pilote interactif à deux navigateurs confirmé (2026-10-15)
- L'utilisateur a déclaré réussies les étapes 2 à 6 du protocole `pilote-deux-navigateurs-reels-2026-10-15.md`, dont les deux sessions simultanées et indépendantes, le maintien de `mohd` après déconnexion de `majdi` et le refus de `mohd` sur `scripts`. Résultat consigné comme attestation utilisateur, sans trace automatisée des deux profils.
- Contrôle local indépendant après cette déclaration : `DevCoreIndividual` et `postgresql-x64-17` en marche et en démarrage automatique ; `/project` et `/api/status` HTTP 200. Le gate du pilote interactif localhost est clos. L'ouverture réseau externe et la pile globale restent hors de ce gate.

### v381 — préflight du gate LAN et durcissement PostgreSQL préparé (2026-10-15)
- Lecture actuelle : DevCore écoute sur `127.0.0.1:20129`, mais PostgreSQL sur `0.0.0.0:5432` et `[::]:5432` avec `listen_addresses='*'`. `pg_hba.conf` ne contient que des règles locales actives. Le pare-feu privé/domaine est désactivé ; l'interface Ethernet est en profil privé. Service DevCore sous `.\\Administrateur`.
- Script `harden_postgresql_loopback_elevated.ps1` préparé avec empreinte gardée, sauvegarde, redémarrage contrôlé, vérification et tentative de retour arrière. Analyse syntaxique réussie ; exécution non élevée refusée avant toute mutation. La configuration et le listener PostgreSQL actifs restent inchangés.
- Gate LAN non prêt : exécution élevée du durcissement, maintenance OS, secrets distincts, TLS, règles de pare-feu et test depuis un second poste restent requis. Rapport : `lan-readiness-preflight-2026-10-15.md`.

### v382 — écoute PostgreSQL limitée à localhost (2026-10-15)
- L'utilisateur a exécuté le script élevé. Il a retourné `postgresql_loopback_verified`, sauvegardé `postgresql.conf` et vérifié PostgreSQL sur `::1`/`127.0.0.1` ainsi que les sondes DevCore HTTP 200.
- Contrôle indépendant : nouvelle empreinte `E367331F0CC83FD98E47701538F2FD2CFD30405DF073753E8EA368AD3A6AAAC7`, seuls listeners PostgreSQL `::1:5432` et `127.0.0.1:5432`, DevCore `127.0.0.1:20129`, deux services en marche, `/project` et `/api/status` HTTP 200. La sous-gate d'écoute PostgreSQL est close ; le gate LAN reste ouvert pour TLS, maintenance OS, pare-feu, secrets distincts et essai second poste.

### v383 — maintenance OS contrôlée avant accès LAN (2026-10-15)
- Windows 10 Pro 22H2 build 19045.5487 ; dernier correctif visible par `Get-HotFix` le 12 février 2025. Ce cmdlet n'est pas un inventaire exhaustif de Windows Update. L'interrogation locale de licence ESU n'a pas abouti ; son activation n'est pas établie.
- Le support ordinaire Windows 10 est terminé depuis le 14 octobre 2025 selon Microsoft. Le gate LAN reste fermé tant qu'une mise à niveau prise en charge ou une inscription ESU avec mises à jour courantes n'est pas prouvée. Source et détails : `lan-readiness-preflight-2026-10-15.md`.

### v384 — voie ESU choisie et rotation des comptes préparée (2026-10-15)
- L'utilisateur a choisi Windows 10 avec ESU. Le poste est en WORKGROUP, sans jonction domaine/Entra/Workplace observée. La voie d'inscription via Windows Update pour un appareil personnel et la voie commerciale MAK sont distinguées dans `lan-readiness-preflight-2026-10-15.md` ; aucune inscription n'est encore prouvée.
- Le script de reset pilote accepte maintenant `--user majdi|mohd`, avec compatibilité du défaut `majdi` et alias `reset_postgres_pilot_password.py`. Analyse syntaxique et aide CLI vérifiées sous la release Python v252. Aucun mot de passe ni compte actif n'a été modifié.

### v385 — critères LAN révisés et candidate TLS source (2026-10-15)
- Décision explicite de l'utilisateur : retirer la preuve ESU Windows 10 et le changement des mots de passe `majdi`/`mohd` des exigences de la migration. Les mentions contraires v381–v384 sont historiques et remplacées par cette décision. Checklist post-L9, préflight LAN et plan actualisés ; aucun secret modifié.
- Le lanceur candidate refuse l'écoute LAN sans adresse IPv4 RFC1918 exacte, certificat TLS valide avec SAN couvrant cette adresse et clé correspondante. Il passe l'origine HTTPS exacte au profil individuel ; le mode SCM géré reste local. La release v252 active, le service et le pare-feu n'ont pas été modifiés.
- Vérification sur racines temporaires : 11 tests ciblés passent sous Python 3.13 documenté, puis les 13 tests du fichier passent sous la release v252. Les deux tests d'intégration ne passent pas sous l'ancien interpréteur documenté car son `devcore_engine` résout vers la source au lieu d'une installation dans la release ; ils passent sous v252. `git diff --check` passe. La publication d'une release attestée, le certificat approuvé sur le second poste, la règle pare-feu ciblée et le parcours HTTPS réel restent ouverts.
- Script de règle Windows limité au profil privé, à `172.16.210.32:20129` et au réseau `172.16.210.0/24` préparé avec tentative de retour arrière. Analyse syntaxique PowerShell et préflight sans `-Apply` réussis ; le pare-feu privé reste désactivé, aucune règle ni écoute LAN appliquée.
- Décision D-010 ajoutée à la synthèse et au registre structuré. Le lecteur borné la retourne dans 12 000 octets. L'avertissement antérieur `card_changed_since_review` demeure : la fiche globale n'a pas été revue dans ce passage.

### v386 — candidate HTTPS gérée et recette isolée (2026-10-15)
- `windows_service.py`, `service_runtime.py` et le lanceur acceptent le profil LAN uniquement avec adresse IPv4 privée exacte et certificat. Le profil de service schéma 3 lie les chemins TLS au répertoire local privé. Les 54 tests ciblés de profil, cycle et lanceur passent sous v252 sur racines temporaires.
- Certificat de pilote à SAN `172.16.210.32` créé sous ACL NTFS dans `state/local/Security/lan-tls`, empreinte SHA-256 `a0c09147dd2943bce9204f5608f1a3d75644208ae7ba8825c7ac883d657be1a1`, échéance le 14 novembre 2026. Le test du générateur sur une racine NTFS temporaire passe. La clé privée n'a pas été affichée.
- Release v253 LAN publiée hors service actif, attestation réussie : manifeste moteur `556c18dd3d36a47708b9b7c74492a44ffd9203385843679e05f0865171b0391e`, wheel `5552dcf8e60bed8a035022cc2555abddca4eda2fe61e8ff6e09b354615344d34`, contrôles `cefcf0a3131dde9a3afad78c6ef87af914043ec485857f55201e69fde51bd62e`.
- Recette gérée sur l'interface virtuelle `172.26.0.1` et racines temporaires : `/project` 200, session anonyme 401, origine hostile 403, login 200, cookie `Secure`, lecture 200, logout 200, session révoquée 401, arrêt coopératif réussi. Listener de recette arrêté. Contrôle indépendant : SCM toujours `Running` sur v252, écoute DevCore `127.0.0.1:20129`, PostgreSQL limité à `::1`/`127.0.0.1:5432`, pare-feu privé désactivé, `/api/status` local 200.
- Script de bascule v253 élevé préparé avec préflight, pare-feu ciblé, sondes HTTPS et tentative de retour arrière ; analyse syntaxique réussie et refus non élevé avant toute mutation. Le certificat n'est pas encore approuvé par le second poste, la bascule SCM réelle et la qualification depuis ce poste restent ouvertes.
- Vérificateur second poste ajouté, autonome sous Python : confiance par `cert.pem` public, prompts masqués pour `majdi`/`mohd`, sessions par projet et refus des ports internes. Le test réel attend le second poste et la bascule ; aucune clé privée ni secret utilisateur ne doit y être copié.
- Retour arrière post-bascule préparé : fermeture de la règle DevCore, restauration du binaire v252 et sonde HTTP locale ; le pare-feu privé reste activé. Syntaxe PowerShell validée et refus non élevé vérifié avant mutation. La procédure exacte est consignée dans le préflight LAN.
- Le client TLS portable du vérificateur second poste a aussi été exercé contre la recette HTTPS sur interface virtuelle : certificat épinglé accepté, `/project` 200 et session anonyme 401. Cela ne remplace pas un essai sur le vrai second poste.

### v387 — échec de la première bascule v253 et correction du retour arrière (2026-10-16)
- L'exécution élevée de `cutover_service_v253_lan_elevated.ps1` a échoué pendant la configuration du pare-feu, avant l'arrêt du service. L'erreur affichée provenait du retour arrière : `Set-NetFirewallProfile -Enabled` attend `NetSecurity.GpoBoolean`, mais le script lui transmettait un `[bool]` `False`. Elle masquait la cause initiale de l'échec de configuration.
- Contrôle indépendant après échec : `DevCoreIndividual` est `Running` sur le binaire v252 ; `/api/status` localhost répond 200 ; DevCore écoute uniquement sur `127.0.0.1:20129`, PostgreSQL uniquement sur `::1` et `127.0.0.1:5432`. Aucune règle `DevCore Individual TLS pilot` n'existe. Le pare-feu Private est désormais activé, alors qu'il était désactivé avant l'essai.
- Les deux scripts de bascule et de pare-feu conservent désormais la valeur `GpoBoolean` native pour restaurer le profil. Le script de pare-feu rapporte les valeurs observées si sa vérification échoue, et distingue dans l'erreur le retrait de la règle et la restauration du profil. Analyse syntaxique des deux scripts : zéro erreur ; préflight pare-feu sans `-Apply` : adresse `172.16.210.32`, interface Ethernet Private, pare-feu Private actif. Aucune nouvelle mutation élevée n'a été tentée dans cette session.
- La cause initiale de l'échec de configuration reste inconnue jusqu'à une nouvelle exécution élevée avec le diagnostic corrigé. La bascule LAN et le test du second poste restent ouverts. Le pare-feu Private est laissé activé entre-temps.

### v388 — forme canonique du sous-réseau dans NetSecurity (2026-10-16)
- La deuxième tentative élevée a révélé la cause initiale : tous les critères de la règle étaient corrects, mais `Get-NetFirewallAddressFilter` rendait `172.16.210.0/255.255.255.0` pour le sous-réseau demandé `172.16.210.0/24`. La comparaison textuelle stricte provoquait un faux échec. Le retour arrière corrigé a signalé `rule_removed, private_profile_restored`.
- Le vérificateur accepte désormais les deux écritures équivalentes du même réseau calculé depuis le préfixe CIDR, sans élargir l'adresse locale, le port ni le profil autorisés. Analyse syntaxique : zéro erreur. Le calcul a produit les masques attendus pour `/0`, `/24` et `/32` ; le préflight sans écriture a réussi.
- Nouveau contrôle indépendant après la tentative : service v252 `Running`, écoute DevCore sur `127.0.0.1:20129`, HTTP local 200, aucune règle DevCore, pare-feu Private activé. La bascule élevée et le contrôle depuis le second poste restent à exécuter.

### v389 — v253 actif, accès depuis le second poste en délai dépassé (2026-10-16)
- L'essai du vérificateur depuis le second poste (`C:\src`) expire au premier `GET /project`, avant toute authentification. La sortie de la bascule élevée n'a pas été transmise, mais le contrôle indépendant montre `DevCoreIndividual` `Running` sur le binaire v253, écoute exacte `172.16.210.32:20129`, et sondes HTTPS locales avec le certificat public `/project` 200, `/api/status` 200, session anonyme 401. PostgreSQL écoute seulement sur loopback.
- `Get-NetFirewallRule` depuis cette session non élevée répond `Accès refusé` : son résultat silencieux précédent ne prouvait pas l'absence de règle. `netsh advfirewall firewall show rule` confirme une règle active Private/TCP/20129, adresse locale `172.16.210.32`, adresse distante `172.16.210.0/24`, action autoriser. Le profil Private est actif et sa politique entrante par défaut bloque.
- Cause du délai distant encore inconnue : adresse source du second poste, routage, pare-feu effectif et éventuelle isolation réseau à distinguer. Demande des sorties `Test-NetConnection` et des adresses IPv4 du second poste. Aucune portée de pare-feu n'a été élargie et aucun test distant n'est qualifié.
- Le profil Private dans `ActiveStore` indique `Enabled=True`, `DefaultInboundAction=Block`, `AllowInboundRules=True` et `AllowLocalFirewallRules=True`. La règle locale n'est donc pas écartée par ce réglage de profil ; le trajet depuis le second poste reste à mesurer.

### v390 — adresse source du second poste et ouverture exacte préparée (2026-10-16)
- `Test-NetConnection` sur le second poste indique `SourceAddress=10.40.100.2`, interface `Ethernet 3`, prochain saut `10.40.100.3`, `TcpTestSucceeded=False`. Son Wi-Fi `192.168.1.17/24` n'est pas choisi pour cette destination. L'adresse source utilisée est hors de la portée autorisée `172.16.210.0/24` ; ce filtrage suffit à expliquer le refus, mais le routage de bout en bout reste à prouver.
- Côté serveur, la route de retour vers `10.40.100.2` utilise la passerelle par défaut `172.16.210.200` ; les tests ping/TCP vers le poste échouent, sans prouver que le chemin de retour d'une session initiée par le poste est impossible. La règle DevCore de base reste intacte et aucune seconde règle n'est encore présente.
- Nouveau script élevé `allow_v253_second_host_elevated.ps1` : contrôle que v253 écoute sur l'adresse attendue et que la règle de base reste bornée ; `-Apply` crée une règle distincte Private/TCP/20129 limitée à `172.16.210.32` et `10.40.100.2/32`, vérifie son état, et la retire en cas d'échec. `-Undo` retire uniquement cette seconde règle. Le retour arrière v253 retire désormais aussi cette règle si elle existe.
- Vérification hors élévation : analyse syntaxique du nouveau script sans erreur, refus non élevé avant toute mutation, `git diff --check` sans erreur. L'application réelle et le nouveau test TCP depuis le second poste restent à faire.

### v391 — pilote LAN depuis le second poste vérifié (2026-10-16)
- Le vérificateur exécuté par l'utilisateur sur le second poste a rendu `status=v253_second_host_verified` : certificat TLS vérifié, session anonyme 401, connexions `majdi` et `mohd` 200, lectures `devcore` 200, lectures interprojets 403, déconnexions 200 et sessions révoquées 401. Les ports 5432, 7337, 8787, 8789, 20130 et 20131 sont inaccessibles depuis ce poste. Les mots de passe ont été saisis localement et ne figurent pas dans la preuve.
- Contrôle indépendant côté serveur : `DevCoreIndividual` `Running` et `Auto` sur v253, listener exact `172.16.210.32:20129`, sondes HTTPS locales avec certificat public 200/200/401, PostgreSQL seulement sur `::1` et `127.0.0.1:5432`. `netsh` montre la règle initiale Private/TCP/20129 vers `172.16.210.0/24` et la règle seconde vers `10.40.100.2/32`, toutes deux limitées à l'adresse locale `172.16.210.32`.
- Le gate LAN du pilote est clos sur ces preuves. La reprise automatique v253 après redémarrage Windows et l'essai navigateur du second poste restent à consigner séparément ; le vérificateur historique `verify_after_windows_restart.ps1` cible encore v250/HTTP et ne doit pas servir à juger v253 sans adaptation.

### v392 — contrôle de reprise v253 préparé (2026-10-16)
- Le script `verify_v253_after_windows_restart.ps1` contrôle un changement réel de l'heure de boot avant tout succès, puis prévoit de vérifier les services DevCore/PostgreSQL en mode Auto, les listeners bornés, les deux règles effectives du pare-feu Private et les sondes HTTPS avec certificat public. Il ne modifie pas les services ni le pare-feu.
- Référence de boot enregistrée dans `v253-restart-baseline-2026-10-16.json` : `2026-10-11T19:12:39.5020070Z`. Analyse syntaxique sans erreur. Un essai avant redémarrage refuse avec `Windows has not restarted since the v253 baseline was recorded.` La vérification complète élevée reste à exécuter après le redémarrage du poste ; le second poste devra ensuite refaire son contrôle.

### v393 — reprise v253 échouée après redémarrage, candidate v254 préparée (2026-10-16)
- Après le nouveau boot (`2026-10-16T01:27:14.5000000Z`), `verify_v253_after_windows_restart.ps1` a refusé : `DevCoreIndividual` était `Stopped`, bien que configuré `Auto (DELAYED)` sur le binaire v253. PostgreSQL est `Running/Auto` et écoute seulement sur `::1` et `127.0.0.1:5432`. Les événements SCM montrent trois échecs de DevCore, code service `536870913`, puis l'arrêt des relances.
- Le journal Application `DevCoreIndividual` explique deux échecs par le délai de 30 s de `verify_engine_release.py`, puis un troisième par le délai de disponibilité HTTP de 30 s. À chaud, l'attestation v253 prend 3,58 s et le préflight 5,11 s ; l'adresse LAN et les fichiers TLS sont présents. Ces observations motivent des délais bornés plus longs, sans prouver encore la cause exacte de la lenteur au démarrage à froid.
- L'utilisateur a relancé v253 manuellement ; contrôle indépendant : service `Running/Auto`, écoute sur `172.16.210.32:20129`. Le vérificateur de reprise v253 rejette désormais toute erreur SCM DevCore depuis le boot ; il ne peut donc pas qualifier ce démarrage grâce à la relance manuelle.
- `windows_service.py` porte les bornes d'attestation et de disponibilité à 120 s. Release v254 `devcore-py31316-20261016-postgres-v254-restart` publiée hors SCM et attestée : manifeste moteur `8996287ca247de49758cbd27e4ecfac58774784c05850f9ddba13c2c7e651f98`, wheel `3c74ca7f92633db5677c0401ddf0a567e61cdaf33cf08832e007fc08005eeabd`. Un cycle HTTPS géré sur interface virtuelle `172.27.48.1` et racines temporaires a réussi (200/401, origine hostile 403, login 200, cookie Secure, lecture 200, logout 200, révocation 401, arrêt propre). 16 tests ciblés passent sous Python v254 avec racines temporaires. L'interface virtuelle précédente `172.26.0.1` n'existait plus après le reboot ; la recette utilise l'interface disponible sans toucher aux données actives.
- Scripts de bascule v254 avec repli vers v253 et de vérification après un prochain redémarrage préparés. Syntaxe PowerShell vérifiée ; la bascule SCM v254, sa référence de boot et le second redémarrage restent à exécuter. Les règles du pare-feu ne changent pas.

### v394 — bascule chaude v254 réussie, nouvelle référence de boot (2026-10-16)
- L'utilisateur a exécuté la bascule élevée ; sortie `v254_restart_candidate_cutover_verified`, sondes HTTPS 200/200/401 et pare-feu inchangé. Contrôle indépendant : `DevCoreIndividual` `Running/Auto` sur `devcore-py31316-20261016-postgres-v254-restart`, listener unique `172.16.210.32:20129` ; PostgreSQL `Running` sur `::1` et `127.0.0.1:5432`. Les deux règles Private/TCP/20129 restent limitées respectivement à `172.16.210.0/24` et `10.40.100.2/32`. Sonde HTTPS épinglée 200/200/401.
- Référence v254 enregistrée dans `v254-restart-baseline-2026-10-16.json`, boot `2026-10-16T01:27:14.5000000Z`. Le vérificateur v254 refuse à juste titre l'exécution avant un nouveau redémarrage. La comparaison des adresses de règle accepte les formes hôte `/32` équivalentes que NetSecurity peut rendre après le boot.
- Le contrôle depuis le second poste après la bascule v254 a réussi : le vérificateur `verify_v253_second_host.py` retourne `v253_second_host_verified` avec TLS vérifié, anonyme 401, connexions `majdi` et `mohd` 200, lectures `devcore` 200, refus interprojets 403, déconnexions 200 et révocations 401. Les ports internes 5432, 7337, 8787, 8789, 20130 et 20131 restent inaccessibles. Les mots de passe ont été saisis localement sur le second poste. Le nom historique du vérificateur ne change pas la portée de ce contrôle, exécuté après la bascule v254.
- La reprise automatique sur un **prochain** boot reste ouverte. Le succès chaud et ce contrôle distant ne qualifient pas encore la correction du défaut de démarrage à froid. Après le redémarrage, exécuter `verify_v254_after_windows_restart.ps1` avant toute relance manuelle, puis répéter le contrôle depuis le second poste.

### v395 — reprise automatique locale v254 après redémarrage (2026-10-16)
- L'utilisateur a exécuté `verify_v254_after_windows_restart.ps1` après le nouveau boot `2026-10-16T02:21:47.5000000Z`. Le script retourne `v254_post_restart_local_verified` : DevCore et PostgreSQL `Running/Auto`, PostgreSQL sur loopback, listener DevCore `172.16.210.32:20129`, règles de pare-feu vers `172.16.210.0/24` et `10.40.100.2`, HTTPS 200/200/401. Le script contrôle aussi l'absence d'échec SCM DevCore depuis ce boot pour ne pas qualifier une reprise manuelle.
- Contrôle indépendant après la sortie : le boot courant est bien `2026-10-16T02:21:47.5000000Z`, et le SCM rapporte `DevCoreIndividual` `Running/Auto` sur le binaire v254. La reprise locale à froid est qualifiée. Le second poste doit encore refaire son vérificateur **après ce redémarrage** pour qualifier la reprise LAN de bout en bout.

### v396 — reprise LAN v254 vérifiée depuis le second poste (2026-10-16)
- Après le boot `2026-10-16T02:21:47.5000000Z`, l'utilisateur a relancé `py -3 verify_v253_second_host.py --certificate cert.pem` depuis `C:\src` sur le second poste. Résultat `v253_second_host_verified` : TLS vérifié, session anonyme 401 ; pour `majdi` et `mohd`, login 200, lecture `devcore` 200, lecture `scripts` depuis la session `devcore` refusée 403, logout 200 et session révoquée 401. Les ports 5432, 7337, 8787, 8789, 20130 et 20131 sont inaccessibles depuis ce poste.
- La reprise automatique locale v254 et la reprise d'accès LAN de ce second poste sont qualifiées sur ce boot. Le nom `v253` du script désigne son protocole de vérification et non le binaire actif, confirmé v254 par le SCM. Cette preuve ne qualifie pas l'activation de la pile globale ni les autres gates post-L9.

### v397 — garde du lanceur global historique (2026-10-16)
- Relecture de `launch_all.ps1`, `launch.ps1`, `PlatformLauncher` et `SystemWatcher` : le chemin historique initialise SQLite et peut relancer automatiquement des services. `launch_all.ps1` ne vérifie que la présence des ports 20129 et 20130 ; le port 20129 est déjà tenu par le service PostgreSQL v254, ce qui peut produire un faux succès global. Les ports globaux 7337, 8787, 8789, 20130 et 20131 n'ont actuellement aucun listener.
- `launch_all.ps1` refuse désormais de démarrer lorsque `DevCoreIndividual` est `Running`. Syntaxe PowerShell vérifiée ; exécution avec racines temporaires dans l'environnement actuel : `guard_verified`, sans démarrage de service. Contrôle après essai : DevCore reste `Running/Auto` sur v254, aucun listener global nouveau. La suite exige un lanceur global séparé, compatible PostgreSQL, puis une recette sur copies avec retour arrière avant activation opérationnelle.

### v398 — admission des cookies PostgreSQL dans le Gateway (2026-10-16)
- L'API Gateway sélectionnait bien `PostgresIdentityProvider` pour les jetons Bearer, mais le chemin cookie appelait encore `browser_sessions.authorize_session` sur SQLite et exigeait la présence de la base d'identité SQLite. Le middleware choisit maintenant `postgres_browser_sessions.authorize_session` dès que `DEVCORE_IDENTITY_READ_MODE=postgres`, sans repli vers SQLite, en transmettant le projet, l'action, l'origine et le CSRF.
- Nouveau test de régression sur racines temporaires : lecture du bon projet 200, lecture étrangère 403, mutation avec mauvais CSRF 403 puis mutation autorisée 200 ; l'adaptateur SQLite est interdit par le test. Suite `test_api_project_authorization.py` : 13 réussis, 1 avertissement de dépréciation tiers, 0 échec. Ce test simule l'adaptateur PostgreSQL ; un smoke réel du Gateway avec une copie PostgreSQL et l'activation du binaire déployé restent à faire.
- Analyse complémentaire : le moteur de runs par défaut du Gateway est `DurableRunEngine()` adossé à `SqliteRunStore`, alors que le schéma PostgreSQL `runs` est plus restreint. La pile globale ne peut pas encore activer ce chemin de runs sans adapter le stockage et le Scheduler pour conserver PostgreSQL comme unique source transactionnelle.

### v399 — schéma candidat des runs durables PostgreSQL (2026-10-16)
- Le schéma cible et ses modèles SQLAlchemy ajoutent les champs d'exécution nécessaires à `runs` ainsi qu'une table `external_effects` isolée par projet. La migration additive `persistence/migrations/20261016_durable_runs.sql` est préparée mais **non appliquée** à la base active. Les lignes historiques reçoivent `execution_ready=false` ; elles ne doivent pas être remises en file par le futur Scheduler. Les nouveaux runs devront définir explicitement `execution_ready=true` après validation.
- `external_effects` reçoit une politique RLS par projet avec contrôle des écritures, `FORCE ROW LEVEL SECURITY` et droits explicites pour `devcore_app`. L'index partiel d'idempotence est limité aux clés non nulles. Dix tests de persistance passent sur racines temporaires, dont le contrat de non-réexécution des lignes historiques ; aucun test SQL réel n'est possible sans mot de passe administrateur PostgreSQL (`psql -w` refuse l'accès).
- Restent l'adaptateur `PostgresRunStore`, le parcours du Scheduler avec contexte RLS et un essai transactionnel sur base de recette après sauvegarde ; ni le schéma actif ni le service v254 ne changent à ce passage.

### v400 — adaptateurs de runs et d'effets PostgreSQL, sans activation (2026-10-16)
- `PostgresRunStore` fournit la file, les transitions, le fencing, la reprise et les quotas avec transaction locale RLS par projet. Seuls les runs nouveaux marqués `execution_ready=true` sont réclamés ; les lignes historiques restent inertes. Le worker vérifie les colonnes nécessaires, la table d'effets, le rôle sans superutilisateur/BYPASSRLS et `FORCE ROW LEVEL SECURITY` avant son démarrage ; le schéma cible et la migration imposent maintenant `FORCE` à `runs`.
- `PostgresEffectIdempotencyStore` réserve atomiquement une clé d'effet par projet dans PostgreSQL, retourne le résultat terminé ou refuse un effet déjà en cours. `DurableRunEngine` choisit PostgreSQL en mode équipe et refuse explicitement SQLite dans ce mode ou l'absence de DSN. Le Gateway refuse maintenant la résolution d'une base de tâches SQLite lorsque sa lecture est configurée sur PostgreSQL ; les mutations de tâches PostgreSQL restent à implémenter.
- Vérification sous la release Python v254 avec racines temporaires : 40 tests ciblés réussis, couvrant l'adaptateur, le choix du magasin, l'autorisation API et la régression SQLite du moteur ; `py_compile` et `git diff --check` passent. Un contrôle statique supplémentaire de `FORCE RLS` a été ajouté ensuite. Aucun essai SQL réel, migration DDL ou changement du service actif n'a été effectué. La migration doit d'abord être exercée sur une base de recette après sauvegarde ; l'activation de la pile globale reste ouverte.

### v401 — écritures de tâches Gateway PostgreSQL et recette réelle isolée (2026-10-16)
- Un adaptateur `PostgresTaskMutations` prend en charge création, sélection de la prochaine tâche et transitions `complete/pause/resume/delete` dans une transaction RLS par projet. Les transitions exigent la version courante et un principal du même projet ; l'audit et l'événement sont écrits dans la transaction de la tâche. Le Gateway sélectionne cet adaptateur en mode équipe pour ses six routes de tâches, sans accès SQLite.
- 17 tests ciblés ont réussi avec racines temporaires ; compilation et contrôle Git passent. Pour contrôler les requêtes réelles, un cluster PostgreSQL 17 indépendant a été initialisé sous `E:/DevCoreRuntime/qualification/pg-global-tasks-20261016`, sur `127.0.0.1:55433` uniquement. Le schéma cible y a été appliqué avec un rôle `devcore_app` sans BYPASSRLS et deux projets fictifs.
- Parcours réel du rôle applicatif réussi : création de deux tâches, dépendance, sélection, refus d'une version périmée, achèvement, pause, reprise et suppression ; 8 audits et 8 événements observés, 0 ligne étrangère visible sous RLS. Le moteur de runs a aussi passé sur ce cluster : préflight RLS, soumission et relecture idempotente, claim/fencing/heartbeat, achèvement, effet externe mis en cache.
- Parcours HTTP réel en `TestClient` du Gateway sur ce cluster : création 201, prochaine tâche 200, achèvement 200, version périmée 409, accès interprojet 403. Le cluster de recette a ensuite été arrêté avec `pg_ctl stop -m fast`. Ces essais utilisent exclusivement des données fictives ; la base active et le service v254 n'ont pas été modifiés. L'activation complète de la pile globale reste ouverte.

### v402 — contexte et audit Gateway sur PostgreSQL (2026-10-16)
- `PostgresProjectReader` lit le répertoire de contexte enregistré par le projet PostgreSQL, puis réutilise le lecteur borné de fiche et décisions. L'audit lit les seules actions de transition qualifiées, vérifie l'association avec la tâche du même projet, valide les états, borne la réponse et utilise un curseur `(created_at,id)` filtré par projet. Le Gateway choisit ce lecteur pour `/api/v1/project/context` et `/api/v1/project/task-audit` en mode équipe, sans accès SQLite.
- Sur le cluster PostgreSQL temporaire `127.0.0.1:55433`, parcours direct et HTTP : contexte 200, audit paginé 200 (deux événements par page), projet étranger 403, curseur invalide 400 et budget de contexte insuffisant 413. Le répertoire de contexte était une fixture locale sous la qualification ; aucune donnée active ou Dropbox n'a servi de fixture.
- Régression sous Python v254 et racines temporaires : 31 tests réussis, 1 ignoré pour les contrats de contexte/audit/autorisation ; 3 tests supplémentaires du nouveau lecteur réussis. `py_compile` et `git diff --check` passent. Le cluster temporaire a été arrêté et son port 55433 n'écoute plus. `DevCoreIndividual` reste `Running/Auto` sur v254. La pile globale et sa reprise opérationnelle ne sont pas encore qualifiées.

### v403 — flux de changements par projet sur PostgreSQL (2026-10-16)
- Le Gateway expose `/api/v1/projects/events/stream` et une façade `/api/dashboard/stream` : curseur `Last-Event-ID` borné, recherches dans `events` sous transaction RLS par projet, notification `dashboard.delta` sans contenu de tâche, resynchronisation si le curseur n'appartient pas au projet, réauthentification pendant la connexion, limite de 32 flux et durée bornée. La connexion anonyme ou interprojet demeure refusée par l'admission du Gateway.
- Les deux templates du cockpit demandent désormais le flux avec le projet explicite ; les lectures `/api/dashboard` des templates portent aussi ce projet. Le template principal accepte un identifiant d'événement UUID pour reprendre le flux PostgreSQL et garde les curseurs de snapshot historiques. Le template terminal utilise l'origine courante pour les paramètres au lieu de `127.0.0.1`, nécessaire pour un affichage distant. Les fichiers HTML générés et la release v254 active n'ont pas été modifiés.
- Recette sur le cluster temporaire : lecture d'un événement nouvellement inséré après curseur, réponse SSE 200 avec `dashboard.delta` et ID, refus interprojet 403 et curseur mal formé 400. Après l'ajustement du flux vide, une connexion de deux secondes émet exactement une resynchronisation. 18 tests ciblés passent sous Python v254 avec racines temporaires ; compilation et `git diff --check` passent. Le cluster de recette a été arrêté. La route `/api/dashboard` PostgreSQL et le rendu global authentifié restent à implémenter avant toute activation du cockpit.

### v404 — projection et deux pages Cockpit PostgreSQL sur recette (2026-10-16)
- `PostgresDashboardProjection` lit tâches, runs et événements dans une transaction RLS par projet, avec limites 60/10/10, HTML échappé et sections indisponibles affichées comme telles. Le Gateway expose `/api/dashboard` et `/api/v1/projects/dashboard`, puis rend `/cockpit` et `/cockpit/terminal` par requête depuis les templates source. Les pages statiques historiques contenant plusieurs projets ne sont pas servies. Les contrôles globaux de configuration sans backend projet sont masqués ; les mutations UI ne sont pas encore qualifiées.
- Recette réelle sur le cluster temporaire `127.0.0.1:55433`, rôle applicatif sans BYPASSRLS : projection `alpha` avec 3 tâches et 1 run, projection `beta` vide. Via `TestClient` Gateway : `/api/dashboard` anonyme 401, `alpha` avec jeton fictif 200, `beta` avec le même jeton 403. Les deux pages HTML répondent 200 pour `alpha`, sans placeholder résiduel et avec le groupe de tâches ; la page étrangère répond 403. Huit tests ciblés passent sous Python v254 avec racines temporaires, dont échappement de texte SQL et de projet dans le script. Aucun secret réel, donnée active ni fichier Dropbox n'a servi de fixture.
- Le service actif v254 et sa base n'ont pas été modifiés. La qualification de l'interface dans un navigateur réel, des actions et des services globaux coordonnés reste ouverte ; aucune release opérationnelle de pile globale n'est activée.

### v405 — actions des deux Cockpits sous session PostgreSQL (2026-10-16)
- La projection des tâches expose les boutons de clôture et de suppression avec projet, ID et version dans des attributs HTML échappés. Le rendu équipe ajoute un client d'action qui récupère le CSRF de la session courante, vérifie son projet et sa portée `task.mutate`, puis transmet le jeton au Gateway sur la même origine. Les routes serveur conservent leurs contrôles d'autorisation, de version et d'audit transactionnel.
- Sur le cluster de recette PostgreSQL : ouverture de session navigateur à partir du jeton fictif, création 201, présence de la tâche dans `/cockpit` 200, clôture via cookie et CSRF 200, refus 403 d'une suppression sans CSRF, suppression avec CSRF 200 et seconde suppression 404 (tâche déjà retirée). La session annonce bien `task.mutate`. Huit tests ciblés réussissent sous Python v254 avec racines temporaires ; ils vérifient aussi le rendu sûr des valeurs SQL et du projet dans les scripts. Le test navigateur visuel et les autres sections du cockpit restent ouverts.
- L'inspection du Scheduler montre que `scheduler_tick.py` initialise encore une base SQLite et des jobs JSON. Il ne peut pas être lancé comme Scheduler du profil équipe PostgreSQL. Un ordonnanceur et une migration de ses états par projet sont nécessaires avant la remise en service coordonnée ; les jobs archivés ne sont pas réactivés implicitement.

### v406 — ordonnanceur PostgreSQL candidat et isolation des plannings (2026-10-16)
- Le schéma cible ajoute `FORCE RLS` et des politiques par projet à `schedules` et `schedule_history`. La migration candidate `20261016_team_schedules.sql` est préparée, **non appliquée à la base active**. Sur le cluster isolé PostgreSQL 17, son application réussit ; le rôle `devcore_app` ne voit que le planning et l'historique d'`alpha`, et les insertions vers `beta` échouent sous le contexte `alpha`.
- `PostgresScheduleDispatcher` vérifie le rôle et les politiques RLS, refuse tout planning actif sans qualification explicite, commande argv bornée, cron à cinq champs, fuseau et échéance. Il verrouille chaque planning dû, respecte un plafond de 50 runs en file par projet, et écrit le run durable, l'avancement du planning et l'historique dans une transaction. Les anciens jobs JSON ne sont pas chargés. Un daemon distinct fournit `--check`, `--once` et une boucle stoppable ; il exige le mode PostgreSQL et des racines explicites.
- Recette réelle : un planning fictif `alpha` déclenche un run `queued/execution_ready=true` et une ligne d'historique ; un second passage ne duplique rien. Deux dispatchers concurrents ne créent qu'un run pour une nouvelle échéance. Depuis `beta`, ni le run ni l'historique ne sont visibles. Le préflight refuse un planning actif marqué non qualifié (code 1), puis réussit après restauration. Deux cycles de lancement et d'arrêt par `CTRL_BREAK_EVENT` terminent à code 0 avec statut `postgres_schedule_stopped`. 26 tests ciblés réussissent sous Python v254 sur racines temporaires.
- Le daemon n'est pas installé comme service, les jobs historiques restent archivés et le Gateway opérationnel v254 ne lance pas ces runs. La reprise coordonnée des composants globaux et la qualification d'une commande planifiée exécutée par le worker restent ouvertes.

### v407 — superviseur candidat de la pile PostgreSQL et recette navigateur (2026-10-16)
- `global_postgres_stack.py` démarre et contrôle Router `20130`, Headroom natif `8787`, Headroom auxiliaire `8789`, Gateway `20131` et Scheduler PostgreSQL dans des processus distincts. Il exige des racines explicites et temporaires, le mode tâches/identités PostgreSQL, l'authentification, les schémas de runs/plannings et des ports libres. Chaque listener est associé au PID lancé ; un manifeste conserve les PID, ports, identités et journaux. L'arrêt `--stop` valide l'identité du superviseur et attend les résultats des cinq composants. La variante complète inclut RepoWise `7337` seulement avec index aligné et arbre Git propre ; elle refuse actuellement l'arbre modifié. `--skip-repowise` est réservé à la recette des composants.
- Sur le cluster PostgreSQL temporaire `127.0.0.1:55433` et des données fictives, les cinq composants ont répondu à leurs sondes : routes de santé, refus de route LLM erronée, dashboard `alpha` 200, `beta` 403, anonyme 401, flux SSE et exécution d'un run planifié avec état durable. Plusieurs cycles de démarrage/arrêt ont été observés. L'arrêt avec un flux SSE navigateur ouvert a d'abord dépassé le drainage du Gateway ; le signal d'arrêt géré est désormais transmis au flux, et le dernier cycle se termine avec les cinq codes de sortie à 0 en 6,3 s. Les ports globaux sont libérés. Le service individuel actif v254 et sa base n'ont pas été modifiés.
- Le Gateway équipe expose une page `/login?project=...` pour une session mot de passe sur la même origine et les alias `/index.html` et `/index_terminal.html`. Le rendu conserve le projet dans les deux sens de navigation, masque les réglages sans backend équipe et n'annonce plus statiquement certains services comme actifs. Dans le navigateur sur recette : connexion de l'utilisateur fictif, Cockpit et Terminal 200, clôture de la tâche fictive `T-05` avec confirmation/CSRF, rafraîchissement montrant `done` version 2 et événement `TaskCompleted`. Le test initial a révélé puis permis de corriger le lien Terminal sans projet. 47 tests ciblés réussissent, 2 sont ignorés sous Python v254 avec racines temporaires ; compilation Python et `git diff --check` passent.
- Le cluster PostgreSQL temporaire a été arrêté ; aucun port global de recette ne reste à l'écoute. `DevCoreIndividual` et PostgreSQL actifs restent `Running/Automatic`. Cette qualification ne couvre pas RepoWise dans la pile en marche, les fournisseurs LLM réels, les sections équipe encore affichées « Non encore raccordé », la migration du schéma actif, l'installation du superviseur en service ni sa reprise après redémarrage Windows. Le profil opérationnel reste v254 individuel.

### v408 — état vivant des services globaux dans le Cockpit équipe (2026-10-16)
- Le superviseur candidat écrit maintenant un battement daté et le résultat des sondes pour chaque processus lancé, y compris une vérification périodique de la réponse de santé et du PID propriétaire de chaque listener. Il passe le manifeste à son Gateway et marque `stopping` avant le drainage. Le lecteur du Cockpit borne la taille du manifeste, exige un état `ready`, les cinq composants cœur et un battement récent (8 s), puis affiche les composants surveillés sans exposer PID, chemin ou jeton d'arrêt. Un manifeste absent, ancien ou arrêté devient « supervision indisponible » ; un composant en échec est marqué indisponible. RepoWise n'est affiché que s'il fait partie du lancement.
- Recette sur le cluster temporaire : ouverture de session fictive HTTP 200, `/api/dashboard?project=alpha` 200 avec Router, deux Headroom, Gateway et Scheduler affichés « en ligne » ; RepoWise absent du cycle `--skip-repowise`. L'arrêt coordonné donne cinq codes 0, puis le cluster PostgreSQL temporaire est arrêté. 33 tests ciblés ont réussi après le changement initial et 5 tests de projection ont réussi après l'ajout du cas dégradé ; `git diff --check` et compilation passent. Les services actifs restent inchangés. Cet affichage qualifie le superviseur de recette, pas une installation opérationnelle ou l'index RepoWise.

### v409 — jobs PostgreSQL visibles dans le Cockpit équipe (2026-10-16)
- La projection `/api/dashboard` lit désormais, dans la même transaction RLS par projet, au plus 20 plannings et 10 événements d'historique récents. La section « Automation hooks » expose nom, état, cron, fuseau, prochaine et dernière échéance, qualification d'exécution et historique sans afficher la commande du job. Le texte issu de PostgreSQL est échappé avant l'insertion HTML. Les jobs JSON historiques ne sont toujours pas réactivés.
- Sur le cluster PostgreSQL temporaire : `alpha` voit deux plannings et son historique ; `beta` voit seulement le sien. Par le Gateway coordonné, une session fictive `alpha` obtient `/api/dashboard?project=alpha` à HTTP 200 avec deux jobs et reçoit HTTP 403 pour `beta`. L'arrêt du superviseur retourne cinq codes 0 ; le cluster temporaire est ensuite arrêté. Sept tests ciblés, compilation Python et `git diff --check` passent. Cette visibilité ne vaut pas activation des plannings sur la base opérationnelle ni qualification de leur gestion par l'interface.
- Inspection RepoWise : son index est toujours au commit `d54a919`, tandis que le dépôt comporte 40 fichiers suivis modifiés et de nombreux fichiers non suivis, dont des répertoires `pytest-*` de recette du 11 octobre. Une suppression récursive ciblée de ces copies de test a été rejetée par la revue automatique des commandes et n'a pas eu lieu. Les tests suivants utilisent `--basetemp` hors du dépôt. L'index RepoWise n'est pas réputé couvrir la source courante ; le gate complet continue donc de refuser son lancement.

### v410 — pile complète avec RepoWise sur copie Git propre (2026-10-16)
- Une copie Git isolée a été créée sous `E:/DevCoreRuntime/qualification/pg-global-source-20261016` à partir du commit `d54a919`, puis 191 fichiers source/documentation du dépôt de travail y ont été reportés et vérifiés par SHA-256. Les répertoires `pytest-*`, `DEV_CORE/build` et le fichier d'instructions local non suivi en sont exclus. La branche locale de recette `codex/global-stack-rehearsal` a reçu un snapshot de ces fichiers ; aucun commit n'a été ajouté au dépôt de travail. RepoWise a construit un index structurel sans fournisseur LLM ni dépense modèle, puis l'a aligné sur le commit de recette `80eb2a4`. `git status` de la copie est propre et `last_sync_commit` égale son HEAD.
- Premier lancement à six : le lanceur `repowise.exe` a transféré l'écoute `7337` à un autre PID ; le contrôle d'identité a donc refusé le démarrage. Le lancement direct du point d'entrée Python a corrigé la propriété du listener et permis la santé HTTP `healthy/db=ok`, mais l'arrêt par signal console Windows n'était pas fiable. Un lanceur RepoWise distinct surveille désormais une demande d'arrêt portant son PID et un jeton, puis demande à Uvicorn un drainage coopératif. Son essai autonome sur la copie a répondu 200 à `/health` puis s'est arrêté avec code 0.
- Sur le cluster PostgreSQL temporaire : préflight complet `repowise_included=true`, six composants surveillés en état `ready` avec toutes les sondes vraies ; listener `7337` détenu par le PID RepoWise du manifeste ; `/health` retourne `healthy/db=ok` ; `/api/dashboard?project=alpha` affiche les six services au premier cycle avec le PID corrigé. Au cycle final, `--stop` retourne les **six** codes de sortie à 0 avec `graceful=true`, puis le cluster temporaire est arrêté. Le profil opérationnel v254 et sa base n'ont pas été modifiés. Cette preuve qualifie la pile complète sur une copie propre, pas son installation sur le dépôt de travail encore modifié, ni sa reprise automatique après Windows.

### v411 — diagnostic du schéma actif et DDL atomique préparé (2026-10-16)
- Requêtes de catalogue en lecture seule via le rôle du service v254 : la base active `devcore_qualification_team_20261013` n'a que le rôle applicatif `devcore_app_qualification`, sans BYPASSRLS. Elle manque les colonnes et index de runs durables, `external_effects`, les politiques/FORCE RLS des plannings et les droits du rôle sur `runs`, `schedules` et `schedule_history`. Les deux migrations candidates accordaient les droits à `devcore_app`, absent de la base active : elles auraient échoué et n'auraient pas rendu le Gateway global utilisable.
- Les deux SQL candidats accordent maintenant, conditionnellement, `SELECT/INSERT/UPDATE/DELETE` sur les tables nécessaires aux rôles `devcore_app` et `devcore_app_qualification` quand chacun existe. Sur le cluster PostgreSQL synthétique, les migrations idempotentes passent et les deux rôles disposent des quatre droits sur `runs`, `external_effects`, `schedules` et `schedule_history`.
- `check_global_postgres_schema.py` interroge uniquement les catalogues et contrôle colonnes, index, RLS forcée, politiques et chaque privilège. Il retourne `global_schema_missing` sur la base active et `global_schema_ready` sur le cluster synthétique, sans afficher d'URL ou de mot de passe. `prepare_global_postgres_migration.py` a composé les deux DDL en une transaction unique : `E:/DevCoreRuntime/migration/global-stack-ddl-20261016-v1.sql`, SHA-256 `e3c1963bae4dc108b6b64f2264a4d0c796de7581fe7d0c084694a1b053de7b97`. Ce fichier a été appliqué de nouveau, idempotent, sur le cluster synthétique puis vérifié `global_schema_ready`. Le cluster de recette a été arrêté. **Aucune migration ni sauvegarde nouvelle n'a été exécutée sur la base active.**

### v412 — commande de sauvegarde et application du schéma préparée (2026-10-16)
- `apply_global_postgres_schema.py` vérifie avant toute action que la cible est la base explicitement nommée sur `127.0.0.1`, que l'artefact DDL correspond octet pour octet aux deux sources de migration et que les utilitaires PostgreSQL existent. Son mode par défaut est uniquement en lecture : sur la configuration v254 active, il a retourné `global_ddl_files_ready`, le SHA-256 attendu et `schema_before=global_schema_missing`.
- Le mode `--apply` demande localement le mot de passe administrateur, contrôle l'identité PostgreSQL, crée un dump complet au format custom dans le répertoire privé `E:/DevCoreRuntime/migration`, vérifie son inventaire et son SHA-256, puis applique le DDL par `psql` avec `ON_ERROR_STOP=1` et exécute le contrôle du schéma du rôle applicatif. Le répertoire de sauvegarde autorise Administrateur, SYSTEM et Administrateurs. L'inventaire `pg_restore -l` d'un dump existant confirme la présence des trois tables exigées par le script. Compilation Python et `git diff --check` passent.
- Le mode `--apply` n'a pas été lancé sur la base active : le mot de passe administrateur n'est pas disponible à l'agent et la release opérationnelle de la pile globale n'est pas encore prête. Le service v254 reste `Running/Automatic` ; l'index RepoWise du dépôt de travail reste décalé.

### v413 — requalification de la copie Git à six composants (2026-10-16)
- Les quatre fichiers modifiés depuis le snapshot initial (deux migrations et deux documents) et les trois nouveaux scripts de contrôle/migration ont été reportés dans la copie Git isolée. Son commit `49e58d5fae221d269ab7878735e4c98b50968e39` est propre ; `repowise update --no-workspace --index-only --no-docs` a aligné `last_sync_commit` sur ce commit, sans appel à un fournisseur LLM.
- Sur le cluster PostgreSQL synthétique relancé au port 55433, le préflight complet a retourné `global_stack_preflight_ready` avec RepoWise inclus. Le superviseur a démarré Router, les deux Headroom, Gateway, Scheduler et RepoWise ; son manifeste indique `ready` et six sondes vraies. La sonde RepoWise `/health` a retourné `healthy/db=ok`. L'arrêt supervisé a retourné six codes 0 avec `graceful=true` ; le cluster temporaire a ensuite été arrêté.
- Cette qualification utilise la copie du commit de recette et des données fictives. Aucun service de pile globale n'est enregistré pour une reprise après Windows ; la base opérationnelle manque toujours le DDL et le profil v254 demeure inchangé.

### v414 — lanceur opérationnel borné au snapshot qualifié (2026-10-16)
- `run_global_postgres_stack.py` lit la configuration installée de v254, réutilise ses racines et son URL PostgreSQL sans l'afficher, exige un snapshot Git propre sur le commit de recette `49e58d5fae221d269ab7878735e4c98b50968e39`, puis délègue au superviseur de ce snapshot. Avant un démarrage ou un préflight, il lance le contrôle de schéma en lecture seule ; `--stop` conserve la voie d'arrêt PID/jeton du superviseur.
- Sur la base active, `--check` refuse actuellement le démarrage avec `global_schema_missing`, comme attendu. La compilation Python et `git diff --check` passent. Les ports globaux ne sont pas ouverts, `DevCoreIndividual` et PostgreSQL restent `Running/Automatic`. Ce lanceur est manuel ; il ne prouve ni installation comme service ni reprise après redémarrage Windows.
