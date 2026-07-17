# DEV_CORE v10 -- Gap Analysis, Baselines & Container Spec

**Date** : 2026-07-17  
**Statut** : final (Sprint 00 Deliverable)  
**Tâche associée** : `[T-226]`

---

## 1. Introduction

Ce document présente l'audit et le cadrage technique requis pour le passage de DEV_CORE en version v10 (mode *container-first*). Il dresse l'inventaire complet des composants existants, définit leur sort dans l'architecture cible via une matrice de décision, consigne les performances de référence (baselines) et spécifie le fichier `docker-compose.yml` cible minimal.

---

## 2. Inventaire complet

### 2.1 Scripts PowerShell (`DEV_CORE/Scripts/`)
Le dépôt contient **~96 scripts PowerShell** (117 en incluant les fichiers archivés). Ils se répartissent dans les catégories suivantes :

- **Moteur & CLI principale** :
  - `dc.ps1` (lanceur unique et dispatcheur de commandes)
  - `launch.ps1` (script d'initialisation et démarrage quotidien)
  - `launch_all.ps1`
  - `endday.ps1` (clôture quotidienne, synthèse et extraction de leçons)
  - `endday_check.ps1`
  - `diagnose.ps1` (diagnostic du système local)
  - `verify.ps1` (vérification déterministe pour la CI)
  - `setup.ps1` (installation des dépendances)
  - `guided_recovery.ps1`
- **Gestion des tâches (Task Board)** :
  - `task_add.ps1`, `task_edit.ps1`, `task_next.ps1`, `task_done.ps1`, `task_pause.ps1`, `task_skip.ps1`, `task_list.ps1`, `task_status.ps1`, `task_step_done.ps1`, `task_sync.ps1`, `task_scan.ps1`
- **Services centraux** :
  - `context_service.ps1`, `event_bus.ps1`, `gateway.ps1`, `learning_service.ps1`, `memory_hierarchy.ps1`, `memory_service.ps1`, `metrics_service.ps1`, `plugin_service.ps1`
- **Processus & Proxies Repowise (Sidecars)** :
  - `ensure_repowise_ipv6_proxy.ps1`, `ensure_repowise_mcp.ps1`, `ensure_repowise_watch.ps1`, `ensure_repowise_web_languages.ps1`, `ensure_repowise_web_proxy.ps1`, `repowise_watch_worker.ps1`
- **Maintenance & Synchro** :
  - `obsidian_sync.ps1`, `qdrant_sync.ps1`, `rotate_dashboard_token.ps1`, `toonify.ps1`
- **Hooks Git** :
  - `post-commit.hook`, `install_hooks.ps1`, `install_universal_hooks.ps1`, `post_tool_hook.ps1`
- **Tests** :
  - ~40 scripts `test_*.ps1` validant les fonctionnalités unitaires et d'intégration.

### 2.2 Modules Python (`DEV_CORE/`)
Le projet contient **~160 fichiers `.py`**, principalement structurés comme suit :

- **API Gateway (`DEV_CORE/API/devcore_api/`)** :
  - `app.py` (FastAPI central)
  - `contracts.py` (gestion et validation des contrats de données)
  - `ports.py`, `schemas.py`, `worker.py`, `run_state.py`, `observability.py`, `llmops.py`, `metrics.py`, `slo.py`, `github_webhooks.py`, `correlation.py`
- **CLI & Core Tools (`DEV_CORE/Tools/devcore/`)** :
  - 21 modules Python (`cli.py`, `router.py`, `paths.py`, `session.py`, `telemetry.py`, `missions.py`, `memory.py`, `memory_sync.py`, `qdrant_queue.py`, etc.) gérant la logique système.
- **Scripts autonomes et daemons (`DEV_CORE/Scripts/`)** :
  - `hermes_cron_tick.py` (boucle d'activation cron)
  - `gemini_router.py` (proxy de requêtage LLM)
  - `dashboard_api.py` (serveur API du cockpit)
  - `ai_capability_registry.py` (déclaration de compétences IA)
- **Sécurité et Évaluations** :
  - `DEV_CORE/Security/security_review.py`
  - Modules d'évaluation sous `DEV_CORE/Evals/`

### 2.3 Endpoints API v1
Exposés par l'application FastAPI (`API/devcore_api/app.py`) :
- `GET /api/v1/health` (vérification de santé basique)
- `GET /api/v1/contracts` (catalogue des contrats de données)
- `GET /api/v1/tasks` (liste des tâches du projet)
- `POST /api/v1/integrations/github/webhook` (réception et vérification des webhooks GitHub)

### 2.4 Jobs Cron Hermes
Déclarés dans `DEV_CORE/Scripts/hermes_cron.yaml` :
- `daily_launch` (tous les jours à 10:00, `no_agent: true`)
- `daily_endday` (tous les jours à 04:00, `no_agent: true`)
- `weekly_maintenance` (le dimanche à 05:00, `no_agent: true`)
- `periodic_task_scan` (toutes les 10 min, `no_agent: true`)
- `periodic_task_sync_dashboard` (toutes les 10 min, `no_agent: true`)
- `event_watcher` (toutes les 2 min, `no_agent: true`)
- `active_agent_task_runner` (toutes les 5 min, exécution autonome via agent, `no_agent: false`)

---

## 3. Matrice de décision (Garder / Migrer / Conteneuriser)

| Composant / Script | Décision v10 | Raison & Implémentation v10 |
|---|:---:|---|
| `launch.ps1` | **Wrapper Host** | Réduit à vérifier la présence de Docker, puis exécuter `docker compose up -d`. |
| `endday.ps1` | **Migrer (Python)** | La logique de consolidation de session et d'extraction de leçons sera portée dans le conteneur `runtime` en Python. |
| `dc.ps1` | **Wrapper Host** | Appelle l'image container `runtime` via `docker compose exec runtime devcore [args]`. |
| `task_*.ps1` | **Conteneuriser** | Les scripts PowerShell de tâches sont remplacés par des appels directs à l'outil CLI Python `devcore` s'exécutant dans le conteneur `runtime`. |
| Services centraux (`*_service.ps1`) | **Supprimer / Migrer** | Toute la logique de gestion de contexte, mémoire, métriques et plugins est reprise par des modules Python équivalents dans les conteneurs `api`/`runtime`. |
| `hermes_cron_tick.py` | **Conteneuriser** | Devient l'entrypoint du service Compose `scheduler`. Plus de dépendance à `msvcrt` (verrous Windows), remplacement par un système de lock multi-plateforme. |
| Qdrant | **Conteneuriser** | Déclaré comme service standard `qdrant` dans le Compose (image officielle `qdrant/qdrant`), persistant sur volume Docker. |
| Gemini Router | **Conteneuriser** | S'exécute dans un conteneur dédié, bindé sur `0.0.0.0`, accessible sur le réseau Docker. |
| Dashboard API | **Consolider** | Fusionné avec le conteneur `api` pour simplifier le réseau et réduire l'empreinte mémoire. |
| Dashboard Web (Next.js) | **Conteneuriser** | S'exécute dans le service `dashboard-web` via une image Node légère. Le fichier HTML lourd de 14.7 MB est décomposé en composants réactifs. |

---

## 4. Mesures de référence (Baselines)

Mesures physiques initiales relevées sur l'hôte Windows :

### 4.1 Tailles et Payloads
- **dashboard_payload_size** : 14 852 499 octets (~14.85 Mo)

### 4.2 Latences de référence
- **verify_config_load** : p50 = 1.657 ms | p95 = 66.313 ms
- **launch.ps1** (initialisation host) : 405203.87 ms (~6 min 45 s)
- **dc next task** (temps de réponse CLI) : 79376.143 ms (~1 min 19 s)
- **task_scan.ps1** (analyse projet) : 2624.826 ms (~2.62 s)
- **gen_dashboard.ps1** (génération du cockpit) : 65137.008 ms (~1 min 5 s)


---

## 5. Spécification Compose Cible (Minimale)

Le fichier `docker-compose.yml` cible pour le Sprint 01 inclut les services fondamentaux suivants :

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: devcore-postgres
    environment:
      POSTGRES_USER: devcore
      POSTGRES_PASSWORD: devcore_secure_pass
      POSTGRES_DB: devcore
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U devcore -d devcore"]
      interval: 10s
      timeout: 5s
      retries: 5
    mem_limit: 512mb

  qdrant:
    image: qdrant/qdrant:latest
    container_name: devcore-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/readyz"]
      interval: 10s
      timeout: 5s
      retries: 3
    mem_limit: 512mb

  gemini-router:
    build:
      context: .
      dockerfile: DEV_CORE/docker/Dockerfile.python
    container_name: devcore-gemini-router
    command: python DEV_CORE/Scripts/gemini_router.py
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DEVCORE_GEMINI_ROUTER_BIND=0.0.0.0
    ports:
      - "20130:20130"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:20130/health"] # Ou check TCP
      interval: 10s
      timeout: 5s
      retries: 3
    mem_limit: 256mb

  api:
    build:
      context: .
      dockerfile: DEV_CORE/docker/Dockerfile.python
    container_name: devcore-api
    command: uvicorn DEV_CORE.API.devcore_api.app:app --host 0.0.0.0 --port 20131
    environment:
      - DEVCORE_PLATFORM_ROOT=/app/DEV_CORE
      - DEVCORE_DATA_ROOT=/data
      - QDRANT_URL=http://qdrant:6333
      - DEVCORE_DATABASE_URL=postgresql://devcore:devcore_secure_pass@postgres:5432/devcore
    volumes:
      - .:/app
      - devcore_data:/data
    ports:
      - "20131:20131"
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:20131/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    mem_limit: 512mb

volumes:
  postgres_data:
  qdrant_storage:
  devcore_data:
```
