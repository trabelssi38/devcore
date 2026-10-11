# Récupération d'un administrateur existant — recette locale

Le canal `recover-local-admin` permet au propriétaire Windows du magasin privé
de rétablir un administrateur existant quand les identifiants applicatifs sont
perdus. Il n'ajoute aucun administrateur, utilisateur ou appartenance projet,
ne rejoue pas le bootstrap et ne délivre aucun jeton. Le service actuel n'a pas
été modifié ni récupéré par ces tests.

## Conditions et transaction

- Magasin v4 déjà bootstrappé, administrateur nommé avec une entrée de mot de
  passe existante ; un lecteur/responsable de projet seul est refusé.
- NTFS local privé : base, parent et sidecars contrôlés par le helper natif ;
  propriétaire SID Windows courant, accès uniquement courant/SYSTEM. Un jeton
  applicatif ne remplace pas cette condition. Les jonctions sont refusées.
- Console interactive, confirmation explicite de récupération et déclaration
  d'arrêt des services utilisant ce magasin. Cette déclaration n'est pas un
  arrêt automatique ni une vérification du superviseur.
- Nouveau mot de passe et confirmation par getpass, sans argument de mot de
  passe, fichier de secret ou variable d'environnement. Prévalidation NTFS et
  de l'administrateur avant toute saisie ; validation répétée avant le hash.

Après le hash Argon2id, une connexion SQLite existante en `mode=rw` prend le
mode de verrouillage EXCLUSIVE **avant tout accès au schéma**, puis une
transaction EXCLUSIVE. Un lecteur ou écrivain déjà en transaction empêche
l'acquisition du verrou, avec attente SQLite bornée à une seconde. Cela est
testé en DELETE et WAL. Aucun changement de mode de journal n'est imposé.

Dans la transaction : permissions et rôle revérifiés, mot de passe remplacé,
compteur/délai de connexion remis à zéro, compte ciblé réactivé, anciens jetons
de projet/administration et cookies du compte révoqués, audit inséré. Le log
porte `admin.recover-local`, auteur `windows:<SID natif>`, cible et activation
précédente ; aucun mot de passe, hash ou jeton. Le SID n'est pas un argument
fourni par l'utilisateur. Échec d'audit : rollback de toutes ces modifications.

Cette opération peut être répétée par l'opérateur Windows de confiance ;
chaque réussite est auditée. Le marqueur de bootstrap reste à 1. Les droits
des projets et les autres comptes ne changent pas. L'utilisateur doit se
reconnecter pour obtenir de nouveaux accès ; une mutation précédemment admise
ou un run déjà lancé n'est pas annulé par la révocation.

## Protocole opérateur sur recette

