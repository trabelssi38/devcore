---
name: web_ui
description: Utiliser pour toute tâche web frontend : HTML, CSS, JS, React, responsive, composants.
compatibility: Claude Code · Codex · Gemini · Qwen
---
# Skill — Web UI

## Règles fondamentales
- Responsive first : mobile 375px → tablet 768px → desktop 1280px
- CSS : variables custom properties, pas de valeurs hardcodées
- Accessibilité : contraste WCAG AA (4.5:1), labels, focus visible
- Performance : images optimisées, lazy loading, bundle minimal
- React : composants fonctionnels + hooks, pas de class components

## Checklist UI
- [ ] Responsive testé (375/768/1280px)
- [ ] Contraste texte ≥ 4.5:1
- [ ] Focus visible au clavier
- [ ] Images avec alt text
- [ ] Touch targets ≥ 44×44px mobile
- [ ] Pas d'informations transmises par couleur seule
