# DEV_CORE Incident Runbook

Ce runbook fixe le contrat minimal de diagnostic, d'escalade et de support pour une exploitation DEV_CORE professionnelle. La politique machine-readable associée est `support_policy.json`.

Références opérateur :

- `PLATFORM_DOCUMENTATION.md`
- `OPERATOR_GUIDE.md`
- `API_REFERENCE.md`
- `DEV_CORE\Support\support_policy.json`

## Severity matrix

| Sévérité | Impact | Réponse initiale | Mises à jour | Objectif résolution |
|---|---|---:|---:|---:|
| `SEV1` | Plateforme indisponible, perte de données probable, faille critique exploitable ou blocage total DEV_CORE. | 15 min | 30 min | 4 h |
| `SEV2` | Fonction majeure dégradée avec workaround disponible et données intactes. | 60 min | 120 min | 24 h |
| `SEV3` | Bug mineur, documentation, optimisation ou support sans impact immédiat. | 240 min | 1440 min | 72 h |

## Triage workflow

1. Capturer l'état santé :

   ```powershell
   dc health --json
   ```

2. Vérifier le gate local avant tout changement :

   ```powershell
   dc check --gate
   ```

3. Lancer le guide diagnostic non destructif :

   ```powershell
   dc guide diagnostic
   ```

4. Si une récupération est nécessaire, utiliser uniquement le guide recovery documenté :

   ```powershell
   dc guide recovery
   ```

5. Avant clôture ou handoff, synchroniser l'état de session :

   ```powershell
   powershell -ExecutionPolicy Bypass -NonInteractive -File "C:\devcore\DEV_CORE\Scripts\endday.ps1" -SkipBackup
   ```

## Evidence bundle

Créer un dossier daté sous `C:\devcore\DEV_CORE_DATA\Logs\incidents\YYYYMMDD-HHMM-<severity>\` et y copier au minimum :

- sortie `dc health --json` ;
- sortie `dc check --gate` ;
- logs récents `DEV_CORE_DATA\Logs\scripts` ;
- état Hermes et cron `DEV_CORE_DATA\Logs\hermes` ;
- `DEV_CORE\Security\security-review.json` si l'incident touche sécurité, dépendances ou release ;
- `DEV_CORE\Release\release-manifest.json` si l'incident touche packaging, rollback ou reproductibilité ;
- commit courant, dernier commit sain connu et commandes de reproduction.

Ne pas inclure de secrets bruts. Remplacer les tokens/API keys par `[REDACTED]`.

## Escalation

Escalader dès qu'un de ces critères est vrai :

- `SEV1` confirmé ou suspecté ;
- données de task board, read model, mémoire ou contexte incohérentes ;
- `dc check --gate` échoue sans mitigation claire ;
- recovery ou rollback nécessaire ;
- incident sécurité, secret exposé, dépendance critique ou finding élevé.

Le handoff doit inclure :

- sévérité ;
- impact utilisateur ;
- heure de début ;
- dernier commit sain connu ;
- étapes de reproduction ;
- chemin de l'evidence bundle ;
- mitigation déjà appliquée ;
- prochaine action proposée.

## Support acceptance criteria

Un incident peut être accepté en support seulement si :

- il correspond à un type accepté dans `support_policy.json` ;
- il contient l'evidence bundle minimal ;
- la sévérité `SEV1`, `SEV2` ou `SEV3` est explicitement assignée ;
- le comportement attendu et le comportement observé sont décrits ;
- les commandes `dc health --json` et `dc check --gate` ont été exécutées ou l'impossibilité de les exécuter est justifiée.

Un incident peut être clôturé seulement si :

- la cause racine ou la mitigation est documentée ;
- le gate pertinent repasse ;
- la documentation ou les tests sont mis à jour si l'incident révèle un trou de contrat ;
- `endday.ps1 -SkipBackup` a été lancé sans bloquer le travail.

## Recovery guardrails

- Priorité à la lecture et au diagnostic avant toute mutation.
- Pas de suppression manuelle de données runtime sans backup ou justification explicite.
- Pas de changement simultané de plusieurs variables pendant le debug.
- Tout correctif doit avoir un test ciblé avant commit quand le bug est reproductible.
- Les changements liés release passent par `dc check --gate`, le manifeste de release et les notes de release.