1. Préparer un magasin de recette avec `init-private-store`, migrations
   explicites v2/v3/v4, mot de passe et bootstrap initial. Voir la
   [procédure d'administration](administration-locale-2026-10-03.md).
2. Arrêter les services utilisant **ce magasin de recette**, vérifier leur
   arrêt, préserver une sauvegarde cohérente privée avec ses permissions.
   Aucune commande automatique de sauvegarde/restauration active n'est proposée.
3. Dans une console Windows du propriétaire NTFS du magasin :

```powershell
$recoveryPython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$recoveryCli = 'E:/src_python/devcore/DEV_CORE/Scripts/manage_local_identity.py'
$recoveryStore = '<chemin-absolu-du-magasin-prive-de-recette>/identity.db'
# Dépendances Argon2 isolées pour cette recette, pas installation dans le runtime :
$env:PYTHONPATH = 'E:/DevCoreRuntime/recipes/devcore-auth-py313-20261003/packages'
& $recoveryPython $recoveryCli --store $recoveryStore recover-local-admin --user alice `
    --confirm-local-recovery --confirm-services-stopped
if ($LASTEXITCODE -ne 0) { throw 'Récupération refusée : conserver la recette pour inspection' }
```

4. Contrôler l'audit, puis tester une nouvelle connexion et le refus des anciens
   accès avant de relancer les services de recette. Le stdout indique seulement
   utilisateur, SID et nécessité de reconnexion. Aucun mot de passe ou jeton
   n'est imprimé. Aucune route HTTP/MCP de récupération n'est ajoutée.

## Limites et qualification opérationnelle

La frontière de confiance reste le propriétaire Windows/SYSTEM/administrateurs
OS et les fichiers du programme. Le SDK interne n'est pas une sandbox contre
un acteur contrôlant le processus ou les fichiers. Le contrôle des ACL reste
un instantané ; droits des ancêtres, second compte Windows et identité d'un
compte de service distinct restent à qualifier. L'audit du bootstrap historique
reste `local-operator`, sans attestation SID ; celui de la récupération est distinct.

Les tests emploient uniquement des magasins/racines temporaires et une saisie
getpass simulée. Aucun secret humain n'a été saisi dans une vraie console,
aucun service actif arrêté, aucune donnée active/Dropbox modifiée. Sauvegarde
et restauration réelle, panne du poste et arrêt brutal pendant la récupération
restent ouverts. Le canal prépare la procédure ; il ne ferme pas le critère de
récupération opérationnelle ni le lot L4.

Sources primaires sur le verrouillage : [PRAGMA locking_mode](https://sqlite.org/pragma.html#pragma_locking_mode),
[WAL en mode exclusif](https://sqlite.org/wal.html#use_of_wal_without_shared_memory).

## Résultats du 3 octobre

Référence avant modification : **27 tests réussis en 73,64 s**. Premier passage
sur récupération/CLI : **25 tests réussis en 100,53 s**. Après les compléments
WAL et prévalidation de console : **50 tests distincts réussis en 175,56 s**,
soit 21 récupération, 19 administration, huit console et deux compatibilité
HTTP v4. Un avertissement existant Starlette/httpx, aucun échec. Les tests ne
s'additionnent pas entre passages.

La gate CI contient désormais quatorze fichiers et reste bornée à douze
minutes pour inclure les contrôles NTFS natifs ; elle n'est pas déclarée
réussie à distance ni intégralement rejouée sur cette révision. Wheel construit
sur copie avec module/PS1 exacts, récupération puis reconnexion exécutées depuis
le paquet extrait. AST, YAML et ordre des racines temporaires vérifiés.

Point de qualification distinct : la recette Python 3.13.3 charge **SQLite
3.49.1**. La documentation SQLite décrit un défaut WAL lors d'écritures et
checkpoints concurrents, corrigé en 3.51.3 et certains backports. La présence
d'une version concernée est confirmée, **pas une corruption reproduite**.
Qualifier un SQLite corrigé avant activation avec écritures WAL concurrentes ;
ces tests de permissions/récupération exclusive ne qualifient pas ce cas.
Voir [description officielle et versions corrigées](https://sqlite.org/wal.html#the_wal_reset_bug).

Extension ultérieure : [sauvegarde et restauration privées](sauvegarde-identite-2026-10-03.md),
avec tests d'arrêt immédiat avant l'audit en DELETE/WAL, réouverture et rollback
SQLite sur fixtures. Ces preuves de processus ne qualifient pas une panne physique.

## Revalidation du 7 octobre

`test_local_recovery.py` : **21 tests passés en94,51s**, sans avertissement.
La recette sur NTFS temporaire reprend les modes DELETE/WAL, comptes/admin
existants, sessions et jetons révoqués pour la cible seulement, refus de
promotion/création d'un administrateur, rollback si l'audit manque/échoue,
refus de verrouillage concurrent, revérification d'admission après hash,
confirmation interactive et secrets absents de stdout. Trace temporaire
`devcore-local-recovery-d1a73f4b43dd46fb9835d9f52d07add6.txt`, SHA256
`675F0A6F02C9292D2E85B6FF163BC34A5C19AC1525F09EB5DCC5B638844460AE`.
Ce re-run ne ferme toujours pas l'opération réelle : aucun service n'a été
arrêté, aucun secret humain saisi dans une console, aucune panne/restauration
physique simulée et aucun magasin actif ouvert.
