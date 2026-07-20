# DEV_CORE v10 -- Standards de Mouvement & Animations (Motion Standards)

Ce document régit les règles de conception et d'implémentation des animations et transitions CSS/JS pour tous les composants Web et Cockpits de la plateforme DEV_CORE v10.

---

## 1. Principes Fondamentaux de Performance

1. **Composite-Only Properties** :
   - Seules les propriétés animables par le compositeur GPU sans provoquer de Reflow ou Repaint layout sont autorisées : `transform` et `opacity`.
   - **Interdit** : Animer `width`, `height`, `top`, `left`, `right`, `bottom`, `margin`, `padding`, `flex`, `grid`.

2. **Interdiction Stricte de `transition: all`** :
   - Ne **JAMAIS** utiliser `transition: all`.
   - Toujours spécifier explicitement les propriétés ciblées, par exemple :
     ```css
     /* CORRECT */
     transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease-out;

     /* INTERDIT */
     transition: all 0.3s ease;
     ```

3. **Plafond de Durée & Courbes d'Accélération** :
   - Durée maximale des transitions UI : **300 ms** (recommandé : 150ms à 250ms).
   - Utiliser des fonctions de Bézier modernes au lieu de `linear` ou `ease` par défaut :
     - Entrée / Apparition : `cubic-bezier(0.16, 1, 0.3, 1)` (out-back ou smooth-out)
     - Sortie / Disparition : `cubic-bezier(0.7, 0, 0.84, 0)`

---

## 2. Accessibilité & Reduced Motion

Toute stylesheet ou composant animé doit obligatoirement inclure un bloc de repli pour l'accessibilité :

```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 3. Checklist d'Audit Motion

- [ ] Aucune occurrence de `transition: all` dans le code CSS / HTML.
- [ ] Aucune transition sur les propriétés de layout (`width`, `height`, `margin`, `padding`, `top`, `left`).
- [ ] Toutes les transitions ont une durée <= 300 ms.
- [ ] Le bloc `@media (prefers-reduced-motion: reduce)` est présent.
- [ ] Les propriétés `will-change` sont utilisées avec parcimonie sur les éléments fréquemment animés.
