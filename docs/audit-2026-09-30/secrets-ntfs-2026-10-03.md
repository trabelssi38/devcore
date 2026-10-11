# Protection des fichiers de jetons — NTFS de recette

Qualification effectuée sur ce poste avec fichiers temporaires uniquement,
Python 3.13 et Windows PowerShell 5.1. Aucun secret actif, magasin d'identité
actif, répertoire Dropbox ou compte Windows modifié.

## Garanties ajoutées

La console protège un fichier réservé par création exclusive **avant** de
créer le credential et d'y écrire le jeton. La DACL est reconstruite :
héritage désactivé, propriétaire égal au SID Windows courant, deux autorisations
FullControl pour ce SID et SYSTEM, aucune autre autorisation. Le descripteur
effectif est relu et contrôlé. Échec de protection : aucune émission ni octet
secret, fichier réservé supprimé. Les chemins sont des arguments littéraux,
pas du code de shell ; volumes réseau/non-NTFS et points de réanalyse dans
le chemin sont refusés. Prévalidation du parent avant création.

Les fichiers de jetons administratifs sont contrôlés **avant** lecture. Un
propriétaire inattendu, un héritage actif, une règle supplémentaire ou des
droits inattendus empêchent leur usage. Aucun secret existant n'est réparé
automatiquement : la lecture ne change ni contenu ni permissions. La
protection d'un fichier refuse un contenu déjà présent.

La protection concerne l'émission administrative, les jetons de projet du
schéma v4 et l'émission historique v1–v3. Les limites transactionnelles du
provisionnement historique restent les mêmes ; les garanties d'émission
atomique avec audit concernent v4.

## Répertoire de secrets choisi explicitement

Pour préparer **un nouveau répertoire de recette vide**, hors Git/Dropbox :

```powershell
$aclPython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$aclCli = 'E:/src_python/devcore/DEV_CORE/Scripts/manage_local_identity.py'
$aclStore = '<magasin-absolu-local-de-recette>/identity.db'
$aclDirectory = '<nouveau-répertoire-absolu-local-de-recette>'
New-Item -ItemType Directory -Path $aclDirectory
& $aclPython $aclCli --store $aclStore protect-secret-dir --directory $aclDirectory
```

Le répertoire doit être vide et exister ; la commande n'initialise pas la base,
ne parcourt pas ses descendants et n'altère aucun répertoire existant rempli.
Sa DACL autorise compte courant/SYSTEM et prévoit l'héritage pour de nouveaux
enfants. Chaque fichier de jeton reste ensuite protégé explicitement.
Un fichier administratif avec anciennes permissions est refusé : se reconnecter
et émettre un nouveau fichier dans le répertoire de recette protégé.

## Preuves et limites

**17 tests distincts réussis** : huit scénarios NTFS natifs, huit scénarios
de console administrative/émission historique et le test de saisie masquée
avec refus de fallback non masqué. La qualification NTFS utilise Get-Acl
indépendamment du vérificateur, contrôle le propriétaire/SYSTEM et l'héritage,
ajoute réellement Everyone par icacls puis vérifie le refus sans réparation,
et crée une jonction temporaire refusée avant écriture. Son retrait ne touche
pas la cible. Un échec de protection simulé interdit l'appel d'émission.

L'environnement PowerShell 7 hérité a empêché de charger le module Windows
PowerShell 5.1 lors des premiers essais. Le lanceur filtre PSModulePath sans
tenir compte de la casse et le script importe le module Security natif via
PSHOME. Les assertions ont aussi été corrigées pour l'alias SDDL LA du SID
Administrateur et la modification DACL de fixture sans privilège SACL.
Ces essais initiaux ne sont pas comptés comme réussis. CI configurée, pas de
résultat distant annoncé.

Cette première preuve couvre les fichiers du compte OS courant et la préparation d'un
répertoire vide. **Ne couvre pas** la base d'identité/WAL/SHM, tous les parents,
un compte de service distinct ou un second compte Windows réel, les privilèges
des administrateurs OS, la sauvegarde/restauration des ACL ni les courses avec
un acteur contrôlant le système de fichiers. SYSTEM et le compte courant
restent de confiance ; un autre processus sous le même compte peut accéder
aux secrets. Le canal getpass n'a pas été essayé dans une vraie console
interactive humaine. Les tests ne qualifient pas la branche POSIX chmod.
Le lot L4 et la récupération opérationnelle restent ouverts.

La création privée et le contrôle ponctuel de la base/journal/WAL/SHM ont ensuite
été qualifiés séparément : [recette du magasin NTFS](magasin-identite-ntfs-2026-10-03.md).
Cette extension ne qualifie pas leur activation sur les services actuels.

Référence primaire : [Set-Acl, Microsoft](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-acl?view=powershell-5.1).
