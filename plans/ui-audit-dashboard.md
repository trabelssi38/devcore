# Audit UI / Motion / A11y — Cockpit DEV_CORE v10

**Date de l'audit** : 2026-07-18  
**Fichiers analysés** : 
- `DEV_CORE/Web/src/app/globals.css`
- `DEV_CORE/Web/src/app/page.tsx`
- `DEV_CORE/Web/src/components/*`
- `DEV_CORE/Web/src/lib/apiClient.ts`

---

## 1. Synthèse globale

| Critère | Statut | Note | Observation |
| :--- | :---: | :---: | :--- |
| **Sémantique HTML5** | ✅ Passant | 5/5 | Utilisation parfaite de `<main>`, `<section>` avec `aria-label` descriptifs. |
| **Accessibilité (A11y)** | ⚠️ Warning | 4/5 | Bons labels et structure, mais pas de déclaration globale `prefers-reduced-motion` ni de protection des interactions hover. |
| **Performance GPU** | ✅ Passant | 5/5 | Zéro animation de layout coûteuse ou transition non-GPU détectée (aucune transition présente). |
| **Qualité Motion** | ⚠️ Warning | 3/5 | Absence de design tokens prédéfinis pour les transitions futures (ex. hover, focus). |
| **UI Craft / Densité** | ✅ Passant | 4.5/5 | Grille responsive propre, espacements bien basés sur l'échelle de 4px. |

---

## 2. Findings Prioritaires

### P0 (HIGH) — Zéro violation bloquante détectée
Aucune violation de type `transition: all`, animation layout ou blocage critique.

---

### P1 (MEDIUM) — Améliorations de Structure & Accessibilité

| Réf | Fichier / Ligne | Code Actuel | Problème observé | Correction recommandée |
| :--- | :--- | :--- | :--- | :--- |
| **UI-01** | `globals.css` (L30) | `* { box-sizing: border-box; }` | Absence de reset global pour la réduction des mouvements | Ajouter le sélecteur `@media (prefers-reduced-motion: reduce)` avec des durées de transition de 0s. |
| **UI-02** | `globals.css` (L173) | `.button:hover { filter: brightness(1.08); }` | Transition de survol instantanée (manque de fluidité) | Ajouter une transition spécifique d'opacité/filtre limitée à 150ms avec un easing `ease-out`. |
| **UI-03** | `globals.css` (L53) | `:focus-visible { outline: 2px ... }` | Pas de transition fluide lors de l'acquisition du focus | Ajouter une transition d'outline-offset ou d'outline-color. |

---

### P2 (LOW) — Bonnes Pratiques & Standardisation

| Réf | Fichier / Ligne | Code Actuel | Problème observé | Correction recommandée |
| :--- | :--- | :--- | :--- | :--- |
| **UI-04** | `globals.css` (L3) | `:root { ... }` | Aucun token de durée ou d'easing de mouvement centralisé | Ajouter des variables CSS `--duration-fast: 150ms` et `--ease-out-strong`. |

---

## 3. Plan d'Implémentation Recommandé
Les corrections ci-dessus feront l'objet de plans détaillés dans le cadre du Sprint 11.
Ces modifications permettront d'introduire des transitions fluides sur les boutons et les focus d'éléments tout en restant conformes à 100% avec les standards de mouvement GPU et l'accessibilité réduite.
