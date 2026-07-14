# DEV_CORE — Plan de remplacement progressif de Hermes

Date : 2026-07-14  
Statut : draft technique  
Objectif : rendre Hermes optionnel en remplaçant ses fonctions critiques par des composants DEV_CORE natifs, sans perte de fiabilité ni de performance.

## 1. Contexte

DEV_CORE utilise Hermes principalement comme orchestrateur cron et registre d'état de jobs. Le cœur fonctionnel de DEV_CORE reste dans les scripts, données et services DEV_CORE.

Problèmes observés :

- deux emplacements runtime possibles : `%LOCALAPPDATA%\hermes` et `~\.hermes`;
- `jobs.json` peut devenir stale;
- `next_run_at` dépassés non réparés automatiquement avant resync;
- `cron_tick.log` peut grossir et ralentir les lectures dashboard;
- risque de plusieurs ticks actifs;
- health cockpit historiquement trop dépendant de `LastWriteTime`.

Conclusion : Hermes doit devenir un adaptateur optionnel, pas une dépendance centrale.

## 2. Fonctions Hermes actuellement utilisées

| Fonction | Usage DEV_CORE | Remplacement cible |
|---|---|---|
| Tick loop cron | Déclenchement périodique des jobs | `DEV_CORE\Scheduler\scheduler_tick.py` |
| `jobs.json` | État des jobs, `next_run_at`, `last_status` | `DEV_CORE_DATA\Scheduler\jobs.json` |
| Wrappers Python | Exécution `launch`, `endday`, sync, watcher | Scripts DEV_CORE directs |
| Daemon background | Process long-running | Windows Task Scheduler + lock DEV_CORE |
| Active Agent Task Runner | Agent autonome sur tâche active | `AgentRunner` interface/adaptateur |
| Health dashboard | Statut Hermes et jobs | Health scheduler DEV_CORE natif |

## 3. Principe d’architecture cible

```text
DEV_CORE Scheduler
├─ DEV_CORE\Scheduler\scheduler_tick.py
├─ DEV_CORE\Scheduler\scheduler_service.py
├─ DEV_CORE\Scheduler\scheduler_cli.ps1
├─ DEV_CORE_DATA\Scheduler\jobs.json
├─ DEV_CORE_DATA\Logs\scheduler\scheduler_tick.log
├─ lock single-instance
├─ retry/backoff
├─ missed-run recovery
├─ dashboard health
└─ adapters optionnels
   ├─ HermesAdapter
   ├─ WindowsTaskSchedulerAdapter
   └─ AgentRunnerAdapter
```

## 4. Scope

À remplacer :

- orchestration cron;
- état runtime des jobs;
- réparation des `next_run_at`;
- statut dashboard scheduler;
- rotation logs scheduler;
- lock single-instance;
- wrappers `no_agent: true`.

À conserver temporairement :

- Hermes comme fallback;
- Active Agent Task Runner tant qu’un runner agent DEV_CORE natif n’est pas stabilisé;
- MCP DEV_CORE existants, car ils ne dépendent pas conceptuellement de Hermes.

Hors scope immédiat :

- remplacement complet d’un agent autonome Codex/Hermes;
- refonte des MCP;
- cloud scheduler;
- Kubernetes/Temporal.

## 5. Roadmap par phases

### Phase 0 — Stabilisation Hermes existant

Statut : en cours / partiellement fait.

Objectifs :

- éviter les faux rouges cockpit;
- éviter deux tick daemons;
- réparer `jobs.json`;
- réduire les coûts de lecture log.

Livrables :

- health cockpit : `OK / DEGRADED / DOWN`;
- seuil tick vieux : 600s;
- lock single-instance;
- rotation `cron_tick.log`;
- resync `~\.hermes\cron\jobs.json`.

Critères d’acceptation :

- un seul tick effectif;
- dashboard ne marque pas rouge si process vivant + tick vieux;
- `next_run_at` futurs après resync;
- log actif < 5 MiB.

### Phase 1 — Modèle scheduler DEV_CORE natif

Objectifs :

- définir le contrat stable des jobs DEV_CORE;
- ne plus dépendre du schéma Hermes pour l’état interne.

Fichiers proposés :

- `DEV_CORE\Scheduler\scheduler_contract.py`
- `DEV_CORE\Scheduler\test_scheduler_contract.py`
- `DEV_CORE_DATA\Scheduler\jobs.json`

Contrat minimal job :

```json
{
  "schema_version": 1,
  "id": "daily_launch",
  "name": "DEV_CORE Daily Launch",
  "enabled": true,
  "schedule": { "kind": "cron", "expr": "0 10 * * *" },
  "command": {
    "type": "powershell",
    "path": "DEV_CORE/Scripts/launch.ps1",
    "args": []
  },
  "state": {
    "next_run_at": "...",
    "last_run_at": "...",
    "last_status": "ok|error|skipped",
    "last_error": null,
    "completed": 0
  }
}
```

Critères d’acceptation :

