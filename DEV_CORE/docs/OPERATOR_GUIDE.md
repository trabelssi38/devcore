# DEV_CORE Operator Guide

Guide d'exploitation pour démarrer, diagnostiquer et récupérer DEV_CORE sans modifier manuellement l'état runtime.

Voir aussi : `API_REFERENCE.md` pour le gateway API, `PLATFORM_DOCUMENTATION.md` pour l'architecture complete, `SYSTEM_OVERVIEW.md` pour la carte systeme, `IMPLEMENTATION_HISTORY.md` pour la chronologie, `ARCHITECTURE_DECISIONS.md` pour les ADR et `AI_CAPABILITY_REGISTRY.md` pour la selection runtime.

## First run

Pré-requis :

- PowerShell non interactif disponible.
- Python disponible dans le `PATH`.
- Docker Desktop lancé si Qdrant ou services conteneurisés sont requis.
- Répertoire de travail : `C:\devcore`.

Séquence recommandée :

```powershell
cd C:\devcore
powershell -ExecutionPolicy Bypass -NonInteractive -File C:\devcore\DEV_CORE\Scripts\launch.ps1
powershell -ExecutionPolicy Bypass -NonInteractive -File C:\devcore\DEV_CORE\Scripts\dc.ps1 "next task"
```

Alias opérationnel :

```powershell
dc launch
```

## Commandes guidées

Les guides sont non destructifs par défaut et destinés aux opérateurs.

| Commande | Usage |
|---|---|
| `dc guide onboarding` | Vérifier le premier lancement, les chemins, services attendus et actions immédiates. |
| `dc guide diagnostic` | Expliquer les checks runtime et prioriser les causes probables. |
| `dc guide recovery` | Proposer une récupération non destructive pour tâches, contexte, services et mémoire. |

Scripts source :

- `DEV_CORE\Scripts\guided_recovery.ps1`
- `DEV_CORE\Scripts\diagnose.ps1`
- `DEV_CORE\Scripts\gateway.ps1`

## Diagnostics

Commandes rapides :

```powershell
dc check
dc check --gate
dc check --fix --dry-run
```

Interprétation :

- `dc check` inspecte l'état courant sans bloquer.
- `dc check --gate` sert de gate locale avant commit ou release.
- `dc check --fix --dry-run` affiche les corrections proposées sans les appliquer.

Les logs runtime sont à consulter dans `DEV_CORE_DATA\Logs\scripts`.

## Recovery non destructive

Procédure standard :

1. Lancer `dc guide diagnostic`.
2. Identifier la zone touchée : tâches, bus d'événements, contexte, services, mémoire.
3. Lancer `dc check --fix --dry-run` pour voir les réparations possibles.
4. Si la proposition est cohérente, appliquer uniquement la correction ciblée via le script indiqué par le diagnostic.
5. Relancer `dc check --gate`.

Règles :

- Ne pas éditer directement `tasks.json` sauf correction contrôlée et sauvegardée.
- Ne pas supprimer `DEV_CORE_DATA` pour résoudre un problème d'affichage dashboard.
- Préférer une reconstruction de read model ou cache à une mutation de source de vérité.
- Garder les secrets dans `DEV_CORE_DATA\Security`, jamais dans `DEV_CORE\Config`.

## Tâches et fin de journée

Cycle quotidien :

```powershell
dc launch
dc next task
dc task status
```

Fin de session courte :

```powershell
powershell -NonInteractive -File C:\devcore\DEV_CORE\Scripts\endday.ps1 -SkipBackup
```

La commande `endday.ps1 -SkipBackup` doit rester non bloquante pour le travail courant. Si une instance est déjà en cours, ne pas en lancer plusieurs; inspecter `DEV_CORE_DATA\Logs\scripts` et poursuivre le développement.

## API et dashboard

- Le dashboard local lit le payload cache et les ressources paginées quand disponibles.
- Les mutations dashboard doivent passer par les endpoints protégés, pas par édition manuelle.
- Pour intégrer un outil externe, partir de `API_REFERENCE.md` et de `DEV_CORE/Schemas/openapi-v1.json`.

