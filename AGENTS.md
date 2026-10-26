# Contexte de travail DevCore

## Reprise d'une conversation

Lire d'abord la fiche et les décisions applicables : appeler
`devcore_project_context(project="devcore", budget_bytes=12000)` si cet outil
MCP est disponible. Sinon, utiliser le lecteur local :

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe' `
  DEV_CORE/Scripts/resume_project_context.py `
  --directory docs/project-context --project devcore --budget-bytes 12000
```

La réponse inclut la fiche et les décisions obligatoires du registre structuré,
leur provenance, les omissions et les avertissements de fraîcheur. Le plafond
est mesuré en octets UTF-8, pas en tokens du modèle. Ne pas relire les documents
déjà retournés sans besoin lié à la tâche ; approfondir avec une `query` ciblée.
Si le lecteur est absent, lire `docs/project-context/devcore.md` et
`docs/project-context/decisions.md` en signalant le mode dégradé sans borne
mesurée. Si le budget est insuffisant ou le registre invalide, signaler l'erreur
et ne pas remplacer silencieusement le contexte obligatoire par un extrait.
Vérifier les preuves actuelles avant d'affirmer qu'un service fonctionne ou
qu'un lot est terminé.

Le projet de ce dépôt est `devcore`. Si les outils MCP sont disponibles,
consulter `devcore_task_status` avec `project="devcore"` lorsque la tâche porte
sur l'avancement. Utiliser RepoWise pour une recherche ciblée utile à la tâche ;
contrôler la fraîcheur et confronter les résultats au code. Signaler une
indisponibilité des outils, puis utiliser les sources locales pertinentes.

Approfondir seulement les sections nécessaires du plan
`plans/2026-10-01-devcore-local-multiutilisateur.md` et du journal
`docs/audit-2026-09-30/`. Ne pas charger tous les journaux au démarrage.
La limite de contexte mesurée et le gain effectif de tokens restent à qualifier.

## Modifications et vérification

Préserver les modifications Git existantes. Avant de modifier, relire l'état
Git, le journal pertinent et les tests concernés. Tester avec des racines
`DEVCORE_LOCAL_ROOT` et `DEVCORE_DATA_ROOT` temporaires, définies avant les
imports ou le lancement des sous-processus. Ne jamais utiliser les données
actives, Dropbox ou les index RepoWise réels comme fixtures de test.

L'environnement de recette documenté est Python 3.13, sous
`E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe` ; vérifier
sa présence. Consigner changements, résultats et limites dans le journal.
Une décision remplacée ne doit plus guider l'implémentation ; une proposition
ne constitue pas une qualification opérationnelle.

## Scripts administrateur

Lancer soi-même les scripts PowerShell nécessitant une élévation avec
`Start-Process -FilePath 'C:\Program Files\PowerShell\7\pwsh.exe' -Verb RunAs
-ArgumentList '-NoProfile -File "E:\chemin\script.ps1"' -Wait`.
Ne pas reporter leur lancement sur l'utilisateur ; les éventuelles invites
Windows ou saisies de secrets restent locales dans la fenêtre élevée.
