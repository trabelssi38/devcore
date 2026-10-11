# Mesurer l'effet du contexte DevCore sur Codex

## Périmètre

La mesure porte sur deux conversations indépendantes pour une tâche identique. Le nombre de tokens est lu dans les événements `event_msg/token_count` et `info.total_token_usage` des rollouts locaux Codex. Ce format a été observé sur le poste ; il peut évoluer avec le client. Les compteurs sont des observations du client, pas une facture ni un pourcentage du quota de l'abonnement.

`Scripts/Auto/token_report.py` utilise les deltas des compteurs cumulés lorsqu'ils existent. Il ignore les snapshots répétés et ne leur ajoute pas les estimations des messages. Une baisse du compteur est signalée ; la couverture de cette session est alors incomplète. En l'absence de compteurs, les estimations historiques restent identifiées comme telles. L'attribution à une tâche dans le rapport général reste heuristique.

## Essai contrôlé

1. Fixer la tâche, le projet, le commit de départ, le modèle, l'effort de raisonnement et les critères de qualité avant les essais.
2. Utiliser des conversations neuves : une référence sans le contexte DevCore supplémentaire, une avec la fiche courte et les décisions. Les droits, sources disponibles et possibilités d'exécuter des tests doivent être identiques. La collecte initiale de contexte fait partie du coût de la seconde condition.
3. Garder les mêmes limites d'exécution. Pour cette première mesure, éviter la délégation : les rollouts des agents enfants ont des compteurs distincts et ne sont pas agrégés par l'outil.
4. Évaluer chaque résultat avec les mêmes critères : tests pertinents, respect des décisions en vigueur, exactitude et absence de données étrangères. Conserver les artefacts de vérification. Ne déclarer un résultat accepté qu'après cette revue.
5. Copier les deux rollouts terminés dans un dossier de recette hors données actives. Ne pas comparer une conversation encore en cours.
6. Répéter sur plusieurs tâches et plusieurs essais, puis présenter les résultats par tâche et leur dispersion. Une seule paire ne démontre pas un gain général.

## Outil hors ligne

`DEV_CORE/Scripts/compare_codex_usage.py` lit uniquement les fichiers explicitement sélectionnés et écrit son résultat sur stdout. Il ne découvre pas les conversations du poste, n'ouvre pas SQLite et ne lance aucun modèle.

Créer `experiment.json` dans le dossier de recette avec ce format. Les valeurs ci-dessous décrivent une structure, pas des résultats réalisés :

```json
{
  "schema_version": 1,
  "runs": [
    {
      "condition": "baseline",
      "rollout": "baseline.jsonl",
      "project_id": "devcore",
      "task_id": "TASK-EXPERIMENT",
      "git_commit": "COMMIT_DE_DEPART",
      "model": "MODELE_OBSERVE",
      "reasoning_effort": "EFFORT_IDENTIQUE",
      "completed": true,
      "quality_checks": {"tests_pass": true, "decisions_respected": true}
    },
    {
      "condition": "context",
      "rollout": "context.jsonl",
      "project_id": "devcore",
      "task_id": "TASK-EXPERIMENT",
      "git_commit": "COMMIT_DE_DEPART",
      "model": "MODELE_OBSERVE",
      "reasoning_effort": "EFFORT_IDENTIQUE",
      "completed": true,
      "quality_checks": {"tests_pass": true, "decisions_respected": true}
    }
  ]
}
```

```powershell
& E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe `
  E:\src_python\devcore\DEV_CORE\Scripts\compare_codex_usage.py `
  E:\DevCoreRuntime\qualification\tokens\experiment.json
```

L'outil contrôle les identités de conversation distinctes, les compteurs, le modèle observé et la cohérence des conditions déclarées. Il fournit les empreintes SHA-256 des sources. Il retourne `inconclusive` sans pourcentage de gain en cas d'anomalie, d'échec qualité déclaré ou de conditions divergentes. Un pourcentage négatif signifie une augmentation de tokens.

Le projet, la tâche, le commit, l'effort et l'acceptation qualité sont déclarés dans le manifeste ; leur preuve reste à vérifier dans les artefacts. Une égalité de champs ne suffit pas à prouver que l'expérience a été exécutée correctement. La comparaison ne couvre pas les appels externes de RepoWise ou les agents enfants ; ces consommations devront être ajoutées au bilan global si ces fonctionnalités sont utilisées.

## Suite du plan

- Vérifier l'intégration réellement utilisée dans une conversation Codex neuve ; ne pas déduire son fonctionnement de la seule présence de `.mcp.json`.
- Construire la fiche projet versionnée et le registre des décisions, avec provenance, remplacement et validation.
- Raccorder une reprise bornée par budget, isolée par projet et droits, puis appliquer ce protocole.
- L'économie réelle reste non démontrée tant que ces essais n'ont pas été réalisés et revus.

Référence de distinction entre usage enregistré et usage absent : [documentation officielle OpenAI sur l'observabilité](https://developers.openai.com/api/docs/guides/agents-api/observability). La prise en charge du format de rollout local repose sur l'observation du poste, indépendamment du contrat de cette API.
