# ADR-013 - Container-First Architecture

**Statut** : accepte

DEV_CORE v10 adopte une architecture orientée conteneurs par défaut (container-first) pour uniformiser l'exécution locale et en production. Le code principal est exécuté via Docker Compose, éliminant la dépendance directe à Windows, PowerShell pour la logique métier, et aux tâches planifiées du système hôte.

## Raisons

- **Portabilité** : Permet de faire tourner le système complet sur Linux, macOS et Windows de façon strictement identique.
- **Isolation** : Finit-en avec les conflits de ports, de versions de dépendances Python, ou de configurations locales du host (ex. proxy IPv6, Qdrant).
- **Reproductibilité** : Assure que l'environnement de développement local, d'intégration (CI) et de déploiement partagent exactement le même runtime et la même configuration.
- **Simplification** : Retire la complexité de gestion du cycle de vie des daemons (Hermes, Gemini Router) sur le host Windows.

## Decisions

1. **Python comme centre de gravité** : Le planificateur (scheduler), le moteur d'exécution (orchestrator), l'exécuteur de tâches (worker) et l'API v1 s'exécutent en Python dans des conteneurs basés sur une image commune DEV_CORE.
2. **Orchestration via Docker Compose** : Le mode par défaut d'initialisation et d'exploitation du système est un projet Docker Compose unifié.
3. **PowerShell restreint au Host** : Les scripts PowerShell ne contiennent plus aucune logique métier ni mutation. Ils servent uniquement de wrappers minces d'amorçage sur l'hôte physique (ex. vérifier la présence de Docker, lancer `docker compose up -d`).
4. **Rust et Go sous conditions strictes** : 
   - Rust n'est introduit que pour l'optimisation des goulots d'étranglement de performance mesurés (ex. scan massif, watch de fichiers).
   - Go est réservé uniquement si Python montre des limites structurelles de robustesse ou de gestion de processus en arrière-plan (daemons).
5. **Chemins configurables** : Le système utilise exclusivement `DEVCORE_PLATFORM_ROOT` (pointant vers `/app/DEV_CORE`) et `DEVCORE_DATA_ROOT` (pointant vers `/data` via volume Compose) pour localiser le code et les données persistantes.

## Consequences

- Pour développer, l'agent utilise le mode dev Compose avec des *bind mounts* (`volumes: - ./DEV_CORE:/app/DEV_CORE`) pour supporter le hot-reload immédiat.
- L'historique des runs, la base vectorielle Qdrant, et la base Postgres résident dans des volumes Docker persistants.
- Les conteneurs ne s'adressent pas via `localhost` mais par les noms de services définis dans le réseau Docker unifié du Compose (ex. `http://qdrant:6333`).
- La performance de démarrage dépend désormais du temps de `docker compose up` (< 60 secondes requis).
