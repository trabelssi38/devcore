# DEV_CORE — Motion & Animation Standards

Ce document définit les standards techniques et esthétiques d'animation pour le Cockpit DEV_CORE. Ces règles doivent être respectées par tout développement d'interface.

---

## 1. Durées Cibles (Durations)

Les animations de l'interface utilisateur doivent être rapides pour maintenir une sensation de réactivité élevée.

| Type d'Élément | Durée Recommandée | Règle Métier |
| :--- | :--- | :--- |
| **Bouton / Interaction rapide** | `100ms` à `160ms` | Effet de clic ou retour tactile immédiat |
| **Survol (Hover) subtil** | `120ms` à `180ms` | Transition d'opacité ou de couleur de bordure |
| **Tooltip / Popover** | `150ms` à `220ms` | Apparition rapide lors du focus/survol |
| **Toast / Notification** | `180ms` à `260ms` | Glissement fluide sur l'axe horizontal ou vertical |
| **Modale / Drawer** | `200ms` à `300ms` | Ouverture/fermeture majeure de l'écran |

> [!IMPORTANT]
> Aucune animation standard d'interface utilisateur ne doit dépasser **300ms** sans justification fonctionnelle explicite (ex. onboarding progressif).

---

## 2. Courbes de Bézier (Easings)

Les fonctions de transition linéaire (`linear`) doivent être limitées aux indicateurs de chargement ou de progression. Les animations interactives doivent utiliser des courbes d'atténuation physiques :

```css
/* Entrée rapide et amortie (Recommandé pour les éléments entrants) */
--ease-out-strong: cubic-bezier(0.23, 1, 0.32, 1);

/* Atténuation douce bidirectionnelle (Mouvements spatiaux) */
--ease-in-out-strong: cubic-bezier(0.77, 0, 0.175, 1);

/* Transition pour les Drawer/Modales */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

### Règles de Courbe
- **Enter UI** : Utilisez un `ease-out` prononcé pour que l'élément semble réactif au clic.
- **Exit/Dismiss UI** : Utilisez un `ease-in` ou un `ease-in-out` rapide.
- Evitez `ease-in` sur une interaction interactive directe (le délai initial donne une impression de lenteur).

---

## 3. Propriétés Animables & Optimisation GPU

Pour éviter les calculs de layout coûteux (reflow/repaint) qui dégradent le taux de rafraîchissement, limitez strictement les propriétés animées :

### ✅ Propriétés Recommandées (Accélérées GPU)
- `transform` (ex. `scale()`, `translateY()`, `translateX()`, `rotate()`)
- `opacity`
- `filter` (avec parcimonie)

### ❌ Propriétés Interdites (Modifications de Layout)
- `width` / `height`
- `top` / `left` / `bottom` / `right`
- `margin` / `padding`
- `font-size` / `line-height`

> [!WARNING]
> L'utilisation de `transition: all` est **strictement interdite** car elle force le navigateur à surveiller et animer des propriétés non GPU, entraînant de la gigue (jank) visuelle.

---

## 4. Accessibilité (Reduced Motion)

L'accessibilité visuelle est une obligation de conception. Toute animation impliquant des mouvements importants doit respecter la préférence de l'utilisateur :

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-delay: 0s !important;
    animation-duration: 0s !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0s !important;
    scroll-behavior: auto !important;
  }
}
```
