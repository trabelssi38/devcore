# DEV_CORE API Reference

Référence publique du gateway API DEV_CORE v1. Le contrat de données historique et les endpoints Cockpit ont été unifiés dans le moteur Python natif (`devcore_engine`) utilisant la base SQLite `devcore.db`.

Voir aussi :
- `OPERATOR_GUIDE.md` pour l'exploitation quotidienne.
- `PLATFORM_DOCUMENTATION.md` pour l'architecture complète.
- `SYSTEM_OVERVIEW.md` pour la carte système.
- `IMPLEMENTATION_HISTORY.md` pour la chronologie des versions.
- `ARCHITECTURE_DECISIONS.md` pour les ADR.
- `AI_CAPABILITY_REGISTRY.md` pour le routage modèle/agent.

---

## Convention Générale
- **Dashboard API** : `http://127.0.0.1:20129` (Sert le cockpit et le read-model).
- **Gemini Router** : `http://127.0.0.1:20130` (Proxy de requêtes IA avec rate-limiting automatique).
- **Format** : JSON UTF-8.

---

## Cockpit Dashboard API Reference (Port 20129)

Le serveur API du Cockpit (`dashboard_api.py`) est exposé localement sur le port `20129`. Il fournit le support pour les mises à jour réactives en temps réel et les interactions avec le tableau de bord.

### 1. GET /api/dashboard
Renvoie le payload complet du tableau de bord.
- **Réponse 200** : Contient les sections HTML pré-rendues, le détail des métriques de tokens, et la liste des projets actifs depuis la table SQLite `projects`.

### 2. GET /api/health
Renvoie l'état détaillé de santé de l'infrastructure locale (SQLite Vector DB, Gemini Router, Headroom Proxy, API Server, Scheduler, Repowise).

### 3. GET /api/sse/events
Flux unidirectionnel SSE (Server-Sent Events) diffusant les événements en temps réel issus de la table `bus_events` de `devcore.db`.

### 4. GET /api/settings et POST /api/settings
Lit et enregistre les paramètres système unifiés en base SQLite.

### 5. POST /api/tasks/complete
Marque une tâche du pipeline comme complétée.
- **Payload** : `{"project_id": "nom-projet", "task_id": "T-XX"}`

### 6. POST /api/tasks/delete
Supprime une tâche du pipeline.
- **Payload** : `{"project_id": "nom-projet", "task_id": "T-XX"}`

---

## Gemini Router API Reference (Port 20130)

Le routeur de modèles (`gemini_router.py`) sert de passerelle OpenAI-compatible en amont de Headroom Proxy.

### 1. GET /health
Renvoie le statut de santé du routeur :
```json
{
  "status": "healthy",
  "service": "gemini-router",
  "port": 20130
}
```

### 2. POST /v1/chat/completions
Proxy les appels de chat completions vers le backend configuré, en assurant le retry automatique sur les codes de statut HTTP 429 (Rate-Limiting).
