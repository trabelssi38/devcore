---
name: fabric-patterns
description: >-
  Utiliser pour : analyser un incident, extraire des insights d'une session,
  améliorer un prompt, créer une feature spec, rédiger un postmortem, analyser
  un argument ou un texte, résumer avec structure, créer une user story agile.
  Patterns issus de Fabric (danielmiessler), adaptés DEV_CORE. Déclencher
  quand la tâche est analytique, extractive ou d'amélioration de prompt.
sources:
  - danielmiessler/Fabric (adapté, client-agnostic)
  - https://github.com/danielmiessler/fabric
compatibility: Claude Code · Codex · Gemini CLI · Qwen · tout agent SKILL.md
---

# Skill — Fabric Patterns DEV_CORE

## Patterns disponibles

| Pattern | Usage | Déclencheur |
|---|---|---|
| `extract_wisdom` | Extraire insights d'une session/texte | Post-session, article, doc |
| `improve_prompt` | Améliorer un prompt existant | Prompt sous-performant |
| `analyze_incident` | Structurer un incident/bug | Après un incident prod |
| `create_postmortem` | Postmortem complet | Après incident majeur |
| `create_coding_feature` | Spec feature développement | Avant de coder |
| `agility_story` | User story agile structurée | Planning sprint |
| `analyze_claims` | Vérifier des affirmations | Audit, review, décisions |
| `summarize_session` | Résumé compressé de session | endday.ps1 |

---

## Pattern : extract_wisdom

**Usage** : après une session, lecture d'un document, ou résultat d'agent.

```
IDENTITÉ : Expert en extraction d'information stratégique.
TÂCHE : Analyser le texte fourni et extraire ce qui a de la valeur durable.

FORMAT DE SORTIE (strict, dans cet ordre) :

## IDÉES
[5 à 10 idées les plus surprenantes ou contre-intuitives, phrases complètes]

## INSIGHTS
[5 à 10 insights actionnables, ce qu'on peut faire différemment]

## CITATIONS
[3 à 5 formulations mémorables, entre guillemets, attribuées si possible]

## HABITUDES
[Actions concrètes recommandées, format "Faire X pour obtenir Y"]

## FAITS
[Statistiques, données vérifiables mentionnées]

## RECOMMANDATIONS
[3 recommandations directes pour le projet ou la situation courante]

CONTRAINTES :
- Pas d'introduction ni de conclusion
- Phrases courtes et denses
- Préférer le concret à l'abstrait
- Si rien de valeur : écrire "Rien d'extractible"
```

---

## Pattern : improve_prompt

**Usage** : transformer un prompt faible en prompt robuste et token-efficient.

```
IDENTITÉ : Expert en prompt engineering pour LLMs (Claude, Codex, Gemini, Qwen).
TÂCHE : Analyser le prompt fourni et produire une version améliorée.

ANALYSE (interne, ne pas afficher) :
1. Identifier l'intention réelle
2. Repérer les ambiguïtés
3. Identifier ce qui génère des tokens inutiles
4. Identifier ce qui manque pour un output précis

FORMAT DE SORTIE :

## Prompt amélioré
[Version améliorée, directement utilisable]

## Ce qui a changé
- [changement 1 — pourquoi]
- [changement 2 — pourquoi]

## Gain token estimé
[Estimation en % de réduction des tokens output]

CONTRAINTES :
- Le prompt amélioré doit être plus court que l'original si possible
- Pas de preamble ni d'explication avant le prompt amélioré
- Compatibilité multi-client : Claude, Codex, Gemini, Qwen
```

---

## Pattern : analyze_incident

**Usage** : structurer l'analyse d'un bug, incident ou comportement inattendu.

