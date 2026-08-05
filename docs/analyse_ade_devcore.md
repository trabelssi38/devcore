# Analyse Comparative : DEV_CORE vs. Ruflo vs. DevSwarm vs. Orca vs. Superset vs. ADE (arul28)

> **Projets analysés** :
> 1. **DEV_CORE v10.0.0** (Votre écosystème d'orchestration local)
> 2. **Ruflo** (Harnais méta-agent et Graph RAG sémantique)
> 3. **DevSwarm** (ADE Desktop d'orchestration de branches / MCP Zig)
> 4. **StablyAI Orca** (ADE TUI-first avec isolation par Git Worktrees)
> 5. **Superset.sh** (Éditeur de code et ADE conçu pour l'ère des agents IA)
> 6. **ADE (arul28/ADE)** (ADE tout-en-un avec lanes Git Worktrees et app iOS compagnon)

---

## Résumé Exécutif

L'écosystème de l'ingénierie logicielle assistée par IA converge massivement vers la création d'**Augmented Development Environments (ADE)**. L'analyse combinée de ces 6 solutions montre que l'isolation via **Git Worktrees** et la **validation de diffs par l'humain (Human-in-the-Loop)** sont devenues des standards industriels indispensables.

| Projet | Positionnement | Force Majeure | Faiblesse Majeure |
|---|---|---|---|
| **DEV_CORE** | Plateforme locale intégrée (FastAPI, Qdrant, Cockpit, PowerShell) | Souveraineté totale, routeur local intelligent, Cockpit moderne, Obsidian Sync. | Pipeline de tâches mono-agent uniquement pour le moment. |
| **Ruflo** | Harnais méta-agent (CLI / MCP) | Swarm de 98 agents, Graph RAG ultra-rapide, fédération inter-machines. | Pas d'interface de gestion de workspaces ou de branches. |
| **DevSwarm** | ADE Graphique (Desktop App) | Sidebar visuelle de branches virtuelles, délégation parent-enfant. | Moins personnalisable, très orienté GUI. |
| **Orca (StablyAI)** | ADE TUI-first (Terminal) | Exécution parallèle d'agents dans des Git Worktrees isolés, split-panes TUI. | Courbe d'apprentissage élevée, pas de base de données de mémoire persistante. |
| **Superset.sh** | ADE en forme d'Éditeur (GUI) | Conçu comme un IDE pour agents, orchestration de 10+ agents en parallèle. | Dépend d'éditeurs externes pour le codage humain. |
| **ADE (arul28)** | ADE Multi-plateforme (Desktop/TUI/iOS) | Lanes de Worktrees, synchronisation iOS, intégration des PR/CI GitHub dans l'app. | Infrastructure cloud requise pour la synchronisation multi-appareils. |

---

## 1. Description des Nouveaux Repos

### A. Superset.sh (superset-sh/superset)
Superset est un IDE open-source configuré spécifiquement pour l'ère des agents de programmation.
* **Orchestration de flotte** : Il est conçu pour faire tourner simultanément plus de 10 agents de codage (comme Claude Code, Codex, Cursor Agent) sur une seule machine.
* **Isolation par Git Worktree** : Chaque agent reçoit une tâche et travaille dans son propre Git Worktree pour éviter tout conflit de fichiers en temps réel.
* **Handoff natif** : Superset offre un dashboard pour suivre l'avancement, visualiser les diffs en cours, et permet de transférer le workspace en un clic vers votre éditeur préféré (VS Code, Cursor, etc.).

### B. ADE (arul28/ADE - ade-app.dev)
ADE (Agentic Development Environment) est un workspace unifié multi-appareils (Desktop, Terminal, Mobile).
* **Worktree Lanes** : Utilise le concept de "lanes" (couloirs) basés sur les Git Worktrees pour paralléliser les tâches des agents sans faire de stash de code ou changer de contexte manuellement.
* **Human-in-the-loop & PR Integration** : Les modifications des agents sont stockées sous forme de suggestions de diffs. ADE intègre la gestion des Pull Requests GitHub et le statut de la CI directement dans l'application, permettant d'approuver ou de rejeter le travail de l'agent sans ouvrir de navigateur.
* **Sync Multi-Appareil & App iOS** : Permet de monitorer le statut des agents, de lire leurs logs et d'approuver des diffs à distance depuis une application iOS ou via la commande CLI `ade code`.

---

## 2. Tableau Comparatif Global

| Dimension | DEV_CORE v10 | Ruflo | DevSwarm | StablyAI Orca | Superset.sh | ADE (arul28) |
|---|---|---|---|---|---|---|
| **Interface (UI)** | Web Cockpit (Grid) & Terminal CRT. | Sans interface (Headless / CLI). | GUI Electron (Sidebar branches). | TUI (Terminal Split-Pane). | IDE GUI Dédié (Dashboard/Diffs). | Native GUI Desktop + CLI + App iOS. |
| **Isolation Espace** | Dossiers par projet, pas d'isolation de branche. | Configuration locale `.claude/`. | Branches virtuelles et sous-workspaces. | **Git Worktrees** physiques. | **Git Worktrees** physiques. | **Git Worktree Lanes** isolés. |
| **Parallélisme** | Mono-agent séquentiel. | Swarms de 98 agents collaboratifs. | Délégation hiérarchique Parent-Enfant. | Fanout parallèle de prompts. | 10+ agents s'exécutant en parallèle. | Plusieurs agents s'exécutant sur différentes lanes. |
| **Interaction Humaine** | Cockpit Dashboard (lecture seule/logs/metrics). | Chat CLI (Claude Code) ou Beta Web Svelte. | Chat GUI Desktop. | Terminal Split-Pane + Visualiseur de Diffs. | Dashboard de supervision de flotte + Diffs. | **Human-in-the-loop** direct, gestion PR/CI + App Mobile. |
| **Mémoire** | Qdrant + SQLite + Obsidian. | Graph RAG (RuVector) & raisonnement. | Graphe de code en Zig. | Déléguée aux agents individuels. | Déléguée aux agents individuels. | Déléguée aux agents individuels. |

---

## 3. Analyse des Tendances Majeures & Opportunités pour DEV_CORE

L'ajout de **Superset.sh** et **ADE** confirme **3 tendances structurelles** dont DEV_CORE doit s'emparer pour son évolution :

### 3A. Le standard absolu des Git Worktrees
Les trois ADE de pointe (Orca, Superset.sh, ADE) ont tous abandonné la manipulation classique de branches locales dans un dossier unique au profit des **Git Worktrees** pour l'isolation.
* **Pourquoi ?** C'est la seule façon d'exécuter 5 agents en parallèle sur 5 tâches différentes sans qu'ils ne se marchent sur les pieds ou ne corrompent le répertoire de travail de l'utilisateur.
* **Impact pour DEV_CORE** : Le service de tâches (`task_service.ps1`) et le planificateur natif de DEV_CORE doivent impérativement intégrer la création et la suppression automatique de `git worktree` lors de l'exécution de l'agent d'arrière-plan (`active_agent_task_runner`).

### 3B. La Revue de Diffs et Validation Humaine intégrée
Superset.sh et ADE mettent l'accent sur le fait que le code produit par l'agent n'est qu'une **suggestion** (diff) tant que l'humain ne l'a pas validé.
* **Impact pour DEV_CORE** : Actuellement, DEV_CORE valide les tâches via `dc task done` qui synchronise directement la mémoire. Nous devrions enrichir le Cockpit de DEV_CORE avec un **visualiseur de diff interactif** (inspiré de Superset.sh) permettant à l'utilisateur de :
  1. Voir les modifications exactes proposées par l'agent pour la tâche active.
  2. Valider, éditer ou rejeter le diff directement depuis le Cockpit.
  3. Intégrer les résultats des gates de tests (`dc check --gate`) directement dans cette vue de validation (concept de monitoring CI d'ADE).

### 3C. Monitoring Responsive / Mobile
ADE propose une application iOS pour monitorer les agents en déplacement.
* **Impact pour DEV_CORE** : Au lieu de développer une application mobile native lourde, DEV_CORE peut rendre son Cockpit existant (Port 20129) pleinement **responsive** en CSS. Ainsi, l'utilisateur peut suivre la consommation de tokens, le statut du scheduler et les logs de l'agent en arrière-plan depuis son smartphone en déplacement via son réseau local ou VPN.

---

## 4. Synthèse Stratégique pour l'Évolution de DEV_CORE

```
                  ┌──────────────────────────────────────────────────┐
                  │                DEV_CORE COCKPIT                  │
                  │   - Supervision Sessions & Tokens (Existant)      │
                  │   - Visualiseur interactif de Diffs (Nouveau)    │
                  │   - Status de la CI & Health Gates (Nouveau)     │
                  └────────────────────────┬─────────────────────────┘
                                           │
                        Orchestre des espaces isolés
                                           ▼
                  ┌──────────────────────────────────────────────────┐
                  │           GIT WORKTREE LANES MANAGER             │
                  │   - Dossiers physiques isolés par tâche          │
                  │   - Permet le multi-agent en parallèle           │
                  └────────────────────────┬─────────────────────────┘
                                           │
                        Exécute les Agents avec Méta-Harnais
                                           ▼
                  ┌──────────────────────────────────────────────────┐
                  │                 AGENT ENGINE                     │
                  │   - Routage intelligent (Existant)               │
                  │   - Pre/Post Hooks & Graph RAG (Inspiré de Ruflo)│
                  └──────────────────────────────────────────────────┘
```

En résumé, DEV_CORE ne doit pas chercher à copier les interfaces complètes de Superset ou d'ADE, mais doit adopter leur mécanisme sous-jacent : **l'isolation des tâches par Git Worktrees** pour son planificateur d'arrière-plan, et **l'interface de validation de diffs Human-in-the-loop** au sein de son Cockpit web.
