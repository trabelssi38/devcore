# Dashboard History, Grouping & Filters

## Goal
Enrichir le dashboard avec un historique complet regroupé par projet/worktree/session, des éléments repliables (accordéons), des effets visuels sur les tâches actives et des filtres temporels (1j, 7j, 30j, All).

## Tasks
- [x] Task 1: Modifier `gen_dashboard.ps1` pour extraire TOUTES les tâches (y compris `done`) et implémenter un regroupement hiérarchique : Projet → Worktree → Mois/Session.
  - **Verify**: La structure de données générée permet un affichage structuré.
- [x] Task 2: Mettre à jour `gen_dashboard.ps1` pour générer du HTML structuré avec des balises `<details>` et `<summary>` pour créer des sections repliables par Projet et par Worktree.
  - **Verify**: Le dashboard reste lisible malgré l'historique complet grâce au pliage.
- [x] Task 3: Ajouter dans `template.html` des animations CSS (ex: `@keyframes pulse`) et des styles pour les tâches `active` afin de créer un effet visuel "vivant" (glow/pulsation).
  - **Verify**: Les tâches en cours sont immédiatement identifiables par leur mouvement/éclat.
- [x] Task 4: Intégrer un script JavaScript léger dans `template.html` avec des boutons de filtrage (1j, 7j, 30j, All) qui filtrent les éléments de l'historique via un attribut `data-date`.
  - **Verify**: Le filtrage est instantané et permet de se concentrer sur l'activité récente.

## Done When
- [x] L'historique complet est affiché et trié par date descendante.
- [x] Le regroupement par Projet/Worktree est fonctionnel et repliable.
- [x] Les filtres temporels (1j, 7j, etc.) cachent/montrent les tâches correctement.
- [x] Les tâches actives ont une animation visuelle distinctive.
