# DEV_CORE — Plan d'amélioration Skills, UI Craft et Motion Quality

Date : 2026-07-14  
Statut : draft  
Source d'inspiration : https://github.com/emilkowalski/skills  
Scope : DEV_CORE skills, Dashboard/Cockpit, frontend quality gates, design engineering workflow.

## 1. Objectif

Renforcer DEV_CORE avec une couche de skills orientée qualité produit : UI craft, animation review, audit motion, accessibilité et plans d'amélioration auto-suffisants.

Le but n'est pas d'ajouter une dépendance runtime. Le but est de transformer des critères de qualité visuelle en règles opérationnelles que les agents peuvent appliquer, vérifier et documenter.

## 2. Constat actuel

DEV_CORE possède déjà des skills solides pour l'automatisation, le développement, Qdrant, Obsidian, API Python, web UI et UI/UX.

Points forts actuels :

- `devcore-automation` encadre le cycle launch/task/commit/endday.
- `dev-methodology` impose une méthode de développement structurée.
- `ui-ux` fournit des règles de design system, accessibilité et dashboard.
- `web_ui` couvre l'exécution frontend.
- Le Dashboard/Cockpit donne une surface produit concrète pour appliquer ces règles.
- Le Token Optimization Stack permet d'envisager un workflow audit fort puis exécution plus économique.

Limites actuelles :

- Les règles UI sont présentes, mais pas encore séparées en review stricte, audit global et exécution.
- Il n'existe pas encore de skill spécialisé pour la qualité motion/animation.
- Les recommandations UI peuvent rester générales si elles ne produisent pas de findings fichier/ligne.
- Il n'y a pas encore de gate explicite contre les anti-patterns motion : `transition: all`, `ease-in` sur UI, animations trop longues, absence de `prefers-reduced-motion`.
- Le Dashboard peut gagner en polish produit : feedback press, reduced motion, cohérence des transitions, densité visuelle, états loading/empty/error.

## 3. Principes à adopter

### 3.1 Expertise codifiée

Chaque skill doit capturer une expertise claire, pas seulement une liste de préférences.

Exemples :

- "Une animation UI fréquente doit être supprimée ou réduite."
- "Une interaction clavier ne doit pas être ralentie par une animation."
- "`transition: all` est un risque performance et un manque de contrôle."
- "Les statuts ne doivent jamais dépendre uniquement de la couleur."

### 3.2 Séparation des responsabilités

Créer des skills spécialisés :

- Un skill pour concevoir.
- Un skill pour auditer.
- Un skill pour reviewer.
- Un skill pour exécuter.
- Un skill pour maintenir les standards.

Cette séparation évite qu'un seul skill devienne trop large et difficile à appliquer.

### 3.3 Plans auto-suffisants

Les audits ne doivent pas seulement dire "améliorer l'animation". Ils doivent produire des plans exécutables :

- fichier exact ;
- ligne ou sélecteur ;
- problème observé ;
- valeur cible ;
- étapes d'implémentation ;
- vérification ;
- critère d'acceptation.

### 3.4 Read-only avant mutation

Pour les audits UI/motion :

- phase 1 : lecture seule ;
- phase 2 : findings priorisés ;
- phase 3 : validation ;
- phase 4 : plans ;
- phase 5 : exécution séparée.

Ce modèle réduit le risque de changements cosmétiques non maîtrisés.

## 4. Skills recommandés

### 4.1 `dashboard-ui-craft`

Rôle : standard DEV_CORE pour la qualité d'interface du Cockpit.

Responsabilités :

- définir le style cible : Dark Tech opérationnel ;
- maintenir les design tokens ;
- imposer la hiérarchie visuelle ;
- contrôler densité, spacing, contraste et typographie ;
- guider les composants : cards, badges, nav, timelines, panels, tables.

Entrées :

- fichiers HTML/CSS/JS/React du dashboard ;
- design tokens existants ;
- captures écran si disponibles ;
- logs console navigateur si disponibles.

Sorties :

- recommandations concrètes ;
- liste d'anti-patterns ;
- plan de refactor UI ;
- checklist avant commit frontend.

Critères d'acceptation :

- tokens centralisés ;
- contraste WCAG AA ;
- états loading/empty/error présents ;
- focus visible ;
- responsive 375/768/1280 vérifié ;
- composants cohérents.

### 4.2 `motion-review`

Rôle : review stricte des animations et transitions dans un diff ou un fichier.

Doit bloquer :

