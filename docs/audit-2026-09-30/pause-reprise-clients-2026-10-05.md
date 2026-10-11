# Pause et reprise individuelles — sources de recette du 5 octobre

## Contrat

`POST /api/pause` et `/api/resume` exigent `project`, `id`, `expected_version`.
Le serveur authentifie l'utilisateur et vérifie `task.mutate` dans ce projet.
Cookie : origine et CSRF obligatoires. Version obsolète ou état incompatible : 409.
Aucun auteur n'est fourni par le client. Tâche/version/audit/événement sont atomiques.
Le succès confirme la réception ; il faut relire l'état, sans déduire une version.
Une erreur de transport ne justifie pas de répéter automatiquement l'écriture.

## Cockpit

Dans la page individuelle, Pause apparaît pour une tâche `in_progress`,
Reprendre pour une tâche `paused`, seulement avec droit de modification.
La version vient de la ligne affichée ; une version indisponible désactive le bouton.
Les conflits provoquent une actualisation sans répéter la mutation.
L'historique reconnaît les quatre actions : clôture, suppression, pause, reprise.
Les versions avancent d'une unité et les transitions pause/reprise sont contrôlées.

## CLI

Les commandes explicites sont `dc individual ... pause` et `resume`.
Exemple à adapter après provisionnement d'un credential privé :

```powershell
dc individual --api-url http://127.0.0.1:20129 `
  --credential-file E:/DevCoreSecrets/Users/UTILISATEUR/tasks.json `
  --project devcore pause --task-id T-XX --expected-version VERSION_OBSERVEE
```

`VERSION_OBSERVEE` est à remplacer par la version lue via `tasks` ; l'exemple
n'est pas exécutable tel quel. La CLI ne consulte pas de base métier locale.

## MCP

Les outils `devcore_task_pause` et `devcore_task_resume` sont exposés seulement si
`DEVCORE_MCP_TASK_ACCESS=write`, `DEVCORE_MCP_TASK_TRANSITIONS=1` et le mode lecture
seule est désactivé. Le défaut reste 0 ; les exemples TOML ne les activent pas.
Il faut aussi les autoriser dans `enabled_tools`. Les flags n'accordent aucun droit
serveur et ne remplacent pas le credential limité à l'utilisateur/projet/actions.
Chaque appel nomme projet, tâche et version attendue ; aucune sélection implicite.

## Limites

Ces changements concernent les sources. Aucun service actif, configuration Codex
personnelle, wheel ou snapshot déjà préparé n'est mis à jour automatiquement.
L'activation et la requalification des bundles restent à faire. Recettes et résultats
sont consignés dans `execution-2026-10-05.md` ; aucune borne de charge ou économie
de tokens n'est déduite des succès fonctionnels.

Candidat v155 : le lanceur MCP accepte `--transitions` seulement avec `--tasks write` ;
les variables héritées ne peuvent pas activer cette capacité. Wheel/snapshot
reconstruits et qualification sur fixtures consignés au journal, sans activation.

Recette v156 : deux profils Edge temporaires utilisent le vrai Cockpit et une API
Uvicorn locale sur fixtures. Pause/reprise, confirmations, audit et déconnexion
sont vérifiés ; sessions de recette provisionnées via Bearer puis cookies HttpOnly,
pas connexion par mot de passe ni qualification cross-site. Snapshot v155 ne
contient pas la correction du texte de confirmation ; reconstruction nécessaire.

Recette v157 : `test_individual_browser_transitions.py` couvre les modes cookie
et password. Le second remplit le vrai formulaire, valide Argon2id côté serveur,
puis vérifie fiche/décisions propres au projet au login et après reload complet.
Le champ mot de passe est effacé immédiatement et la requête de login ne porte
pas de Bearer ; profils/données entièrement temporaires. Cela ne qualifie pas
l'injection dans une nouvelle conversation IA ni une économie de tokens.

Qualification v158 : le harnais Edge a été simplifié en une instance headless et
deux BrowserContext CDP isolés. Cela conserve deux magasins de cookies/sessions
distincts sans lancer deux processus Edge gourmands. Modes cookie/password et
deux vues SSE standard/terminal réussissent ensemble (4 tests, 83,58 s). Cette
recette ne prouve pas une séparation de processus ni plusieurs postes.

Recette v159 : un formulaire HTML hostile sur une origine IPv6 loopback `[::1]`
soumet un POST sans jeton ni authorization vers l'API IPv4 `127.0.0.1`, avec
project beta et version1. Le navigateur émet la navigation cross-site, SameSite
Strict n'apporte pas de session utilisable ; le serveur rend401
`individual_credential_required`. Les contrôles SQL confirment beta toujours
in_progress/version1 et sans audit. Test réel Edge/CDP, endpoints fixtures only.
Le serveur hostile écoute exclusivement sur ::1 et s'arrête en finally.

Recette v160 : le même site hostile lance aussi un `fetch` JSON cross-origin
vers `/api/pause`, `credentials: include`, avec `X-CSRF-Token` forgé. Le profil
individuel transmet les prévols OPTIONS au middleware CORS : une origine permise
reçoit200 et ACAO exact ; l'origine hostile reçoit400 et le script observe le
refus CORS. Une sonde ASGI extérieure à l'application confirme que seuls le
POST Pause d'Alice et le formulaire hostile précédent atteignent `/api/pause` :
aucun POST du fetch n'est transmis. CDP émet aussi un événement POST logique
pour cette opération refusée avant le prévol ; l'assertion côté serveur évite
de le prendre pour une requête envoyée. Bob revient ensuite au Cockpit et reste
autorisé ; SQL confirme beta version1 sans audit, alpha version3 et les deux
seuls audits Alice. Les deux variantes cookie/password passent sur racines
temporaires, Edge154 et API/Uvicorn loopback ; CI distante non lancée. L'origine
permise est configurée avant l'import de l'app, pas seulement après l'import.
