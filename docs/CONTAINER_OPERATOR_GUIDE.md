# DEV_CORE v10 -- Guide Opérateur Conteneur (Container-First Operator Guide)

Ce guide détaille l'exploitation et la maintenance des conteneurs Docker Compose pour la plateforme DEV_CORE v10.

---

## 1. Architecture des Services Conteneurisés

| Service Docker | Rôle & Port | Dockerfile | Limite RAM |
|---|---|---|---|
| `qdrant` | Base de données vectorielle (Port 6333) | `qdrant/qdrant` | 512 MB |
| `gemini-router` | Routage d'infaillibilité IA (Port 20130) | `docker/Dockerfile.python` | 256 MB |
| `dashboard-api` | API REST & Stream SSE (Port 20129) | `docker/Dockerfile.python` | 256 MB |
| `web` | Interface Web Next.js (Port 3000) | `Web/Dockerfile` | 512 MB |
| `mcp-qdrant` | Serveur MCP Vectoriel Python | `docker/Dockerfile.python` | 128 MB |
| `mcp-devcore` | Serveur MCP Outils DEV_CORE Python | `docker/Dockerfile.python` | 128 MB |

---

## 2. Commandes d'Exploitation Courante

### Démarrage des services en arrière-plan
```bash
docker compose up -d
```

### Vérification de l'état des conteneurs
```bash
docker compose ps
```

### Consultation des logs d'un service
```bash
docker compose logs -f dashboard-api
```

### Arrêt et nettoyage des conteneurs
```bash
docker compose down
```

---

## 3. Gestion des Volumes Persistants

- **`devcore_data`** : Héberge la base SQLite `devcore.db`, la mémoire et les logs de l'application.
- **`qdrant_storage`** : Stocke les collections vectorielles Qdrant (`decisions`, `patterns`, `lessons`, `codebase`).
