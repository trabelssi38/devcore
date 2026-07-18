# Skill: dashboard-ui-craft

Ce skill guide la conception esthétique, le respect des standards graphiques et l'intégration des composants de l'interface Cockpit de DEV_CORE.

---

## 1. Description
Utiliser ce skill pour toute tâche relative au design, à la mise en page, à la typographie, aux espacements ou à l'intégration HTML/CSS de l'application Next.js ou du dashboard historique.

---

## 2. Triggers
- Modification de fichiers de style (`.css`, `.scss`)
- Modification de composants d'interface React (`.tsx`, `.jsx`)
- Amélioration visuelle ou modification de la structure de mise en page (layout)
- Intégration de nouveaux composants (badges, panels, timelines)

---

## 3. Directives Techniques

### 3.1 Design System Dark Tech
- **Palette** : Utilisez des nuances de gris sombres et froids (ex. `slate` ou `zinc` Tailwind). Évitez le noir pur (`#000000`) pour les fonds afin de conserver de la profondeur visuelle.
- **Accents** : Utilisez des couleurs d'accentuation précises : Indigo (`#6366f1`) pour l'action principale, Violet (`#8b5cf6`) pour les processus en cours, et Gris-Bleu (`#64748b`) pour le contenu secondaire.
- **Bordures** : Utilisez des bordures fines et semi-transparentes (`border: 1px solid rgba(255, 255, 255, 0.05)`) pour séparer les éléments sans encombrer la mise en page.

### 3.2 Spacing & Densité
- Respectez une échelle d'espacement stricte basée sur un pas de `4px` (`4px`, `8px`, `12px`, `16px`, `24px`, `32px`).
- Privilégiez des structures en grille (`display: grid`) ou flexibles (`display: flex`) plutôt que des positionnements absolus.

### 3.3 États de Composants Obligatoires
Chaque élément dynamique (comme la liste des tâches ou les chronologies) doit implémenter 3 états :
1. **Loading** : Spinner ou squelette de chargement avec animation pulsée.
2. **Empty** : Message explicite invitant à l'action si aucune donnée n'est présente.
3. **Error** : Message d'erreur clair avec bouton de reconnexion ou de réessai.

---

## 4. Workflow de Validation Visuelle

Lors de l'implémentation de modifications d'interface :
1. **Lecture des Fichiers** : Inspectez les règles d'accessibilité dans `docs/ACCESSIBILITY_CHECKLIST.md`.
2. **Respect des Standards** : N'utilisez pas de couleurs hardcodées orphelines. Utilisez des variables ou des tokens CSS définis dans `index.css`.
3. **Vérification Responsive** : Assurez-vous que l'affichage reste lisible et ne produit aucun débordement horizontal sur les largeurs suivantes :
   - Mobile (`375px`)
   - Tablette (`768px`)
   - Bureau (`1280px` et plus)