## Supervision des jetons & Sessions Libres (Headroom)

Dans le cadre de l'exploitation quotidienne, l'opérateur doit surveiller la consommation des jetons et identifier les comportements anormaux des agents IA (boucles de requêtes, fuites de tokens) via la section **Supervision Headroom** :
1. **Identifier les Sessions Libres** : Les sessions d'agents IA non associées à une tâche ID sont marquées avec le badge **`OK (Session Libre)`** (jaune) ou **`ALERTE (Hors Tâche)`** (rouge clignotant).
2. **Interpréter le statut ALERTE** : Une session hors tâche passe en `ALERTE` dès qu'elle consomme plus de **500 000 tokens** ou engendre un coût estimé supérieur à **$0.50 USD**.
3. **Actions de récupération** :
   - En cas d'alerte, retrouver la session dans `DEV_CORE_DATA/Logs/metrics/metrics-YYYY-MM-DD.jsonl` pour analyser les payloads JSON des appels récents.
   - S'assurer que l'agent est bien rattaché à sa tâche active en relançant `dc next task` ou en spécifiant l'ID dans l'environnement de l'agent.

## Checklist opérateur

- [ ] `dc launch` terminé ou timeout diagnostiqué sans processus orphelin.
- [ ] `dc check --gate` passe avant publication.
- [ ] Logs récents consultés dans `DEV_CORE_DATA\Logs\scripts` en cas d'erreur.
- [ ] Logs de télémétrie de jetons vérifiés dans `DEV_CORE_DATA\Logs\metrics\metrics-YYYY-MM-DD.jsonl`.
- [ ] Tâche active vérifiée depuis `DEV_CORE_DATA\Memory\<project>\tasks.json`.
- [ ] Aucun conteneur ou agent libre en état d'alerte (`ALERTE (Hors Tâche)`) persistant dans le cockpit.
- [ ] `endday.ps1 -SkipBackup` exécuté avant clôture d'une session courte.

## Radar Repowise & Régénération Cockpit

### Propagation des scores de santé

Après chaque commit, la chaîne de propagation est :

```
post-commit hook
├── task_sync.ps1 → gen_dashboard.py  (régénération immédiate, données partielles)
└── repowise_update.py → scan → gen_dashboard.py  (régénération finale avec scores à jour)
```

Le cockpit est régénéré **deux fois** : une fois rapidement (tâches/événements), puis une seconde fois après le scan Repowise (~1-3 min). Les scores de la carte Radar sont uniquement fiables après la seconde régénération.

### Lock fichier (`gen_dashboard.lock`)

`gen_dashboard.py` utilise un lock fichier cross-platform (`DEV_CORE_DATA/Runtime/gen_dashboard.lock`) pour éviter les générations concurrentes. Si plusieurs processus tentent de générer le cockpit simultanément :

- Le premier acquiert le lock et génère normalement.
- Les suivants **attendent jusqu'à 30 s** puis s'exécutent séquentiellement.
- Un lock périmé (>120 s, processus mort) est nettoyé automatiquement.
- Le mode `--json` (API) n'est pas soumis au lock pour éviter de bloquer les requêtes.

En cas de lock bloqué, supprimer manuellement :

```powershell
Remove-Item "$env:DEVCORE_DATA_ROOT\Runtime\gen_dashboard.lock" -Force
```

### Reconstruire la base SQLite si corrompue

En cas de warning `database disk image is malformed` dans les logs :

```powershell
Remove-Item "$env:DEVCORE_DATA_ROOT\devcore.db" -Force
Remove-Item "$env:DEVCORE_DATA_ROOT\devcore.db-shm" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:DEVCORE_DATA_ROOT\devcore.db-wal" -Force -ErrorAction SilentlyContinue
python C:\devcore\DEV_CORE\Scripts\migrate_json_to_sqlite.py
python C:\devcore\DEV_CORE\Scripts\gen_dashboard.py
```
