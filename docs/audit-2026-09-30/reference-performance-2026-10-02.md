# Référence de performance locale — 2 octobre 2026

Mesures ponctuelles, sur ce poste Windows, sans écriture dans la base active ni Dropbox. Elles servent de référence pour comparer le pilote ; elles ne sont pas une qualification de charge multiutilisateur. Python de test : CPython 3.13.3 dans `E:/DevCoreRuntime/releases/devcore-py313-20261002`.

## Régressions de l'audit

`tests/test_project_isolation.py`, `tests/test_sqlite_fk_preview.py`, `tests/test_sqlite_reconciliation.py`, `tests/test_benchmark_sqlite_snapshot.py`, `API/test_ports.py` et `devcore_engine/tests/test_agent_runner.py` : **28 tests réussis** dans des racines locale/partagée temporaires. Ils couvrent notamment deux projets avec `T-01`, les références entre projets, la migration des clés étrangères sur copie, la lecture API qui ne bloque pas l'endpoint de santé, et les refus de faux succès du runner. Un avertissement de dépréciation Starlette/TestClient subsiste.

La première commande de cette suite a échoué pendant la collecte, car `test_agent_runner.py` importe `DEV_CORE` comme paquet depuis la racine du dépôt. La relance avec `PYTHONPATH` contenant à la fois la racine du dépôt et `DEV_CORE` a réussi. Aucun test n'a pointé vers les racines actives.

## SQLite sur sauvegarde restaurée

`Scripts/benchmark_sqlite_snapshot.py` ouvre uniquement la sauvegarde `E:/DevCoreRuntime/backups/2026-10-01-l0-baseline/devcore.db` en `mode=ro&immutable=1`, refuse un WAL et vérifie le SHA-256 contre `manifest.json` avant les requêtes. La sauvegarde mesure 98 488 320 octets ; le projet le plus fourni a 389 tâches. Chaque requête reçoit 5 échauffements puis 50 mesures avec `perf_counter_ns`.

| Requête | p50 | p95 | max |
|---|---:|---:|---:|
| `COUNT(*)` par projet | 0,019 ms | 0,020 ms | 0,024 ms |
| 50 premières tâches non supprimées d'un projet, triées par création | 0,190 ms | 0,201 ms | 0,203 ms |

Ces durées sont celles de lectures locales probablement servies par le cache. Elles n'incluent ni réseau, ni API, ni concurrence d'écriture. La sauvegarde date du 1er octobre ; la base active peut avoir grossi depuis. Le test de l'outil vérifie sur un SQLite temporaire que son empreinte ne change pas et qu'un manifeste erroné est refusé.

## Processus et index

Sur un intervalle de 6,01 secondes, les quatre processus observés ont eu un delta CPU arrondi à 0,000 seconde. C'est une observation au repos pendant cet intervalle, pas une mesure du pic ni une garantie de charge nulle. Ensembles résidents instantanés : scheduler 20 942 848 octets, Dashboard API 19 783 680, lanceur RepoWise 3 756 032 et processus Python RepoWise 266 162 176. Les PID ont été identifiés par rôle, sans recopier leurs arguments.

Index RepoWise du dépôt : 536 fichiers, 68 434 989 octets. État RepoWise du profil utilisateur : 3 458 fichiers, 130 899 106 octets. Ces totaux incluent toutes les catégories de fichiers présentes et ne prouvent ni la fraîcheur des pages ni leur couverture.

À refaire en L9 sur la nouvelle architecture : charge simultanée de deux projets, p50/p95/p99 API et file, débit et erreurs, CPU/RAM au pic, blocages d'écriture, redémarrage/reprise et taille des index après réindexation. Ne pas extrapoler les lectures SQLite ci-dessus en capacité multiutilisateur.
