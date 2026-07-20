---
name: motion-review
description: Automated audit skill for scanning HTML, CSS, and React components for motion performance regressions, costly layout transitions, and missing accessibility reduced-motion blocks.
---

# Motion Review Skill

Ce skill fournit un analyseur statique pour auditer la conformité des animations et transitions CSS vis-à-vis du document `MOTION_STANDARDS.md`.

---

## Rôles & Vérifications

1. **Détection `transition: all`** :
   - Recherche d'occurrences de `transition: all` ou `transition:all`.
   - Priorité : **P0 (Bloquant)**.

2. **Détection des Transitions de Layout** :
   - Recherche de transitions ciblant `width`, `height`, `margin`, `padding`, `top`, `left`.
   - Priorité : **P1 (Majeur)**.

3. **Vérification Reduced-Motion** :
   - Vérifie la présence de `@media (prefers-reduced-motion: reduce)` dans les fichiers CSS/HTML comportant des animations.
   - Priorité : **P1 (Majeur)**.

---

## Commande d'Exécution

Pour exécuter l'audit automatique :
```bash
python C:\devcore\DEV_CORE\Scripts\audit_ui_motion.py
```
