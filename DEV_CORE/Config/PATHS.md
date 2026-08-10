# PATHS.md — DEV_CORE v6
# Chemins de référence absolus — Updated 2026-08-10

## Architecture deux racines (depuis v10.3.4)
#
#  DEVCORE_DATA_ROOT   = Dropbox/DEV_CORE_DATA  (partagé entre machines)
#  DEVCORE_LOCAL_ROOT  = %LOCALAPPDATA%/DEV_CORE_LOCAL  (local à chaque machine)
#
# devcore.db et les fichiers runtime (Logs, Cache, Scheduler, Bus...)
# se trouvent dans DEVCORE_LOCAL_ROOT pour éviter les conflits Dropbox WAL.

## Plateforme
DEVCORE_PLATFORM_ROOT = C:\devcore\DEV_CORE
DEVCORE_LEGACY_ROOT   = C:\devcore\DEV_CORE_LEGACY

## Données partagées (Dropbox) — auto-détecté via info.json
DEVCORE_DATA_ROOT     = <Dropbox>/DEV_CORE_DATA
VAULT       = <Dropbox>/DEV_CORE_DATA\Vault
MEMORY      = <Dropbox>/DEV_CORE_DATA\Memory
PLUGINS     = <Dropbox>/DEV_CORE_DATA\Plugins
VAULT       = <Dropbox>/DEV_CORE_DATA\Vault
SKILLS      = <Dropbox>/DEV_CORE_DATA\Skills
WORKFLOWS   = <Dropbox>/DEV_CORE_DATA\Workflows
METRICS     = <Dropbox>/DEV_CORE_DATA\Metrics
KNOWLEDGE   = <Dropbox>/DEV_CORE_DATA\Knowledge

## Données locales machine — ne jamais synchroniser Dropbox
DEVCORE_LOCAL_ROOT = %LOCALAPPDATA%\DEV_CORE_LOCAL
DEVCORE_DB         = %LOCALAPPDATA%\DEV_CORE_LOCAL\devcore.db
LOGS        = %LOCALAPPDATA%\DEV_CORE_LOCAL\Logs
CACHE       = %LOCALAPPDATA%\DEV_CORE_LOCAL\Cache
SCHEDULER   = %LOCALAPPDATA%\DEV_CORE_LOCAL\Scheduler
BUS         = %LOCALAPPDATA%\DEV_CORE_LOCAL\Bus
SESSIONS    = %LOCALAPPDATA%\DEV_CORE_LOCAL\Sessions
BACKUPS     = %LOCALAPPDATA%\DEV_CORE_LOCAL\Backups
QDRANT_DATA = %LOCALAPPDATA%\DEV_CORE_LOCAL\qdrant_storage
RUNTIME     = %LOCALAPPDATA%\DEV_CORE_LOCAL\Runtime

## Sous-répertoires plateforme
SCRIPTS     = C:\devcore\DEV_CORE\Scripts
SCRIPTS_AUTO= C:\devcore\DEV_CORE\Scripts\Auto
CONFIG      = C:\devcore\DEV_CORE\Config
TEMPLATES   = C:\devcore\DEV_CORE\Templates
TOOLS       = C:\devcore\DEV_CORE\Tools
SCHEMAS     = C:\devcore\DEV_CORE\Schemas

## Fichiers clés (data partagée)
MEMORY_MD       = <Dropbox>/DEV_CORE_DATA\Memory\MEMORY.md
TASKS_JSON      = <Dropbox>/DEV_CORE_DATA\Memory\tasks.json
DECISIONS_MD    = <Dropbox>/DEV_CORE_DATA\Memory\DECISIONS.md
GLOBAL_STATE_MD = <Dropbox>/DEV_CORE_DATA\Memory\GLOBAL_STATE.md
SKILLS_REGISTRY = C:\devcore\DEV_CORE\Skills\skills_registry.json

## Fichiers clés (data locale)
ACTIVE_CLIENT   = %LOCALAPPDATA%\DEV_CORE_LOCAL\Runtime\active_client.txt
SESSION_CONTEXT = %LOCALAPPDATA%\DEV_CORE_LOCAL\Logs\scripts\session_context.txt

## Qdrant
QDRANT_URL      = http://localhost:6333
EMBED_PROVIDER  = ollama
EMBED_MODEL     = nomic-embed-text
EMBED_URL       = http://localhost:11434

## Variables d'environnement (override possible)
DEVCORE_PLATFORM_ROOT -> env var DEVCORE_PLATFORM_ROOT
DEVCORE_DATA_ROOT     -> env var DEVCORE_DATA_ROOT  (Dropbox, partagé)
DEVCORE_LOCAL_ROOT    -> env var DEVCORE_LOCAL_ROOT (local machine)
