# Support des Git Worktrees pour DEV_CORE

## Goal
Centraliser la gestion des tâches d'un dépôt Git dans un seul fichier `tasks.json` canonique, tout en ajoutant un tag dynamique permettant d'identifier si une tâche appartient au projet global ou à un worktree spécifique (Approche 2).

## Tasks
- [x] Task 1: Modifier `Get-ActiveProject.ps1` pour utiliser `git rev-parse --git-common-dir` et extraire le nom du projet canonique. Exporter `$env:DEVCORE_ACTIVE_PROJECT_NAME`.
  - **Verify**: L'exécution dans un worktree renvoie le nom du dépôt principal, pas celui du worktree.
- [x] Task 2: Ajouter dans `Get-ActiveProject.ps1` la détection du worktree courant (en comparant `--show-toplevel` et le parent de `--git-common-dir`). Exporter `$env:DEVCORE_ACTIVE_WORKTREE_NAME`.
  - **Verify**: L'exécution dans un worktree expose correctement son nom (ex: `feature-x`). Dans le dépôt principal, il expose `main` (ou la branche par défaut).
- [x] Task 3: Modifier `task_add.ps1` pour injecter la propriété `"worktree": "$env:DEVCORE_ACTIVE_WORKTREE_NAME"` lors de la création d'une nouvelle tâche.
  - **Verify**: `dc new task "Test WT"` crée une tâche dans le `tasks.json` canonique avec un champ `worktree` correctement renseigné.
- [x] Task 4: Modifier `task_status.ps1` pour afficher le nom du worktree à côté du titre de la tâche dans le tableau de bord CLI (ex: `[feature-x]`).
  - **Verify**: `dc task status` affiche clairement les tâches associées aux worktrees avec un repère visuel.
- [x] Task 5: Mettre à jour `Auto\task_spec_parser.ps1` et `task_git_scanner.ps1` pour qu'ils injectent le champ `worktree` aux tâches générées automatiquement.
  - **Verify**: Un scan automatique depuis un worktree assigne le bon worktree aux tâches découvertes.

## Done When
- [x] Les tâches de tous les worktrees sont sauvegardées dans le même dossier `Memory\<projet_canonique>\tasks.json`.
- [x] Chaque tâche préserve la granularité de son environnement d'origine grâce à la métadonnée `worktree`.
- [x] Le tableau de bord CLI permet de distinguer facilement la provenance des tâches.
