# DEV_CORE -- Guide de Migration de la v9 vers la v10 Unifiée

Ce document guide les utilisateurs et développeurs dans la transition depuis l'ancienne architecture v9 basée sur des fichiers JSON dispersés vers la plateforme unifiée DEV_CORE v10.

---

## 1. Changements Majeurs d'Architecture (v9 vs v10)

| Domaine | DEV_CORE v9 | DEV_CORE v10 Unifiée |
|---|---|---|
| Stockage d'État | 100+ fichiers `tasks.json` séparés | Base centralisée SQLite WAL `devcore.db` + sync JSON |
| APIs & Rendu | Génération HTML monolithique synchrone (~2.4s) | API REST paginée (`dashboard_api.py`, < 2ms) + SSE Stream |
| Intégrations MCP | Commandes `powershell.exe` dépendantes | Serveurs MCP 100% Python-natifs (`mcp-devcore`, `mcp-qdrant`) |
| Ingestion & Logging | Fichiers `.jsonl` non bornés | Rotation automatique logs (> 30j) et limite d'historique (50 sessions) |
| Déploiement | Scripts de lancement Powershell | Conteneurs Docker Compose isolés (`mem_limit` 128 - 512 MB) |

---

## 2. Étapes de Migration pour un Projet

1. **Exécution de la Migration SQLite** :
   ```bash
   python C:\devcore\DEV_CORE\Scripts\migrate_json_to_sqlite.py
   ```
2. **Purge des Logs et Backups Ansiens** :
   ```bash
   python C:\devcore\DEV_CORE\Scripts\rotate_logs_and_backups.py
   ```
3. **Mise à Jour de la Configuration Repowise** :
   Créer ou vérifier la présence du fichier `.repowiseignore` à la racine pour exclure `DEV_CORE_DATA/` et `.next/`.

4. **Démarrage des Services v10 Conteneurisés** :
   ```bash
   docker compose up -d
   ```
