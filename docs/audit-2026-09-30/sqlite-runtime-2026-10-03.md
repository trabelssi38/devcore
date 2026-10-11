# Prérequis SQLite pour la qualification WAL

Le contrôle `DEV_CORE/Scripts/check_sqlite_runtime.py` interroge la bibliothèque
SQLite réellement chargée par le Python choisi, dans une base `:memory:`.
Il n'importe aucun magasin DevCore et n'accepte aucun chemin de base. Il produit
une ligne JSON avec exécutable, versions Python/SQLite, source_id et options de
compilation. Il ne modifie ni le runtime ni les données actives.

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe' `
  DEV_CORE/Scripts/check_sqlite_runtime.py
$LASTEXITCODE
```

- Code 0 : version avec correctif WAL-reset connu et WAL disponible ; autorise
  seulement le passage à la qualification de concurrence sur fixtures.
- Code 2 : prérequis refusé ou sonde SQLite en échec. Préparer un runtime séparé
  corrigé, puis relancer le contrôle avec son exécutable exact.
- `operationally_qualified` reste toujours faux. Les tests de l'application,
  extensions comme sqlite-vec, permissions, sauvegarde et charge réelle ne sont
  pas qualifiés par cette sonde. Elle ne couvre pas les autres moteurs ou les
  autres processus Python d'une instance.

La politique vérifiée le 3 octobre accepte les branches upstream 3.44 à partir
de 3.44.6, 3.50 à partir de 3.50.7, et 3.51 à partir de 3.51.3 ainsi que les
versions 3.x ultérieures. Versions inconnues, chaînes vendor et futur major
refusés ; un backport vendor nécessite une preuve et une politique revue.
Source primaire : [SQLite, WAL-reset](https://sqlite.org/wal.html#the_wal_reset_bug).

## Résultat local

Recette existante : **Python 3.13.3 / SQLite 3.49.1**, versions SQL/module
concordantes, WAL disponible. Le prérequis retourne **2**, correction inconnue
pour cette version. Aucun défaut de corruption n'a été reproduit dans ce passage.
L'installation Python 3.13 globale charge également SQLite 3.49.1 ; changer
seulement de virtualenv basé sur ce Python ne corrige donc pas ce prérequis.

**24 tests réussis en 1,06 s** : seuils/backports, inconnu refusé, base mémoire
uniquement et connexion fermée, différence de versions, WAL absent malgré version corrigée, erreur expurgée,
CLI avec racines temporaires contenant une fausse base inchangée.
Trace et JSON :
`C:/Users/Administrateur/AppData/Local/Temp/devcore-sqlite-preflight-91d28ec97a54458f9e09a760c9487f40/`.

La CI Windows appelle désormais la sonde et refuse ce prérequis avant les tests
WAL, puis exécute les tests de la sonde. Aucun passage CI distant n'est annoncé.
L'ancien runtime reste en place. La prochaine étape consiste à préparer un
runtime Python 3.13 distinct avec SQLite corrigé, conserver sa provenance et
rejouer régressions, écritures/checkpoints concurrents et restauration sur
fixtures. La bascule des services reste conditionnée à cette qualification.


## Candidat séparé préparé ensuite

- `E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe` :
  Python 3.13.16, SQLite 3.53.1 ; sonde code 0, qualification opérationnelle
  toujours fausse. Ancien runtime et services actifs conservés.
- Interpréteur python-build-standalone installé par uv 0.11.14 avec
  `--no-bin --no-registry`, sous `E:/DevCoreRuntime/interpreters/`.
  Métadonnées upstream uv obtenues explicitement pour 3.13.16 ; URL d'archive,
  empreinte déclarée et empreintes des binaires installés dans
  `E:/DevCoreRuntime/releases/devcore-py31316-20261003/provenance.json`.
  Empreinte d'archive consignée depuis les métadonnées, pas revérifiée par un
  téléchargement indépendant. Build 20261003. Les 53 dépendances du lock
  Windows installées avec `--require-hashes` ; `uv pip check` réussi.
  DevCore testé depuis les sources via PYTHONPATH, pas encore publié comme
  artefact applicatif figé dans cet environnement.
- Premier candidat 3.13.13 refusé : SQLite 3.50.4 réellement chargé. Environnement
  `devcore-py31313-20261003` conservé mais non qualifié et non sélectionné.
  Une version Python plus récente n'est donc pas une preuve de correctif SQLite.

### Concurrence et extension

Test `DEV_CORE/tests/test_sqlite_wal_qualification.py`, bases neuves temporaires :
2 écrivains, 2 connexions de checkpoint et 1 lecteur, départ par barrière.
Transactions FULL avec compteur et ledger atomiques par projet. Deux modes :

| Mode | Commits | Checkpoints tentés | Retours busy | Snapshots lecteur | Durée |
|---|---:|---:|---:|---:|---:|
| PASSIVE | 80 | 80 | 4 | 40 | 5,688 s |
| TRUNCATE | 80 | 80 | 40 | 40 | 7,176 s |

Intégrité, valeurs exactes et isolation alpha/beta vérifiées après réouverture,
checkpoint final réussi et sauvegarde SQLite restaurée et relue. Extension
sqlite-vec 0.1.9 : chargement réel, longueur vectorielle et schéma DevCore validés.
**3 tests réussis en 15,83 s**. Ce scénario ne reproduit pas de façon déterministe
le défaut amont et ne constitue pas un benchmark de production ni une preuve
contre une panne physique. Les retours busy de checkpoint restent visibles.

Premier passage : 52 autres tests réussis mais deux scénarios WAL échouaient sur
`database is locked` avec timeout 5 s et lots de 120 écritures. Recette finale :
timeout 30 s conforme à connect_db, 40 écritures par projet et pause 1 ms entre
transactions. Le changement de charge et de timeout est explicite : il ne
prouve ni équité ni réactivité sous charge saturée. Les 52 tests déjà réussis
couvrent sonde, versions/audit des tâches et racines ; non rejoués inutilement.
La CI inclut désormais ces scénarios après le prérequis corrigé (2 minutes).

Traces :
`C:/Users/Administrateur/AppData/Local/Temp/devcore-wal-qualification-0579181ae2274518b75f0f196e3b8268/` :
`tests.txt` contient les échecs initiaux, `wal-final.txt` le passage corrigé,
`runtime.json` la sonde. Qualification service Windows, runtime de tous les
processus, HTTP/MCP complets et charge cible restent ouverts.

### Sauvegarde et récupération des identités

Sous le candidat : **35 tests réussis en 237,57 s**, sans skip/échec,
`test_identity_backup.py` et `test_local_recovery.py` sur magasins temporaires
NTFS, modes DELETE/WAL. Les arrêts de workers et révocations restent des preuves
sur fixtures. Total du passage : **90 cas distincts réussis** avec les 55 cas
précédents. Trace : `C:/Users/Administrateur/AppData/Local/Temp/devcore-runtime-recovery-fd8e3e017bf149229835ea9f213993eb/tests.txt` ; SHA-256 `db32c4d6370315abdfa365df0a5e0c98fa0f089404a0a10bea84c8a6c5dffed8`.


## Artefact moteur préparé le 4 octobre

Wheel construit sur copie de sources, puis installé sans nouvelles dépendances
sur le candidat :
`E:/DevCoreRuntime/releases/devcore-py31316-20261003/artifacts/wheels/devcore_engine-10.2.0-py3-none-any.whl`.
SHA-256 : `486dfdf1f19fdecbb2935781fc089c4983caac4e104bec926300f34961e6ec07`.
Le manifeste contient le commit et les empreintes des sources modifiées ; l'état
Git est dirty et le commit seul ne représente donc pas l'artefact.
`artifacts/manifest.json` SHA-256 :
`a0118d1795c295cc4b1a551388864b0695986174a2aa2f79bc67e56052fc40c7`.

CLI `python -m devcore_engine individual --help` exécutée depuis le dossier
artifacts, sans PYTHONPATH, charge bien site-packages ; racines CLI inexistantes
après l'appel. Ce contrôle n'effectue aucune mutation et ne contacte aucune API.
Les 54 paquets moteur inclus passent `uv pip check`. Provenance et liste figée
actualisées ; provenance.json SHA-256 :
`3e1c4fccaa6e8cd67a511d160f49dd4181e300ad83130176f3dec71968575dfc`.

Portée : moteur et clients seulement. Dashboard/API/MCP serveur ne sont pas
embarqués par ce wheel ; ce n'est pas une release complète d'instance.
L'instance active et l'ancien runtime sont conservés.


## Qualification HTTP/CLI/MCP du 4 octobre

**216 tests réussis en 795,61 s**, zéro skip/échec, un avertissement Starlette/httpx
connu : HTTP audit/sessions/contexte, MCP contexte/tâches/CLI/suppression/audit et
stdio. Racines temporaires avant imports/sous-processus, build tooling séparé.
Trace `C:/Users/Administrateur/AppData/Local/Temp/devcore-runtime-http-mcp-c671f1fcf81b46dd8127fa1faa11c187/tests.txt` ; SHA-256 `a73dd37d45a16826c4e615912ca6ac5fc22f062cfada24db6f34dd309b930d44`.
Les fixtures incluent les opérations du client wheel installé et les échanges
stdio réels. Cette suite ne qualifie pas tous les endpoints historiques ni une
instance déployée ; voir le [journal](execution-2026-10-04.md).
