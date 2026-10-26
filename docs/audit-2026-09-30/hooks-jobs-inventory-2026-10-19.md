# Inventaire des anciens hooks et jobs — phase 0

Contrôle en lecture seule du 19 octobre 2026. Ce document distingue les
définitions dans le dépôt, les déclencheurs installés sur ce poste et les
exécutions prouvées. Il ne qualifie pas une activation future.

## Sources et constat d'exploitation

- Le registre `DEV_CORE/Scheduler/jobs.devcore.json` porte huit définitions :
  quatre désactivées et quatre marquées `enabled=true`. Le fichier
  `DEV_CORE/Scripts/hermes_cron.yaml` porte huit entrées (toutes marquées
  actives), dont `periodic_repowise_update` à la place de `system_watcher`.
  **Correction de l'estimation initiale du plan : Hermes en compte huit,
  pas neuf.** Seul `check_active_task.py` parmi les huit scripts désignés par
  Hermes se trouve dans `DEV_CORE/Scripts` ou `Scripts/Auto` ; les sept autres
  wrappers ne sont pas présents dans le dépôt. Une copie externe éventuelle
  chez Hermes n'a pas été prise comme preuve d'exécution.
- Le manifeste `scheduler-archive-2026-10-12.json` recense huit anciennes
  définitions et 12 245 résultats. Il porte `archive_only` et
  `jobs_activation_allowed=false`.
- La seule tâche Windows dont le nom mentionne DevCore, Hermes ou RepoWise est
  `DevCoreGlobal`, en état `Running` au contrôle. Cela ne prouve pas à lui seul
  l'exécution d'un job ; les anciens daemons n'ont pas été trouvés par le
  filtre de processus de cet utilisateur. Le scheduler PostgreSQL est inclus
  par le code de la pile globale, sans chargement des anciens fichiers JSON.
- Les réglages utilisateur de Claude appellent `cli.py session start` à
  `UserPromptSubmit`, `hooks/post_tool.py` après Bash et `cli.py session end`
  à `Stop`, avec `C:\Python314\python.exe` présent. Gemini appelle les mêmes
  points d'entrée au moyen de `python`, résolu ici à Python 3.14. Les réglages
  Codex ne déclarent pas ces anciens hooks. Le `SessionManager` et le hook
  post-outil ouvrent SQLite ; ils ne constituent pas des événements du profil
  équipe PostgreSQL. Les hooks RepoWise de Claude sont distincts.
- Une lecture PostgreSQL `BEGIN READ ONLY` avec le rôle applicatif voit 29
  projets. Vingt-deux ont un `root_path` inexistant sur ce poste ; un chemin
  existant (`pramax_prefs_patch`) n'est pas un dépôt Git ; six chemins sont
  des dépôts Git locaux. Quatre de ces six (`dashboard_recette_br`, `devcore`,
  `job_tracker`, `oracle_legacy_intelligence_platform`) ont le même hook
  `post-commit` DevCore. `conso_api_madania` possède un hook différent, sans
  référence DevCore ; `migration_to_12c` n'a pas de hook `post-commit`.
  L'existence des fichiers n'établit ni leur fréquence ni leur réussite.
- Dernier audit des données Cockpit : zéro planification PostgreSQL pour les
  29 appartenances de `majdi`. La carte actuelle lit `schedules` et
  `schedule_history`, sans convertir les anciens journaux en réussite.

## Matrice de décision

| Mécanisme | Effet actuel dans le code historique | Profil équipe | Décision |
| --- | --- | --- | --- |
| `session_start` | Sélection/création de tâche et événement dans SQLite ; les réglages Claude/Gemini l'appellent | Pas d'événement PostgreSQL équivalent qualifié | Reprendre l'identification de session et du contexte ; exclure la création automatique de tâche |
| `session_end` | Événement SQLite ; le script PowerShell ajoute métriques, scan et régénération | Pas d'événement PostgreSQL équivalent qualifié | Reprendre le bilan/métriques attribuables au projet ; exclure `task_sync` |
| `post_tool_hook` | Événement et métrique SQLite | Pas de pont PostgreSQL installé | Reprendre uniquement une télémétrie bornée si le client fournit auteur et projet fiables |
| `post-commit` | Peut modifier/terminer automatiquement une tâche SQLite, même sans tag | Quatre dépôts locaux portent ce hook | Remplacer par un événement de commit et une suggestion, sans mutation de tâche |
| `daily_launch` | Lance le cycle individuel sans projet dans le registre historique | Supervision globale distincte | Archiver comme cron ; déclenchement de session explicite seulement |
| `daily_endday` | Bilan individuel ; la commande exige désormais un projet | Aucune planification projet | Adapter comme job projet optionnel |
| `weekly_maintenance` | Vérification mémoire, cache et copie locale ; option explicite requise | Pas de sauvegarde PostgreSQL qualifiée par ce script | Reconcevoir sauvegarde/restauration avant tout planning |
| `periodic_task_scan` | Scan Git/SQLite ; registre statique désactivé | Événements et tâches projet PostgreSQL | Reprendre un scan ciblé sur dépôt Git, sans clôture automatique |
| `periodic_task_sync_dashboard` / `task_sync` | Régénère l'ancien tableau de bord | Cockpit lu depuis PostgreSQL | Archiver ; aucune reprise de ce job |
| `event_watcher` | Consomme les fichiers du bus local | Événements PostgreSQL par projet | Archiver le lecteur de fichiers ; employer le bus PostgreSQL |
| `active_agent_task_runner` | Peut lancer un agent sur la tâche SQLite active | Runs durables disponibles, mais aucune autorisation d'autonomie qualifiée | Réserver à une décision et une qualification indépendantes ; inactif |
| `system_watcher` | Redémarre des services et l'ancien scheduler | `DevCoreGlobal` supervise sa propre pile | Archiver pour ce profil afin d'éviter deux boucles de relance |
| `periodic_repowise_update` (Hermes) | Demande une mise à jour toutes les cinq minutes ; wrapper absent du dépôt | Index vérifié au démarrage, pas une mise à jour périodique prouvée | Reconcevoir par dépôt/commit et seuil de fraîcheur |

## Limites et passage à la phase 1

Les vingt-deux chemins de projet absents doivent être corrigés ou exclus
avant toute planification ; l'audit ne les a pas parcourus. Les réglages
Claude/Gemini et les hooks Git installés n'ont pas été modifiés. Les heures
de dernière exécution de chaque client ne sont pas disponibles dans ces
réglages. Aucun script administrateur n'a été nécessaire pour cet inventaire.

La phase 1 peut partir de cette matrice : définir séparément les événements
de session/commit et les crons PostgreSQL, avec source, acteur, projet,
idempotence et résultat terminal. L'activation reste fermée.
