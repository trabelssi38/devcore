# Administration d'instance — recette locale

Implémentation sur magasin SQLite de recette ; aucune activation sur le magasin
ou les services actuels. [Fichiers de secrets NTFS qualifiés](secrets-ntfs-2026-10-03.md)
sur fixtures ; [création privée du magasin NTFS](magasin-identite-ntfs-2026-10-03.md)
ajoutée sur recette. PostgreSQL, activation du magasin/compte de service et vraie console Windows
restent à qualifier avant l'exploitation en équipe.

## Rôles et périmètres

| Capacité actuelle | Lecteur de projet | Contributeur | Responsable de projet | Administrateur d'instance |
| --- | --- | --- | --- | --- |
| Lire les tâches du projet | oui | oui | oui | seulement avec appartenance et jeton/session de projet |
| Lire fiche/décisions du projet (`context.read`) | oui | oui | oui | seulement avec appartenance et jeton/session de projet |
| Lire l'audit qualifié des tâches (`task.audit.read`) | non | non | oui | seulement avec appartenance et jeton/session de projet |
| Modifier les tâches du projet | non | oui | oui | seulement avec appartenance et jeton/session de projet |
| Gérer comptes, appartenances, mots de passe et jetons | non | non | non | jeton administratif individuel |
| Attribuer/retirer le rôle d'administrateur | non | non | non | jeton administratif individuel |
| Initialiser le premier administrateur | non | non | non | opérateur OS local, une seule fois |

Cette matrice porte sur les actions effectivement implémentées. Le responsable
et le contributeur ont actuellement les mêmes actions de tâches ; aucun droit
de gestion des utilisateurs n'est déduit du rôle owner. Le rôle d'instance ne
donne pas implicitement accès aux données des projets. Un jeton de projet ne
peut pas gérer les identités ; un jeton administratif n'est accepté ni par les
routes de tâches ni par l'échange de sessions de projet.

## Préparation explicite sur un magasin de recette

Les commandes ci-dessous sont un protocole opérateur, pas des commandes
exécutées sur les données actives pendant cette implémentation. Choisir une
racine locale de recette et deux nouveaux répertoires vides séparés pour le
magasin et les jetons, hors Git et Dropbox.

```powershell
$adminPython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$adminCli = 'E:/src_python/devcore/DEV_CORE/Scripts/manage_local_identity.py'
$adminStoreDirectory = '<nouveau-répertoire-absolu-local-de-recette-pour-identité>'
$adminStore = Join-Path $adminStoreDirectory 'identity.db'
$adminSecretDirectory = '<nouveau-répertoire-absolu-local-de-recette>'
$adminSecret = Join-Path $adminSecretDirectory 'admin-credential.json'
New-Item -ItemType Directory -Path $adminSecretDirectory
New-Item -ItemType Directory -Path $adminStoreDirectory -ErrorAction Stop
& $adminPython $adminCli --store $adminStore protect-secret-dir --directory $adminSecretDirectory
# Pour la recette uniquement, tant qu'Argon2 n'est pas installé dans le runtime :
$env:PYTHONPATH = 'E:/DevCoreRuntime/recipes/devcore-auth-py313-20261003/packages'

& $adminPython $adminCli --store $adminStore init-private-store
if ($LASTEXITCODE -ne 0) { throw 'Création privée refusée : arrêter la recette' }
& $adminPython $adminCli --store $adminStore upgrade-sessions
& $adminPython $adminCli --store $adminStore upgrade-passwords
& $adminPython $adminCli --store $adminStore add-user --user alice
& $adminPython $adminCli --store $adminStore set-password --user alice
# La saisie du secret et sa confirmation sont masquées, sans argument secret.
& $adminPython $adminCli --store $adminStore upgrade-admin
& $adminPython $adminCli --store $adminStore bootstrap-admin --user alice --confirm-local-bootstrap
& $adminPython $adminCli --store $adminStore login-admin --user alice --output $adminSecret
& $adminPython $adminCli --store $adminStore check-store-protection
```

L'utilisateur initial doit être activé et posséder un mot de passe avant le
passage v3→v4 et le bootstrap. Les migrations sont explicites et idempotentes,
préservent comptes/appartenances/jetons/cookies et n'assignent aucun rôle.
Le bootstrap exige une console interactive et le drapeau explicite ; son
marqueur persistant interdit de le rejouer. Il n'existe pas de bootstrap HTTP.
Son entrée d'audit porte le marqueur `local-operator` : l'identité OS précise
de cet opérateur n'est pas encore attestée dans ce journal.

