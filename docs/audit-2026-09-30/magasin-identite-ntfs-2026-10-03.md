# Magasin d'identité privé — recette NTFS

Le magasin SQLite d'identité peut maintenant être créé explicitement dans un
répertoire privé. Cette recette complète la protection des fichiers de jetons.
Elle n'active ni ne migre le magasin des services actuels.

## Création et inspection

`manage_local_identity.py init-private-store` exige un chemin absolu sur un
volume local NTFS et un répertoire parent **existant et vide**. Il refuse les
jonctions/points de réanalyse, y compris dans les ancêtres, en contrôlant le
chemin d'origine. Aucun magasin ou répertoire contenant des données n'est adopté.

Ordre : protéger le répertoire, réserver la base exclusivement, protéger son
fichier encore vide, créer le schéma v1, contrôler les permissions. La DACL du
répertoire autorise uniquement le SID Windows courant et SYSTEM, avec héritage
pour ses nouveaux enfants ; la base a une DACL explicite sans héritage. Aucun
utilisateur, mot de passe, rôle ou jeton n'est créé par cette commande. Les
migrations suivantes vers v2/v3/v4 restent explicites.

`check-store-protection` inspecte les descripteurs du parent, de la base et des
fichiers présents `-journal`, `-wal`, `-shm`. Il ne lit aucun secret, n'ouvre pas
SQLite, ne rejoue pas de journal et ne répare aucune permission. Un ajout de
règle, même pour Tout le monde, provoque un refus et un code CLI 2. Le résultat
JSON contient seulement les SID, le type et les suffixes contrôlés.

Exemple sur **une nouvelle recette temporaire**, hors Dropbox :

```powershell
$storeRecipeRoot = Join-Path $env:TEMP ('devcore-identity-recipe-' + [guid]::NewGuid().ToString('N'))
$env:DEVCORE_LOCAL_ROOT = Join-Path $storeRecipeRoot 'local'
$env:DEVCORE_DATA_ROOT = Join-Path $storeRecipeRoot 'data'
$storePrivateDirectory = Join-Path $storeRecipeRoot 'identity'
New-Item -ItemType Directory -Path $storePrivateDirectory -ErrorAction Stop | Out-Null
$storeRecipe = Join-Path $storePrivateDirectory 'identity.db'
$storePython = 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe'
$storeCli = 'E:/src_python/devcore/DEV_CORE/Scripts/manage_local_identity.py'
& $storePython $storeCli --store $storeRecipe init-private-store
if ($LASTEXITCODE -ne 0) { throw 'Création privée refusée : arrêter la recette' }
& $storePython $storeCli --store $storeRecipe check-store-protection
if ($LASTEXITCODE -ne 0) { throw 'Permissions du magasin refusées' }
```

Les fichiers de jetons doivent avoir **un autre répertoire**, préparé avec
`protect-secret-dir`. Sinon leur présence fait refuser l'initialisation du
répertoire du magasin. La commande historique `init` reste compatible avec
les anciennes recettes et ne fournit pas cette protection NTFS.

En cas d'échec après réservation, le fichier réservé reste disponible pour
inspection : la commande ne supprime aucune donnée. Un échec de protection du
fichier interdit tout appel d'initialisation du schéma. Une initialisation
interrompue ne devient pas un succès et ne peut pas être relancée sur un
répertoire devenu non vide.

## Qualification et limites

Les tests natifs utilisent uniquement des répertoires temporaires et Python
3.13. Ils contrôlent les droits avant les premiers octets du schéma, l'absence
de compte créé, le refus sans modification des répertoires occupés et d'une
jonction, et un échec ACL avant création du schéma. SQLite crée réellement les
fichiers de journal en mode DELETE, puis WAL/SHM en mode WAL ; leurs ACL sont
contrôlées pendant une transaction d'écriture ouverte. Les cinq cibles parent,
base, journal, WAL et SHM sont élargies à Tout le monde dans des fixtures
distinctes : le contrôle refuse et conserve les descripteurs/données tels quels.
La commande d'inspection est aussi vérifiée avec toute ouverture SQLite interdite.

Résultats du 3 octobre : **28 tests ciblés réussis en 61,78 s**, puis **110 tests
distincts réussis en 300,00 s** pour la gate complète identité, administration,
audit et profils HTTP. Un avertissement existant Starlette/httpx est émis, sans
échec. Wheel Python 3.13 construit sur copie : nouveau module et helper PS1
identiques aux sources, puis initialisation privée réussie depuis le paquet
extrait. La CI inclut les treize fichiers concernés ; résultat distant non établi.

Un processus Windows élevé peut créer un enfant hérité appartenant au groupe
Administrateurs. Le contrôle accepte ce propriétaire pour ces enfants, tout en
exigeant exactement les droits courant/SYSTEM hérités du parent privé. Aucune
règle DACL du groupe Administrateurs n'est acceptée. Les administrateurs OS et
SYSTEM restent une frontière de confiance ; un autre processus du même compte
Windows peut accéder aux données.

Cette inspection est un **instantané**, pas une surveillance continue. Elle
n'est pas exécutée dans le chemin de chaque requête HTTP : les coûts d'un
processus PowerShell par authentification ne sont pas imposés au service.
L'activation opérationnelle doit encore qualifier le compte de service, les
droits des parents, un autre compte Windows réel, la restauration des ACL et
les courses avec un acteur contrôlant le système de fichiers. Les autres
fichiers temporaires SQLite, sauvegardes/exportations, chiffrement et POSIX
restent hors de cette preuve. L4/L9 et la récupération sans administrateur
joignable restent ouverts.

Références primaires : [journaux et fichiers temporaires SQLite](https://sqlite.org/tempfiles.html),
[fonctionnement WAL](https://sqlite.org/wal.html). SQLite documente les fichiers
adjacents contrôlés ici ; la protection des autres catégories de fichiers
temporaires doit être examinée selon les requêtes réellement déployées.
