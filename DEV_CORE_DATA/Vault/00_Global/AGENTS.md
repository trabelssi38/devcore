# Global Agent Rules — DEV_CORE v6

## Comportement universel (tous clients)
- Toujours chercher solution simple d'abord
- Skills first : vérifier skills_registry.json avant d'exécuter
- Memory first : consulter MEMORY.md + Qdrant avant de re-générer
- Réponse concise — pas de préambule
- Terminer par Next Actions si la tâche génère des suites
- Commit tag [M-XX] pour chaque étape de mission

## Par domaine
- DB : attention impacts prod, patch minimal
- Python : lisibilité + vitesse, async si pertinent
- Web : responsive + propre, checklist accessibilité
- Android : batterie + perf, patch minimal

## Token discipline
- Charger uniquement les skills pertinents à la tâche courante
- Résumés structurés > prose longue
- Ne pas répéter le contexte déjà fourni

## Agents spécialisés
- Claude Code (GML) : architecture · décisions · review · specs
- Codex Desktop    : coding rapide · patches · TDD · refactoring
- Antigravity      : bulk · génération masse · automation · parallèle
