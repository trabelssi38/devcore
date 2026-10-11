# Reprise locale de contexte

`context.json` est la source structurée utilisée par le lecteur : projet,
date de revue, empreinte de la fiche et décisions. `decisions.md` reste une
synthèse lisible ; actualiser les deux lors d'une nouvelle décision.
Les références de sources sont déclarées, pas automatiquement certifiées.

Depuis la racine du dépôt, avec l'interpréteur de recette :

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe' `
  DEV_CORE/Scripts/resume_project_context.py `
  --directory docs/project-context --project devcore `
  --budget-bytes 12000 --query 'worker reprise'
```

La commande n'écrit aucun fichier et ne consulte ni SQLite ni un fournisseur.
Le projet est obligatoire et doit correspondre au manifeste. Chaque autre
projet peut fournir son propre répertoire explicite et son `context.json` ;
l'autorisation d'accès doit être contrôlée par l'adaptateur appelant.
Ce lecteur n'implémente pas les ACL du profil équipe.

## Utilisation par MCP

`devcore_project_context` accepte `project`, `budget_bytes` et une `query`
facultative. Dans le profil historique (`DEVCORE_MCP_AUTH_PROFILE=legacy`,
valeur par défaut), il utilise uniquement `DEVCORE_CONTEXT_ROOT`, chemin absolu
configuré côté serveur ; le client ne peut pas choisir un répertoire.
`DEVCORE_CONTEXT_MAX_BYTES` impose le plafond serveur (12 000 dans ce dépôt),
que le client peut réduire. Le profil de consultation lie le serveur au
projet configuré et refuse les autres projets avant lecture.

L'outil retourne un seul bloc texte JSON compact, mesuré comme la sortie CLI ;
il ne duplique pas le contexte dans `structuredContent`. Les enveloppes du
protocole MCP et les schémas d'outils ne sont pas inclus dans cette mesure.
Le lecteur ne passe pas par les hooks qui pourraient modifier sa réponse
ou écrire des journaux. L'audit des accès authentifiés reste à construire en L4.

### MCP individuel via l'API

Le profil de recette `DEVCORE_MCP_AUTH_PROFILE=individual` expose par défaut
**uniquement** `devcore_project_context`. Il appelle la route HTTP individuelle ci-dessous ;
il n'importe ni les adaptateurs historiques ni leurs hooks, n'ouvre aucune base
métier/identité et n'utilise pas `DEVCORE_CONTEXT_ROOT`. Sans activation des tâches,
leurs outils restent refusés, même avec `DEVCORE_MCP_READ_ONLY=0`.
Les tâches peuvent être ajoutées explicitement comme décrit ci-dessous.
Le projet configuré doit être explicitement demandé ; l'API contrôle aussi les
droits du credential, indépendamment de cette liaison locale.

Configuration séparée :
[`mcp-individual.example.toml`](../../DEV_CORE/Config/mcp-individual.example.toml).
`DEVCORE_MCP_API_URL` exige une origine explicite sans chemin, userinfo, query ou
fragment. HTTP limité à 127.0.0.1, localhost ou ::1 ; ailleurs HTTPS avec la
vérification TLS standard Python. Aucun proxy hérité, cookie, redirection, retry
ou repli local. L'API et sa configuration d'identité doivent être de confiance ;
le profil actif de ce dépôt demeure historique tant que la recette n'est pas
activée. Un profil inconnu ou une configuration invalide arrête le démarrage.

`DEVCORE_MCP_CREDENTIAL_FILE` désigne un fichier JSON privé créé par
`manage_local_identity.py issue-token --action context.read` pour le projet
voulu. Provisionnement administratif et NTFS existants requis ; aucun secret
dans TOML, arguments MCP, ligne de commande ou valeur d'environnement. Le client
contrôle chemin/ACL NTFS puis lit au plus 4 097 octets et refuse au-delà de 4 096.
Contrôle et lecture répétés à chaque appel : rotation possible, aucune copie en
cache. Les jetons de tâches ne gagnent pas context.read. L'API revérifie état du
compte, appartenance, scope, expiration et révocation à chaque admission.
Protection de ce client qualifiée sous Windows NTFS ; autres OS refusés.
Le contrôle ACL est ponctuel, les acteurs possédant le compte OS restent de confiance.

Plafond client `DEVCORE_CONTEXT_MAX_BYTES` : 12 000 par défaut, 256–65 536 ; budget
explicite transmis à l'API, qui peut imposer un plafond inférieur et le refuser.
Lecture HTTP bornée à budget+1, réponse JSON canonique, mesure complète, projet,
décisions/provenance/omissions/fraîcheur contrôlés avant retour. Le bloc texte
unique préserve la ligne mesurée, sans structuredContent dupliqué. Refus HTTP
401/403/413/422/503 traduits en codes MCP ; corps d'erreur distant, chemins et
secrets non retransmis. Aucun contexte partiel ou ancien résultat substitué.
Les erreurs ne constituent pas un contexte mesuré. Le timeout socket
`DEVCORE_MCP_API_TIMEOUT_SECONDS` vaut 10 secondes (1–30), distinct du contrôle
NTFS pouvant attendre 15 secondes ; ce n'est pas un délai global strict et une
annulation MCP n'arrête pas forcément le thread. Exécution hors boucle asyncio.

Recette en vrais sous-processus stdio et API HTTP temporaire ; activation réelle,
HTTPS/réseau distant, délais globaux, audit de consultation, autres outils MCP
et injection automatique des clients IA encore ouverts.

### Tâches MCP individuelles, sur activation explicite

`DEVCORE_MCP_TASK_ACCESS=disabled` (défaut) conserve le contexte seul ; `read`
ajoute `devcore_task_status`, `write` ajoute aussi `devcore_task_done`.
`DEVCORE_MCP_TASK_DELETE=1` ajoute séparément `devcore_task_delete` seulement
avec write ; défaut 0, toute autre valeur refusée au démarrage. Le profil
read/READ_ONLY=1 ferme également la suppression avant lecture du credential.
Valeur inconnue : démarrage refusé. `DEVCORE_MCP_READ_ONLY=1` ramène write à read,
avec refus de clôture avant ouverture du fichier de credential. Ces choix
annoncent les outils exposés, pas les capacités réelles du credential : l'API
contrôle `task.read` pour la liste et `task.mutate` pour la clôture à chaque appel.
Rôle lecteur, retrait/déclassement, révocation et projet étranger sont refusés
côté serveur. Un jeton de tâches ne reçoit toujours pas context.read implicitement.

`DEVCORE_MCP_TASK_AUDIT=1` ajoute séparément `devcore_task_audit`, même si
TASK_ACCESS=disabled ou READ_ONLY=1. Défaut 0 ; toute autre valeur refuse le
démarrage. Ce choix ne donne aucun droit serveur : un credential avec
`task.audit.read` et le rôle responsable du projet sont requis. Aucun outil
d'audit ajouté au profil historique. L'outil appelle uniquement la route HTTP
décrite ci-dessous, avec projet explicite, limit 1–100, task_id et before_id
facultatifs. Un credential limité à l'audit n'accorde pas la lecture des tâches
ou du contexte. L'exemple TOML garde l'audit désactivé ; sa recette nécessite
aussi d'ajouter devcore_task_audit à enabled_tools.

Exemple de consultation :
[`mcp-individual-tasks.example.toml`](../../DEV_CORE/Config/mcp-individual-tasks.example.toml).
Les anciens outils de contrôle global, sync, émission arbitraire d'événement,
lancement restent fermés. Aucun changement de configuration active.

`devcore_task_delete(project, task_id, expected_version)` appelle
`DELETE /api/delete` avec une tâche nommée et la version observée. L'API exige
task.mutate, valide le principal/projet et conserve identité/historique par
suppression logique (statut deleted), avec audit dans la transaction. Une
dépendance active refuse la suppression ; version ancienne : conflit ; déjà
supprimée/absente : 404. Aucune sélection implicite ni retry. Comme pour la
clôture, le succès est un accusé avec refresh_required, sans nouvelle version
inventée ; une réponse perdue, invalide ou une erreur serveur rend le résultat
incertain. Relire les tâches avant une nouvelle action, sans déduire un auteur
ou une preuve d'audit depuis la seule absence dans une page. La consultation
de l'audit est disponible via la commande CLI audit et l'outil MCP explicite
décrits ci-dessous. Publication durable des événements ouverte.

`devcore_task_status(project, limit=20, offset=0)` appelle la liste HTTP de
tâches du projet. Limit 1–100, offset positif ou nul, réponse distante limitée
à 128 Kio. Toutes les lignes sont contrôlées avant retour ; identifiants uniques,
projet concordant, statuts/versions valides. Champs retournés : id, project,
title, status, version ; données supplémentaires abandonnées. Une ancienne base
sans version peut être lue (version null) mais la clôture conditionnelle exige
une version. `page_may_have_more` signifie seulement que la page est pleine,
pas qu'un total global a été calculé. Réponses invalides/trop grosses/étrangères
refusées entièrement. Aucun parcours de toutes les pages ni tâche choisie implicitement.

`devcore_task_done(project, task_id, expected_version)` appelle POST /api/done
avec seulement ces trois valeurs (task_id devient id). Identifiant explicite
et entier positif borné requis ; actor, token et autres champs sont refusés
avant lecture du secret. Auteur/trace de l'audit viennent de l'admission API.
Conflit 409 : code métier conservé si reconnu (stale_task_version ou
task_version_unavailable), message distant supprimé. Aucun retry ou passage
automatique à la tâche suivante. Écriture et audit atomiques déjà assurés par
ce parcours HTTP ; la publication durable d'événements reste à qualifier.

Succès HTTP : **accusé de réception** avec requested_task_id, expected_version,
acknowledged et refresh_required. Cette route ne retourne pas la ligne/version
committée : elles ne sont pas inventées. Relire la page après la clôture.
Transport interrompu, réponse invalide, redirection ou erreur serveur :
mutation_outcome_unknown et refresh_required, même si l'écriture a déjà abouti.
Réconcilier par une lecture autorisée avant toute nouvelle action ; aucun
ancien résultat ni succès supposé. Bloc JSON texte unique pour chaque outil
individuel, sans duplication structuredContent. La limite de 128 Kio concerne
la réception HTTP des tâches, pas une mesure de tokens ni du protocole MCP.

Recette seulement : vrais MCP stdio/API temporaires, projets et audit concurrents,
conflits sur une même version, réponse perdue après commit et absence de retry.
Les commandes CLI historiques, autres opérations, délais globaux, service/HTTPS
et bascule restent ouverts ; client CLI explicite décrit ci-dessous.

### CLI individuelle explicite

`DEV_CORE/Scripts/individual_project_client.py` délègue au module empaqueté
`devcore_engine.clients.individual_cli`, qui utilise les mêmes clients dans
`devcore_engine/clients` que MCP. Les anciens modules MCP réexportent ces classes
pour compatibilité. Aucun import de mcp, FastAPI, adaptateurs/hooks historiques
ou base locale dans cette commande ; pas de découverte d'instance/projet/secret.
URL API, chemin absolu du fichier privé et projet sont obligatoires. Le lecteur
local `resume_project_context.py` reste un outil OS de confiance distinct.

Depuis la racine du dépôt, après provisionnement d'une API individuelle et
d'un credential protégé de recette (remplacer les placeholders) :

```powershell
$individualPython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$individualClient = 'E:/src_python/devcore/DEV_CORE/Scripts/individual_project_client.py'
$individualCredential = 'E:/DevCoreSecrets/Users/UTILISATEUR/project.json'

