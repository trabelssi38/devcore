# Reprise des hooks et jobs DevCore — plan par phases

Date : 19 octobre 2026. État revu le 25 octobre : phases 0 à 4 qualifiées en isolation ; sortie de phase 5 vérifiée pour le seul pilote `devcore`. Les deux schedules du pilote sont ensuite désactivés à la demande de l'utilisateur. L'extension à d'autres projets et la phase 6 optionnelle ne sont pas réalisées.

## Objectif et périmètre

Rétablir les fonctions encore utiles des anciens hooks et jobs dans le profil
équipe PostgreSQL, avec une attribution explicite à l'utilisateur et au projet,
une exécution durable et un état vérifiable dans le Cockpit. Ce plan complète
le [plan multiutilisateur](2026-10-01-devcore-local-multiutilisateur.md) ; il
ne réactive pas les archives SQLite/JSON ou Hermes.

État de départ : `Scheduler/jobs.devcore.json` définit huit jobs, tandis que
`Scripts/hermes_cron.yaml` en décrit huit avec une entrée différente. L'archive du 12 octobre conserve
12 245 résultats historiques et interdit l'activation de ses huit définitions.
Le profil équipe lance un dispatcher PostgreSQL, mais le dernier audit des
29 appartenances de `majdi` ne trouve aucune ligne dans `schedules`.
La carte « Automation Hooks » actuelle lit cette table et son historique,
pas les journaux de `task_sync`, `session_start` ou `session_end`.

Sources de référence :

