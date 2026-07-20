# DEV_CORE v10 -- Checklist d'Accessibilité Web (A11y Standards)

Checklist minimale d'accessibilité à appliquer sur l'ensemble des interfaces HTML, composants React/Next.js et Cockpits de la plateforme DEV_CORE v10.

---

## 1. Contraste de Couleurs & Lisibilité

- [ ] **Contraste de Texte Principal** : Ratio de contraste d'au moins **4.5:1** pour le texte normal (14px et plus) par rapport au fond.
- [ ] **Contraste de Grand Texte / Titres** : Ratio d'au moins **3:1** pour les grands titres (18px+ ou gras 14px+).
- [ ] **Éléments d'État UI** : Badges, boutons et icônes d'état disposent d'un contraste suffisant et ne reposent pas uniquement sur la couleur (ajouter texte ou icône distincte).

---

## 2. Navigation au Clavier & Indicateurs de Focus

- [ ] **Contrôle Clavier** : Tous les éléments interactifs (`<button>`, `<a>`, `<input>`, `<details>`) sont manipulables au clavier (Tab, Space, Enter).
- [ ] **Focus Visuel** : Aucun contour de focus supprimé sans alternative (`outline: none` interdit sans `:focus-visible`).
- [ ] **Ordre des Onglets Logical Tab Index** : Respect de la hiérarchie DOM naturelle. `tabindex` supérieur à 0 est interdit.

---

## 3. Sémantique HTML & Attributs ARIA

- [ ] **Structure Sémantique** : Utilisation d'éléments HTML5 sémantiques (`<header>`, `<main>`, `<nav>`, `<section>`, `<article>`, `<aside>`).
- [ ] **Labels d'Éléments** : Tous les boutons interactifs et icônes cliquables possèdent un attribut `aria-label` ou un texte d'accompagnement explicite.
- [ ] **Conteneurs Dynamiques** : Zones de notifications ou résultats de recherche dynamiques disposent de `aria-live="polite"`.

---

## 4. Préférences Utilisateur & Reduced Motion

- [ ] **Reduced Motion** : Respect des préférences système de réduction de mouvement via `@media (prefers-reduced-motion: reduce)`.
- [ ] **Zoom Navigateur** : Interface parfaitement lisible et utilisable lors d'un zoom textuel à 200%.
