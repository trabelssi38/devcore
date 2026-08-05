# Analyse : Ruflo × DEV_CORE — Opportunités d'Intégration et Synergies

> **Source analysée** : [ruvnet/ruflo](https://github.com/ruvnet/ruflo) (anciennement Claude Flow)
> **Architecture DEV_CORE auditée** : Single Client Mode v10.0.0, API/MCP (`devcore-scripts/server.py`), plugin registry (`plugin_service.ps1`), knowledge graph (`knowledge_graph.ps1`).

---

## Résumé Exécutif

Ruflo (ex-Claude Flow) est un **agent meta-harness** open-source conçu pour Claude Code et Codex. Contrairement à DEV_CORE qui orchestre le cycle de vie du développement via un agent unique, Ruflo se concentre sur l'orchestration de **swarms multi-agents**, l'apprentissage autonome et une mémoire RAG ultra-performante.

L'introduction de Ruflo dans l'écosystème de DEV_CORE représente un **multiplicateur de valeur critique**, en particulier pour la transition vers des architectures multi-agents et l'amélioration de la mémoire de code.

| Opportunité | Verdict | Effort d'Intégration | Impact pour DEV_CORE |
|---|---|---|---|
| **1. Modèle de Swarm Multi-Agent** | 🟢 **CRITIQUE (Inspiration/Design)** | Moyen-Élevé | Révolutionnaire (Transition de Single à Multi-Agent) |
| **2. Graph RAG et RuVector** | 🟢 **FAIRE (Intégrer via MCP)** | Moyen | Élevé (Rappel de code granulaire) |
| **3. Pre/Post Tool Hooks Sécurisés** | 🟢 **FAIRE (Étendre server.py)** | Faible-Moyen | Élevé (Guardrails, Télémétrie) |
| **4. Portabilité des Plugins** | 🟡 **À LA CARTE (Wrap en Manifest v2)** | Variable par plugin | Moyen (Enrichissement fonctionnel) |

---

## 1. Comprendre Ruflo (Claude Flow)

Ruflo définit l'architecture **Agent = Modèle + Harnais** (Harness). Le modèle écrit le code, tandis que le harnais (Ruflo) fournit l'environnement d'exécution : outils, mémoire adaptative, boucles autonomes, bacs à sable (sandboxes) et contrôle de flux.

### Caractéristiques majeures :
1. **Multi-Agent Swarm Orchestration** : Gère des équipes d'agents spécialisés (jusqu'à 98 rôles) qui collaborent en parallèle avec des contrats de communication typés.
2. **Dynamic Agent Behavior (Autopilot)** : Permet aux agents de boucler de manière autonome sur des tâches complexes.
3. **Adaptive Memory & RuVector** : Mémoire sémantique, temporelle et de graphe hautement optimisée (GPU-accelerated vector DB avec 103 outils).
4. **Federation** : Communication sécurisée d'agents entre plusieurs machines physiques sans fuite de données.
5. **Dual Installation Path** : Intégration légère via plugin Claude Code (slash commands uniquement) ou boucle complète (MCP server, hooks, background workers).

---

## 2. Analyse Comparative : Ruflo vs. DEV_CORE

