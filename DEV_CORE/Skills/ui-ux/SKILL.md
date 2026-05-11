---
name: ui-ux
description: >-
  Utiliser pour toute tâche de design ou développement frontend : composants UI,
  design system, wireframes, choix typographie, palettes couleurs, accessibilité,
  responsive layout, micro-interactions. Fournit 99 guidelines UX, règles de
  raisonnement design, styles visuels, palettes et paires de polices.
  Déclencher avant de générer du HTML, CSS, React, SwiftUI ou Flutter.
sources:
  - nextlevelbuilder/ui-ux-pro-max-skill (adapté, client-agnostic)
  - https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
compatibility: Claude Code · Codex · Gemini CLI · Qwen · tout agent SKILL.md
---

# Skill — UI/UX DEV_CORE

## Processus design

Avant de générer du code UI, toujours dans cet ordre :

```
1. Identifier le style visuel cible (tableau ci-dessous)
2. Sélectionner la palette couleurs adaptée
3. Choisir la paire de polices
4. Appliquer les guidelines UX pertinentes
5. Générer le code
```

---

## Styles visuels

| Style | Caractéristiques | Idéal pour |
|---|---|---|
| **Minimal** | Espace blanc, 1-2 couleurs, typographie forte | SaaS, dashboards, outils |
| **Corporate** | Bleu/gris, grille stricte, iconographie standard | Entreprise, B2B |
| **Dark Tech** | Fond sombre, accents néon, mono font | DevTools, IDE, terminaux |
| **Glassmorphism** | Blur, transparence, gradients subtils | Apps modernes, landing |
| **Brutalist** | Couleurs saturées, bordures épaisses, sans serif | Portfolio, créatif |
| **Neumorphism** | Shadows soft, relief, palette monochrome | Mobile, settings UI |

---

## Palettes recommandées par usage

### Dashboard / outil interne (DEV_CORE)
```css
--color-bg:         #0f1117;
--color-surface:    #1a1d27;
--color-border:     #2d3148;
--color-accent:     #6366f1;   /* Indigo */
--color-success:    #22c55e;
--color-warning:    #f59e0b;
--color-danger:     #ef4444;
--color-text-1:     #f8fafc;
--color-text-2:     #94a3b8;
--color-text-3:     #475569;
```

### SaaS / App claire
```css
--color-bg:         #ffffff;
--color-surface:    #f8fafc;
--color-border:     #e2e8f0;
--color-accent:     #6366f1;
--color-success:    #16a34a;
--color-warning:    #d97706;
--color-danger:     #dc2626;
--color-text-1:     #0f172a;
--color-text-2:     #475569;
--color-text-3:     #94a3b8;
```

---

## Paires de polices

| Usage | Titres | Corps | Code |
|---|---|---|---|
| Dashboard tech | Inter | Inter | JetBrains Mono |
| SaaS moderne | Cal Sans | Inter | Fira Code |
| Corporate | Sora | DM Sans | — |
| Créatif | Clash Display | Satoshi | — |

```css
/* Dashboard DEV_CORE — recommandé */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

---

## 20 guidelines UX prioritaires

**Hiérarchie visuelle**
1. Un seul élément dominant par écran — tout le reste est secondaire
2. Taille, poids, couleur : trois leviers seulement, ne pas utiliser les trois en même temps
3. L'œil suit la F-pattern ou le Z-pattern — placer l'action principale dans ces zones

**Espacement**
4. Utiliser une échelle d'espacement fixe : 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64px
5. Plus d'espace entre les groupes qu'au sein d'un groupe (loi de proximité)
6. Les éléments interactifs doivent avoir une zone de touch min 44×44px

**Couleurs**
7. Ratio de contraste minimum : 4.5:1 pour le texte (WCAG AA)
8. Utiliser la couleur pour informer, pas décorer — chaque couleur a une sémantique
9. Ne jamais distinguer deux états par la couleur seule (daltonisme)

**Typographie**
10. Line-height : 1.4-1.6 pour le corps, 1.1-1.2 pour les titres
11. Longueur de ligne optimale : 60-80 caractères (environ 680px à 16px)
12. Pas plus de 2 graisses de police par hiérarchie visuelle

**Interactions**
13. Feedback dans les 100ms (visuel immédiat) puis résultat dans les 1000ms
14. Chaque action destructive demande confirmation (avec temps d'annulation si possible)
15. Les états de chargement doivent être explicites — ne jamais laisser l'interface muette

**Formulaires**
16. Labels au-dessus des champs, jamais à l'intérieur comme placeholder permanent
17. Valider les champs à la perte du focus (blur), pas à chaque frappe
18. Le message d'erreur explique comment corriger, pas juste "champ invalide"

**Navigation**
19. L'utilisateur doit toujours savoir où il est (breadcrumb, état actif, titre de page)
20. Maximum 7 items de navigation principale (Miller's Law)

---

## Composants standard DEV_CORE

### Bouton
```css
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}
.btn-primary { background: var(--color-accent); color: white; }
.btn-secondary { background: var(--color-surface); border-color: var(--color-border); color: var(--color-text-1); }
.btn-danger { background: var(--color-danger); color: white; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
```

### Carte / Card
```css
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
}
```

### Badge / Tag
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.badge-green  { background: #dcfce7; color: #166534; }
.badge-blue   { background: #dbeafe; color: #1e40af; }
.badge-amber  { background: #fef3c7; color: #92400e; }
.badge-red    { background: #fee2e2; color: #991b1b; }
.badge-gray   { background: var(--color-border); color: var(--color-text-2); }
```

---

## Checklist avant livraison UI

```
□ Contraste texte/fond ≥ 4.5:1 (tester sur WebAIM Contrast Checker)
□ Tous les états interactifs ont un style (hover, focus, active, disabled)
□ Focus visible au clavier (outline ou équivalent)
□ Images ont un alt text
□ Formulaires ont des labels associés (for/id ou aria-label)
□ Responsive testé : 375px (mobile) · 768px (tablet) · 1280px (desktop)
□ Touch targets ≥ 44×44px sur mobile
□ Pas d'informations transmises par la couleur seule
```

---

## Anti-patterns à éviter

- **Faux loading** : spinner sans vrai chargement derrière
- **Modal sur modal** : jamais plus d'une modal ouverte
- **Overflow caché silencieux** : si du contenu est tronqué, le signaler visuellement
- **Couleurs sémantiques inversées** : rouge = succès ou vert = danger
- **Toasts qui disparaissent trop vite** : minimum 4 secondes, 6 si message long
- **CTA fantôme** : bouton outline trop discret pour une action principale
