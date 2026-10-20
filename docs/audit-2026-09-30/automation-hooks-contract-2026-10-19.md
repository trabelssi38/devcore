# Contrat de preuve des hooks — phase 1

Le profil équipe sépare un **hook déclenché par événement** d'un job temporel.
Les hooks utilisent `automation_hook_events` ; les jobs continuent d'utiliser
`schedules`, `schedule_history` et les runs durables PostgreSQL. Aucune
définition SQLite/JSON/Hermes n'est importée par ce contrat.

## Admission

Le service interne `PostgresAutomationHooks` exige un `Principal` déjà admis
par le contrôle d'identité du serveur : action `task.mutate` pour démarrer ou
terminer, `task.read` pour consulter. Le projet du principal doit être celui
de l'opération ; la transaction fixe `app.current_project_id` et la table
force RLS. Le projet doit être actif, enregistré avec un chemin existant qui
est exactement la racine d'un dépôt Git. Les clients ne peuvent pas créer un
principal à partir d'un simple nom d'utilisateur fourni dans un payload.

## Cycle de vie et idempotence

`start(principal, project, hook, source, idempotency_key, details,
correlation_id)` accepte `session_start`, `session_end`, `git_commit` et
`tool_use`. Le couple `(project_id, idempotency_key)` est unique. Un rejeu du
même auteur, hook et source retourne le même identifiant avec `created=false` ;
une clé reprise avec une origine différente est refusée. Le statut initial
est `running`.

`finish(principal, project, event_id, status, error)` n'accepte que
`succeeded` ou `failed`, par l'auteur initial et depuis `running`. Un second
résultat terminal ne remplace pas le premier. `error` est un code court sans
texte libre ; `details` est borné à 8 192 octets UTF-8 et doit exclure prompts,
secrets et sorties brutes. Le temps de début et de fin est enregistré par
PostgreSQL. Un `running` persistant après interruption reste visible et doit
être qualifié par le consommateur avant toute reprise ; il n'est pas marqué
« réussi » par une simple lecture du Cockpit.

`recent(principal, project, limit)` renvoie au plus 100 résultats, sous le
même RLS. Les dates de dernière réussite et de dernière tentative doivent
être calculées à partir de ces lignes terminales ; une ancienne date n'est
pas une erreur sans fréquence attendue.

## Qualification et activation

Le DDL est dans `DEV_CORE/devcore_engine/persistence/automation_hook_events.sql`.
Il n'a pas été appliqué à la base active. Une recette sur un cluster
PostgreSQL temporaire vérifie la création du schéma, le rôle applicatif sans
`BYPASSRLS`, deux projets Git, deux auteurs, l'isolation, le rejeu et le
résultat terminal après création d'une nouvelle instance du magasin. Les
tests hors ligne vérifient aussi les refus précoces.

La phase 2 raccordera les déclencheurs authentifiés. La phase 4 décidera le
rendu Cockpit à partir de ces résultats. La phase 5 effectuera sauvegarde,
migration et bascule contrôlée ; aucune route utilisateur ne publie encore de
résultat de hook, afin de ne pas créer un voyant vert déclaratif.