```
IDENTITÉ : Ingénieur senior spécialisé en analyse d'incidents.
TÂCHE : Analyser l'incident décrit et produire un rapport structuré.

FORMAT DE SORTIE :

## Résumé
[1 phrase : quoi, quand, impact]

## Timeline
[Chronologie précise des événements — format HH:MM si disponible]

## Cause racine
[Root cause identifiée — 1 à 3 niveaux de "pourquoi ?"]

## Facteurs contributifs
[Ce qui a aggravé ou permis l'incident]

## Impact
[Utilisateurs, données, systèmes affectés — chiffres si disponibles]

## Actions immédiates prises
[Ce qui a été fait pour stopper l'incident]

## Actions préventives
[Ce qui empêchera la récurrence — avec responsable et délai]

## Leçon principale
[1 phrase actionnable à upsert dans Qdrant/MEMORY.md]

CONTRAINTES :
- Factuel, pas d'hypothèses non vérifiées
- Pas de blâme nominatif
- Focus sur le système, pas les individus
```

---

## Pattern : create_postmortem

**Usage** : postmortem complet pour un incident majeur.

```
IDENTITÉ : Engineering Manager rédigeant un postmortem blameless.
TÂCHE : Produire un postmortem complet à partir des informations fournies.

FORMAT DE SORTIE (Markdown, prêt à coller dans Obsidian) :

---
title: Postmortem — [Titre incident]
date: YYYY-MM-DD
tags: [postmortem, incident, [composant]]
severity: [P0|P1|P2]
status: draft
---

# Postmortem — [Titre]

## Résumé exécutif
[3 phrases max : quoi, durée, impact, statut]

## Impact
| Métrique | Valeur |
|---|---|
| Durée | X heures |
| Utilisateurs affectés | N |
| Perte estimée | € si applicable |

## Timeline détaillée
| Heure | Événement |
|---|---|
| HH:MM | ... |

## Cause racine
...

## Ce qui a bien fonctionné
- ...

## Ce qui n'a pas fonctionné
- ...

## Action items
| Action | Responsable | Délai |
|---|---|---|
| ... | ... | ... |

## Leçons
- ...
```

---

## Pattern : create_coding_feature

**Usage** : générer une spec feature complète avant de coder.

```
IDENTITÉ : Tech Lead rédigeant une spec de feature.
TÂCHE : À partir de la description fournie, produire une spec complète.

FORMAT DE SORTIE :

## Feature : [Nom]
Priorité : [P0/P1/P2] | Sprint : [N] | Estimation : [XS/S/M/L/XL]

## Problem statement
[Le problème que cette feature résout — 2 phrases]

## Scope
✓ Inclus : ...
✗ Exclus : ...

## Interfaces
[APIs, types TypeScript/Python, schémas DB si applicable]

## Comportements
- Cas nominal : ...
- Edge case 1 : ...
- Edge case 2 : ...

## Critères d'acceptance
- [ ] [test observable 1]
- [ ] [test observable 2]

## Plan d'implémentation
- [ ] 1. [étape atomique]
- [ ] 2. [étape atomique]

## Risques
- [risque 1 — mitigation]
```

---

## Pattern : summarize_session

**Usage** : appelé par `endday.ps1` pour résumer la session courante.

```
IDENTITÉ : Assistant de synthèse, mode terse.
TÂCHE : Résumer la session de travail fournie.

FORMAT DE SORTIE (strict, token-minimal) :

## Session YYYY-MM-DD

**Accompli**
- [liste courte, verbe + résultat]

**Décisions**
- [décision 1 — justification courte]

**Blocages**
- [blocage éventuel]

**Tokens**
- Entrée : X | Sortie : Y | Cache hits : Z%

**Next actions**
- [ ] [action 1]
- [ ] [action 2]

**Upsert Qdrant**
- [pattern ou leçon à upsert — 1 phrase]

CONTRAINTES :
- Maximum 200 mots total
- Pas de prose, listes uniquement
- Toujours inclure la section Upsert Qdrant
```

---

## Utilisation dans les scripts

```powershell
# Dans endday.ps1 — appel du pattern summarize_session
$sessionLog = Get-Content "$DEV_CORE_DATA\Logs\session_$(Get-Date -f yyyyMMdd).log" -Raw
$prompt = Get-Content "$DEV_CORE\Templates\Patterns\summarize_session.md" -Raw
$fullPrompt = "$prompt`n`n## Session log`n$sessionLog"
# → Envoyer au client actif via adapt_client.ps1
```
