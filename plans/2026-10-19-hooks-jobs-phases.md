# Reprise des hooks et jobs DevCore — plan par phases

Date : 19 octobre 2026. Statut : phases 0 à 2 qualifiées ; pilotes de phase 3 qualifiés en isolation ; aucune activation.

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
- [dispatcher PostgreSQL](../DEV_CORE/devcore_engine/runs/postgres_schedules.py) et [projection Cockpit](../DEV_CORE/devcore_engine/services/postgres_dashboard.py) ;
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
