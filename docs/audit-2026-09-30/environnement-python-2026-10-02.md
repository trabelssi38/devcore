# Environnement Python isolé du pilote — 2 octobre 2026

Le pilote local est qualifié sur **CPython 3.13.3 Windows x64**, déjà installé sur ce poste et utilisé en version 3.13 par la CI. Le Python 3.14 actuellement employé par les services n'a pas été remplacé. L'environnement de recette se trouve hors dépôt et hors Dropbox, sous `E:/DevCoreRuntime/releases/devcore-py313-20261002`.

`DEV_CORE/pyproject.toml` déclare désormais les dépendances directes des services actifs et l'extra `test` ; `requirements-ci.txt` est un raccourci d'installation depuis la racine du dépôt. Le fichier `requirements-py313-windows.lock` contient 51 paquets résolus avec versions et empreintes SHA-256. La CI Windows 3.13 l'installe avec `pip --require-hashes`, puis installe le code local sans résoudre de nouvelles dépendances. Le backend de construction `setuptools>=61` reste hors de ce verrouillage et la CI distante n'a pas encore validé ce changement.

Reproduction sur Windows x64, depuis la racine du dépôt :

```powershell
uv venv --python 3.13 E:\DevCoreRuntime\releases\devcore-py313-20261002
uv pip sync --python E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe --require-hashes DEV_CORE\requirements-py313-windows.lock
uv pip install --python E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe --no-deps -e DEV_CORE
uv pip check --python E:\DevCoreRuntime\releases\devcore-py313-20261002\Scripts\python.exe
```

Pour modifier les contraintes, éditer `pyproject.toml`, puis régénérer depuis la racine avec `uv pip compile DEV_CORE/pyproject.toml --extra test --python-version 3.13 --python-platform windows --generate-hashes -o DEV_CORE/requirements-py313-windows.lock`. Examiner le diff du verrou et relancer les tests dans un environnement neuf ; une régénération peut choisir de nouvelles versions et n'est pas une mise à niveau automatique de l'instance active.

Validation locale : résolution 51 paquets avec `uv 0.11.14`, installation dans l'environnement isolé, `uv pip check` compatible pour 52 paquets avec le projet, et **22 tests réussis** (`tests/test_project_isolation.py`, `tests/test_sqlite_reconciliation.py`, `tests/test_inspect_dropbox_conflicts.py`, `API/test_ports.py`) avec racines locale/partagée temporaires. Un avertissement de dépréciation Starlette/TestClient concernant `httpx` subsiste. `pip install --dry-run --require-hashes` sous Python 3.13 a aussi accepté le verrou. Ni la base active ni Dropbox n'ont servi de données de test.

Limites : la suite CI complète n'a pas encore été exécutée dans cet environnement ni sur GitHub ; les dépendances des composants archivés ou optionnels non couverts par ces 22 tests restent à qualifier. `DEV_CORE/MCP/requirements.txt` est encore un manifeste autonome pour un mode d'installation MCP historique ; son regroupement doit être vérifié avec les commandes de lancement concernées. Le basculement des services actifs vers Python 3.13 attend les lots de migration et de déploiement.