- `transition: all` ;
- `ease-in` sur une interaction UI ;
- animation d'une action clavier ou très fréquente ;
- durée UI > 300ms sans justification ;
- animation de propriétés layout : `width`, `height`, `top`, `left`, `margin`, `padding` ;
- absence de `prefers-reduced-motion` pour les mouvements ;
- hover motion non protégée par media query adaptée ;
- popover/dropdown qui scale depuis le centre au lieu de son trigger ;
- entrée depuis `scale(0)`.

Sortie obligatoire :

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 180ms var(--ease-out)` | Évite les propriétés non GPU et réduit le coût de rendu |

Verdict :

- `Block` si régression motion significative.
- `Approve` si aucun problème bloquant.
- `Needs manual feel-check` si le code seul ne suffit pas.

### 4.3 `motion-audit`

Rôle : audit complet du codebase frontend, en lecture seule, avec findings priorisés.

Catégories à auditer :

1. But de l'animation.
2. Fréquence d'exposition.
3. Easing et durée.
4. Origine physique.
5. Interruptibilité.
6. Performance GPU.
7. Accessibilité.
8. Cohésion visuelle.
9. Opportunités manquées.

Sortie :

| Priorité | Sévérité | Catégorie | Localisation | Finding | Fix summary |
| --- | --- | --- | --- | --- | --- |
| P0 | HIGH | Performance | `Dashboard/index.html` | `transition: all` sur composant fréquent | Limiter à `transform, opacity, border-color` |

Règles :

- ne modifie pas le code ;
- ne lance pas de formatters ;
- ne fait pas de commit ;
- écrit uniquement dans `plans/` si l'utilisateur demande la génération des plans.

### 4.4 `motion-plan-writer`

Rôle : convertir un finding validé en plan d'implémentation auto-suffisant.

Template recommandé :

```markdown
# Plan NN — [Titre court]

Commit de référence : [hash]
Statut : TODO
Sévérité : HIGH|MEDIUM|LOW

## Problème

[Description courte + fichier/ligne]

## Changement cible

- Durée : [valeur exacte]
- Easing : [valeur exacte]
- Propriétés animées : [liste]
- Reduced motion : [règle]

## Fichiers concernés

- [chemin]

## Étapes

1. [étape atomique]
2. [étape atomique]
3. [étape atomique]

## Vérification

- [ ] Test visuel normal
- [ ] Test reduced motion
- [ ] Test clavier
- [ ] Test responsive
- [ ] Aucun layout property animé
```

### 4.5 `ui-accessibility-review`

Rôle : review accessibilité ciblée sur le Cockpit et les composants web DEV_CORE.

Contrôles :

- labels de formulaire ;
- focus visible ;
- navigation clavier ;
- landmarks ;
- aria-label utile ;
- contraste ;
- statuts lisibles hors couleur ;
- reduced motion ;
- messages d'erreur explicites ;
- touch targets minimum 44px.

### 4.6 `skill-quality-review`

Rôle : contrôler la qualité des skills DEV_CORE eux-mêmes.

Critères :

- description claire ;
- trigger précis ;
- scope/non-scope explicite ;
- règles vérifiables ;
- workflow concret ;
- sorties attendues ;
- exemples ;
- absence de dépendance implicite ;
- compatibilité Codex/Claude/Gemini documentée si nécessaire.

## 5. Intégration dans DEV_CORE

### 5.1 Registre des skills

Ajouter les nouveaux skills au registre DEV_CORE avec :

- nom ;
- description ;
- triggers ;
- priorité ;
- compatibilité ;
- scope ;
- dépendances éventuelles.

Exemple :

```json
{
  "name": "motion-review",
  "category": "frontend_quality",
  "priority": 70,
  "triggers": [
    "animation",
    "transition",
    "motion",
    "dashboard polish",
    "frontend review"
  ],
  "mode": "coding"
}
```

### 5.2 Workflow agent

Pour une tâche frontend :

1. Charger `devcore-automation`.
2. Charger `dev-methodology`.
3. Charger `ui-ux`.
4. Si motion ou dashboard : charger `dashboard-ui-craft`.
5. Si review : charger `motion-review`.
6. Si audit global : charger `motion-audit`.
7. Produire findings ou plan.
8. Exécuter uniquement après validation ou tâche dédiée.

### 5.3 Dashboard integration

Ajouter dans le Cockpit :

- score UI Craft ;
- nombre de findings motion ;
- findings accessibility ;
- dette UX par sévérité ;
- derniers audits ;
- liens vers plans générés ;
- statut reduced-motion ;
- statut design tokens.

### 5.4 Metrics Service

Exposer des métriques :

- `ui_findings_total` ;
- `ui_findings_high` ;
- `motion_violations_total` ;
- `accessibility_violations_total` ;
- `dashboard_components_with_tokens_ratio` ;
- `reduced_motion_coverage_ratio` ;
- `transition_all_count`.

### 5.5 Knowledge Graph

Indexer :

- skills ;
- règles ;
- composants UI ;
- findings ;
- plans ;
- commits ;
- décisions design ;
- relations composant -> token -> règle -> finding.

Objectif : permettre des requêtes du type :

- "Quels composants violent reduced motion ?"
- "Quels plans UI sont liés au Dashboard Cockpit ?"
- "Quelle règle bloque `transition: all` ?"

### 5.6 Token Optimization Stack

Utiliser le modèle suivant :

- modèle fort : audit/review avec jugement ;
- sortie structurée et courte ;
- plans écrits dans fichiers ;
- modèle économique : exécution des plans ;
- Qdrant/Knowledge Graph : réutilisation des décisions.

## 6. Standards motion DEV_CORE

### 6.1 Durées

| Élément | Durée recommandée |
| --- | --- |
| Button press | 100-160ms |
| Hover subtil | 100-160ms |
| Tooltip | 125-180ms |
| Dropdown/popover | 150-220ms |
| Toast | 180-260ms |
| Modal/drawer | 200-300ms |
| Onboarding rare | 300-500ms |

Règle : une animation UI courante doit rester sous 300ms.

### 6.2 Easing

Tokens recommandés :

```css
--ease-out-strong: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out-strong: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

