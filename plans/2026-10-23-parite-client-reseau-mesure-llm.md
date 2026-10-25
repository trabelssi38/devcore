# DevCore — parité historique, client réseau et mesure des modèles

Date : 23 octobre 2026. Statut : plan proposé, non exécuté.

Point d'arrêt du 25 octobre : le pilote `devcore` du plan hooks/jobs a sa sortie
de phase 5 vérifiée (runs naturels, Cockpit sous `majdi`, reboot, reprise après
panne et retour arrière). Ses deux schedules quotidiens sont désormais
`disabled`, sans prochaine échéance ; leur historique est conservé. La phase 6
du plan précédent, consacrée à l'agent autonome, n'a pas été déclenchée. Ce
constat prépare l'admission P0 mais ne valide aucune phase P0–P9 ci-dessous.
La source active est une candidate Git figée distincte du dépôt de travail.
Son contenu `DEV_CORE/`, sauf deux scripts historiques à mots de passe en dur,
et la documentation du pilote sont publiés sur
`codex/devcore-hooks-jobs-20261025`. Le dépôt de travail comporte encore des
modifications locales non publiées. Les preuves du pilote décrivent donc ce
poste, pas une installation reproductible depuis `main` seul.

## Déclenchement et objectif

Exécuter ce plan après la clôture factuelle du
[plan hooks et jobs](2026-10-19-hooks-jobs-phases.md). Ses phases 0 à 5 doivent
avoir leurs preuves de sortie ; sa phase 6 optionnelle doit porter une décision
explicite (réalisée séparément ou hors périmètre), sans bloquer par défaut cette
suite. Une date, un board terminé ou la présence de code ne constituent pas une
preuve de qualification. Ce document n'active aucun service, hook ou modèle.

Objectif : établir ce que le nouveau DevCore reprend réellement de l'ancien,
terminer les reprises retenues, livrer un client réseau reproductible et mesurer
l'effet sur les modèles natifs et auxiliaires à qualité comparable.

La demande utilisateur du 23 octobre couvre les dix points du tableau de §2,
ainsi que l'installation, les responsabilités serveur/client, le routage
auxiliaire explicite et l'optimisation des appels natifs discutés dans le fil.

## 1. État de départ et sources

Constats de préparation, à réévaluer au lancement :

- Le profil équipe utilise API commune et PostgreSQL ; le profil historique
  SQLite/JSON reste distinct. Aucune parité intégrale n'est établie.
- Le dépôt est `E:/src_python/devcore`. La tâche Windows `DevCoreGlobal`
  désigne une source figée sous `E:/DevCoreRuntime/qualification/` et un
  environnement versionné distinct ; le répertoire nommé `qualification` peut
  donc contenir le pilote actif. Ne pas le traiter comme un dossier jetable.
- La configuration relue utilise `runtime/state/local` et `runtime/state/data`
  sous `service-profile-v250-postgres`. Les anciens dossiers ne sont pas tous
  matérialisés dans ces racines ; cela ne prouve ni perte ni migration.
- Le listener LAN observé est `172.16.210.32:20129`. Les contrôles HTTPS de second
  poste ne démontrent pas le parcours Codex/MCP complet ni sa santé future.
- Les pertes de santé RepoWise et la récupération automatique restent ouvertes
  dans le journal v486–v492. Réutiliser les résultats ultérieurs du plan préalable.
- Le contexte borné en octets, les compteurs client et les métriques fournisseur
  sont des mesures différentes. Aucun gain réel de tokens n'est établi.
- Le code `postgres_llm_usage.py` enregistre actuellement l'usage Gemini ; sa
  présence n'établit pas une collecte universelle de l'usage natif.
- Le contrat de routage sépare 8787 natif, 8789 auxiliaire, 20130 Router et les
  embeddings. Le passage réel de Codex Desktop par 8787 n'est pas prouvé.
- Le compacteur de leçons utilise un alias auxiliaire explicite. Une
  automatisation peut choisir cet alias sans dialogue utilisateur à chaque run ;
  cela n'autorise pas une substitution silencieuse du modèle Codex.

Sources à lire de manière ciblée :

- `docs/project-context/context.json`, fiche et décisions applicables via le
  lecteur borné ; ne pas réappliquer les décisions remplacées.
- [plan multiutilisateur](2026-10-01-devcore-local-multiutilisateur.md), sections
  L1/L2/L4/L5/L7/L8/L9 pertinentes, et journal des preuves les plus récentes.
- [inventaire hooks/jobs](../docs/audit-2026-09-30/hooks-jobs-inventory-2026-10-19.md).
- [séparation LLM](../docs/audit-2026-09-30/separation-llm-2026-10-04.md).
- [protocole tokens Codex](../docs/audit-2026-09-30/protocole-tokens-codex.md).
- `docs/project-context/README.md`, `DEV_CORE/Config/mcp-individual.example.toml`,
  `DEV_CORE/Scripts/run_global_postgres_stack.py`, `router/policy.py`,
  `Auto/memory_compactor.py`, `Auto/token_report.py`, `compare_codex_usage.py`,
  `devcore_engine/services/postgres_llm_usage.py` et leurs tests.

