# PATHS.md — DEV_CORE v6
# Chemins de référence absolus — Updated 2026-05-11

## Plateforme
DEVCORE_PLATFORM_ROOT = C:\devcore\DEV_CORE
DEVCORE_DATA_ROOT     = C:\devcore\DEV_CORE_DATA
DEVCORE_LEGACY_ROOT   = C:\devcore\DEV_CORE_LEGACY

## Sous-répertoires plateforme
SCRIPTS     = C:\devcore\DEV_CORE\Scripts
SCRIPTS_AUTO= C:\devcore\DEV_CORE\Scripts\Auto
SKILLS      = C:\devcore\DEV_CORE\Skills
CONFIG      = C:\devcore\DEV_CORE\Config
TEMPLATES   = C:\devcore\DEV_CORE\Templates
TOOLS       = C:\devcore\DEV_CORE\Tools
SCHEMAS     = C:\devcore\DEV_CORE\Schemas

## Sous-répertoires data (persistants)
VAULT       = C:\devcore\DEV_CORE_DATA\Vault
MEMORY      = C:\devcore\DEV_CORE_DATA\Memory
SESSIONS    = C:\devcore\DEV_CORE_DATA\Sessions
LOGS        = C:\devcore\DEV_CORE_DATA\Logs
BACKUPS     = C:\devcore\DEV_CORE_DATA\Backups
QDRANT_DATA = C:\devcore\DEV_CORE_DATA\qdrant_storage

## Fichiers clés
MEMORY_MD       = C:\devcore\DEV_CORE_DATA\Memory\MEMORY.md
TASKS_JSON      = C:\devcore\DEV_CORE_DATA\Memory\tasks.json
DECISIONS_MD    = C:\devcore\DEV_CORE_DATA\Memory\DECISIONS.md
GLOBAL_STATE_MD = C:\devcore\DEV_CORE_DATA\Memory\GLOBAL_STATE.md
ACTIVE_CLIENT   = C:\devcore\DEV_CORE\Config\active_client.txt
SKILLS_REGISTRY = C:\devcore\DEV_CORE\Skills\skills_registry.json
SESSION_CONTEXT = C:\devcore\DEV_CORE_DATA\Logs\scripts\session_context.txt

## Qdrant
QDRANT_URL      = http://localhost:6333
EMBED_PROVIDER  = ollama
EMBED_MODEL     = nomic-embed-text
EMBED_URL       = http://localhost:11434

## Variables d'environnement (override possible)
DEVCORE_PLATFORM_ROOT -> env var DEVCORE_PLATFORM_ROOT
DEVCORE_DATA_ROOT     -> env var DEVCORE_DATA_ROOT