Règles :

- enter UI : `ease-out` ;
- mouvement spatial : `ease-in-out` ;
- action clavier : pas d'animation ;
- loading constant : `linear` ;
- éviter `ease-in` sur UI interactive.

### 6.3 Propriétés autorisées

Privilégier :

- `transform` ;
- `opacity` ;
- `filter` avec prudence ;
- `box-shadow` uniquement sur interactions peu fréquentes.

Éviter :

- `width` ;
- `height` ;
- `top` ;
- `left` ;
- `margin` ;
- `padding` ;
- `transition: all`.

### 6.4 Reduced motion

Chaque mouvement non trivial doit avoir une variante :

```css
@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto;
  }

  .animated-panel {
    transition-duration: 1ms;
    transform: none;
  }
}
```

## 7. Plan de mise en œuvre par sprints

### Sprint UI-01 — Cadrage et standards

Objectif : stabiliser le référentiel de qualité UI/motion.

Tâches :

- [ ] Créer `dashboard-ui-craft/SKILL.md`.
- [ ] Créer `motion-review/SKILL.md`.
- [ ] Créer `motion-audit/SKILL.md`.
- [ ] Ajouter un fichier `MOTION_STANDARDS.md`.
- [ ] Ajouter les triggers au registre des skills.
- [ ] Documenter scope/non-scope de chaque skill.

Critères d'acceptation :

- chaque skill a description, triggers, workflow, sorties ;
- les règles bloquantes sont explicites ;
- aucun changement runtime.

### Sprint UI-02 — Audit Dashboard en lecture seule

Objectif : produire une première photographie de la dette UI/motion.

Tâches :

- [ ] Scanner le Dashboard pour transitions, animations, keyframes et hover.
- [ ] Identifier les violations `transition: all`.
- [ ] Identifier les animations sans reduced motion.
- [ ] Identifier les composants sans état loading/empty/error.
- [ ] Générer un rapport `plans/ui-audit-dashboard.md`.

Critères d'acceptation :

- findings avec fichier/ligne ;
- sévérité HIGH/MEDIUM/LOW ;
- aucun code modifié.

### Sprint UI-03 — Plans auto-suffisants

Objectif : transformer les findings prioritaires en plans exécutables.

Tâches :

- [ ] Créer 3 à 5 plans pour findings HIGH.
- [ ] Ajouter `plans/README.md`.
- [ ] Définir ordre d'exécution.
- [ ] Ajouter étapes de vérification reduced motion.

Critères d'acceptation :

- chaque plan peut être exécuté sans contexte conversationnel ;
- valeurs exactes incluses ;
- fichiers et sélecteurs indiqués.

### Sprint UI-04 — Gates statiques

Objectif : empêcher les régressions simples.

Tâches :

