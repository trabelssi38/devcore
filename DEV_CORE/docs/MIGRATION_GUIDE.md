# Guide de Migration DEV_CORE v10.0 (SQLite Unifié)

Ce guide détaille la migration historique de la stack Docker multi-services (PostgreSQL, Qdrant, Node API) et des scripts PowerShell vers l'architecture native Python unifiée basée sur SQLite WAL (`devcore.db`) et `sqlite-vec`.

---

## Changements Majeurs

### 1. Simplification de l'Architecture
- **Avant** : Une stack Docker lourde consommant ~2.8 GB de RAM (Postgres, Qdrant, API Node, Web dashboard, etc.) et des scripts d'orchestration PowerShell (`.ps1`).
- **Après** : Un moteur Python unifié (`devcore_engine`), utilisant une base de données unique SQLite WAL (`devcore.db`), sans aucune dépendance Docker. Consommation RAM < 250 MB.

### 2. Base de Données Unique (`devcore.db`)
Toutes les sources de vérité et de télémétrie sont consolidées dans `C:\devcore\DEV_CORE_DATA\devcore.db` :
- Tâches (`tasks`)
- Projets (`projects`)
- Événements (`bus_events`)
- Mémoire sémantique (`memory_entries` via table virtuelle sémantique `vec_memory_entries` avec `sqlite-vec` 768d)
- Skills, Métriques, Notes et Graph de Connaissances.

---

## Procédure de Migration de Données

Le script d'intégration unifiée `migrate_to_unified_db.py` s'occupe de la migration transparente de l'ensemble de l'historique :

```powershell
# Lancer le script de migration idempotent
python -m devcore_engine.migrate_to_unified_db
```

### Données migrées automatiquement :
1. **Projects & Tasks** : Extraction depuis les fichiers `tasks.json` de chaque projet.
2. **Event Bus** : Importation de tout l'historique d'événements.
3. **Mémoire Multi-couches** : Indexation des vecteurs L1 (Qdrant) directement dans la table virtuelle `sqlite-vec` de `devcore.db`.
4. **Notes Vault & Knowledge Graph** : Extraction des relations et métadonnées.

---

## Commandes d'Exploitation Unifiées (`cli.py`)

Les anciens scripts PowerShell sont remplacés par la CLI Python unifiée :

| Rôle | Commande PowerShell (obsolète) | Commande Python unifiée (v10) |
|---|---|---|
| Démarrage | `.\launch.ps1` | `python -m devcore_engine launch` ou `dc launch` |
| Arrêt | `.\stop.ps1` | `python -m devcore_engine.cli session end` |
| Diagnostic | `.\diagnose.ps1` | `python -m devcore_engine diagnose` ou `dc check` |
| Suivi Tâches | `.\task_next.ps1` | `python -m devcore_engine task board` ou `dc task board` |
| Événements | `.\events.ps1` | `python -m devcore_engine events tail` ou `dc events tail` |

---

## Vérification Post-Migration

### Checklist de Validation
- [ ] La stack Docker est éteinte (`docker compose down`) et les ressources nettoyées (`docker system prune`).
- [ ] Le fichier `DEV_CORE_DATA/devcore.db` est présent et accessible.
- [ ] La commande `python -m devcore_engine diagnose` (ou `dc check`) affiche tous les indicateurs au vert.
- [ ] Le Cockpit Web (`http://127.0.0.1:20129/`) est accessible et affiche le statut sémantique correct.
- [ ] Le Gemini Router (`http://127.0.0.1:20130/health`) répond positivement.

### Exécution des Tests de Non-Régression
```powershell
# Tests unitaires de l'engine unifié
python -m pytest c:\devcore\DEV_CORE\tests\test_devcore_engine.py
```