# Credential avec context.read pour PROJET ; plafond par défaut 12 000 octets.
& $individualPython $individualClient --api-url http://127.0.0.1:20129 `
  --credential-file $individualCredential --project PROJET context `
  --budget-bytes 12000 --query 'worker'

# Credential avec task.read ; une page seulement, version observée retournée.
& $individualPython $individualClient --api-url http://127.0.0.1:20129 `
  --credential-file $individualCredential --project PROJET tasks --limit 20 --offset 0

# Credential avec task.mutate ; copier tâche/version de la lecture précédente.
& $individualPython $individualClient --api-url http://127.0.0.1:20129 `
  --credential-file $individualCredential --project PROJET done `
  --task-id TACHE --expected-version VERSION_OBSERVEE

# Credential task.mutate ; suppression logique, même version observée obligatoire.
& $individualPython $individualClient --api-url http://127.0.0.1:20129 `
  --credential-file $individualCredential --project PROJET delete `
  --task-id TACHE --expected-version VERSION_OBSERVEE

# Credential task.audit.read du responsable ; une page, pas d'accès à une base locale.
& $individualPython $individualClient --api-url http://127.0.0.1:20129 `
  --credential-file $individualCredential --project PROJET audit --limit 20 --task-id TACHE
# Page suivante : même projet et filtre ; UUID reçu dans next_before_id.
& $individualPython $individualClient --api-url http://127.0.0.1:20129 `
  --credential-file $individualCredential --project PROJET audit --task-id TACHE `
  --before-id UUID_RECU
```

