# DEV_CORE v10 -- Budgets de Performance Plateforme (Performance Budgets)

Ce document établit les budgets de performance maximaux tolérés (SLA/SLO) pour chaque sous-système de la plateforme DEV_CORE v10.

---

## 1. Budgets de Latence Exécution (ms)

| Composant / Sous-système | Cible p50 | Plafond p95 | Fréquence |
|---|---|---|---|
| Requêtes SQLite WAL (`devcore.db`) | **< 2.0 ms** | **< 5.0 ms** | Sur chaque polling / API read |
| Génération Dashboard HTML (`gen_dashboard.py`) | **< 30.0 ms** | **< 100.0 ms** | Post-commit & sync |
| Audit Statique UI/Motion (`audit_ui_motion.py`) | **< 50.0 ms** | **< 150.0 ms** | CI Gates & verify |
| Rotation Logs & Compression (`rotate_logs_and_backups.py`) | **< 100.0 ms** | **< 300.0 ms** | Cron horaire / endday |
| Service SSE Granulaire Delta Stream | **< 10.0 ms** | **< 25.0 ms** | Streaming continu HTTP/2 |

---

## 2. Budgets de Consommation Mémoire (RAM)

| Daemon / Service | Empreinte Cible | Plafond Toléré (Limit Docker) |
|---|---|---|
| Dashboard API Server (`dashboard_api.py`) | **< 64 MB** | **256 MB** |
| Gemini Router (`gemini_router.py`) | **< 48 MB** | **128 MB** |
| Repowise Watcher / Proxy | **< 60 MB** | **256 MB** |
| MCP Devcore Server (`mcp-devcore`) | **< 40 MB** | **128 MB** |
| MCP Qdrant Server (`mcp-qdrant`) | **< 40 MB** | **128 MB** |

---

## 3. Budgets Réseau & Payloads

- **Payload Initial Dashboard API** : **< 100 KB** (obtenu : ~5.5 KB par page).
- **Mises à jour SSE Delta** : **< 5 KB** par message JSON (`dashboard.delta`).
- **En-têtes CORS / CSRF overhead** : **< 0.5 ms** par requête HTTP.