- [ ] Ajouter test statique contre `transition: all`.
- [ ] Ajouter test statique pour `prefers-reduced-motion`.
- [ ] Ajouter test statique pour design tokens critiques.
- [ ] Ajouter test statique pour couleurs hardcodées hors exceptions.

Critères d'acceptation :

- tests rapides ;
- messages d'erreur actionnables ;
- intégration CI possible.

### Sprint UI-05 — Dashboard observability

Objectif : rendre la qualité UI visible dans DEV_CORE.

Tâches :

- [ ] Ajouter métriques UI au Metrics Service.
- [ ] Ajouter card "UI Craft" au Cockpit.
- [ ] Afficher findings HIGH/MEDIUM/LOW.
- [ ] Lier findings aux plans.
- [ ] Afficher statut reduced motion/design tokens.

Critères d'acceptation :

- état lisible dans le Dashboard ;
- pas de dépendance externe ;
- dégradation gracieuse si aucun audit.

### Sprint UI-06 — Knowledge Graph

Objectif : relier skills, règles, composants, findings et décisions.

Tâches :

- [ ] Modéliser les nœuds `Skill`, `Rule`, `Component`, `Finding`, `Plan`.
- [ ] Relier `Finding -> Rule`.
- [ ] Relier `Plan -> Finding`.
- [ ] Relier `Component -> Token`.
- [ ] Ajouter requêtes utiles pour diagnostics.

Critères d'acceptation :

- recherche par règle ;
- recherche par composant ;
- historique des décisions UI.

### Sprint UI-07 — Exécution des plans prioritaires

Objectif : appliquer les corrections les plus rentables.

Tâches :

- [ ] Exécuter les plans P0/P1 validés.
- [ ] Vérifier visuellement le Cockpit.
- [ ] Vérifier reduced motion.
- [ ] Mettre à jour les screenshots/docs si nécessaire.

Critères d'acceptation :

- aucun finding HIGH restant sur les règles de base ;
- tests statiques passants ;
- Dashboard plus stable et plus lisible.

## 8. Backlog recommandé

Priorité haute :

- [ ] Supprimer ou remplacer les mentions legacy `9Router` dans la documentation active.
- [ ] Clarifier `Gemini Router` vs `routing local` vs `Tools/devcore/router.py`.
- [ ] Créer `motion-review`.
- [ ] Ajouter gate contre `transition: all`.
- [ ] Ajouter reduced-motion au Dashboard.
- [ ] Ajouter card `UI Craft` au Cockpit.

Priorité moyenne :

- [ ] Créer `motion-audit`.
- [ ] Générer les premiers plans dans `plans/`.
- [ ] Ajouter métriques UI au Metrics Service.
- [ ] Indexer findings UI dans Knowledge Graph.
- [ ] Ajouter skill `skill-quality-review`.

Priorité basse :

- [ ] Ajouter vocabulaire animation DEV_CORE.
- [ ] Ajouter presets motion par composant.
- [ ] Ajouter screenshots de référence.
- [ ] Ajouter mode slow-motion debug pour review visuelle.

## 9. Risques

| Risque | Impact | Mitigation |
| --- | --- | --- |
| Trop de règles cosmétiques | Perte de vitesse | Bloquer uniquement P0/P1, laisser P2 en recommandations |
| Skills trop larges | Faible adoption | Séparer review, audit, exécution |
| Tests UI fragiles | CI instable | Commencer par tests statiques simples |
| Sur-animation du Dashboard | Interface moins performante | Principe : supprimer avant d'ajouter |
| Dépendances inutiles | Maintenance accrue | Pas de nouvelle dépendance runtime pour la phase standards |

## 10. Définition de Done

Le chantier est terminé quand :

- les skills UI/motion sont créés et enregistrés ;
- les règles motion de base sont documentées ;
- le Dashboard a un audit initial ;
- les findings HIGH ont des plans ;
- les gates statiques bloquent les régressions évidentes ;
- le Metrics Service expose les métriques UI ;
- le Knowledge Graph relie skills, règles, findings et plans ;
- la documentation DEV_CORE explique ce workflow.

## 11. Recommandation finale

Adopter l'approche `emilkowalski/skills` comme modèle de qualité : expertise codifiée, review stricte, audit read-only, plans auto-suffisants, exécution séparée.

Pour DEV_CORE, la meilleure première étape est de créer `motion-review` et `dashboard-ui-craft`, puis de lancer un audit read-only du Cockpit. Cela apporte un gain visible sans risque sur le runtime.