`--context-max-bytes` fixe le plafond client (12 000 par défaut) ;
`--timeout-seconds` fixe le timeout socket (10 s par défaut), tous deux avant
la sous-commande. Les conditions NTFS/URL/TLS/redirect/proxy/budget/scopes et
résultat incertain du client MCP s'appliquent. Chaque commande explicite active
seulement son opération côté client ; l'API garde l'autorité sur les droits.
Les variables MCP d'exposition d'outils ne sont pas une autorisation CLI.

Stdout : une ligne JSON UTF-8, pas de journal/secret ; corps de contexte conservé
avec sa mesure exacte. Erreur de parsing/configuration : code de sortie **2**,
erreur API/permission/conflit/budget ou résultat incertain : **1**, succès **0**.
Les erreurs sont génériques sans reprise des valeurs d'arguments/chemins.
--token/--password ne sont pas des arguments acceptés ; credential seulement
dans un fichier protégé. Aucune configuration active ni données locales adoptées.
Après done/delete, relire tasks ; ni version inventée ni retry après timeout.

La commande explicite est également accessible par `dc individual` dans un wheel
actualisé, `python -m devcore_engine.cli individual` et
`python -m devcore_engine individual` si le package actualisé est importable.
Les sources `Scripts/dc.py` et `Scripts/dc.ps1` prennent aussi `individual` en
premier argument, avec les mêmes options et codes de sortie. Exemple sur sources :

