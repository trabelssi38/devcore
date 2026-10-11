# Sauvegarde et restauration privée des identités — recette

`identity_backup.py` et deux commandes locales complètent la récupération de
l'administrateur. Elles portent sur **le magasin d'identité de recette** :
pas la base métier, les runs, les fichiers projets ni PostgreSQL. Aucune
sauvegarde/restauration des données actives n'a été exécutée pendant les tests.

## Sauvegarde

`backup-private-store` exige une console interactive et la déclaration d'arrêt
des services. Le magasin source v4 déjà bootstrappé est contrôlé sur NTFS,
avec son parent et ses journaux. Une connexion existante `mode=rw` acquiert un
verrou EXCLUSIVE avant accès au schéma ; un lecteur/écrivain en transaction
fait refuser l'opération, avec attente SQLite d'une seconde. Ce n'est pas une
vérification du superviseur ni un arrêt automatique de DevCore.

Après contrôle d'intégrité et des clés étrangères, la transaction exclusive
est terminée mais le verrou du mode EXCLUSIVE est conservé jusqu'à fermeture.
La copie utilise l'API SQLite backup, par 256 pages avec contrôle de progression
et budget de copie de 30 secondes aux callbacks. Elle ne s'exécute pas depuis
une transaction d'écriture ouverte, qui pourrait maintenir SQLite backup en BUSY.
Ce budget ne borne pas une panne ou un blocage d'E/S entre deux callbacks.

La destination exige un autre répertoire existant vide. Le parent et le fichier
intermédiaire `.identity.db.pending-<id>` sont protégés avant les premiers octets.
La copie est autonome en mode DELETE, sans WAL/SHM restant à publier. Après
contrôles NTFS, intégrité et fsync du fichier, un hard link NTFS publie le nom
final exclusivement ; aucun fichier existant n'est remplacé. Le fichier
intermédiaire est ensuite retiré. Le reçu contient chemin, SHA-256 et SID OS.

La source conserve ses données logiques ; l'ouverture/fermeture SQLite peut
effectuer une récupération ou un checkpoint et changer sa représentation
physique. L'archive conserve ses comptes, hashes, anciens jetons et historique.
Elle est **réservée à la restauration**, jamais à l'activation directe d'un service.
Le reçu `archive_only=true` précise cette portée. L'archive doit rester privée,
hors Git/Dropbox et protégée contre la modification comme ses secrets.

## Restauration et anciens accès

`restore-private-store` exige le SHA-256 attendu conservé séparément, une console
et les confirmations de restauration/maintenance. L'archive doit être privée,
autonome, en mode DELETE, sans sidecars préexistants. Le digest est vérifié avant
toute mutation de la destination et après acquisition du verrou de source.
Cette empreinte détecte une différence ; elle n'est pas une signature contre
un acteur capable de modifier à la fois l'archive et le reçu.

La restauration crée **un nouveau magasin**, dans un répertoire vide. Elle ne
remplace ni la source, ni un magasin actif, ni une destination existante. Avant
publication, une transaction dans la copie :

- désactive tous les comptes ;
- révoque tous les jetons de projet/administration et tous les cookies ;
- retire les hashes des comptes non administrateurs, nécessitant un nouveau secret ;
- remplace chaque secret d'administrateur par un hash Argon2id d'un secret aléatoire
  distinct, inconnu et non délivré ; cela maintient son éligibilité au secours OS ;
- conserve les rôles/appartenances et le bootstrap, puis ajoute `identity.restore-local`
  avec auteur `windows:<SID natif>`, empreinte d'archive et métadonnées de révocation.

Les comptes désactivés, révocations et hashes attendus sont revérifiés après
l'audit, ainsi que l'intégrité/FK. Audit refusé ou réactivation d'un ancien
credential par un trigger : rollback, aucune destination finale publiée.
Cette protection évite aussi qu'un ancien mot de passe soit rétabli depuis
l'archive. Le propriétaire Windows doit récupérer un administrateur avec un
**nouveau** mot de passe, puis assigner de nouveaux secrets aux autres comptes
avant de les réactiver. Une simple réactivation ne restaure pas leurs anciens secrets.

Les fichiers intermédiaires d'un échec ou arrêt brutal restent privés pour
inspection. Ils ne doivent jamais être configurés comme magasin du service ;
la présence d'un `.pending-*` ne prouve pas une restauration terminée. La commande
refuse de recommencer dans ce répertoire non vide ; utiliser une autre destination
après inspection. La source/archive n'est pas supprimée.

