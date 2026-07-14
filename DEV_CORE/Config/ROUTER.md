# ROUTER.md v3 -- DEV_CORE v9.0
# Single client · Mode-based routing · Model-agnostic
# DEV_CORE detecte le mode -- Headroom compresse -- AI Capability Registry choisit le candidat -- Gemini Router appelle le backend

Voir aussi : `DEV_CORE/docs/AI_CAPABILITY_REGISTRY.md` et `DEV_CORE/docs/SYSTEM_OVERVIEW.md`.

## Architecture de routage & Offloading (DevCore v9.0)

```
                       Requete Utilisateur (DEV_CORE)
                                     |
                                     v
                       [TencentDB Agent Memory Canvas] (Offloading L0-L3)
                                     |
                                     v
                       [Headroom Proxy] (Port 8787) (Compression KV)
                                     |
                                     v
                       [AI Capability Registry] (capacites, cout, vitesse, contexte)
                                     |
                                     v
                       [Gemini Router] (Port 20130) (Primary / Retries 429)
                                     |
                                     v
                            [Google Gemini API]
                         (gemini-2.5-pro / flash)
```

- **TencentDB Agent Memory Canvas** : Décharge de contexte sémantique hiérarchique (L0-L3 via Mermaid et SQLite FTS5) pour préserver le contexte de l'agent.
- **Headroom Proxy (Port 8787)** : Compression de jetons transparente (JSON, Code, Logs) et gestion de cache.
- **AI Capability Registry** : Selection declarative du meilleur agent ou modele selon les capacites requises, le cout, la vitesse, le contexte maximal et les specialites.
- **Gemini Router (Port 20130)** : Proxy de communication directe avec l'API Google Gemini, gérant le Rate-Limiting (HTTP 429) par retries avec backoff exponentiel.


### Couche profile/model DEV_CORE

La source de verite de compatibilite est `DEV_CORE/Config/routing_profiles.json`.
La source de verite de selection modele/agent est `DEV_CORE/Config/ai_capability_registry.json`.

Le resolver `DEV_CORE/Scripts/routing_profile.ps1` transforme un mode en profil :

```
mode       profile          model DEV_CORE       Gemini
---------------------------------------------------------------
reasoning  deep-reasoning   devcore-reasoning    gemini-2.5-pro
coding     implementation   devcore-coding       gemini-2.5-pro
bulk       high-throughput  devcore-bulk         gemini-2.5-flash
plan       alias            devcore-reasoning    gemini-2.5-pro
```

Limite explicite : cette couche ne change pas le modele interne de Codex Desktop.
Pour Codex, elle injecte seulement le profil, le budget, le modele DEV_CORE cible
et le comportement attendu dans `AGENTS.md` et `session_context`.

Pour les services controles par DEV_CORE, le Gemini Router accepte maintenant :

- `{"mode":"reasoning"}` -> `gemini-2.5-pro`
- `{"mode":"coding"}` -> `gemini-2.5-pro`
- `{"mode":"bulk"}` -> `gemini-2.5-flash`
- `{"model":"devcore-bulk"}` -> `gemini-2.5-flash`

Selection avancee par capacites :

```json
{
  "capability_requirements": {
    "languages": ["python", "powershell"],
    "specialties": ["tests", "documentation"],
    "min_context_tokens": 32000,
    "optimize_for": "balanced"
  }
}
```

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

## Signal mode vers Gemini Router

Inclure dans chaque requete selon le contexte :

```
# Dans CLAUDE.md -- l'agent ajoute ce parametre
# L'agent l'injecte dans les metadonnees de la requete

mode=reasoning  -> Gemini Router utilise gemini-2.5-pro
mode=coding     -> Gemini Router utilise gemini-2.5-pro
mode=bulk       -> Gemini Router utilise gemini-2.5-flash
(vide)          -> Gemini Router utilise gemini-2.5-pro par defaut
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
