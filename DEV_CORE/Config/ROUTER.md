# ROUTER.md v2 -- DEV_CORE v6
# Single client · Mode-based routing · Model-agnostic
# DEV_CORE detecte le mode -- 9Router choisit le modele

## Architecture

```
Requete utilisateur
      |
      v
DEV_CORE detecte le mode (reasoning / coding / bulk)
      |
      v
Signal mode -> 9Router combo "devcore-always-on"
      |
      +-- reasoning -> Tier 1 (claude-opus, o3, kimi-k2-thinking...)
      +-- coding    -> Tier 2 (codex, sonnet, glm-coder...)
      +-- bulk      -> Tier 3 (gemini-flash, qwen, glm...)
      +-- fallback  -> Tier 4 (kiro gratuit illimite)
```

DEV_CORE ne connait pas les noms de modeles.
9Router gere les quotas, fallbacks et couts.

---

## Detection automatique du mode

### REASONING
Declarer model=reasoning quand :
- Mots cles : spec, architecture, pourquoi, decide, analyse, review,
              conception, strategy, tradeoffs, incident, postmortem,
              debug (cause inconnue), quel choix, comparer
- Contexte attendu > 10k tokens
- Tache implique une decision non reversible
- Skill requis : dev-methodology, fabric-patterns, qdrant

### CODING
Declarer model=coding quand :
- Mots cles : implemente, code, fix, patch, test, refactor,
              ecris la fonction, corrige, ajoute, modifie, TDD
- Output < 500 lignes
- Tache mecanique avec spec deja definie
- Skill requis : dev-methodology, python_api, web_ui, android_release

### BULK
Declarer model=bulk quand :
- Mots cles : tous les fichiers, migration entiere, genere N tests,
              toutes les docs, batch, en masse, pour chaque fichier
- Output > 500 lignes OU > 20 items
- Tache repetitive et parallelisable
- Skill requis : fabric-patterns

### AUTO (defaut si incertain)
- Incertain entre reasoning et coding -> reasoning
- Output prevu > 500 lignes -> bulk
- Sujet connu en memoire + tache simple -> coding

---

## Regles

R1 -- Memory first
  Interroger Qdrant (decisions/lessons/patterns) avant de generer.
  Score > 0.75 : utiliser sans re-generer.
  Score 0.5-0.75 : utiliser comme base, enrichir.

R2 -- Skills first
  Charger le SKILL.md pertinent avant d'executer.
  Verifier skills_registry.json si la tache est non triviale.

R3 -- Task scope
  Rester dans le perimetre de la tache active (tasks.json).
  Si hors scope : noter dans next_actions, ne pas deriver.

R4 -- Commit tag
  Tagger chaque commit avec [T-XX] (ID de la tache courante).
  Le hook post-commit incremente steps_done automatiquement.

R5 -- Confirmation humaine
  Ne jamais envoyer de code en production sans validation.
  Les scripts DEV_CORE (endday, task done) s'executent sans confirmation.
  Le code metier requiert une validation humaine avant merge.

R6 -- Mode degradation
  Budget depasse en reasoning -> basculer en coding pour finir.
  Budget depasse en coding -> compresser l'output, livrer minimal.
  Bulk toujours en mode streaming si > 1000 lignes.

---

## Budget token par mode

```
reasoning : 32k tokens max  -- qualite prioritaire
coding    :  8k tokens max  -- precision prioritaire
bulk      : 16k tokens max  -- volume, compresser outputs
lookup    :  2k tokens max  -- simple, rapide
```

---

## Routing par type de tache

```
Type de tache                   Mode          Skill charge
------------------------------------------------------------------
Architecture, decision          reasoning     dev-methodology
Spec nouvelle feature           reasoning     dev-methodology
Review code complexe            reasoning     dev-methodology
Incident / postmortem           reasoning     fabric-patterns
Analyse, extraction insights    reasoning     fabric-patterns
Amelioration prompt             reasoning     fabric-patterns

Implementation TDD              coding        dev-methodology
Patch / bugfix                  coding        selon stack
Refactoring                     coding        selon stack
Tests unitaires                 coding        selon stack
UI / composants                 coding        ui-ux

Tests en masse                  bulk          fabric-patterns
Migration fichiers              bulk          selon stack
Generation docs (N fichiers)    bulk          fabric-patterns
Batch automation                bulk          --

Vault Obsidian (R/W)            coding        obsidian
Memoire Qdrant (R/W)            coding        qdrant
Design / UX                     coding        ui-ux
```

---

## Signal mode vers 9Router

Inclure dans chaque requete selon le contexte :

```
# Dans CLAUDE.md -- l'agent ajoute ce parametre
# Claude Code l'injecte dans les metadonnees de la requete

mode=reasoning  -> 9Router route vers Tier 1
mode=coding     -> 9Router route vers Tier 2
mode=bulk       -> 9Router route vers Tier 3
(vide)          -> 9Router utilise le Tier 1 par defaut
```

---

## Remplace les anciens concepts

```
AVANT (multi-client)          APRES (single client)
-----------------------------------------------------
Claude -> reasoning           mode=reasoning
Codex  -> coding              mode=coding
Gemini -> bulk                mode=bulk
Qwen   -> offline             mode=coding (Tier 4 local)
adapt_client.ps1              inutile -- supprime
handoffs next_actions.md      inutile -- supprime
mission agent: claude/codex   task mode: reasoning/coding/bulk
[M-XX] commit tag             [T-XX] commit tag
```