- validation stricte du schéma;
- rejet des chemins hors DEV_CORE;
- `next_run_at` recalculable;
- migration depuis `hermes_cron.yaml`.

### Phase 2 — Tick loop natif

Objectifs :

- exécuter les jobs `no_agent: true` sans Hermes;
- garantir single-instance;
- gérer logs et erreurs.

Fichiers proposés :

- `DEV_CORE\Scheduler\scheduler_tick.py`
- `DEV_CORE\Scheduler\scheduler_lock.py`
- `DEV_CORE\Scheduler\scheduler_logs.py`
- `DEV_CORE\Scheduler\test_scheduler_tick.py`

Comportements :

- tick toutes les 60s;
- lock fichier;
- timeout par job;
- capture stdout/stderr;
- retry/backoff simple;
- mise à jour atomique de `jobs.json`;
- rotation log.

Critères d’acceptation :

- aucun double tick;
- une panne job ne tue pas le scheduler;
- `last_status` fiable;
- `next_run_at` réparé si stale.

### Phase 3 — Migration des jobs `no_agent: true`

Jobs à migrer :

- `DEV_CORE Daily Launch`;
- `DEV_CORE Daily Endday`;
- `DEV_CORE Weekly Maintenance`;
- `DEV_CORE Periodic Task Scan`;
- `DEV_CORE Periodic Sync & Dashboard`;
- `DEV_CORE Event Watcher`.

Livrables :

- registre `DEV_CORE\Scheduler\jobs.devcore.json`;
- script `scheduler_sync.ps1`;
- script `scheduler_status.ps1`;
- dashboard branché sur `DEV_CORE_DATA\Scheduler\jobs.json`.

Critères d’acceptation :

- tous les jobs ci-dessus passent par scheduler DEV_CORE;
- Hermes et DEV_CORE scheduler donnent le même prochain run pendant la phase dual-run;
- pas de doublon d’exécution.

### Phase 4 — Dashboard et diagnostic natifs

Objectifs :

- remplacer l’affichage “Hermes Cron Daemon” par “DEV_CORE Scheduler”;
- garder Hermes comme fallback visible.

Livrables :

- section cockpit `DEV_CORE Scheduler`;
- `dc scheduler status`;
- `dc scheduler doctor`;
- `dc scheduler repair --dry-run`;
- intégration `dc check --gate`.

Critères d’acceptation :

- status `OK / DEGRADED / DOWN`;
- détection jobs stale;
- réparation dry-run;
- logs paginés ou tronqués.

### Phase 5 — Agent Runner abstraction

Objectifs :

- isoler le job “Active Agent Task Runner” derrière une interface;
- permettre plusieurs backends : Hermes, Codex CLI, no-op, futur runner interne.

Interface proposée :

```text
AgentRunner
├─ has_active_task()
├─ build_prompt(task)
├─ run(task, timeout)
├─ checkpoint(task)
└─ report_status()
```

Critères d’acceptation :

- le scheduler ne connaît pas Hermes directement;
- le runner peut être désactivé sans casser les jobs système;
- timeouts et checkpoints documentés.

### Phase 6 — Hermes optionnel

Objectifs :

- supprimer Hermes du chemin critique;
- garder seulement un adaptateur si souhaité.

Livrables :

- flag config : `scheduler.backend = devcore|hermes`;
- migration docs;
- procédure rollback vers Hermes;
- suppression des dépendances obligatoires Hermes dans launch.

Critères d’acceptation :

- DEV_CORE démarre sans Hermes installé;
- les jobs système fonctionnent;
- cockpit reste complet;
- `dc check --gate` passe sans Hermes.

## 6. Plan de tests

Tests unitaires :

- parsing cron;
- calcul `next_run_at`;
- validation job schema;
- lock single-instance;
- rotation log.

Tests intégration :

- job success;
- job timeout;
- job error;
- stale `next_run_at`;
- restart scheduler;
- dual-run Hermes vs DEV_CORE.

Tests non-régression :

- `ci_python_tests.ps1`;
- `ci_powershell_tests.ps1`;
- `dc check --gate`;
- dashboard payload.

## 7. Risques

| Risque | Mitigation |
|---|---|
| Double exécution de jobs | lock global + idempotency key par job/run |
| Divergence Hermes/DEV_CORE pendant migration | phase dual-read, un seul backend actif en écriture |
| Perte historique jobs | importer telemetry existante depuis Hermes |
| Active Agent difficile à remplacer | interface `AgentRunner` et Hermes fallback |
| Dashboard lent | logs rotatés + lectures bornées |

## 8. Recommandation finale

Ne pas supprimer Hermes immédiatement.

Ordre recommandé :

1. stabiliser Hermes actuel;
2. créer scheduler DEV_CORE natif;
3. migrer les jobs système;
4. abstraire l’agent runner;
5. rendre Hermes optionnel;
6. supprimer Hermes seulement après deux semaines de fonctionnement sans incident.

Décision cible : DEV_CORE doit posséder son orchestration. Hermes doit devenir un adaptateur, pas une dépendance.
