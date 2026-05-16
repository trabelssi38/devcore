# Dashboard Single View & Active Tasks

## Goal
Réorganiser le dashboard pour qu'il s'affiche intégralement sur un seul écran (sans défilement global), en mettant l'accent sur les projets et leurs tâches actives ou en cours (sessions non fermées).

## Tasks
- [x] Task 1: Modifier `Dashboard\template.html` pour utiliser une architecture CSS Grid ou Flexbox en 3 colonnes principales (ex: Projets/Tâches, Token Stack, Infrastructure) avec une hauteur fixée à l'écran (`height: 100vh; overflow: hidden`).
  - **Verify**: La page HTML générée utilise toute la largeur de l'écran et ne permet pas de scroller globalement.
- [x] Task 2: Ajouter un style `overflow-y: auto` aux conteneurs internes pour que chaque colonne puisse défiler indépendamment si son contenu est trop long.
  - **Verify**: Les longues listes défilent à l'intérieur de leur bloc sans affecter le reste de l'écran.
- [x] Task 3: Dans `gen_dashboard.ps1`, modifier la génération du bloc `{{TASKS_PIPELINE}}` pour filtrer les tâches : n'afficher que les tâches `active` et `todo` (ou uniquement celles des sessions non fermées).
  - **Verify**: Les tâches "done" (historiques) disparaissent de la vue principale pour désencombrer l'écran.
- [x] Task 4: Mettre en évidence visuellement la tâche `active` de chaque projet (par exemple avec une bordure lumineuse, une icône de lecture ou une couleur de fond distincte).
  - **Verify**: L'œil est immédiatement attiré par la tâche sur laquelle l'agent travaille actuellement.

## Done When
- [x] Le dashboard tient sur un seul écran d'ordinateur (Single View).
- [x] L'affichage des tâches est épuré, centré sur le travail en cours et actif.
- [x] Les 3 sections (Projets, Token Stack, Infra) sont visibles simultanément côte à côte.