| Dimension | Capacité de Ruflo | Existant dans DEV_CORE v10 | Écart & Diagnostic |
|---|---|---|---|
| **Orchestration d'agents** | **Multi-Agent (Swarm)** : Collaboration parallèle, handoffs d'agents et rôles spécialisés (coder, tester, reviewer). | **Single Client Mode** : Exécution séquentielle par un agent unique. Pas de handoff natif. | 🔴 **Majeur** — DEV_CORE n'a pas encore implémenté sa transition multi-agent (prévue à partir de la spécification `AgentRunner`). |
| **Mémoire de Code** | **Graph RAG / RuVector** : Indexation AST fine du code, sublinear graph reasoning (PageRank, delta updates). | **Structurel** : [knowledge_graph.ps1](file:///c:/devcore/DEV_CORE/Scripts/knowledge_graph.ps1) gère les liens tâches/commits/fichiers, mais pas le code interne (pas d'AST ni appels de fonctions). | 🔴 **Critique** — Manque de granularité sémantique sur le code source de DEV_CORE (indexé sous forme de gros blobs Qdrant). |
| **Sécurité & Bac à sable** | **ruflo-aidefence** : Blocage d'injections de prompts, détection de PII, audits de sécurité au niveau du harnais. | **plugin_service.ps1** : Isolation du processus de staging, détection de secrets dans les fichiers. | 🟡 **Partiel** — Pas de guardrail en direct sur les entrées/sorties du LLM avant l'appel d'outil. |
| **Système de Hooks** | Hooks système automatisés (`PreToolUse`, `PostToolUse`) pour intercepter les outils et enregistrer la télémétrie. | [post_tool_hook.ps1](file:///c:/devcore/DEV_CORE/Scripts/post_tool_hook.ps1) : Exécuté après certains outils, mais pas de pipeline de hooks centralisé dans le serveur MCP. | 🟡 **Partiel** — Le serveur MCP dispatch directement aux scripts sans interception globale. |
| **Architecture des Plugins** | Auto-découverte basée sur les dossiers (agents/, skills/, hooks/). | **Manifest-based (v2)** : [manifest_v2.py](file:///c:/devcore/DEV_CORE/Plugins/manifest_v2.py) avec validation stricte des permissions et scopes. | ✅ **DEV_CORE est plus robuste** sur la validation et le sandboxing des plugins tiers. |

---

## 3. Comment Ruflo peut-il enrichir DEV_CORE ?

### 3A. Modèle de Swarm pour la spécification `AgentRunner`
DEV_CORE a planifié l'abstraction d'un `AgentRunner` (Sprint 06 / Sprint 12) pour rendre l'exécution de l'agent modulaire et remplacer le démon Hermes hérité.
* **Apport de Ruflo** : Au lieu de réinventer l'orchestration multi-agent, DEV_CORE peut s'inspirer de `ruflo-swarm` et du format de communication typé des agents Ruflo pour implémenter un routeur de swarm d'agents en Python.
* **Proposition d'architecture** : Créer un orchestrateur `devcore_swarm_router.py` capable d'instancier des agents spécialisés (spécifiés dans `DEV_CORE/Skills`) et de gérer leurs handoffs en utilisant le bus d'événements existant (`DEV_CORE/Bus`).

### 3B. Intégration de RuVector et Graph RAG
La mémoire de code de DEV_CORE souffre d'un manque de précision (blobs globaux). Ruflo utilise `ruvector` pour faire de l'indexation de code ultra-rapide et du Graph RAG.
* **Apport de Ruflo** : L'intégration de `ruvector` en tant que serveur MCP ou bibliothèque Python permettrait à DEV_CORE d'obtenir instantanément :
  1. Une indexation incrémentale du graphe syntaxique (AST).
  2. Des relations de dépendance précises (fonction -> fonction, classe -> import).
  3. Des capacités d'analyse d'impact beaucoup plus granulaires pour l'outil `devcore_impact_analysis`.
* **Proposition** : Mettre en place un pont de synchronisation entre `ruvector` (SQLite `.code-review-graph/graph.db`) et le `knowledge_graph.ps1` de DEV_CORE pour fusionner les structures de tâches et les dépendances du code.

### 3C. Pipeline de Hooks MCP Standardisé
Inspiré par le concept de méta-harnais de Ruflo, DEV_CORE peut réformer le dispatch de son serveur MCP [devcore-scripts/server.py](file:///c:/devcore/DEV_CORE/MCP/devcore-scripts/server.py) pour y insérer des intercepteurs globaux.
* **Apport de Ruflo** : Permet de découpler la logique métier des outils de leurs contraintes de sécurité (guardrails) et de télémétrie.
* **Proposition d'implémentation** (déjà proposée dans `analyse_3repos_devcore.md`) :
  ```python
  # Dans MCP/devcore-scripts/hooks.py
  async def pre_tool_hook(tool_name: str, arguments: dict) -> dict:
      # 1. Détection injection de prompt
      # 2. Vérification du budget de jetons (Token budget)
      return arguments

  async def post_tool_hook(tool_name: str, result: dict) -> dict:
      # 1. Journalisation des coûts / Télémétrie
      # 2. Extraction automatique de leçons en cas d'échec/succès
      return result
  ```

### 3D. Portabilité des fonctionnalités sous forme de Plugins DEV_CORE
DEV_CORE possède une architecture de plugins (v2) saine et sécurisée. Les plugins de Ruflo peuvent être adaptés pour DEV_CORE :
* **`ruflo-testgen`** : Pourrait être adapté en tant que plugin DEV_CORE utilisant le SDK pour scanner le code et générer des tests unitaires manquants lors du cycle de validation (`dc check`).
* **`ruflo-cost-tracker`** : Pourrait alimenter directement le module `metrics_service.ps1` et la section "Headroom Supervision" du Cockpit de DEV_CORE.
* **`ruflo-security-audit`** : Permettrait d'exécuter des scans de sécurité et de conformité automatisés lors des gates CI de DEV_CORE (`dc verify --ci`).

---

## 4. Recommandations et Plan d'Action

Pour maximiser les bénéfices sans surcharger le système :

1. **Court Terme (Priorité 1) - Intégration de la Télémétrie & Budget de Tokens** :
   * Adapter la logique de `ruflo-cost-tracker` dans `metrics_service.ps1` pour comptabiliser de manière granulaire les coûts par agent/tâche.
2. **Moyen Terme (Priorité 2) - Hooks MCP & Guardrails** :
   * Implémenter le fichier `DEV_CORE/MCP/devcore-scripts/hooks.py` avec des guardrails pré-exécution inspirés de `ruflo-aidefence`.
3. **Long Terme (Priorité 3) - Transition Multi-Agent** :
   * Utiliser le modèle de coordination de swarms de Ruflo comme blueprint technique pour le développement du module `AgentRunner` de la version v11.