RepoWise consulté lors de la préparation : HEAD indexé annoncé `d54a91944e95`,
âge annoncé neuf jours, embedder mock, recherche sémantique désactivée ; dates
relatives incohérentes et fichier d'usage PostgreSQL sans fiche indexée. Les
constats ci-dessus reposent aussi sur les fichiers locaux. Recontrôler index,
commit, modifications non commitées et couverture avant toute conclusion.

## 2. Couverture obligatoire de la demande

| Point | Phases (identifiants) | Preuve de clôture attendue |
| --- | --- | --- |
| Équivalence avec l'ancien DevCore | P1, P9 | Matrice fonctionnelle exhaustive, chaque fonction conservée testée ou remplacement/abandon justifié |
| Migration de DEV_CORE_LOCAL | P1, P2, P9 | Inventaire, réconciliation, import rejouable, rollback ; ancien dossier conservé |
| Memory, Knowledge, Learning, Vault | P3 | Contenus et provenance repris, consommateurs équipe vérifiés, isolation prouvée |
| Plugins, Skills, Refs | P4 | Catalogue, emplacements, compatibilité, distribution et révocation qualifiés |
| Bus et Workflows | P5 | Contrats et scénarios historiques comparés, reprise/déduplication qualifiées |
| Métriques | P7 | Usage, dépassements et conformité par projet avec sources, couverture et limites |
| Client réseau Codex | P6 | Installation sur second PC et conversation neuve de bout en bout |
| RepoWise partagé | P6 | Décision documentée local/central/hybride ; qualification de la solution retenue |
| Stabilité du serveur | P0, P9 | Preuves héritées vérifiées, lacunes corrigées, panne et récupération automatiques observées |
| Économie de tokens | P7, P8 | Essais comparables répétés, qualité et consommation totale documentées |

## 3. Règles d'exécution

### Apports ECC retenus — complément du 23 octobre 2026

Source d'inspiration examinée : [ECC, commit 90606c8](https://github.com/affaan-m/ECC/tree/90606c8315ee09cafc303515c5f33024db6b9882),
version déclarée 2.2.3. Analyse statique, sans installation ni qualification de
ses hooks. Reprendre les mécanismes utiles dans les contrats DevCore ; aucune
installation globale d'ECC, modification de configuration client ou activation
d'observateur n'est impliquée par cette mise à jour du plan. Tout code repris
doit porter sa provenance, son commit et les mentions requises par sa licence MIT.

| Apport retenu | Phases | Priorité et preuve attendue |
| --- | --- | --- |
| Collecte d'usage depuis les sources client disponibles | P6, P7, P8 | Priorité 1 : provenance, cache, déduplication et couverture vérifiés avant tout gain annoncé |
| Évaluation réelle et télémétrie des skills | P4, P7, P8 | Priorité 2 : résultats par version et critères de tâche, remplacement du score fixe historique |
| Leçons atomiques proposées avec preuves | P3, P4, P8 | Priorité 3 : validation, révocation et isolation ; aucune promotion automatique en décision obligatoire |
| Reprise de session liée au worktree | P3, P6, P8 | Priorité 4 : restauration exacte, fraîcheur et conservation des originaux |
| Contrôles légers après modification | P4, P5, P6, P9 | Complément : outils locaux détectés, délais bornés et résultats explicites sans exécution en double |

Les priorités indiquent la valeur recherchée, sans changer l'ordre P0–P9.
La conception du contrat de mesure et du corpus d'évaluation peut commencer après
P1 ; toute modification d'optimisation reste inactive dans la référence de P8.
PostgreSQL, l'API commune, les droits par projet et le moteur durable conservent
leurs responsabilités. Les fichiers locaux ECC ne deviennent pas un stockage
transactionnel concurrent. La compatibilité des événements doit être prouvée
pour chaque client/version ; un hook Claude Code n'est pas réputé compatible Codex.

### Contraintes communes

1. Préserver l'état Git existant. Avant chaque phase : état Git, contexte obligatoire,
   journal ciblé, code et tests pertinents ; identifier les changements du lot.
