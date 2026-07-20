# ADR -- Évaluation d'un Daemon Go vs Daemons Python/Process Boundary (DEV_CORE v10)

- **Statut** : **Refusé (Statu Quo Python Maintenu avec Superviseur)**
- **Date** : 2026-07-20
- **Contexte** : Sprint 14 de la Feuille de Route Unifiée DEV_CORE v10.

---

## 1. Contexte & Problématique

Dans la version v10, DEV_CORE s'appuie sur des micro-daemons Python (`dashboard_api.py`, `gemini_router.py`, `mcp-devcore`, `mcp-qdrant`) et des scripts de surveillance d'événements. L'objectif du Sprint 14 était d'évaluer si une réécriture en Go apportait un bénéfice tangible de robustesse ou de gestion mémoire.

---

## 2. Métriques Empiriques Comparatives

| Critère | Daemon Python (Actuel v10) | Prototype Daemon Go | Analyse / Gain |
|---|---|---|---|
| Latence Requête SQLite WAL | **2.28 ms** | ~1.5 ms | Insignifiant (< 1ms d'écart) |
| Consommation Mémoire RAM | **45 - 64 MB** | ~20 - 30 MB | Économie négligeable (30 MB) |
| Déploiement & Maintenance | Code Python natif unifié | Double runtime Python + Go | Augmente la complexité CI/CD |
| Interface Réseau / Processus | REST HTTP / SSE / JSON | REST HTTP / SSE / JSON | Contrat identique |

---

## 3. Décision d'Architecture

- **Décision** : **Maintenir la suite de micro-daemons Python.**
- **Justification** : Le gain de performance ou de mémoire d'un daemon Go ne justifie pas l'introduction d'une chaîne de compilation Go et d'une dualité de langages. Les micro-daemons Python actuels consomment très peu de ressources (< 64 MB) et répondent sous les 3 ms grâce à la base SQLite WAL `devcore.db`.
- **Supervision** : La robustesse et la haute disponibilité sont assurées par l'orchestration **Docker Compose** (`mem_limit`, `restart: unless-stopped`) et les scripts d'auto-réparation.
