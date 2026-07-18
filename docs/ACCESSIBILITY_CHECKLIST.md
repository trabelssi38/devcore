# DEV_CORE — Accessibility & A11y Standards

Ce document contient la checklist minimale d'accessibilité que chaque composant et page de l'interface DEV_CORE doit valider avant mise en production.

---

## 1. Landmarks HTML5 (Structure Sémantique)

Toutes les pages doivent utiliser une structure sémantique claire pour aider les lecteurs d'écran à naviguer dans le document :
- Une page doit contenir **un et un seul** élément `<main>` décrivant le contenu principal de l'application.
- Les zones de navigation doivent être délimitées par `<nav>`.
- Les blocs d'information autonomes doivent utiliser `<section>` dotés d'un `aria-label` descriptif (ex. `aria-label="Santé plateforme"`).

---

## 2. Contraste Visuel (WCAG AA)

- Le texte normal (en dessous de 18pt) doit avoir un contraste minimal de **4.5:1** par rapport à son arrière-plan.
- Le grand texte (18pt et plus) doit avoir un contraste minimal de **3.0:1**.
- Les éléments graphiques fonctionnels (icones d'état, boutons) doivent avoir un contraste minimal de **3.0:1**.

---

## 3. Clavier & Focus Visuel

- Tout élément interactif (liens, boutons, triggers) doit être accessible via la touche `Tab`.
- Le style de focus par défaut du navigateur ne doit pas être supprimé (`outline: none`) sans être remplacé par un indicateur de focus personnalisé et hautement visible (ex. une bordure colorée ou un anneau d'accentuation).
- Aucun mouvement automatique ou popup inattendu ne doit interrompre le focus de l'utilisateur.

---

## 4. Statuts Multi-Sensoriels (Non-Dépendance de la Couleur)

La couleur seule ne doit jamais être le seul canal d'information pour transmettre un statut, une erreur ou une progression :
- Un badge de succès vert doit être accompagné d'un texte explicite (ex. "ONLINE" ou "OK") ou d'une icone spécifique (`✓`).
- Un badge d'erreur rouge doit être accompagné d'un texte explicite (ex. "OFFLINE" ou "FAIL") ou d'une icone spécifique (`✗`).
- Utilisez les éléments masqués de classe `.sr-only` pour donner du contexte additionnel aux lecteurs d'écran (ex. `<span className="sr-only">Statut : </span>`).

---

## 5. Cibles de Clic (Touch Targets)

Pour garantir la facilité d'utilisation sur tablette, écran tactile ou pour les utilisateurs souffrant de troubles moteurs :
- La zone cliquable de chaque bouton, lien ou élément interactif autonome doit mesurer au moins **44px × 44px**.
- Si l'élément lui-même est plus petit visuellement (ex. une petite icone), utilisez un padding CSS transparent pour étendre sa zone de détection de clic.
