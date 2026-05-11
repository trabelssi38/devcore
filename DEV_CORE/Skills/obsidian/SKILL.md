---
name: obsidian
description: >-
  Utiliser quand la tâche implique de lire, créer, modifier ou rechercher dans
  le vault Obsidian de DEV_CORE_DATA. Couvre : Daily Notes, Decisions, Lessons,
  Architecture, wikilinks, frontmatter, callouts, JSON Canvas, Bases, CLI.
  Déclencher pour toute opération vault : obsidian_sync, lesson_extractor,
  endday summary, recherche de notes passées.
sources:
  - kepano/obsidian-skills (adapté, client-agnostic)
  - https://github.com/kepano/obsidian-skills
compatibility: Claude Code · Codex · Gemini CLI · Qwen · tout agent SKILL.md
vault: C:\DEV_CORE_DATA\Vault\
---

# Skill — Obsidian DEV_CORE

## Vue d'ensemble

Ce skill encode les règles pour interagir correctement avec le vault Obsidian
de DEV_CORE_DATA. Il couvre deux modes : **CLI Obsidian** (si Obsidian est
ouvert) et **fichiers directs** (manipulation des .md sans Obsidian).

---

## Mode 1 — CLI Obsidian (Obsidian doit être ouvert)

Utiliser `obsidian` CLI pour toutes les opérations quand Obsidian est en cours.

```bash
# Lire une note
obsidian read file="Decisions/2026-04-25-qdrant-local"

# Créer une note
obsidian create name="Decisions/2026-04-25-titre" content="# Titre\n\nContenu" silent

# Appender à une note existante
obsidian append file="Daily Notes/2026-04-25" content="## Leçons\n- point 1"

# Lire la Daily Note du jour
obsidian daily:read

# Appender à la Daily Note
obsidian daily:append content="- [ ] Tâche ajoutée"

# Rechercher dans le vault
obsidian search query="qdrant performance" limit=10

# Définir une propriété frontmatter
obsidian property:set name="status" value="done" file="Projects/monprojet"

# Lister les tâches ouvertes
obsidian tasks daily todo

# Voir les backlinks d'une note
obsidian backlinks file="Architecture/DEV_CORE_v6"
```

---

## Mode 2 — Fichiers directs (sans Obsidian)

Quand Obsidian n'est pas ouvert, manipuler les fichiers `.md` directement
dans `C:\DEV_CORE_DATA\Vault\`.

---

## Format Obsidian Markdown

### Frontmatter obligatoire
```markdown
---
title: Titre de la note
date: 2026-04-25
tags:
  - categorie
  - sous-categorie
status: active  # active | archived | draft
project: nom_projet  # optionnel
---
```

### Wikilinks (TOUJOURS pour les liens internes)
```markdown
[[Nom de la note]]                    ← lien simple
[[Dossier/Nom de la note]]            ← lien avec chemin
[[Note|Texte affiché]]                ← lien avec alias
![[Note à embarquer]]                 ← embed
![[image.png]]                        ← image
```

### Callouts DEV_CORE
```markdown
> [!decision] Décision prise
> Contenu de la décision avec justification.

> [!lesson] Leçon apprise
> Ce qui a été appris et pourquoi c'est important.

> [!warning] Attention
> Point critique à ne pas oublier.

> [!todo] Prochaine action
> Action concrète avec responsable et date.
```

### Tâches
```markdown
- [ ] Tâche ouverte
- [x] Tâche terminée
- [/] Tâche en cours
- [-] Tâche annulée
```

---

## Structure du vault DEV_CORE_DATA

```
Vault\
├── Daily Notes\
│   └── YYYY-MM-DD.md          ← Une par jour, auto-générée par obsidian_sync.ps1
├── Decisions\
│   └── YYYY-MM-DD-titre.md    ← Décisions architecturales et techniques
├── Architecture\
│   └── DEV_CORE_v6.md         ← Document vivant de l'architecture
├── Lessons\
│   ├── bug\
│   ├── architecture\
│   ├── prompt\
│   └── workflow\
└── References\
```

---

## Template — Daily Note

```markdown
---
title: Daily Note YYYY-MM-DD
date: YYYY-MM-DD
tags:
  - daily
  - devcore
---

# YYYY-MM-DD

## Résumé de journée
<!-- Auto-généré -->

## Tâches accomplies
- 

## Décisions prises
- Voir [[Decisions/YYYY-MM-DD-titre]] pour le détail

## Leçons apprises
- 

## Métriques tokens
- Total : X | Cache hits : Y% | Moteur principal : Z

## Next actions
- [ ] 
```

---

## Template — Decision

```markdown
---
title: Décision — [Titre]
date: YYYY-MM-DD
tags:
  - decision
  - [catégorie]
status: active
---

# Décision — [Titre]

## Contexte
Pourquoi cette décision était nécessaire.

## Options considérées
1. Option A — avantages / inconvénients
2. Option B — avantages / inconvénients

## Décision retenue
Option X, parce que...

## Conséquences
Ce qui change suite à cette décision.

## Liens
- [[Architecture/DEV_CORE_v6]]
- [[Lessons/...]]
```

---

## Template — Lesson

```markdown
---
title: Leçon — [Titre]
date: YYYY-MM-DD
tags:
  - lesson
  - [bug|architecture|prompt|workflow]
score: 0.0   # 0.0 à 1.0, mis à jour par memory_rotate.ps1
---

# Leçon — [Titre]

## Contexte
Situation dans laquelle cette leçon a été découverte.

## Ce qui s'est passé
Description factuelle.

## Leçon
Ce qu'on retient concrètement.

## Application
Comment appliquer cette leçon à l'avenir.
```

---

## Erreurs fréquentes à éviter

- Ne jamais utiliser `[lien](url-interne)` pour les notes internes → toujours `[[wikilink]]`
- Ne jamais oublier le frontmatter sur une nouvelle note
- Ne jamais écrire dans `C:\DEV_CORE_DATA\Vault\` sans mettre à jour les backlinks
- Ne pas dupliquer une décision déjà documentée → chercher d'abord avec `obsidian search`
