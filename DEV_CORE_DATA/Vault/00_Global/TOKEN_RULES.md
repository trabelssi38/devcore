# Token Rules — DEV_CORE v6

## Règles fondamentales
- Ne jamais coller de gros fichiers dans le contexte
- Utiliser des résumés structurés
- Demander patch only quand possible
- Demander json only si besoin de structure
- Retrieval Qdrant avant contexte brut
- Charger seulement les fichiers ciblés

## Stack d'optimisation (3 couches)
1. CLAUDE.md terse : -70% verbosité outputs
2. MCP cache (ooples/token-optimizer-mcp) : -95% sur appels répétés
3. Ghost finder (alexgreensh/token-optimizer) : audit fantômes

## Budgets par catégorie
- Simple (lookup, patch) : 2k tokens max
- Moyen (feature, debug) : 8k tokens max
- Complexe (architecture) : 32k tokens max
- Bulk (automation) : 16k, compresser outputs

## Commit tags
- Toujours tagger [M-XX] dans les commits de mission
- Permet l'auto-incrémentation des steps (post-commit hook)
