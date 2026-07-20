---
name: dashboard-ui-craft
description: Guidelines and patterns for crafting responsive, modern, dark-mode web dashboards with high contrast, glassmorphism, and reactive micro-interactions.
---

# Dashboard UI Craft Skill

Ce skill fournit les directives et patrons de conception pour construire des tableaux de bord web modernes, performants et hautement lisibles pour la plateforme DEV_CORE v10.

---

## 1. Principes de Design System

### Palette Sombre & Harmonie HSL
- **Fond de page** : `#0b0f19` ou `#0d1117`
- **Cartes / Panneaux** : `rgba(15, 23, 42, 0.6)` avec `backdrop-filter: blur(12px)` (glassmorphism)
- **Bordures** : `1px solid rgba(255, 255, 255, 0.08)`
- **Accents** : Indigo (`#6366f1`), Cyan (`#06b6d4`), Vert Succès (`#22c55e`), Rouge Erreur (`#ef4444`)

### Typographie Système Moderne
- Utiliser `system-ui`, `Inter`, ou `Roboto` pour les textes.
- Utiliser `'JetBrains Mono', monospace` pour les identifiants de tâches, hashs SHA-256, codes de réponse HTTP et compteurs de jetons.

---

## 2. Micro-Interactions & États Survol

1. **Cartes Interactives** :
   ```css
   .card {
     background: rgba(15, 23, 42, 0.6);
     border: 1px solid rgba(255, 255, 255, 0.08);
     border-radius: 8px;
     transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease;
   }

   .card:hover {
     transform: translateY(-2px);
     border-color: rgba(99, 102, 241, 0.4);
   }
   ```

2. **Badges d'État Rehaussés** :
   - Formater les compteurs avec espaces séparateurs de milliers (ex: `52 136`).
   - Utiliser des badges translucides avec texte en gras et fond atténué.

---

## 3. Conformité & Performance

- **Zero Monolithe HTML** : Séparer la logique d'état et le rendu DOM.
- **Réduction du DOM Footprint** : Ne jamais rendre plus de 20 éléments complétés par vue sans pagination.
