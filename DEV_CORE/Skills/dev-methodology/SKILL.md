---
name: dev-methodology
description: >-
  Utiliser pour toute tâche de développement : nouvelle feature, debug, review
  architecture, planning sprint, TDD, refactoring, postmortem. Couvre :
  brainstorming structuré, spec validée par sections, plan d'implémentation
  granulaire, TDD red/green/refactor, subagent-driven-development, review
  deux étapes. Déclencher avant d'écrire la moindre ligne de code.
sources:
  - obra/superpowers (adapté, client-agnostic)
  - https://github.com/obra/superpowers
compatibility: Claude Code · Codex · Gemini CLI · Qwen · tout agent SKILL.md
---

# Skill — Dev Methodology DEV_CORE

## Principe fondamental

**Ne jamais écrire de code avant d'avoir une spec validée.**
Chaque étape doit être approuvée avant de passer à la suivante.
Le code le moins cher est celui qu'on n'écrit pas.

---

## Phase 1 — Brainstorming (toujours en premier)

Avant toute feature ou fix non trivial :

```
1. Reformuler le problème dans ses propres mots
2. Lister 3 à 5 approches possibles avec trade-offs
3. Identifier les hypothèses implicites
4. Poser les questions bloquantes
5. Choisir l'approche → ATTENDRE VALIDATION avant de continuer
```

**Format de sortie brainstorming :**
```markdown
## Brainstorming — [Titre]

### Problème
[Reformulation en 2 phrases max]

### Approches
1. **[Nom]** — [description courte]
   - ✓ [avantage]
   - ✗ [inconvénient]

2. **[Nom]** — [description courte]
   ...

### Hypothèses
- [hypothèse 1]

### Questions bloquantes
- [question 1]

### Recommandation
Approche X, parce que [raison courte].

**→ Validation requise avant de continuer**
```

---

## Phase 2 — Spec par sections

Une fois l'approche validée, écrire la spec par petits blocs.
Chaque bloc doit être validé avant le suivant.

```
Section 1 : Scope et non-scope
    → VALIDATION
Section 2 : Interfaces et contrats (APIs, types, schémas)
    → VALIDATION
Section 3 : Comportements et edge cases
    → VALIDATION
Section 4 : Critères d'acceptance
    → VALIDATION
```

**Template spec :**
```markdown
## Spec — [Titre]
Version : 1.0 | Date : YYYY-MM-DD | Status : draft → validated

### Scope
Ce que cette feature fait : ...
Ce qu'elle ne fait PAS : ...

### Interfaces
[Types, APIs, schémas, contrats entre composants]

### Comportements
- Cas nominal : ...
- Edge case 1 : ...
- Edge case 2 : ...

### Critères d'acceptance
- [ ] [test observable 1]
- [ ] [test observable 2]
```

---

## Phase 3 — Plan d'implémentation granulaire

Après validation de la spec, décomposer en étapes atomiques (max 30 min chacune).

```markdown
## Plan — [Titre]

- [ ] 1. [Étape atomique — verbe + objet précis]
- [ ] 2. [Étape atomique]
- [ ] 3. [Étape atomique]
...

Chaque étape = 1 commit logique.
**→ Validation du plan avant d'exécuter**
```

---

## Phase 4 — TDD : Red / Green / Refactor

Pour chaque étape du plan :

```
RED    : Écrire le test qui échoue AVANT le code
GREEN  : Écrire le minimum de code pour que le test passe
REFACTOR : Nettoyer le code sans casser les tests
```

**Règles TDD DEV_CORE :**
- Un seul test à la fois
- Le test doit échouer pour la bonne raison (pas une erreur de syntaxe)
- Ne jamais skip le refactor — c'est là que la qualité se construit
- Commiter après chaque cycle Green

---

## Phase 5 — Review deux étapes

### Étape 1 — Self-review (avant de soumettre)

```markdown
## Self-review checklist
- [ ] Le code fait exactement ce que la spec dit
- [ ] Tous les critères d'acceptance passent
- [ ] Pas de code mort ou commenté
- [ ] Pas de TODO sans ticket associé
- [ ] Nommage explicite (pas d'abbréviations cryptiques)
- [ ] Edge cases couverts par des tests
- [ ] Pas de secrets ou configs hardcodées
```

### Étape 2 — Review agent (subagent-driven)

Utiliser un second agent (ou second passage) avec ce prompt :

```
Tu es un reviewer senior. Tu n'as aucun contexte sur cette feature.
Lis ce code et réponds uniquement :
1. Ce que le code fait (reformulation)
2. Ce qui pourrait casser
3. Ce qui manque
4. Une amélioration critique
Ne dis pas ce qui est bien. Sois bref.
```

---

## Patterns de debug

### Processus debug structuré

```
1. Reproduire le bug de façon minimale et isolée
2. Former une hypothèse précise ("je pense que X cause Y parce que Z")
3. Tester UNE hypothèse à la fois
4. Logger la conclusion (lesson_extractor.ps1 si récurrent)
```

### Ne jamais faire

- Modifier plusieurs variables en même temps pour "voir ce qui fonctionne"
- Commiter un fix sans comprendre pourquoi ça marchait pas
- Ignorer un test qui passe par accident

---

## Subagent-driven development

Pour les tâches complexes multi-étapes, décomposer en subagents :

```markdown
## Mission subagent [N]
Context : [contexte minimal, < 100 mots]
Input : [ce qu'il reçoit]
Task : [une seule tâche précise]
Output : [format attendu exact]
Constraint : [budget token, format, limites]
Handoff : [ce qu'il transmet au subagent suivant]
```

**Règle** : chaque subagent a une seule responsabilité.
Si le subagent doit "aussi faire X", c'est un subagent séparé.

---

## Handoff inter-sessions

À la fin de chaque session de développement :

```markdown
## Handoff Dev — [Feature]

### Done
- [Liste des étapes complétées]

### État actuel
- Tests : [X passing, Y failing]
- Dernier commit : [hash court + message]
- Blocage éventuel : [description]

### Next
- [ ] Prochaine étape précise (étape N+1 du plan)

### Context minimal pour reprendre
[Décisions prises, choix techniques, contraintes découvertes — < 150 mots]

### Qdrant query suggérée
"[requête pour retrouver le contexte pertinent]"
```

---

## Quand logger dans la mémoire

| Situation | Action |
|---|---|
| Bug résolu de façon non-évidente | → lesson_extractor (catégorie: bug) |
| Décision d'architecture | → obsidian Decisions + Qdrant decisions |
| Pattern réutilisable découvert | → Skills + Qdrant patterns |
| Postmortem incident | → Fabric pattern create_postmortem |
| Prompt particulièrement efficace | → Qdrant patterns + MEMORY.md |