## Commandes opérateur sur copie de recette

Après préparation d'un magasin privé v4 et arrêt des services de cette recette,
dans une vraie console Windows de son propriétaire :

```powershell
$snapshotPython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$snapshotCli = 'E:/src_python/devcore/DEV_CORE/Scripts/manage_local_identity.py'
$snapshotSource = '<magasin-prive-absolu-de-recette>/identity.db'
$snapshotArchiveDirectory = '<nouveau-repertoire-local-vide-pour-archive>'
$snapshotRestoreDirectory = '<autre-nouveau-repertoire-local-vide-pour-restauration>'
$env:PYTHONPATH = 'E:/DevCoreRuntime/recipes/devcore-auth-py313-20261003/packages'
New-Item -ItemType Directory -Path $snapshotArchiveDirectory -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Path $snapshotRestoreDirectory -ErrorAction Stop | Out-Null
$snapshotArchive = Join-Path $snapshotArchiveDirectory 'identity.db'
$snapshotRestored = Join-Path $snapshotRestoreDirectory 'identity.db'
$snapshotReceipt = & $snapshotPython $snapshotCli --store $snapshotSource backup-private-store `
    --output $snapshotArchive --confirm-services-stopped | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Sauvegarde refusee : ne pas poursuivre' }
# Conserver le reçu/empreinte dans un emplacement privé séparé de l'archive.
& $snapshotPython $snapshotCli --store $snapshotRestored restore-private-store `
    --backup $snapshotArchive --expected-sha256 $snapshotReceipt.sha256 `
    --confirm-local-restore --confirm-services-stopped
if ($LASTEXITCODE -ne 0) { throw 'Restauration refusee : ne pas activer la destination' }
& $snapshotPython $snapshotCli --store $snapshotRestored recover-local-admin --user alice `
    --confirm-local-recovery --confirm-services-stopped
if ($LASTEXITCODE -ne 0) { throw 'Recuperation refusee : garder les services arretes' }
```

Tester ensuite la nouvelle connexion administrative, les anciens accès refusés,
les rôles et l'audit sur le nouveau magasin avant toute activation. Voir le
[protocole de récupération](recuperation-locale-2026-10-03.md) et la
[console d'administration](administration-locale-2026-10-03.md).

## Preuves et limites

Tests sur sources DELETE/WAL et répertoires temporaires uniquement : archive
cohérente, source logique/historique préservés, empreinte refusée sans mutation,
destination occupée conservée, lecteur actif refusé, audit/trigger en échec ne
publiant pas la copie, contrôle avant copie et absence de secrets au stdout.

Deux workers terminés immédiatement avec `os._exit` avant l'audit de récupération
en DELETE/WAL : contrôle NTFS et intégrité, réouverture rw et rollback vérifiés.
Un worker arrêté avant l'audit de restauration ne publie aucun nom final ; seuls
les fichiers intermédiaires privés subsistent. Cela ne simule pas une coupure
d'alimentation ni une panne physique du volume.

Pas de console humaine/arrêt réel des services, compte de service distinct,
restauration sur autre compte/poste, chiffrement ou sauvegarde métier complète
qualifiés. Le fsync du fichier ne qualifie pas la persistance du lien de publication
face à une panne du stockage. Les parents et acteurs OS restent la frontière de
confiance ; les coûts de remise à zéro des secrets administrateurs sont ceux de
leur hash Argon2id, dans cette maintenance locale. La recette SQLite 3.49.1 n'est
toujours pas qualifiée pour le défaut WAL concurrent documenté. L4/L9 restent ouverts.

Sources primaires : [SQLite backup API](https://sqlite.org/backup.html),
[Python 3.13 Connection.backup](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup).

Résultats du 3 octobre : référence privée avant modification **12 tests réussis
en 29,14 s** ; **14 nouveaux tests réussis en 121,53 s** ; puis **43 tests
distincts réussis en 240,32 s** (14 sauvegarde/arrêts, 21 récupération, huit CLI).
Pas 69 tests distincts : les passages se recouvrent. La gate CI comporte quinze
fichiers, sans réussite distante ou requalification de sa totalité annoncée.
Wheel Python 3.13 construit sur copie, modules/PS1 exacts ; sauvegarde,
restauration, récupération et reconnexion vérifiées depuis le paquet extrait.
AST, YAML, espaces et racines temporaires avant pytest vérifiés.