La connexion administrative réutilise Argon2id, les deux places de
vérification et le compteur/délai d'échecs du compte. Après vérification, le
secret, le compte et le rôle d'instance sont revérifiés dans la transaction.
Elle délivre un jeton distinct de ceux des projets : durée 900 secondes par
défaut, intervalle permis 60..3600 secondes, empreinte SHA-256 en base. Après
expiration, l'administrateur se reconnecte avec son mot de passe. Un nouveau
fichier de sortie est requis : un fichier existant n'est jamais écrasé.

## Opérations authentifiées et récupération

Avec le schéma v4, les anciennes commandes de modification du magasin exigent
aussi un fichier de jeton administratif. Les schémas v1–v3 restent le protocole
historique de recette sans authentification de l'opérateur ; ils ne sont pas
annoncés comme un profil d'administration d'équipe.

```powershell
& $adminPython $adminCli --store $adminStore --admin-credential-file $adminSecret add-user --user bob
& $adminPython $adminCli --store $adminStore --admin-credential-file $adminSecret set-password --user bob
& $adminPython $adminCli --store $adminStore --admin-credential-file $adminSecret grant --user bob --project beta --role contributor
& $adminPython $adminCli --store $adminStore --admin-credential-file $adminSecret grant-admin --user bob
# Un second administrateur activé avec mot de passe peut récupérer Alice :
& $adminPython $adminCli --store $adminStore --admin-credential-file '<jeton-administratif-Bob>' reset-password --user alice
```

Autres commandes protégées : enable-user, disable-user, remove-membership,
remove-admin, issue-token, revoke-token et revoke-admin-token. Le secret
administratif est lu depuis un fichier absolu borné à 4 Kio, pas depuis argv.
Le stdout indique uniquement résultat, identifiant de credential et chemin de
sortie ; ni mot de passe ni jeton brut. Les répertoires doivent déjà exister.

La désactivation révoque les jetons administratifs, ceux des projets et leurs
sessions ; une réactivation ne rétablit pas ces anciens accès. Un reset
révoque ces trois catégories pour le compte ciblé, sans modifier son rôle ni
son activation. Le retrait du rôle administratif révoque ses seuls jetons
administratifs. La suppression/désactivation du dernier administrateur activé
est refusée, avec sérialisation transactionnelle des retraits concurrents.
Ce garde-fou ne prouve pas que tous les administrateurs restants connaissent
encore leur mot de passe. Un [canal de récupération locale](recuperation-locale-2026-10-03.md)
est désormais préparé sur magasin NTFS privé : administrateur déjà existant,
console et confirmations de maintenance, propriétaire OS attesté dans l'audit,
reset/réactivation/révocations atomiques. Sa qualification opérationnelle reste ouverte.

## Audit et transactions

Les opérations administratives admises sont journalisées dans identity_audit
dans la même transaction que leur modification. Auteur issu du jeton vérifié,
action, cible, projet éventuel et métadonnées construites explicitement : rôle,
identifiant de credential, portée. Aucun corps de requête, hash de mot de
passe ou secret brut n'est copié. Journal absent/insertion refusée : rollback.
Les refus ne sont pas encore journalisés. L'émission écrit le fichier exclusif
et flush/fsync avant le commit ; un échec géré supprime ce fichier et annule
l'émission. Un arrêt brutal entre écriture et commit peut laisser un fichier
avec un jeton invalide : aucun commit distribué fichier/SQLite n'est annoncé.

## Limites restantes

Pas d'interface d'administration Web, API/MCP d'administration, OIDC ou RLS
PostgreSQL. Les fonctions Python de provisionnement restent un canal interne
de confiance OS, pas une frontière contre un acteur contrôlant le processus
ou les fichiers. Initialisation/migrations locales ne sont pas des opérations
administratives authentifiées. Activation des ACL NTFS, rétention/protection du journal,
vraie saisie console et procédure de secours opérationnelle restent ouvertes.
Les fichiers de secrets sont désormais protégés
et contrôlés par DACL native avant écriture/lecture ; `0600` seul ne suffit pas.
La création privée de la base et le secours OS sont testés sur fixtures ;
leur activation, les parents et les comptes de service restent à qualifier.
Le critère L4 global et celui de l'auteur de chaque mutation restent ouverts.

La [recette de sauvegarde/restauration des identités](sauvegarde-identite-2026-10-03.md)
crée exclusivement une nouvelle destination privée. Après restauration, tous les
comptes sont désactivés et les anciens mots de passe/jetons/cookies invalidés :
récupérer localement un administrateur, puis attribuer de nouveaux secrets aux
autres comptes avant réactivation. Une archive ne doit pas être activée directement.