2. Vérifier Python 3.13 de recette à
   `E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe`.
   Définir `DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires avant imports
   et sous-processus. PostgreSQL temporaire, dépôts synthétiques et index
   RepoWise de recette uniquement ; aucune donnée active ou Dropbox en fixture.
3. Lecture d'inventaire des données actives autorisée sans mutation ni diffusion
   de secrets. Migration et panne : répétition sur copies, sauvegarde vérifiée,
   candidate figée et rollback avant opération réelle.
4. PostgreSQL reste la seule source transactionnelle de l'instance équipe.
   Un document, une archive, un cache ou un index ne devient pas une seconde
   autorité. Identités et projets sont contrôlés côté serveur.
5. Conserver `DEV_CORE_LOCAL` et les archives durant tout ce plan. Sa suppression
   n'est pas une sortie de ce travail ; elle nécessiterait une décision distincte.
6. Ne jamais stocker prompts, réponses, mots de passe ou jetons dans les rapports
   d'usage par défaut. Documenter collecte, accès et rétention des métadonnées.
7. Garder fournisseur/modèle natifs ; auxiliaire choisi explicitement. Les droits
   techniques de déploiement ne constituent pas une décision de changer de modèle.
   OpenAI/Anthropic réels restent hors du périmètre courant : préparer les sondes
   simulées, puis obtenir l'extension explicite du périmètre avant ces appels.
8. Pour les opérations élevées, lancer directement PowerShell 7 via
   `Start-Process -Verb RunAs -Wait`, conformément à AGENTS.md ; les saisies
   Windows et secrets restent locales. Aucun lancement reporté sur l'utilisateur.
9. Chaque phase distingue « défini », « implémenté », « testé en isolation »,
   « déployé » et « observé en usage réel ». Signaler les blocages et poursuivre
   seulement les travaux indépendants ; ne pas cocher une sortie sans preuve.

## Phase 0 — Admission et reprise des preuves du plan précédent

Identifiant de suivi : `P0`. Statut : à démarrer.

**Objectif :** Vérifier la clôture du plan hooks/jobs et les preuves de stabilité.

**Prérequis :** Clôture documentée des phases 0–5 du plan précédent et décision sur sa phase 6 optionnelle.

**Travaux à réaliser :**

- [ ] Relever la clôture des phases 0–5 et la décision de phase 6 optionnelle.
- [ ] Enregistrer commit du dépôt, modifications locales, source déployée,
  version Python, configurations effectives et identités des services.
- [ ] Vérifier schedules, derniers runs, échéances, état de la pile et
  observations du second poste ; distinguer succès manuel et échéance naturelle.
- [ ] Reprendre les preuves de reboot, panne en cours d'exécution, relance Windows,
  arrêt coopératif, processus orphelins, disponibilité PostgreSQL et RepoWise.
- [ ] Si des lacunes persistent : diagnostiquer avant correction, définir les
  délais de sonde/reprise et le budget de relance, tester d'abord sur pile isolée.
  Observer ensuite une récupération sans intervention et sans duplication de job.
- [ ] Fixer le seuil proposé de stabilité à 48 heures incluant deux échéances
  naturelles ; enregistrer incidents, indisponibilité et éventuelles reprises
  manuelles. Adapter la fenêtre par décision motivée avant l'essai.

Livrable : `docs/audit-2026-09-30/post-hooks-admission-2026-10-23.md`.
Sortie : preuves actuelles, limites explicites ; aucune clôture de stabilité
fondée seulement sur HTTP 200 ou un manifeste `ready`.

## Phase 1 — Matrice de parité et cartographie des installations

Identifiant de suivi : `P1`. Statut : à démarrer.

**Objectif :** Établir la liste exhaustive des fonctions et leur emplacement ancien/nouveau.

**Prérequis :** Phase 0 validée.

**Travaux à réaliser :**

- [ ] Inventorier chacun des quinze dossiers historiques : Bus, Dashboard,
  Knowledge, Learning, Logs, Memory, Metrics, Plugins, Projects, Refs, Security,
  Skills, Vault et Workflows. Relever taille, formats, dates, propriétaires,
  références de code, déclencheurs et fonctions réellement utilisées.
- [ ] Pour chaque fonction : ancien producteur/consommateur, nouveau service/API,
  stockage, emplacement serveur/client, droits, état et preuve de test.
- [ ] Décider : conserver, remplacer, importer, archiver ou option future.
  Une absence de dossier n'est pas une preuve d'absence fonctionnelle ; une table
  existante n'est pas une preuve d'alimentation ou d'utilisation.
- [ ] Décrire les racines effectives : dépôt, source figée, Python/release,
  PostgreSQL, état, logs, caches, secrets, workspaces, artefacts et sauvegardes.
  Identifier les références résiduelles à LOCALAPPDATA/DEV_CORE_LOCAL/Dropbox.
- [ ] Corriger les documents présentant comme automatiques le routage Codex,
  la migration complète ou la centralisation de RepoWise sans preuve.

Livrables : `legacy-parity-matrix-2026-10-23.md` et
`runtime-client-storage-map-2026-10-23.md` dans le répertoire d'audit.
Sortie : quinze dossiers couverts, aucune fonction utile sans décision et aucun
chemin implicite non recensé. Les abandons utiles à l'utilisateur sont explicites.

## Phase 2 — Migration des données et réversibilité

Identifiant de suivi : `P2`. Statut : à démarrer.

**Objectif :** Préparer et qualifier la reprise des données sans perte ni double producteur.

**Prérequis :** Matrice de parité de phase 1 validée et sources à reprendre identifiées.

**Travaux à réaliser :**

- [ ] Identifier les sources historiques concurrentes, dont SQLite/JSON,
  conversations, missions, leçons, notes, graphes, pièces jointes et références.
- [ ] Établir un manifeste sur copie cohérente : empreintes, volumes, clés,
  encodages, fuseaux, relations et correspondance ancien ID → projet/utilisateur.
- [ ] Définir les cas ambigus sans affectation automatique au projet `devcore` :
  quarantaine documentée, conflits, doublons, orphelins et provenance conservée.
- [ ] Préparer une prévisualisation sans écriture, les migrations versionnées et
  un import idempotent ; vérifier comptes et intégrité avant/après/rejeu.
- [ ] Répéter sauvegarde/restauration sur cible isolée et mesurer interruption,
  conservation des nouveaux événements et stratégie de rollback après écritures.
- [ ] Après répétition réussie : préparer le gel coordonné des producteurs
  historiques, le delta final, les vérifications et la bascule des consommateurs.
  Exécuter les opérations réelles uniquement dans le périmètre autorisé du lot.
- [ ] Maintenir l'ancien dossier comme archive protégée ; neutraliser uniquement
  les producteurs remplacés après preuve, sans effacer les contenus.

Livrables : manifeste, rapport de réconciliation et procédure de migration/retour.
Sortie : aucune perte silencieuse, aucun double producteur actif, refus explicite
des données non réconciliées et preuve de restauration.

## Phase 3 — Memory, Knowledge, Learning et Vault

Identifiant de suivi : `P3`. Statut : à démarrer.

**Objectif :** Rendre les connaissances reprises accessibles et isolées dans le profil équipe.

**Prérequis :** Données nécessaires de phase 2 réconciliées et restaurables.

**Travaux à réaliser :**

- [ ] Cartographier conversations, memory_entries, knowledge_items, graphes,
  embeddings, leçons et notes ; distinguer fiche/décisions, mémoire et index.
- [ ] Raccorder les producteurs et lecteurs retenus au profil équipe ; vérifier
  la persistance, l'alimentation réelle et l'utilité dans une conversation neuve.
- [ ] Préserver source, commit/date, auteur, projet, confiance et statut de revue ;
  une extraction automatique ne devient pas une décision validée.
- [ ] Qualifier deux utilisateurs/deux projets : recherche, exports, citations,
  graphes et refus interprojets, y compris lorsque les sources ont des noms proches.
- [ ] Vérifier dimensions/version des embeddings, reconstruction de recette,
  indisponibilité fournisseur et repli lexical ; un index périmé doit être signalé.
- [ ] Qualifier résumé/compactage : déclencheur et quota explicites, sauvegarde,
  provenance, conservation des décisions, absence de pollution entre projets,
  résultat invalide ou fournisseur en panne conservant l'original.
- [ ] Vérifier Vault/Obsidian et références de fichiers sur second poste : chemins
  portables, droits, notes par projet et absence d'écriture concurrente non gérée.
- [ ] Définir des leçons atomiques : déclencheur, action, preuves liées aux
  observations, auteur/extracteur, version, projet, confiance justifiée et revue.
  Cycle : observation → proposition → validation → règle ou skill évalué.
  Prévoir contradiction, expiration, révocation et retour arrière ; aucune
  promotion globale implicite ni modification automatique des décisions obligatoires.
- [ ] Qualifier l'extraction sur corpus synthétique : correction utilisateur,
  résolution d'erreur et répétition ; une occurrence répétée n'est pas une preuve
  de vérité. Protéger les contenus sensibles, appliquer droits et rétention ;
  les exports de métriques n'incluent pas les transcriptions. Tout appel auxiliaire
  conserve alias autorisé, quota, provenance et usage séparé.
- [ ] Définir un instantané de reprise de session : identité utilisateur/projet,
  session, racine canonique du worktree, commit et modifications locales connues,
  objectif, travaux restants, vérifications et références aux décisions applicables.
  Borner son volume, dater sa fraîcheur et conserver l'original avant compactage.
  Refuser une restauration dans un autre projet/worktree ; qualifier worktrees
  homonymes, session concurrente, résumé invalide et absence d'événement précompactage.
  Un résumé de session complète la fiche obligatoire sans la remplacer.

Livrable : rapport mémoire/connaissances avec corpus de questions et preuves de
lecture réelle. Sortie : chaque contenu retenu est retrouvable et traçable ; les
fonctions non reprises portent un état explicite, jamais une réussite fictive.

## Phase 4 — Plugins, Skills et Refs

Identifiant de suivi : `P4`. Statut : à démarrer.

**Objectif :** Définir et qualifier la distribution des extensions, instructions et références.

**Prérequis :** Phase 3 validée et cartographie serveur/client disponible.

**Travaux à réaliser :**

- [ ] Construire un catalogue versionné : origine, licence si nécessaire,
  dépendances, version, empreinte, plateforme et privilèges.
- [ ] Séparer les extensions serveur des instructions/outils du client Codex ;
  ne pas supposer qu'un dossier Skills serveur installe une compétence dans Codex.
- [ ] Définir installation, découverte, mise à jour, retrait et restauration,
  ainsi que la résolution des références locales sur un autre PC.
- [ ] Remplacer les chemins absolus du poste administrateur et isoler secrets et
  configurations personnelles ; le paquet public ne contient aucun credential.
- [ ] Tester installation et mise à niveau sur poste propre, dépendance absente,
  artefact modifié, retrait de droits et retour à une version précédente.
- [ ] Remplacer le score fixe `0.95` de `SkillService.evaluate_skill()` par un
  résultat non évalué tant qu'aucune preuve n'existe, puis des évaluations
  versionnées : corpus, critères de réussite définis avant exécution, vérificateurs,
  résultats et limites. Distinguer lint, invocation réussie et réussite de tâche.
  Enregistrer ces résultats dans le profil équipe via API/PostgreSQL et droits projet.
- [ ] Définir le contrat d'exécution d'un skill : identifiant/version/empreinte,
  client, projet/utilisateur/session/run attribuables, début/fin, durée, statut,
  vérifications et corrections nécessaires. Usage joint seulement si observable ;
  appels non reconnus ou non attribuables visibles, sans inventer de réussite.
- [ ] Préparer des contrôles légers après modification : détection des outils du
  projet, fichiers concernés, timeout et statuts réussi/échoué/non disponible.
  Mode contrôle par défaut, correction explicite et réversible ; éviter les
  doublons avec hooks existants, la relance récursive et les tests globaux à chaque
  édition. Vérifier l'effet réel du code de sortie, sans supposer un blocage client.

Livrables : catalogue et matrice de compatibilité serveur/client.
Sortie : chaque élément retenu a un emplacement et un cycle de distribution prouvés.

## Phase 5 — Bus, Workflows et parité des comportements

Identifiant de suivi : `P5`. Statut : à démarrer.

**Objectif :** Combler les écarts de comportement des événements et exécutions durables.

**Prérequis :** Phase 4 validée et contrats hooks/jobs hérités vérifiés.

**Travaux à réaliser :**

- [ ] Comparer anciens événements/files et workflows au moteur durable : états,
  ordre, délais, annulation, retries, sorties, effets externes et traitement manuel.
- [ ] Réutiliser les contrats hooks/jobs du prédécesseur, identifier les seuls
  écarts fonctionnels restants et implémenter les adaptateurs nécessaires.
- [ ] Qualifier doublon, réponse perdue, crash entre effet et acquittement,
  redémarrage de worker, bail expiré, fencing et concurrence multiutilisateur.
- [ ] Contrôler propagation user/project/run/trace, droits à l'admission et après
  retrait, refus de projet archivé et arrêt de l'arborescence de processus.
- [ ] Vérifier qu'un statut historique ou une tâche active ne lance pas un agent
  autonome ; toute autonomie reste soumise à la décision séparée du prédécesseur.
- [ ] Raccorder les événements de skills, contrôles et instantanés de session aux
  contrats existants plutôt qu'à un second bus ; qualifier rejeu, ordre inversé,
  timeout et crash entre contrôle et publication. L'échec d'un collecteur reste
  visible et ne devient pas une réussite de tâche.

Livrable : scénarios ancien/nouveau et résultats. Sortie : effets non dupliqués,
historique cohérent et limites de garantie documentées sans promesse « exactly once » globale.

## Phase 6 — Client réseau Codex et choix RepoWise

Identifiant de suivi : `P6`. Statut : à démarrer.

**Objectif :** Livrer un client reproductible et prouver le parcours depuis un autre poste.

**Prérequis :** Phases 0–5 validées et services nécessaires disponibles sur la candidate.

**Travaux à réaliser :**

- [ ] Définir le paquet minimal Windows : Python compatible, connecteur MCP,
  dépendances verrouillées, manifeste d'intégrité, exemples TOML et désinstallation.
  Vérifier les imports hors du dépôt serveur avant de promettre un client autonome.
- [ ] Fournir diagnostic et configuration paramétrables : URL HTTPS, certificat,
  projet, credential privé NTFS, délais et outils de lecture/écriture autorisés.
- [ ] Provisionner un compte distinct, appartenance projet et jeton de portée
  minimale ; tester expiration, rotation, révocation, ACL du fichier et certificats.
  Ne jamais partager le jeton de l'administrateur ou celui du service serveur.
- [ ] Vérifier l'origine LAN, pare-feu et renouvellement du certificat ; clients
  sans accès direct PostgreSQL/RepoWise serveur/ports internes. Garder les modèles
  natifs et l'authentification Codex indépendants des identifiants DevCore.
- [ ] Valider les supports réels Codex Desktop/extension/CLI ciblés et leur
  configuration effective ; relire la documentation officielle au moment du lot.
- [ ] Qualifier sur second PC une conversation neuve : découverte des outils,
  contexte borné, décisions, statut, mutation autorisée si prévue, refus autre
  projet, perte réseau, reconnexion, serveur indisponible et retour d'erreur clair.
- [ ] Vérifier AGENTS.md portable et absence de repli vers les données historiques
  locales ou d'accès à une base sans API. Documenter renouvellement et dépannage.
- [ ] Établir une matrice de capacités par client/version : événements de session,
  précompactage, outils et skills, format des transcriptions et compteurs exposés.
  Tester chaque adaptateur sur fixtures synthétiques versionnées, puis sur le
  client retenu dans le périmètre autorisé. Une capacité absente reste explicite.
- [ ] Qualifier la reprise après reconnexion ou nouvelle session sur second poste :
  association authentifiée au projet/worktree, chemins portables et détection du
  commit divergent. Ne pas injecter automatiquement un instantané ambigu ou périmé.
- [ ] Pour RepoWise, comparer local, central et hybride : confidentialité, racines
  Git, droits, différences non commitées, version/commit d'index, coût et fraîcheur.
  Ne pas transformer la recommandation locale du fil en décision d'architecture.
- [ ] Si local retenu : qualifier installation MCP, index par dépôt et changements
  locaux. Si central retenu : implémenter admission authentifiée via frontière
  autorisée, isolation des index et gestion de leur fraîcheur ; aucun port interne
  ouvert directement comme raccourci. Sinon documenter l'option différée.

Livrables : paquet versionné, guide second poste, diagnostic sans secret et décision
RepoWise. Sortie : parcours Codex réel prouvé, installation rejouable, restauration
de configuration vérifiée ; HTTPS seul ne clôture pas ce lot.

## Phase 7 — Mesure des modèles natifs, auxiliaires et conformité

Identifiant de suivi : `P7`. Statut : à démarrer.

**Objectif :** Mesurer les usages observables et rendre visibles les sources manquantes.

**Prérequis :** Parcours client de phase 6 qualifié et identités/projets attribuables.

**Travaux à réaliser :**

- [ ] Construire la matrice client/transport/authentification : Codex abonnement,
  Codex API si autorisé, autres IDE retenus ; direct ou proxy, HTTP/SSE/WebSocket,
  source de compteurs disponible et couverture réellement qualifiée.
- [ ] Observer le chemin natif sans modifier la configuration : compteurs Codex,
  processus et preuves de requête sans secret. Ne pas déduire le passage par
  Headroom de OPENAI_BASE_URL ni assimiler l'API abonnement à une clé API.
- [ ] Prioriser une collecte passive des compteurs disponibles. Un proxy natif
  est une option conditionnelle à la compatibilité, au périmètre fournisseur et
  aux tests ; il n'est pas nécessaire à la mesure hors ligne des rollouts.
- [ ] Définir un événement d'usage versionné : identifiant/idempotence, source,
  user/project/session/run/task lorsque prouvés, route, fournisseur, modèle demandé
  et observé, dates, durée, statut, entrée/sortie/cache/raisonnement si exposés.
  Définir les relations entre compteurs pour éviter de sommer des sous-ensembles.
- [ ] Distinguer provider_reported, client_observed, estimated et unavailable.
  Valeur absente ≠ zéro ; compteur cumulatif ≠ delta ; modèle demandé ≠ modèle
  attesté. Une baisse/reset de compteur rend la couverture explicite/incomplète.
- [ ] Relier les événements client et proxy par preuve, jamais par proximité de
  date seule ; ingestion rejouable sans double comptage. Conserver l'usage non
  attribuable dans une catégorie distincte, sans projet par défaut.
- [ ] Étendre si nécessaire le stockage PostgreSQL au-delà du seul Gemini, avec
  migration versionnée, ACL dédiées, rétention et export. Vérifier si `task.mutate`
  reste adapté à l'écriture d'usage ou doit devenir une permission distincte.
- [ ] Comptabiliser séparément retries, tentatives échouées, génération auxiliaire,
  embeddings, indexation RepoWise et sous-agents si utilisés ; inconnus visibles.
- [ ] Qualifier la route auxiliaire : seuls alias autorisés, choix/configuration
  explicite de l'appelant, correspondance modèle versionnée et refus des modèles
  natifs. Tester timeouts, 429, annulation, stream incomplet et usage absent.
  Aucun secours par défaut ; secours demandé et pris en charge tracé séparément.
- [ ] Vérifier les consommateurs réels : compacteur, bulk et endpoint équipe Gemini.
  Distinguer raccordement en code, déploiement et exécution fournisseur observée.
- [ ] Définir budgets par projet/période, dépassement et politique alerte/blocage
  explicite. Éviter qu'une estimation déclenche silencieusement un blocage dur.
- [ ] Définir les règles de conformité agent : projet explicite, décisions chargées,
  identité, attribution, modèle préservé, résultats requis. Pour chaque règle,
  préciser preuve, version, états conforme/non conforme/non observable et limites.
- [ ] Publier dans le Cockpit usage et couverture, dépassements et conformité par
  projet ; distinguer aucune activité, source manquante et échec de collecte.
  Pas de « 100 % conforme » si les événements ne sont pas tous observables.
- [ ] Prix : registre daté par modèle et unité, source officielle relue à l'exécution.
  Coût API estimé distinct de facture ; tokens Codex distincts du quota ou du prix
  d'abonnement. Ne pas appliquer les constantes historiques à tous les modèles.
- [ ] Pour les transcriptions client accessibles et autorisées, extraire uniquement
  les métadonnées d'usage nécessaires ; ne pas les recopier intégralement au serveur.
  Qualifier messages fragmentés partageant un ID, événements Stop répétés,
  reprise de session, rotation/troncature, format inconnu et cache. Stocker la
  version d'adaptateur et le curseur de collecte ; réconcilier totaux/deltas sans
  compter deux fois une réponse ou une session. Une lecture impossible ne vaut pas zéro.
- [ ] Publier la santé des skills dans le Cockpit : version, nombre d'exécutions
  observées, échecs techniques, réussites de tâche vérifiées, durée et couverture.
  Séparer absence de données et succès ; un appel d'outil sans erreur ne suffit
  pas à valider le résultat utilisateur. Relier aux preuves P4 et aux usages P7
  par identifiants attestés, sans inférence temporelle seule.

Tests à étendre selon les écarts : `test_token_report_codex_counters.py`,
`test_token_report_clients.py`, `test_token_report_project_scope.py`,
`test_compare_codex_usage.py`, `test_router_reported_usage.py`,
`test_router_stream_usage.py` et tests PostgreSQL d'isolation/ingestion.
Inclure rejeu, reset, session multi-projet, zéro explicite, données absentes,
annulation et événements partiels. Tests réseau fournisseur simulés par défaut.

Livrables : contrat d'usage, rapport de couverture natif/auxiliaire, migrations,
tests et vues Cockpit. Sortie : une mesure peut rester partielle, mais son périmètre
et ses inconnus sont visibles ; aucune estimation présentée comme un compteur réel.

## Phase 8 — Optimisation et expérience comparative

Identifiant de suivi : `P8`. Statut : à démarrer.

**Objectif :** Comparer les optimisations à une référence à qualité équivalente.

**Prérequis :** Contrat de mesure et couverture de phase 7 validés.

**Travaux à réaliser :**

- [ ] Établir une référence avant toute optimisation avec le protocole existant.
  Préparer au minimum six tâches représentatives : reprise de contexte, recherche
  de code, correction, modification multi-fichiers, documentation et mémoire.
- [ ] Prévoir au moins trois paires d'essais par tâche, conversations neuves et
  copies de dépôt au même commit. Alterner l'ordre des conditions et enregistrer
  versions client/modèle, effort, permissions, outillage et état du cache connu.
  Si ces conditions ne sont pas maîtrisables, le rapport doit le signaler.
- [ ] Référence et variante respectent toutes deux les décisions et instructions
  obligatoires : le gain ne doit pas provenir de leur suppression.
- [ ] Tester séparément : fiche bornée, recherche RepoWise ciblée, sorties outils
  limitées, réutilisation de résultats frais, suppression de doublons, puis cumul.
  Inclure les tokens des définitions/outils et de la collecte initiale observables.
- [ ] Évaluer le cache fournisseur à travers les compteurs disponibles ; préserver
  la stabilité des préfixes utiles. Ne pas confondre compression structurelle sans
  perte, résumé LLM avec perte possible et baisse du coût par token en cache.
- [ ] Comparer l'auxiliaire explicite au traitement natif pour les tâches adaptées :
  compteurs séparés, coût, durée et qualité finale. Le résumé peut omettre une règle :
  inclure un corpus de décisions/provenance et un refus de résumé non conforme.
- [ ] Changement de modèle/effort : expérience distincte et explicitement choisie,
  pas mélangée à l'effet du contexte. Ne pas remplacer automatiquement le modèle IDE.
- [ ] Pour un proxy natif retenu et autorisé, qualifier protocole/outillage,
  cache, erreurs, stream et annulation sans substitution de modèle ; publier un
  résultat « non qualifié » si le client réel ne prend pas ce chemin.
- [ ] Vérifier tests, exactitude, décisions, sécurité interprojets et complétude
  avec la même grille avant de déclarer chaque résultat accepté.
- [ ] Rapporter par tâche : tokens observés et couverture, cache/raisonnement selon
  disponibilité, nombre d'appels/retries, durée, qualité et coût lorsque calculable.
  Inclure les échecs, médiane et dispersion ; ne pas cacher les surconsommations.
- [ ] Calculer séparément gain de tokens natifs, variation par fournisseur et coût
  global connu incluant RepoWise/Gemini/embeddings. Les tokens de modèles différents
  ne constituent pas une unité économique équivalente ; ventilation obligatoire.
- [ ] Conclusion : gain démontré pour un périmètre nommé, neutre, régression ou
  inconclusif. Aucun pourcentage si les sources ou conditions sont incompatibles.
- [ ] Étendre le corpus aux apports ECC retenus : skill versionné avec/sans
  amélioration, leçon validée pertinente ou contradictoire, reprise au bon/mauvais
  worktree et contrôle léger. Mesurer chaque variante séparément avant combinaison ;
  inclure coût d'extraction, résumé et contrôles, latence et corrections utilisateur.
  Figer l'état de la mémoire entre essais, désactiver l'apprentissage pendant la
  référence et conserver les échecs ; aucune contamination entre conditions.
- [ ] Définir les critères et seuils d'acceptation avant les essais. Distinguer
  réussite en une tentative et fiabilité sur répétitions ; tout score comporte
  effectif, corpus et version de vérificateur. Un jugement LLM est identifié comme
  tel, avec fournisseur autorisé et usage comptabilisé ; préférer les vérifications
  déterministes lorsqu'elles établissent le résultat attendu.

Livrables : manifestes d'expérience, empreintes des sources, sorties du comparateur,
preuves qualité et rapport `native-auxiliary-token-benchmark-2026-10-23.md`.
Sortie : recommandations fondées sur les essais ; aucune cible de gain garantie.

## Phase 9 — Recette intégrée et mise en service progressive

Identifiant de suivi : `P9`. Statut : à démarrer.

**Objectif :** Qualifier ensemble les fonctions et déployer progressivement avec retour arrière.

**Prérequis :** Phases 0–8 validées dans leur périmètre, avec options différées documentées.

**Travaux à réaliser :**

- [ ] Relire toutes les lignes de la matrice P1 : fonction, contenu, droits,
  consommateurs et localisation ; les écarts encore ouverts restent visibles.
- [ ] Réaliser une recette deux utilisateurs/deux projets depuis deux postes,
  incluant sessions simultanées, mémoire, tâches, jobs, contexte, RepoWise et métriques.
- [ ] Vérifier les preuves de stabilité P0 après les changements : panne isolée,
  reprise automatique, redémarrage et schedules sans duplication ni dérive.
- [ ] Préparer candidate figée, sauvegarde restaurable, schéma compatible et retour
  arrière client/serveur sans perte des données produites après la bascule.
- [ ] Déployer sur le pilote `devcore`, puis un second projet après recette ;
  ne pas activer tous les projets ou anciens producteurs d'un seul coup.
- [ ] Observer 48 heures et deux échéances naturelles après bascule, y compris
  renouvellement des compteurs, défaut réseau et droits révoqués.
- [ ] Publier la matrice finale : repris et qualifié / partiel / remplacé /
  archivé / option future. Ne pas appeler « parité complète » un périmètre réduit.
- [ ] Actualiser fiche et registre de décisions uniquement sur preuves et décisions
  réelles ; conserver `DEV_CORE_LOCAL`, procédures d'exploitation et limites.
- [ ] Inclure dans la recette intégrée le retrait d'un skill, la révocation d'une
  leçon, l'instantané d'un autre worktree refusé, la collecte indisponible et le
  contrôle expiré. Vérifier rollback des adaptateurs et absence d'installation ECC
  globale ou d'observateur autonome activé implicitement.

Sortie : dossier de recette avec résultat go/no-go motivé, limites restantes et
guide utilisateur installable. Aucun service déclaré qualifié sur le seul nombre
de tests ou de tâches terminées.

## 4. Passage entre phases, suivi et commande de reprise

Ordre : P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → P9.

Les identifiants P0–P9 correspondent aux phases 0–9 et restent stables pour les rapports.

| Phase | Résultat permettant le passage à la suivante |
| --- | --- |
| 0 — Admission et stabilité | Prérequis hooks/jobs vérifiés, stabilité prouvée et limites consignées |
| 1 — Parité et architecture | Matrice des quinze dossiers et décision pour chaque fonction |
| 2 — Migration | Réconciliation, import rejouable et restauration prouvés |
| 3 — Mémoire et connaissances | Contenus retrouvables, provenance et isolation vérifiées |
| 4 — Extensions et références | Installation, distribution, mise à jour et retrait qualifiés |
| 5 — Événements et workflows | Scénarios historiques repris ou remplacés, reprise et déduplication vérifiées |
| 6 — Client réseau et RepoWise | Conversation Codex réelle sur second poste et architecture RepoWise décidée |
| 7 — Mesure et conformité | Compteurs et couverture qualifiés, attribution et limites visibles |
| 8 — Optimisation | Comparaison répétée, qualité revue et bilan natif/auxiliaire documenté |
| 9 — Recette et déploiement | Recette intégrée, observation après bascule et retour arrière vérifiés |

Une phase passe de **à démarrer** à **en cours**, puis **qualifiée** seulement
lorsque ses critères de sortie et ses preuves sont consignés. Une option différée
est nommée et justifiée ; une fonction obligatoire non qualifiée laisse la phase
**partielle** ou **bloquée** et ne permet pas de déclarer le plan terminé.
La préparation documentaire d'une phase suivante peut avancer sans franchir son
gate de qualification. Aucun passage de phase ne repose sur le seul nombre de tests.

Les inventaires de P3–P7 peuvent être préparés après P1 ; les qualifications
dépendent des données/contrats correspondants. Cet ordre ne demande pas de
subagents, ne crée pas d'automatisation et ne lance pas le plan aujourd'hui.

Pour chaque phase, tenir une ligne : ID, prérequis, commit, décision, statut,
livrables, tests/commandes, résultat réel, limites, rollback et prochaine action.
Rapports dans `docs/audit-2026-09-30/`, données de recette sous racines dédiées
temporaires. Les noms datés de rapports de ce plan identifient le chantier ;
chaque preuve doit aussi porter sa date réelle d'exécution.

Instruction de reprise proposée :

> Exécute `plans/2026-10-23-parite-client-reseau-mesure-llm.md` après avoir vérifié
> la clôture du plan `2026-10-19-hooks-jobs-phases.md`. Charge d'abord le contexte
> obligatoire, préserve Git et les données historiques, puis avance phase par phase.
> Réutilise les preuves encore valides, implémente les écarts retenus et qualifie
> les parcours réels. N'annonce aucun gain de tokens ni parité sans mesures.
> Respecte le périmètre fournisseur courant et consigne toute limite bloquante.
