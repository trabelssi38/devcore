# Copies conflictuelles Dropbox — 2 octobre 2026

Relevé en lecture seule de `%USERPROFILE%/Dropbox/DEV_CORE_DATA` avec `python DEV_CORE/Scripts/inspect_dropbox_conflicts.py <racine>`. La comparaison utilise les octets et, pour `tasks.json`, les identifiants et noms de champs uniquement. Aucun fichier partagé n'a été modifié, fusionné ou supprimé.

| Catégorie | Copies | Observation |
|---|---:|---|
| `Logs/scripts/task_*.log` | 8 | Deux dates en août ; toutes diffèrent de leur fichier courant. |
| `Logs/scripts/weekly_maintenance_*.log` | 3 | Août et septembre ; toutes diffèrent du fichier courant. |
| `Logs/token_reports/*.html` | 1 | Diffère du fichier courant. |
| `Memory/devcore/tasks.json` | 1 | Ancienne copie de 379 tâches contre 389 dans le fichier courant. |

Les 13 copies ont un homologue courant, et aucun couple n'est identique octet pour octet. Les étiquettes Dropbox mentionnent `DESKTOP-5K6VPR6` et `DESKTOP-BB8O9C7` entre le 18 août et le 20 septembre. Elles attestent des conflits historiques, pas de la présence actuelle de ces machines ni de leurs processus.

Dans le conflit `tasks.json`, 379 identifiants sont communs, 10 n'existent que dans la version courante et aucun n'existe seulement dans la copie conflictuelle. Parmi les identifiants communs, 33 objets diffèrent : `completed_at` (17), `commit_hash` (14), `committed_at` (14), `source` (14), `title` (3), `details` (1), `status` (1), `steps_done` (1). Les valeurs `current_task` diffèrent aussi. Les nombres de champs se recouvrent et ne doivent pas être additionnés pour obtenir un nombre de tâches. Ce relevé ne détermine pas la version correcte de chaque tâche ; le SQL local et l'historique des événements devront être rapprochés sur une copie de recette.

## Préparation du gel

1. Confirmer auprès des utilisateurs si ces deux postes, ou d'autres postes, lancent encore DevCore avec `DEV_CORE_DATA`. Identifier aussi l'écrivain de `Memory/conversations.db` et les éventuels jobs sur le poste actuel.
2. Choisir une fenêtre de gel et arrêter les écrivains DevCore sur **tous** les postes concernés. Garder la synchronisation Dropbox des documents ordinaires si nécessaire, mais interdire alors toute écriture des fichiers d'état hérités (`Memory/**/tasks.json`, `Bus`, `Scheduler`, `Logs/scripts`).
3. Attendre la fin de synchronisation sur chaque poste et capturer des sauvegardes cohérentes en dehors de Dropbox. Refaire cet inventaire ; toute nouvelle copie conflictuelle ou mutation d'état annule le gel et demande une nouvelle capture.
4. Réconcilier les tâches, événements et états du planificateur sur une copie de recette avec journal des décisions. Ne pas utiliser la date ou le fichier courant comme règle automatique de priorité. Conserver les originaux jusqu'à la validation de la restauration et de la bascule.

Le gel n'a pas été exécuté. L'identification des postes actifs et la décision de réconciliation restent ouvertes avant migration réelle.

## Copie du second poste fournie le 2 octobre

`E:/devcore_autre_poste` a été inspecté en lecture seule. La copie complète contient 766 fichiers (66 937 065 octets), dont 573 sous `DEV_CORE`. Elle contient quatre bases SQLite **d'index RepoWise** sous `.repowise` ; le précédent relevé « aucun `.db` » était incorrect pour la copie entière. Aucun `devcore.db`, `jobs.json` dynamique, copie conflictuelle ni racine `DEV_CORE_DATA` n'y a été trouvé. `DEV_CORE/download/tasks.json` contient quatre tâches, contre 389 dans le JSON Dropbox courant ; ce fichier isolé n'est pas une sauvegarde démontrée de l'état actif. Le fichier source/configuration le plus récent de cette copie porte un horodatage du 20 septembre ; les dates du dossier principal correspondent à la copie effectuée aujourd'hui et ne prouvent pas une exécution récente sur le poste d'origine.

Le registre de cette copie décrit 28 projets contre 7 dans le registre du poste actuel : 7 noms communs et 21 propres à la copie. Il référence 23 chemins sur `C:` et 5 sur `E:`. Ces chemins n'ont pas été parcourus depuis ce poste ; leur existence et leur propriétaire restent inconnus. Parmi neuf fichiers repères comparés par SHA-256, `pyproject.toml`, `Config/network.json` et `Config/security.json` sont identiques ; `requirements-ci.txt`, `Config/projects.json`, `Scheduler/jobs.devcore.json`, `Scripts/session_start.ps1`, `Scripts/Auto/weekly_maintenance.ps1` et `devcore_engine/services/tasks.py` diffèrent. Une comparaison étendue sous `DEV_CORE`, excluant caches Python, cache de tests et HTML de tableau de bord, trouve 500 fichiers dans la copie, aucun fichier propre à cette copie et 68 fichiers communs dont les octets diffèrent. Plusieurs de ces différences correspondent aux corrections locales en cours ; cette comparaison seule ne classe pas leur contenu. Ne pas remplacer le code ou le registre actuel par cette copie sans examen des écarts.

Cette copie permet d'identifier une autre installation DevCore, mais pas de relier de façon certaine son poste d'origine aux deux étiquettes Dropbox, ni de savoir si elle écrit encore dans Dropbox. Il faut vérifier sur le poste d'origine les services/planifications actifs et les racines de données utilisées avant le gel.

L'utilisateur a ensuite confirmé que DevCore ne tourne plus sur cet autre poste et fourni `E:/DEV_CORE_LOCAL_autre_poste`. L'analyse de ses bases et de ses écarts avec ce poste est consignée dans [copie-locale-autre-poste-2026-10-02.md](copie-locale-autre-poste-2026-10-02.md). La phrase précédente reflète l'état de preuve avant cette confirmation.

L'utilisateur a également confirmé qu'aucun troisième poste n'utilise `DEV_CORE_DATA`. La [préparation du gel](preparation-gel-2026-10-02.md) couvre donc les deux postes connus ; le gel effectif et la vérification de Dropbox restent à réaliser lors de la bascule.
