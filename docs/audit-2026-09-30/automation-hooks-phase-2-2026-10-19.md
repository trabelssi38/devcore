# Hooks de session et Git — candidat de phase 2

Le profil équipe dispose d'un service `PostgresAutomationLifecycle` et de deux
routes authentifiées : `POST /api/v1/automation/hooks` et
`GET /api/v1/automation/hooks?project=...`. Le middleware admet la mutation
sous `task.mutate`, la lecture sous `task.read`; le magasin fixe le projet dans
la transaction PostgreSQL et refuse tout projet non actif ou non racine Git
enregistrée. L'auteur vient du principal admis, jamais du corps HTTP.

Un début de session lit la tâche active et les comptes de tâches du projet,
puis consigne le résultat. Le client `Scripts/team_automation_hook.py` récupère
d'abord la fiche et les décisions via le droit indépendant `context.read`, puis
publie le début de session ; l'URL de contexte retournée par le service permet
aux autres clients de faire cette lecture séparément. La fin exige un début
réussi du même auteur, source et identifiant de session. Elle enregistre les
comptes courants et le nombre de tâches achevées depuis ce début. Ces chiffres
sont lus sur `tasks` : ils ne représentent ni les tokens, ni un temps de
travail, ni une mesure des outils exécutés. Aucun statut de tâche n'est changé.

Le commit est vérifié avec Git dans la racine enregistrée : SHA complet
résoluble comme commit et ancêtre du `HEAD` courant. Le message de commit ne
clôt aucune tâche. L'auteur Git peut différer de l'utilisateur authentifié :
la trace attribue **la soumission** à ce dernier, et le dépôt/commit vérifiés
à Git. L'événement d'outil est une déclaration du client uniquement ; le champ
`verification=client_report_only` interdit de l'interpréter comme preuve que
l'outil a réussi. Les sources `codex`, `claude`, `gemini` et `git` sont également
des déclarations du client authentifié, consignées comme telles.

La phase 3 ajoute, après un commit vérifié sur la route HTTP, une tentative
distincte de soumission du scan Git et de l'indexation RepoWise. Le résultat
du hook et l'admission de chaque job restent séparés dans la réponse ; aucun
succès de job n'est déduit du succès du hook.

Les clés `session:<id>:start/end`, `commit:<sha>` et `tool:<occurrence>` sont
uniques par projet. Un rejeu rend la trace existante sans répéter le travail ;
une soumission d'un autre auteur ou d'une autre source sur la même clé est
refusée. Un échec de vérification reste terminal et visible. Un client qui
veut réessayer après un échec doit employer une nouvelle occurrence qualifiée,
et non maquiller l'ancien résultat.

Le client candidat lit un jeton individuel depuis un fichier absolu, accepte
seulement une origine loopback, refuse les redirections, borne les réponses et
n'imprime jamais le jeton. Exemple non activant :

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe' `
  DEV_CORE/Scripts/team_automation_hook.py `
  --token-file 'E:/chemin/prive/token.txt' --project devcore `
  --hook session_start --source codex --session mon-id-stable
```

Les tests sur un cluster PostgreSQL 17 temporaire couvrent deux projets Git,
deux utilisateurs, RLS, début/fin, rejeu, commit réel, refus d'un faux SHA,
rapport d'outil et API HTTP avec identité limitée à un projet. Les tests du
client vérifient la contrainte loopback, l'ordre contexte/événement, l'absence
du jeton dans la sortie et le refus d'une redirection. Les racines DevCore des
essais sont temporaires. Le résultat exact et les commandes sont au journal
v463.

**Limites opérationnelles :** le DDL de phase 1 n'est pas appliqué à la base
active ; le client n'est installé dans aucun hook Claude/Gemini/Codex/Git et
les anciens points d'entrée individuels SQLite demeurent distincts. Le
Cockpit ne projette pas encore ces événements. Les séquences incomplètes
`running` restent visibles, sans succès inventé ; leur reprise et la
rétention devront être qualifiées à la mise en service. La phase 5 devra
vérifier les droits du fichier de jeton, les profils réels, les autorisations
SQL `SELECT tasks` et la bascule sans coexistence des deux effets.
