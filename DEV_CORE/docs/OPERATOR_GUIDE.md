# DEV_CORE Operator Guide

Guide d'exploitation pour démarrer, diagnostiquer et gérer DEV_CORE v10.0 à l'aide du moteur Python natif (`devcore_engine`) et de la base unifiée SQLite.

Voir aussi :
- `API_REFERENCE.md` pour le gateway API.
- `PLATFORM_DOCUMENTATION.md` pour l'architecture complète.
- `SYSTEM_OVERVIEW.md` pour la carte système.
- `IMPLEMENTATION_HISTORY.md` pour la chronologie des versions.
- `ARCHITECTURE_DECISIONS.md` pour les ADR.
- `AI_CAPABILITY_REGISTRY.md` pour le routage modèle/agent.

---

## Démarrage et Cycle de Vie

### 1. Démarrage de la Plateforme
DEV_CORE démarre instantanément en arrière-plan sans Docker :
```powershell
python -m devcore_engine launch
# ou plus court :
dc launch
```
Cette commande :
- Initialise ou valide la base de données unifiée `DEV_CORE_DATA/devcore.db`.
- Lance automatiquement le **System Watchdog & Auto-Healer** ([`system_watcher.py`](file:///c:/devcore/DEV_CORE/devcore_engine/infra/system_watcher.py)) qui surveille et auto-guérit en arrière-plan :
  - **Dashboard API** (Port `20129`)
  - **Gemini Router** (Port `20130`)
  - **Headroom Proxy** (Port `8787`) avec timeout d'initialisation porté à 15s
  - **Anthropic Adapter** (Port `8788`)
  - **Repowise Server** (Port `7337`)
  - **Scheduler Daemon** (`scheduler_tick.py`)

### 2. Arrêt Propre d'une Session
```powershell
python -m devcore_engine.cli session end
```

---

## Diagnostics et Vérifications

### 1. Inspection Rapide de l'État (Cockpit Check)
Le moteur de diagnostic intégré inspecte les variables d'environnement, les ports des services actifs et la validité de la base de données SQLite :
```powershell
python -m devcore_engine diagnose
# ou plus court :
dc check
```

En cas de corruption ou de dysfonctionnement, cette commande suggère et applique des réparations non destructives.

### 2. Tests de Non-Régression
```powershell
# Exécuter les tests unitaires de l'engine Python
python -m pytest c:\devcore\DEV_CORE\tests\test_devcore_engine.py
```

---

## Gestion des Données et de la Mémoire

### 1. Base Sémantique Unifiée (`devcore.db`)
Toutes les entités (tâches, logs, métriques, événements, mémoire) sont enregistrées dans le fichier unique `DEV_CORE_DATA/devcore.db`. 
- **WAL (Write-Ahead Logging)** est activé pour autoriser des lectures/écritures simultanées ultra-rapides.
- Les requêtes sémantiques s'exécutent en interne via l'extension native `sqlite-vec` (portée à 768 dimensions), remplaçant l'ancienne instance Qdrant.

### 2. Réparation de la Base SQLite
Si la base de données SQLite présente un état de corruption, vous pouvez la régénérer de manière idempotente :
```powershell
# Supprimer le fichier corrompu
Remove-Item "C:\devcore\DEV_CORE_DATA\devcore.db" -Force

# Relancer la migration de données historique
python -m devcore_engine.migrate_to_unified_db
```

---

## Régénération Manuelle du Cockpit Dashboard
Le cockpit (Dashboard HTML) est mis à jour en continu à la réception d'événements. Vous pouvez forcer sa régénération manuellement via :
```powershell
python c:\devcore\DEV_CORE\Scripts\gen_dashboard.py
```

Le script utilise un fichier de verrouillage (`gen_dashboard.lock`) pour éviter les générations concurrentes. Si un processus se termine anormalement, le verrou expire au bout de 120 secondes ou peut être supprimé manuellement :
```powershell
Remove-Item "C:\devcore\DEV_CORE_DATA\Runtime\gen_dashboard.lock" -Force
```

