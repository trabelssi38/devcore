# Consultation HTTP de l'audit des tâches — recette locale

## Admission

Le profil Cockpit `individual` ajoute `GET /api/project/task-audit`.
Le projet est obligatoire. La capacité `task.audit.read` est distincte de
`task.read`, `task.mutate` et `context.read` : seul le responsable du projet
(`owner`) peut la recevoir. Le contributeur et le lecteur sont refusés.
L'administrateur d'instance doit aussi posséder une appartenance et une
capacité de projet ; son jeton administratif n'accorde aucun accès implicite.

Chaque admission revérifie compte, credential, expiration, révocation,
appartenance et rôle actuels. Les anciens credentials et cookies ne gagnent
pas cette capacité lors d'une promotion. Les nouvelles connexions par mot de
passe d'un responsable prennent les capacités courantes de ce rôle. Un jeton
Bearer limité à l'audit peut consulter directement la route ; son échange en
cookie nécessite également `task.read`. Les règles d'origine des cookies
restent applicables. Le profil historique refuse cette route, même avec un
jeton partagé. Aucun profil ni magasin actif n'a été modifié ou migré.

## Contrat de lecture

Paramètres autorisés : `project`, `limit` (20 par défaut, 1–100), `task_id`
facultatif et `before_id` facultatif. Aucun acteur, chemin, requête SQL ou
scope libre n'est admis. Paramètres invalides : 400 avec code générique
`invalid_audit_arguments`. La lecture SQLite utilise une connexion existante
en `mode=ro`, `query_only=ON`, sans création, réparation ou migration.
Elle s'exécute hors de la boucle asyncio.

Seules les entrées du projet admis, de type tâche et d'action
`task.complete` ou `task.delete`, sont sélectionnées avant décodage du JSON.
Le schéma qualifié est `schema_version=1`, avec association projet/tâche,
auteur, statut et versions cohérents ; la version après vaut celle avant + 1.
UUID canonique, identifiant de tâche ASCII de 1–128 caractères, auteur
imprimable de 1–128 caractères ; les données hors de ces bornes sont refusées.
Une entrée qualifiée invalide ou un magasin indisponible donne 503 générique
`task_audit_unavailable`, sans restitution partielle ni détail de stockage.
Les autres actions historiques ne sont pas exposées ; `supported_actions`
indique explicitement cette couverture limitée.

La réponse contient `success`, `project`, `events`, `supported_actions`,
`has_more` et `next_before_id`. Chaque événement expose seulement :

| Champ | Contenu |
| --- | --- |
| `id` | UUID de l'entrée d'audit |
| `project`, `task_id` | Association au projet et à la tâche |
| `actor`, `action`, `created_at` | Auteur, action et date enregistrés |
| `before`, `after` | Statut et version uniquement |

Le JSON brut des détails, les identifiants de session/trace, les titres et les
champs supplémentaires ne sont pas retournés. Corps compact UTF-8, saut de
ligne compris, limité à **65 536 octets**, avec `Cache-Control: no-store`.
Les en-têtes ne font pas partie de ce plafond ; ce n'est pas un budget tokens.
La place du curseur est réservée avant de mesurer une page tronquée.

Pagination par ordre d'insertion décroissant : `next_before_id` est un UUID
de la dernière entrée incluse. Le serveur retrouve sa position uniquement
dans le même projet et le même filtre de tâche. Un UUID absent, étranger ou
incompatible avec le filtre reçoit la même erreur générique. Les ajouts
ultérieurs ne réapparaissent pas dans les pages suivantes. Ce parcours
n'est pas un snapshot durable : suppression/réécriture de l'audit par un
opérateur ou maintenance peut invalider un curseur.

## Lecteurs CLI/MCP

Le transport partagé dans `devcore_engine/clients` dispose désormais du
lecteur de projection `individual_audit.py`, sans import de stockage serveur.
La commande explicite `dc individual ... audit` admet `--limit`, `--task-id`
et `--before-id`. Le client MCP individuel ajoute `devcore_task_audit` seulement
avec `DEVCORE_MCP_TASK_AUDIT=1` (défaut 0, valeurs autres que 0/1 refusées).
L'audit reste disponible en READ_ONLY=1, indépendamment des mutations ; la
capacité authentifiée du responsable demeure vérifiée côté serveur.
Profil historique et configuration active inchangés. Voir les
[commandes et paramètres](../project-context/README.md#cli-individuelle-explicite).

Lecture distante bornée à plafond + 1 octet, contrôle de toute la page avant
restitution, rejet des clés JSON dupliquées et suppression des champs libres.
Projet/filtre/UUID uniques/auteur/date/statuts/versions et curseur cohérents
requis. Aucun corps d'erreur, secret ou chemin distant retourné. L'API demeure
de confiance ; ce lecteur ne certifie pas une preuve d'audit cryptographique.
Bloc texte MCP compact UTF-8 avec saut de ligne, structuredContent absent ;
même ligne CLI avec code 0 en succès, 2 pour paramètres/cursor invalides,
1 pour autres refus/pannes. Aucun retry, redirect, cookie, proxy hérité ou
repli vers la base locale. Délai socket existant, délai global/cancellation
du thread non qualifiés.

## Qualification et limites

Les tests et leurs traces sont consignés dans
[le journal d'exécution](execution-2026-10-03.md), sections consultation HTTP
et lecteurs CLI/MCP. La suite finale CLI/MCP comporte **162 tests réussis**
dont 48 nouveaux cas d'audit ; le wheel installé est également qualifié.
Ils utilisent uniquement des racines LOCAL/DATA temporaires définies avant
les imports. Le scénario non bloquant vérifie une lecture alpha retenue et
des réponses beta/status disponibles, sans constituer une mesure de charge.

Cette étape expose l'audit des clôtures et suppressions déjà qualifiées ;
elle ne prouve pas l'audit de chaque mutation historique ou de chaque canal.
La page Cockpit individuelle possède désormais une consultation à la demande,
filtre et cursor, affichage de texte inerte et rejet des réponses obsolètes.
Voir [le parcours Cockpit](../project-context/README.md#historique-dans-le-cockpit-individuel).
La [capture sur fixtures](audit-cockpit-2026-10-03.png) montre clôture et suppression
de T-01, auteur alice et versions v1→v2→v3. La fixture n'a pas de fiche projet :
son erreur de contexte reste indépendante de l'historique.
Protection/rétention, journal des lectures/refus, outbox, PostgreSQL,
correction WAL/checkpoints, service Windows et bascule restent ouverts.
L'opérateur OS demeure de confiance : aucune inviolabilité cryptographique,
ACL globale, performance de production ou économie de tokens n'est annoncée.