```powershell
& $individualPython 'E:/src_python/devcore/DEV_CORE/Scripts/dc.py' individual `
  --api-url http://127.0.0.1:20129 --credential-file $individualCredential `
  --project PROJET tasks --limit 20

$env:DEVCORE_PYTHON = $individualPython
& 'E:/src_python/devcore/DEV_CORE/Scripts/dc.ps1' individual `
  --api-url http://127.0.0.1:20129 --credential-file $individualCredential `
  --project PROJET context --budget-bytes 12000
```

Ce parcours est admis avant les imports des services locaux et migrations. La
branche PowerShell utilise le script voisin et le Python sélectionné, sans
charger le bootstrap historique de plateforme/Dropbox. Elle restitue la sortie
UTF-8 et le code du client. Aucune instance/projet/credential implicite.

Recette en subprocess, dont Python -I -S sans paquets MCP/FastAPI, API locale
temporaire, équivalence CLI/MCP pour page et conflit, et réponse perdue après
commit. Les autres commandes historiques et wrappers de tâches restent des
parcours locaux ; le runtime actif, l'injection d'une conversation IA et la
bascule réelle restent à qualifier.

Le test de la console installée nécessite l'outil de construction séparé
`DEV_CORE/requirements-build-test.lock` (version et empreinte figées), installé
dans un target temporaire et désigné par `DEVCORE_TEST_BUILD_TOOLS`. Le runtime
de recette n'a pas besoin de pip/setuptools : le test utilise le backend de
construction de ce target, puis ensurepip uniquement dans son venv temporaire.
La CI provisionne ce target avant les tests ; l'installation du wheel utilise
`--no-index --no-deps`, sans réutiliser les sources via PYTHONPATH. Aucune
dépendance serveur n'est ajoutée à cette installation de qualification.

## Consultation HTTP individuelle

Le profil Cockpit de recette `individual` expose désormais
`GET /api/project/context?project=alpha&budget_bytes=12000&query=worker`.
Il exige un Bearer individuel ayant **explicitement** `context.read` pour ce
projet, ou une session de projet par cookie possédant cette capacité. Les
appartenances, état du compte, révocation et expiration sont revérifiés à
l'admission de chaque requête. Un jeton administratif d'instance ne donne pas
ce droit. Les rôles lecteur/contributeur/responsable permettent cette lecture.

Les anciens jetons limités aux tâches et leurs cookies ne gagnent pas de
capacité. Les nouvelles connexions par mot de passe prennent les capacités
courantes du rôle, dont `context.read` ; les anciennes sessions restent limitées
par les actions de leur credential source. L'échange Bearer→cookie continue
d'exiger `task.read` ; un jeton limité au seul contexte s'utilise directement
en Bearer, sans Origin navigateur. Les contrôles d'origine existants s'appliquent
aux cookies ; aucune mutation n'est exposée par cette route.

Le serveur consulte en lecture seule le projet enregistré dans `projects`,
puis **uniquement** `<root_path>/docs/project-context`. La racine doit être
absolue/existante ; répertoire résolu et fichiers doivent rester dans leur
périmètre. Aucun paramètre client ne choisit une racine ; aucun repli vers la
fiche globale DevCore ou les anciennes collections mémoire n'existe. Une fiche
absente/invalide, un manifeste d'un autre projet, une racine relative ou une
base absente donnent 503 sans chemin ni contenu étranger. La base n'est ni
créée ni migrée par ce lecteur. Les racines enregistrées et leurs auteurs
restent de confiance : ce contrôle de chemins n'est pas une sandbox contre
un acteur OS modifiant les jonctions/fichiers pendant une lecture.

`DEVCORE_HTTP_CONTEXT_MAX_BYTES` fixe le plafond serveur (12 000 par défaut,
256–65 536 autorisés au démarrage). Un budget omis utilise ce plafond ; un budget
supérieur ou une query de plus de 4 096 caractères donne 422. Le corps de succès
est exactement la ligne JSON UTF-8 mesurée, avec saut de ligne ; en-têtes et
enveloppes sont exclus. Budget insuffisant pour les éléments obligatoires :
413, sans contexte partiel. Réponse `no-store`, avertissements/provenance et
omissions conservés. La lecture synchrone est exécutée dans le pool FastAPI.

Qualification HTTP sur racines temporaires seulement ; route non activée sur
l'instance courante, injection automatique des autres
clients et recherche mémoire globale encore ouverts. Le contexte MCP personnel
dispose du profil de recette décrit ci-dessus ; autres outils et activation ouverts.

### Page individuelle `/project`

Après connexion ou reprise de session, la page charge automatiquement la fiche
et les décisions obligatoires si la session possède `context.read`. Les anciens
cookies limités aux tâches continuent de consulter les tâches sans appeler le
contexte. Le formulaire « Approfondir » charge les décisions facultatives liées
au sujet ; les propositions gardent ce statut, les décisions remplacées restent
exclues. Justification, validation, sources déclarées, date et diagnostics sont
affichés en texte, sans interpréter le Markdown/HTML ni ouvrir les sources.

Le chargement du contexte est indépendant de celui des tâches : une lecture
lente ne désactive pas leurs actions. La page valide le projet, le registre
retourné, la provenance et la longueur UTF-8 exacte du corps reçu. Budget/source
indisponible : contexte précédent effacé, tâches conservées. Refus d'identité :
session affichée et toutes ses données effacées. Rafraîchissement, déconnexion
et changement de compte annulent les requêtes précédentes ; une réponse tardive
ne repeuple pas un autre projet. Aucun cache localStorage/sessionStorage n'est
créé. Les cookies restent contrôlés par le serveur ; le navigateur ne reçoit
aucun Bearer par ce parcours.

Scénarios Node et parcours dans un navigateur sur fixtures qualifiés ; ce
chargement dans le Cockpit ne constitue pas une injection dans une conversation
IA. Le budget est toujours en octets, pas en tokens. Deux profils indépendants,
interactions cross-site/HTTPS, ACL des autres clients et activation restent ouverts.

### Consultation HTTP de l'audit des tâches

`GET /api/project/task-audit?project=<projet>&limit=20` exige `task.audit.read`,
réservé au responsable (`owner`) du projet. Anciens jetons/cookies inchangés ;
nouvelles connexions par mot de passe du responsable suivant ses capacités.
Rôle, appartenance et révocation revérifiés à chaque admission. Un jeton
administratif d'instance n'accorde pas cette lecture. Profil historique refusé.

Lecture seule des actions qualifiées `task.complete` et `task.delete`, avec
auteur, identité et statuts/versions avant/après ; aucun détail brut, titre,
trace ou session. `task_id` filtre facultatif ; `before_id` est le curseur UUID
du précédent `next_before_id`. Limit 1–100 ; réponse UTF-8 de 65 536 octets
maximum, pagination bornée et no-store. Erreurs de curseur génériques ; audit
qualifié invalide : 503 sans page partielle ni réparation du magasin.
Voir [le contrat et ses limites](../audit-2026-09-30/consultation-audit-2026-10-03.md).
Le client CLI/MCP partagé lit au plus 65 537 octets et refuse le dépassement.
Toutes les lignes sont contrôlées avant retour : projet/filtre concordants,
UUID uniques, acteur, date, statuts et versions cohérents, curseur égal à la
dernière entrée lorsque has_more est vrai. Clés JSON dupliquées refusées ;
champs supplémentaires supprimés. Une page malformée ne produit aucun extrait.
MCP retourne un bloc texte JSON compact avec saut de ligne, sans duplication
structuredContent ; CLI produit la même ligne. Refus, credential invalide,
réponse distante incorrecte ou panne : erreur générique, sans détail distant,
retry, redirection, proxy ou repli SQLite. Cursor refusé : invalid_arguments,
code CLI 2 ; autre refus/panne : code 1. Le délai socket reste distinct d'un
délai global strict et une annulation peut laisser le thread de lecture finir.
### Historique dans le Cockpit individuel

La page `/project` propose « Historique des modifications » aux sessions
possédant `task.audit.read`. Chargement à la demande, filtre facultatif par
identifiant de tâche et bouton « Modifications plus anciennes » utilisant le
curseur de la dernière page. Changer le champ ne modifie pas le filtre de la
page suivante : soumettre le formulaire recommence la sélection.
L'historique affiche date enregistrée, tâche, auteur et statuts/versions
avant/après. Le texte est inerte ; aucun HTML, lien ou détail libre interprété.

Chargement indépendant des tâches et du contexte, sans Bearer ni cache local.
Actualisation des tâches, mutation, déconnexion ou changement de session
annulent/ignorent les réponses anciennes et effacent la page d'audit.
Refus 401/403 : toutes les données de session effacées ; erreur de curseur,
source invalide ou indisponibilité : historique vide et tâches conservées.
Les versions hors plage entière sûre JavaScript sont refusées, sans arrondi.
Toute la page est validée avant affichage, avec plafond UTF-8 de 65 536 octets.
Le flux Fetch moderne est arrêté au dépassement ; fallback sans ReadableStream
mesuré après réception. Ce contrôle n'est pas un budget de mémoire total.
Qualification Node/HTTP et navigateur sur fixtures seulement ; audit des
lectures, deux profils indépendants, HTTPS et activation encore ouverts.

## Contrat du budget

Le budget porte sur toute la ligne JSON retournée, saut de ligne compris,
mesurée en **octets UTF-8**. Les octets ne sont pas des tokens du modèle.
L'environnement de recette ne contient pas de tokenizer ; le raccordement
d'un comptage adapté au fournisseur reste à qualifier. Les schémas d'outils,
instructions client et échanges ultérieurs ne sont pas inclus dans ce budget.

La fiche et les décisions obligatoires en vigueur sont indivisibles. Si elles
dépassent le budget, le lecteur CLI local échoue avec code 2 et sans contexte sur stdout.
Les décisions facultatives sont sélectionnées par correspondance de mots avec
leurs tags, puis admises si le budget le permet. Les décisions proposées
gardent ce statut. Les décisions remplacées sont exclues, avec leurs identifiants
signalés ; une chaîne de remplacement doit aboutir à une décision en vigueur.

`omitted` explique les exclusions par pertinence ou budget. `warnings` signale
une fiche modifiée depuis sa revue, une revue de plus de sept jours ou datée
dans le futur. Ces avertissements n'inventent pas de validation opérationnelle.
Après revue d'une fiche modifiée, mettre à jour sa date et son SHA-256 dans le
manifeste. Les chemins sortant du répertoire, y compris par lien symbolique,
sont refusés ; chaque fichier est limité à 256 Kio.

## Raccordement restant

Le lecteur est disponible en CLI, service Python et MCP ; `AGENTS.md` demande
son utilisation lors de la reprise dans Codex, avec repli CLI si MCP absent.
L'activation HTTP et le raccordement aux hooks des autres clients, le compteur de tokens, la validation dans une
conversation neuve et l'expérimentation comparative restent ouverts. Aucun
gain de tokens ni critère de sortie L7 complet n'est revendiqué.
