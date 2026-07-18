# Skill: motion-review

Ce skill fournit les directives d'audit et de validation des animations et transitions d'interface utilisateur dans le Cockpit DEV_CORE.

---

## 1. Description
Utiliser ce skill lors de la révision de code (review de diff, commit, pull request) ou de l'audit de fichiers CSS/React contenant des transitions, transformations ou animations.

---

## 2. Triggers
- Modification ou introduction de styles CSS liés à `transition`, `animation`, `keyframes`
- Utilisation de bibliothèques d'animation (ex. Framer Motion, Anime.js) dans React/Next.js
- Audit ou optimisation de performances de rendu (jank, saccades d'interface)

---

## 3. Directives d'Audit Strictes (Blocages)

L'agent doit inspecter le code et **bloquer (Block / Reject)** toute révision introduisant l'un des anti-patterns suivants :

1. **`transition: all`** :
   - *Pourquoi* : Ralentit le rendu et provoque des saccades car le navigateur doit surveiller toutes les propriétés.
   - *Alternative* : Ciblez spécifiquement les propriétés (ex. `transition: transform 150ms, opacity 150ms`).
2. **Animation de propriétés de Layout** :
   - *Pourquoi* : Forcer le calcul de layout (reflow) sur chaque frame est extrêmement coûteux pour le CPU.
   - *Propriétés bloquées* : `width`, `height`, `margin`, `padding`, `top`, `left`, `right`, `bottom`.
   - *Alternative* : Utilisez des translations (`transform: translate(...)`) ou des échelles (`transform: scale(...)`).
3. **Absence de `prefers-reduced-motion`** :
   - *Pourquoi* : Indispensable pour éviter la cinétose ou la gêne chez certains utilisateurs.
   - *Règle* : Tout mouvement ou déplacement spatial significatif (glissement, scaling important) doit être annulé ou remplacé par une transition d'opacité simple lorsque `prefers-reduced-motion: reduce` est actif.
4. **Easings interactifs non-physiques** :
   - *Pourquoi* : Donne une impression de lourdeur ou de saccade à l'interface.
   - *Règle* : Interdire l'usage de `ease-in` pour les éléments qui apparaissent au clic de l'utilisateur. Privilégier les atténuations de type `ease-out`.

---

## 4. Format de Rapport de Verdict Attendu

Chaque exécution de ce skill sur un fichier ou un diff doit produire un tableau récapitulatif structuré comme suit :

| Fichier | Ligne / Sélecteur | Propriété Analysée | Problème Détecté | Correction Recommandée | Sévérité |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `index.css` | `.card` | `transition: all 0.3s` | Utilisation de `transition: all` | Remplacer par `transition: transform 150ms, opacity 150ms` | **HIGH** |
| `timeline.tsx` | `.timeline-item` | `transition: height` | Animation d'une propriété de layout | Remplacer par une translation GPU | **HIGH** |
