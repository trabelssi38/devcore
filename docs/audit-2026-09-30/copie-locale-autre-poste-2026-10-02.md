# Copie locale de l'autre poste — 2 octobre 2026

Source fournie : `E:/DEV_CORE_LOCAL_autre_poste`. L'utilisateur confirme que DevCore ne tourne plus sur cet autre poste. Inspection en lecture seule ; aucun service, script de migration ou test n'a été lancé depuis cette copie. Les lectures SQLite ont utilisé `mode=ro&immutable=1` et chargé `sqlite_vec` pour reconnaître les tables virtuelles. La base de ce poste a été ouverte en `mode=ro` pour la comparaison ponctuelle, sans verrouillage ni sauvegarde de référence. Les nombres du poste actuel peuvent évoluer pendant que ses services tournent.

## Contenu et cohérence

| Élément | Copie de l'autre poste | Observation |
|---|---:|---|
| Fichiers | 74 ; 83 260 078 octets | Racines `Bus`, `Cache`, `Dashboard`, `Logs`, `Runtime`, `Scheduler`, `Sessions` et base principale. |
| `devcore.db` | 37 818 368 octets ; dernière modification UTC 27 septembre | Pas de `-wal` ni `-shm` dans la copie ; `PRAGMA integrity_check` retourne `ok`. |
| `Scheduler/scheduler.db` | 3 203 072 octets ; dernière modification UTC 27 septembre | `integrity_check` retourne `ok` ; 12 245 lignes de `run_history`. |
| `Scheduler/jobs.json` | 8 définitions | À traiter comme historique ; ne pas réactiver ces commandes sur ce poste. |

La vérification `PRAGMA foreign_key_check` de `devcore.db` **échoue** avec `foreign key mismatch - "runs" referencing "tasks"`, défaut de schéma déjà connu de l'audit. Le `integrity_check` positif ne signifie donc pas que les relations sont valides. L'ancienne base a 4 projets SQL, alors que le registre de code fourni avec elle décrit 28 projets ; le registre et la base ne sont pas interchangeables.

## Comparaison ponctuelle avec la base de ce poste

| Donnée | Autre poste | Ce poste | Résultat |
|---|---:|---:|---|
| Projets SQL | 4 | 27 | 3 identifiants communs, 1 seulement dans l'autre copie (`xtream_universal_manager`), 24 seulement ici. |
| Tâches | 1 336 | 1 378 | Les 1 336 clés `(project_id, id)` de l'autre copie sont présentes ici ; 42 clés supplémentaires ici. |
| Événements `bus_events` | 757 | 20 988 | Aucun identifiant commun. 154 lignes correspondent si l'on ignore `id` et `created_at` ; ce rapprochement ne suffit pas à dédupliquer. |
| États de workflow | 64 | 64 | Identifiants et champ `state` identiques au relevé. |

Les 1 336 tâches communes ont des différences d'horodatage (`created_at`, `updated_at`) ; **8** diffèrent sur le statut ou le nombre d'étapes. D'autres champs diffèrent : `worktree` (119), `completed_at` (30), `metadata` (11), `title` (1). Les comptes par champ se recouvrent. Aucun contenu de tâche n'est reproduit dans ce rapport. Les dates peuvent refléter des formats ou réécritures différents et ne servent pas de règle de priorité.

La copie contient 611 tâches dont `project_id` manque dans ses 4 projets SQL, réparties sur 7 identifiants. La base de ce poste compte 46 tâches analogues : 33 sous `xtream_universal_manager`, dont le projet existe dans la copie mais manque ici, et 13 sous `scripts`. Son `foreign_key_check` ponctuel retourne 268 912 violations, dominées potentiellement par le graphe de connaissances ; ce nombre n'a pas été ventilé et ne doit pas être assimilé aux seules tâches. L'anomalie de schéma de la copie interdit d'obtenir un décompte global de ses violations via ce pragma.

## Suite de la réconciliation

1. Conserver les deux copies et capturer une sauvegarde cohérente de la base encore active sur ce poste au moment du gel. Vérifier à nouveau les empreintes et les comptes après arrêt des écrivains.
2. Réconcilier les projets SQL et le registre de 28 projets sur une base de recette. Examiner particulièrement `xtream_universal_manager` et `scripts`, sans attribuer automatiquement les chemins d'un autre ordinateur.
3. Comparer individuellement les 8 changements de statut/progression et le titre divergent, puis documenter la décision par tâche. Préserver les deux versions des champs historiques avant toute fusion.
4. Examiner les 757 événements de l'autre copie avec leur source et leur chronologie. Les 154 ressemblances sans horodatage ne prouvent pas une identité logique ; aucun événement ne doit être réinjecté automatiquement.
5. Réparer le schéma des clés étrangères sur une copie de recette, puis valider les comptes, références, intégrité et restauration avant une bascule. La copie de l'autre poste reste inchangée.

L'utilisateur confirme qu'il n'existe pas d'autre poste concerné ; la [procédure de gel](preparation-gel-2026-10-02.md) couvre donc ces deux installations. L'état final de la synchronisation Dropbox devra être contrôlé lors de la fenêtre réelle. La migration reste inactive.
