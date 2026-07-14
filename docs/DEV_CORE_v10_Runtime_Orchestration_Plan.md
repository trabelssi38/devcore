# DEV_CORE v10 --- Plan de transformation vers un Runtime d'Orchestration

## Vision

Transformer DEV_CORE d'une collection de scripts en un **runtime
d'orchestration** multiplateforme (Windows, Linux, Docker) piloté par
des workflows déclaratifs.

Inspirations : - **ORCA** : moteur d'orchestration, exécution pilotée
par workflows, séparation des responsabilités. - **Loop Engineering** :
boucles autonomes, gouvernance, état, budgets, validation humaine.

> Objectif : conserver l'identité de DEV_CORE (mémoire, tâches,
> diagnostic, dashboard, Repowise) tout en remplaçant progressivement
> les scripts par un moteur Python modulaire.

------------------------------------------------------------------------

# Principes

-   Runtime unique écrit en Python.
-   Scripts PowerShell réduits à des wrappers Windows.
-   Workflows décrits en YAML.
-   Plugins pour chaque domaine.
-   Événements internes (Event Bus).
-   État centralisé.
-   Compatible Docker dès la conception.

------------------------------------------------------------------------

# Architecture cible

``` text
CLI
 │
 ▼
Runtime
 ├── Planner
 ├── Executor
 ├── Checker
 ├── Scheduler
 ├── Event Bus
 ├── State Engine
 ├── Plugin Manager
 └── API
        │
        ├── Memory (Qdrant)
        ├── Git
        ├── Docker
        ├── Gemini
        ├── Dashboard
        ├── Repowise
        └── Obsidian
```

------------------------------------------------------------------------

# Modules

## Runtime

Responsable de : - charger les workflows - gérer les plugins - publier
les événements - maintenir l'état global - orchestrer les services

## Planner

Décompose un objectif en étapes.

## Executor

Exécute les actions.

## Checker

Valide : - compilation - tests - lint - architecture - sécurité

## Scheduler

Déclenche : - tâches planifiées - hooks - workflows périodiques

## Event Bus

Événements : - TaskCompleted - CommitCreated - DockerStarted -
MemoryUpdated - ServiceFailed - WorkflowFinished

## State Engine

Source unique de vérité.

Expose : - tâches - services - mémoire - métriques - workflows

------------------------------------------------------------------------

# Plugins

-   memory
-   qdrant
-   git
-   github
-   docker
-   gemini
-   repowise
-   obsidian
-   dashboard
-   android

Tous implémentent :

-   start()
-   stop()
-   health()
-   execute()

------------------------------------------------------------------------

# Workflows

Exemple launch.yaml

``` yaml
steps:
  - service: qdrant
  - service: repowise
  - service: gemini
  - service: dashboard
  - task: load-memory
  - task: load-project
```

Autres workflows : - endday - maintenance - release - dockerize -
review - fix-bug

------------------------------------------------------------------------

# Boucles autonomes (Loop Engineering)

Niveaux :

## L1

Rapport uniquement.

## L2

Proposition de correctifs.

## L3

Correction automatique avec validation.

Chaque boucle possède : - budget - timeout - kill switch - métriques -
historique

Fichiers : - LOOP.md - STATE.md - loop-budget.md - loop-run-log.md

------------------------------------------------------------------------

# Docker

Services :

-   runtime
-   qdrant
-   dashboard
-   repowise

Volumes : - DEV_CORE_DATA - qdrant

Variables : - GEMINI_API_KEY - DEVCORE_PLATFORM_ROOT - DEVCORE_DATA_ROOT

------------------------------------------------------------------------

# Migration

## Phase 1

Créer runtime Python.

## Phase 2

Créer CLI Python.

## Phase 3

Migrer : - launch - diagnose - tasks - endday

## Phase 4

PowerShell devient wrapper.

## Phase 5

Docker officiel.

## Phase 6

Suppression progressive des scripts historiques.

------------------------------------------------------------------------

# Objectif v10

DEV_CORE devient :

-   un runtime d'orchestration
-   extensible par plugins
-   piloté par workflows
-   orienté événements
-   compatible Docker
-   multi-plateforme
-   prêt pour plusieurs agents ou un agent unique
-   conservant sa mémoire persistante et son identité.