- [archive et interdiction d'activation](../docs/audit-2026-09-30/scheduler-archive-2026-10-12.json) ;
- [registre JSON](../DEV_CORE/Scheduler/jobs.devcore.json) et [registre Hermes](../DEV_CORE/Scripts/hermes_cron.yaml) ;
- dispatcher PostgreSQL `DEV_CORE/devcore_engine/runs/postgres_schedules.py` et projection Cockpit `DEV_CORE/devcore_engine/services/postgres_dashboard.py` (sources locales du pilote, non incluses dans la publication documentaire) ;
- [revue opérationnelle](../docs/audit-2026-09-30/execution-2026-10-05.md), notamment v457–v460.
- [inventaire des déclencheurs installés et matrice de décision](../docs/audit-2026-09-30/hooks-jobs-inventory-2026-10-19.md).
- [contrat PostgreSQL des hooks et état de qualification](../docs/audit-2026-09-30/automation-hooks-contract-2026-10-19.md).

## Règles communes à toutes les phases

1. Le couple `user_id`/`project_id` provient de la session ou d'une identité
   serveur autorisée ; le dépôt doit être versionné par Git et enregistré.
   Refuser les jobs sans projet, sans droit ou visant un projet archivé.
2. PostgreSQL est la seule source transactionnelle du profil équipe. Les
   journaux historiques restent consultables comme archives, sans devenir un
   signal de santé ni déclencher une nouvelle exécution.
3. Les événements et les jobs portent identifiant, auteur, projet, source,
   date, statut, erreur et clé de déduplication. Un voyant « réussi » provient
   d'un résultat persisté, jamais de la simple création d'un fichier journal.
4. Les essais utilisent des racines `DEVCORE_LOCAL_ROOT` et
   `DEVCORE_DATA_ROOT` temporaires avant tout import ou sous-processus ; ni les
   données actives, ni Dropbox, ni les index RepoWise réels ne servent de
   fixtures.
5. Toute activation est réversible : inventaire avant/après, sauvegarde,
   candidat figé, sonde de santé, arrêt coopératif et procédure de retour à la
   version précédente. Ne pas activer simultanément l'ancien ordonnanceur et
   son remplacement.

## Phase 0 — Inventaire et décision fonctionnelle

- Relever les deux registres, les hooks Claude/Gemini/Codex/Git réellement
  installés, les tâches Windows et les processus sur le poste ; distinguer
  définition, activation et dernière exécution prouvée.
- Pour chaque ancien mécanisme, consigner déclencheur, entrées, écritures,
  dépendances, projet/utilisateur, doublon actuel et décision : reprendre,
  remplacer, archiver ou réserver à une option future.
- Vérifier les wrappers cités par Hermes et les divergences entre ses huit
  entrées et les huit définitions JSON. Ne pas déduire leur présence d'un nom
  dans YAML.

**Sortie attendue :** matrice exhaustive signée par des preuves de code et
d'exploitation, aucun job historique relancé. Les écarts de définition et les
effets encore non qualifiés sont explicitement listés.

**État : réalisé le 19 octobre 2026.** La matrice, les limites de portée et
les déclencheurs installés sont dans l'inventaire lié ci-dessus. Les chemins
inexistants des projets enregistrés restent un prérequis de leur activation.

## Phase 1 — Contrat de déclenchement et traçabilité

- Définir deux objets distincts : événement de cycle de vie (`session_start`,
  `session_end`, commit, changement de tâche) et planification temporelle
  (`schedules` PostgreSQL). Un hook événementiel ne devient pas artificiellement
  un cron.
- Définir l'admission par droits, l'idempotence par session/commit/échéance,
  le résultat terminal, les reprises après interruption et la rétention des
  historiques. Utiliser le moteur de runs durable existant pour les travaux
  longs et limiter les effets externes.
- Prévoir des statuts lisibles : jamais déclenché, en cours, réussi, échoué,
  désactivé, source indisponible. Un statut vieux de plusieurs jours ne suffit
  pas à annoncer une panne sans fréquence attendue.

**Sortie attendue :** contrat API/schéma et tests de refus inter-projet,
double soumission et crash/reprise, avec deux utilisateurs et deux projets Git
sur fixtures temporaires. Aucune mutation de tâche implicite à ce stade.

**État : magasin et schéma qualifiés en isolation le 19 octobre 2026.** Le
contrat détaillé, les limites et les résultats de recette sont dans le
document lié ci-dessus. Le DDL n'est pas appliqué à la base active et aucune
route utilisateur ne publie encore de résultat : ces raccordements appartiennent
aux phases 2 et 5.

## Phase 2 — Hooks de session et Git utiles

- Raccorder début et fin de session à des événements authentifiés du profil
  équipe. Au début : retrouver le contexte et la tâche existante. À la fin :
  enregistrer le bilan et les métriques attribuables au projet. Ne créer ou
  terminer une tâche automatiquement qu'après une règle métier distincte et
  explicitement qualifiée.
- Remplacer les effets de `post-commit.hook` et `post_tool_hook.ps1` sur SQLite
  par un événement serveur corrélé au dépôt, à l'auteur et au projet. Le commit
  peut suggérer une progression ; il ne clôture pas une tâche sur la seule base
  d'un message Git.
- Retirer du cycle courant les appels à `task_sync`/`gen_dashboard` et les
  synchronisations globales Qdrant/Obsidian. Étudier séparément une publication
  documentaire par projet si elle répond à un besoin confirmé.

**Sortie attendue :** début/fin visibles avec provenance et résultat, une
seule occurrence par session, aucune écriture dans un autre projet, aucun
changement automatique de statut de tâche sans règle qualifiée. Les anciens
hooks demeurent désactivés pour le profil équipe.

**État : candidat qualifié en isolation le 19 octobre 2026.** Le service, les
routes API et le client local sont implémentés ; les résultats et limites sont
dans le [contrat de phase 2](../docs/audit-2026-09-30/automation-hooks-phase-2-2026-10-19.md).
Le DDL, le client et les nouveaux déclencheurs ne sont pas déployés dans le
profil actif. Leur activation et le remplacement des hooks installés restent
à la phase 5 ; le rendu Cockpit relève de la phase 4.

## Phase 3 — Jobs utiles, projet par projet

Ordre de reprise proposé :

1. **Scan Git ciblé** : déclenchement après commit ou sur demande ; un scan
   périodique n'est qu'un repli borné pour les dépôts qui ne publient pas
   d'événement. Comparer aux tâches sans les terminer automatiquement.
2. **Bilan quotidien et métriques** : exécuter seulement pour les projets
   inscrits, avec calendrier et fuseau explicites ; produire un résultat par
   projet, sans `MEMORY.md` ou note quotidienne partagée.
3. **Sauvegarde/maintenance** : définir précisément données couvertes,
   rétention, vérification de restauration et effets de nettoyage avant toute
   activation. Le script hebdomadaire historique ne sert pas de job direct.
4. **RepoWise** : index par dépôt sur changement Git ou seuil de fraîcheur,
   sans mise à jour globale toutes les cinq minutes ; contrôle du commit indexé
   et des omissions, puis exposition du résultat au projet concerné.

`daily_launch`, `periodic_task_sync_dashboard`, le lecteur de fichiers
`event_watcher` et l'ancien `system_watcher` ne sont pas recréés : la session,
la projection PostgreSQL, les événements projet et la supervision globale
couvrent leurs fonctions pertinentes. Chaque nouveau job exige une commande
argv qualifiée, `execution_ready=true`, des bornes de durée et une règle de
non-chevauchement.

**Sortie attendue :** chaque job pilote produit un run et une ligne d'historique
PostgreSQL attribués au bon projet ; rejouage et concurrence n'en créent pas
de doublon ; échec et reprise sont visibles. Zéro écriture dans les anciens
registres actifs.

**État : pilotes qualifiés en isolation le 19 octobre 2026.** Scan Git,
bilan quotidien et indexation RepoWise ont des runs durables et des traces
projet. Le [rapport de phase 3](../docs/audit-2026-09-30/automation-jobs-phase-3-2026-10-19.md)
précise les recettes et limites. La maintenance historique reste archivée ;
une [politique de sauvegarde candidate](../docs/audit-2026-09-30/team-backup-maintenance-policy-2026-10-19.md)
prévoit la restauration de contrôle avant toute mise en service. Aucune
planification ou indexation n'a été créée dans l'instance active.

## Phase 4 — Cockpit et observabilité

- Afficher dans « Automation Hooks » les événements de session et Git ainsi
  que les jobs planifiés, en sections clairement identifiées. Montrer état,
  dernière tentative, dernière réussite, prochaine échéance s'il y en a une,
  auteur/source et erreur courte. Conserver un état explicite lorsqu'aucune
  donnée n'existe.
- Charger uniquement les données du projet sélectionné ; maintenir le
  document, la liste des projets et les autres panneaux lors du basculement.
  Les abonnements temps réel sont réattachés au nouveau projet sans mélange.

**Sortie attendue :** test des deux vues avec projets A/B, état vide, succès,
échec et changement de projet ; aucun « vert » produit par le rendu HTML et
aucune donnée du projet A visible dans B.

**Candidat implémenté le 20 octobre :** projection séparée des hooks, runs et
planifications, avec dernières tentatives/réussites et état vide explicite.
Les deux vues et le basculement A/B passent les tests ciblés. Voir le
[rapport de phase 4](../docs/audit-2026-09-30/automation-cockpit-phase-4-2026-10-20.md).
La base active ne possède pas encore le DDL de phase 1 ; la mise en service
et la recette HTTP/visuelle sont des travaux de phase 5.

## Phase 5 — Qualification et mise en service progressive

- Exécuter les tests unitaires/contrats, puis une recette avec deux comptes,
  deux dépôts Git et des racines temporaires. Vérifier droits, RLS, fréquence,
  idempotence, arrêt/reprise, restauration de sauvegarde et absence de
  réactivation des archives.
- Déployer d'abord un job non destructif sur `devcore` seul, observer au moins
  deux échéances et un échec simulé, puis étendre progressivement aux projets
  Git autorisés. Consigner les versions, résultats, limites et la procédure de
  retour arrière dans le journal.
- Si une opération requiert l'administrateur Windows, lancer soi-même le
  script PowerShell 7 via `Start-Process -FilePath
  'C:\Program Files\PowerShell\7\pwsh.exe' -Verb RunAs -ArgumentList
  '-NoProfile -File "E:\chemin\script.ps1"' -Wait`, après avoir remplacé le
  chemin par celui du script qualifié. La sortie du script doit fournir une
  preuve vérifiable de réussite ou d'échec.

**Sortie attendue :** candidat actif sain, Cockpit vérifié sous `majdi`,
redémarrage Windows vérifié, historique PostgreSQL cohérent et retour arrière
essayé. Étendre à d'autres projets seulement sur cette preuve.

**État au 20 octobre :** migration sauvegardée et restaurée en essai, puis
candidate `ea06de89…` active et saine sur `DevCoreGlobal`. Les 53 tests ciblés
et les préflights serveur passent. Le bilan quotidien non destructif du seul
projet `devcore` est inscrit à 08:00 `Africa/Tunis` par l'opérateur Windows
élevé, après vérification de l'appartenance contributrice de `majdi`. Il est
visible dans la projection Cockpit ; première échéance le 21 octobre.
Un déclenchement manuel tracé a produit un run `succeeded` pour le 19 octobre,
sans déplacer l'échéance de demain. Le Cockpit connecté sous `majdi` montre ce
succès et le prochain passage ; la même session confirme que le run est absent
d'un autre projet. Un échec simulé, son historique terminal et son rendu isolé
dans le Cockpit ont été qualifiés sur PostgreSQL temporaire. L'observation de
deux échéances planifiées, ainsi que la
reprise après redémarrage restent ouvertes ; la
phase 5 n'est donc pas déclarée terminée. Voir le [journal v466](../docs/audit-2026-09-30/execution-2026-10-05.md).
La bascule vers l'heure tunisienne et la candidate Cockpit ont révélé puis
corrigé le conflit entre l'interpréteur du superviseur et celui du scheduler.
Le service est redevenu sain après l'indisponibilité détaillée dans le journal
v470 ; le contrôle visuel de la nouvelle version sous `majdi` a ensuite été
effectué dans le navigateur connecté. Le préflight des deux interpréteurs est
couvert sur PostgreSQL temporaire. Un retour arrière vers `355e6dfc…` suivi
du retour à `ea06de89…` a réussi avec la planification brièvement suspendue ;
celle-ci est redevenue active sans déplacer l'échéance. Les passages planifiés
réels et un retour arrière avec schedule actif restent ouverts. Voir v472.

**État au 21 octobre :** le premier passage automatique réel à 08:00
`Africa/Tunis` a créé un unique run pour sa clé d'idempotence, terminé
`succeeded` ; `schedule_history` contient `dispatched` puis
`finished/succeeded`, et le scheduler a déplacé la prochaine échéance au
22 octobre à 08:00. Le préflight serveur de la candidate active rend le succès
et cette échéance pour `devcore`, ainsi que des états vides pour
`dashboard_recette_br` et `job_tracker`. L'onglet navigateur est revenu sur la
page de connexion ; le passage réel n'est donc pas encore vérifié visuellement
sous `majdi`. La seconde échéance, la reprise après redémarrage Windows et le
retour arrière avec schedule actif restent à qualifier. La correction candidate
du libellé « dernière tentative » n'est pas déployée. Voir journal v474–v475.

**État au 22 octobre :** les deux passages réels prévus les 21 et 22 octobre
à 08:00 `Africa/Tunis` ont chacun créé un run distinct terminé `succeeded`.
Les journaux du scheduler, `runs` et `schedule_history` concordent ; aucune
clé d'idempotence en doublon n'a été observée. La prochaine échéance est le
23 octobre à 08:00. Le préflight de la source active rend trois runs et le
prochain passage pour `devcore`, et aucun job ni planification pour
`dashboard_recette_br` et `job_tracker` ; les vues normale et terminale sont
rendues pour chaque projet. Le suivi quotidien dédié à ces deux échéances peut
être mis en pause. La phase 5 reste ouverte pour la preuve visuelle authentifiée
des nouveaux passages sous `majdi`, la reprise après redémarrage Windows, le
retour arrière avec planification active et le correctif d'affichage non encore
déployé. Voir journal v476–v477.

**Séquence demandée le 22 octobre :** l'essai de redémarrage Windows est
reporté à la fin de l'implémentation des phases, après les corrections de code
et les autres contrôles de phase 5. Aucun redémarrage n'est lancé pendant cette
vérification du Cockpit. Dans le navigateur connecté sous `majdi`, `devcore`
montre les deux runs planifiés réussis, la prochaine échéance du 23 octobre et
l'historique associé. La sélection de `dashboard_recette_br` montre « Aucun job
lancé » et « Aucune planification » ; le retour à `devcore` restaure ses
données propres. Cette preuve visuelle complète le contrôle serveur par projet.
Le 22 octobre, la correction « dernière tentative » a été installée sur le
commit figé `5eff4ac0…`. Son préflight serveur affiche le dispatch à 08:00:01
et le dernier succès à 08:00:10 ; la planification conserve l'échéance du
23 octobre. La pile a subi un arrêt de santé du gateway avant cette bascule ;
elle a été rétablie sur l'ancien commit, puis la bascule contrôlée a terminé
avec six composants sains. Le redémarrage du service a expiré la session du
navigateur ; après reconnexion, le contrôle visuel sous `majdi` montre la
tentative à 08:00:01, le succès à 08:00:10 et la prochaine échéance du
23 octobre. Le retour arrière avec schedule actif et le redémarrage Windows
restent ouverts. Voir journal v478–v479.

**Contrôles complémentaires du 22 octobre :** le retour arrière réel vers
`ea06de89…` avec le schedule actif, puis la restauration de `5eff4ac0…`, ont
conservé le dernier passage et l'échéance du 23 octobre à 08:00 Tunis. La
candidate `657de6b1…` rafraîchit seulement les données du projet sélectionné
quand le flux SSE se reconnecte ; les tests ciblés passent et la bascule est
active avec six composants sains. Un arrêt et une relance contrôlés de ce
service ont rétabli cinq listeners et quatre sondes HTTP à 200. La session
navigateur a expiré lors de la relance. Après reconnexion de `majdi`, une
coupure réseau limitée à son onglet a montré la reconnexion SSE suivie d'un
fetch ciblé `project=devcore` à 200, sans navigation de page ; la nouvelle
fiche de contexte est apparue sans rechargement. L'essai de redémarrage Windows demeure
la dernière vérification de la phase 5, conformément au report demandé ; la
cause des délais et pertes de santé intermittents du gateway reste ouverte.
La vérification de reprise Windows est préparée par
`verify_global_after_windows_restart_elevated.ps1` : le préflight avant reboot
confirme la tâche S4U, la source figée, les six composants, les cinq ports,
quatre réponses HTTP 200 et la commande du schedule sans la modifier. Le
contrôle final exige une heure de boot postérieure au préflight et un Cockpit
authentifié après le retour du poste.

**Reboot réel du 22 octobre :** Windows a redémarré à 15:53:35 heure de
Tunisie, après le préflight. `DevCoreGlobal` n'a pas repris seul : la tâche est
revenue à `Ready` avec code 1 après un échec du statut RepoWise et dix relances
épuisées. Les ports étaient fermés. La récupération contrôlée a validé
l'absence d'orphelins, relancé la tâche et retrouvé six composants sains,
cinq listeners et quatre HTTP 200. La planification `devcore` reste active
pour le 23 octobre à 08:00 Tunis. La candidate `c8ab7979…` déployée ensuite
retente le statut RepoWise trois fois sans accepter un index périmé ; la tâche
dispose maintenant de 288 relances toutes les cinq minutes. Le préflight
post-reboot passe sur cette version, mais **la reprise automatique corrigée
demande encore un futur reboot réel**. Après reconnexion de `majdi`, le Cockpit
a été vérifié visuellement sur `devcore` puis `dashboard_recette_br`, et le
retour ciblé à `devcore` a rétabli son run et son échéance sans rechargement
explicite de la page. La phase 5 n'est pas déclarée terminée. Voir journal
v482–v483. Le préflight élevé du 22 octobre à 19:25Z confirme la source,
les six composants, les cinq ports, les quatre sondes et l'échéance du 23
octobre ; il ne remplace pas la preuve d'un nouveau démarrage automatique.
Voir journal v484.

**Second reboot du 23 octobre :** Windows a démarré à 00:09:50 heure de
Tunisie. `DevCoreGlobal` a démarré avant que PostgreSQL accepte les connexions,
puis son contrôle de schéma a échoué (code 1) et la tâche est revenue à `Ready`.
Le type d'exception n'a pas été conservé ; la cause interne exacte reste donc
à établir. Le lanceur attend désormais PostgreSQL avec tentatives bornées et
refuse immédiatement une vraie divergence de schéma. Deux tests ciblés
passent. La relance élevée contrôlée a retrouvé six composants sains et
conservé l'échéance du 23 octobre à 08:00. Le déclencheur Windows attend
maintenant deux minutes après le boot ; sa sauvegarde XML et la tâche en cours
ont été vérifiées. **La reprise automatique après redémarrage n'est toujours
pas qualifiée.** Voir journal v485.

**Troisième reboot du 23 octobre :** la tâche S4U a démarré sans intervention,
la pile est devenue prête et le passage réel de 08:00 Tunis a réussi une fois.
La prochaine échéance est le 24 octobre à 08:00. Vers 08:44, le gateway et
RepoWise ont perdu leur santé ; le superviseur a terminé avec code 1 et la
relance manuelle contrôlée a rétabli six composants. Le démarrage automatique
à froid est observé, mais **la phase 5 reste ouverte sur la stabilité et
l'auto-récupération après une panne en cours d'exécution**. Voir journal v486.

**Renouvellement du contexte par DevCore (23 octobre) :** un schedule distinct
`schedule-context-refresh-devcore` est actif à 09:00 `Africa/Tunis`. Son run
immédiat a réussi et a préservé l'échéance du 24 octobre. Il renouvelle un
instantané vérifiable de Git, de la fiche et du registre, sans antidater la
revue narrative. Le lecteur du Cockpit et sa présentation ont été déployés
dans la source figée `1f5ec0f…` ; le lecteur PostgreSQL renvoie l'instantané
sous 12 000 octets sans avertissement, et le test JS de la ligne affichée
passe. Le rendu a été vérifié dans le navigateur reconnecté sous `majdi` :
instantané à 10:54 Tunis, schedule actif et changement de projet ciblé.
Le 24 octobre, la première échéance quotidienne réelle a terminé `succeeded`
une seule fois à 09:00 Tunis. PostgreSQL, le journal du daemon, le lecteur MCP
de nouveau accessible et le Cockpit connecté sous `majdi` concordent ; le
prochain passage est le 25 octobre à 09:00. Restent le traitement d'une revue
narrative expirée sur preuves, la stabilité de la pile et l'auto-récupération
après panne. Voir journal v488–v493.
Le canal Windows `TaskScheduler/Operational` a été activé le 23 octobre pour
tracer les prochaines tentatives de relance de `DevCoreGlobal` ; il ne permet
pas de reconstituer les échecs antérieurs. La pile est restée saine de 10:50
à 15:01 Tunis, sans que cela qualifie encore l'auto-récupération. Voir v492.

**Reprise après panne du 24 octobre :** une sonde S4U isolée a montré que
`RestartOnFailure` ne relançait pas une action sortie avec code non nul dans
ce profil, quelle que soit la valeur 3 ou 288 du compteur. Un déclencheur
temporel répétitif toutes les cinq minutes a donc été ajouté à
`DevCoreGlobal`, avec `IgnoreNew` ; l'événement 322 a prouvé l'absence de
doublon lorsque la pile tournait. Après arrêt contrôlé du processus RepoWise
supervisé, l'ancien superviseur a quitté avec code 1 et Windows a lancé une
nouvelle instance au passage de 12:23 Tunis, sans relance manuelle. La pile
était prête à 12:24 avec six composants et cinq sondes HTTP sains. La reprise
après cette panne en cours d'exécution est qualifiée une fois ; la cause des
incidents précédents et la stabilité prolongée restent à observer. La revue
narrative du contexte demeure distincte du job automatique. Voir journal v494.

**Contrôle du 25 octobre :** les passages naturels du bilan à 08:00 et des
faits de contexte à 09:00 Tunis ont chacun réussi avec une seule clé
d'idempotence et leur historique PostgreSQL complet ; le Cockpit connecté
sous `majdi` affiche les deux résultats et les échéances du 26 octobre.
Le superviseur revenu automatiquement le 24 est resté actif jusqu'au contrôle
de 12:30 le 25. Les passages du déclencheur de reprise ont été ignorés sans
nouvelle instance ; les cinq sondes HTTP répondent 200. La sortie attendue
du **pilote `devcore`** est satisfaite : candidat actif, Cockpit authentifié,
démarrage Windows déjà observé, reprise après panne observée, historique et
retour arrière qualifiés. L'extension des jobs à d'autres projets Git n'est
pas encore faite. La cause des anciens incidents, un nouveau reboot avec le
déclencheur additionnel et une disponibilité prolongée restent des limites
opérationnelles, pas des preuves déjà acquises. Voir journal v495.

**Arrêt des échéances après qualification (25 octobre) :** sur instruction de
l'utilisateur, les deux schedules quotidiens du seul projet `devcore` sont
`disabled` et leurs `next_run_at` sont vides. Les runs, leurs derniers
passages et l'historique PostgreSQL sont conservés. Le Cockpit sous `majdi`
affiche « prochain passage — » pour chacun. Le déclencheur Windows de reprise
de `DevCoreGlobal` reste un mécanisme de disponibilité de la pile, distinct
des deux jobs du pilote. Voir journal v496.

## Phase 6 — Autonomie de l'agent, option distincte

L'ancien `active_agent_task_runner` ne fait pas partie de la reprise de base.
Un remplacement éventuel exige un choix explicite par projet, une identité
porteuse des droits, des commandes autorisées, un quota, un périmètre de dépôt,
des points d'approbation et une trace de chaque modification. Il doit passer
les mêmes tests d'isolation et d'arrêt/reprise que les autres runs avant une
mise en service séparée. La présence d'une tâche `in_progress` ne suffit jamais
à lancer un agent autonome.

**Sortie attendue :** décision indépendante documentée ; en son absence,
aucun agent autonome planifié.
