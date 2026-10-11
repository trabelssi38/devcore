# Snapshot de plateforme individuelle — candidat

Le moteur wheel ne contient pas les scripts serveur ni la page. Le constructeur
`DEV_CORE/Scripts/build_individual_bundle.py` copie sept fichiers explicites :
Dashboard API, HTML/JS de /project, serveur MCP et ses deux adaptateurs individuels,
et sonde SQLite. Aucun credential, magasin, fiche de projet, configuration ou
index n'est copié. Les anciens handlers/hooks ne sont pas embarqués.

```powershell
& 'E:/DevCoreRuntime/releases/devcore-py31316-20261003/Scripts/python.exe' `
  DEV_CORE/Scripts/build_individual_bundle.py verify `
  E:/DevCoreRuntime/releases/devcore-py31316-20261003/individual-platform
```

La construction refuse l'écrasement, une destination dans les sources, les liens
et jonctions sources, les fichiers absents/trop gros et une modification pendant
la copie. Publication du dossier staging seulement après contrôle ; staging non
publié conservé en cas d'échec. La vérification refuse fichiers altérés, absents ou
supplémentaires. Ne pas générer de pycache dans ce snapshot (PYTHONDONTWRITEBYTECODE=1).
Le contrôle des empreintes ne garantit pas l'authenticité d'un manifeste remplacé :
son empreinte doit être comparée à celle conservée dans une provenance de confiance.

Snapshot réel : `E:/DevCoreRuntime/releases/devcore-py31316-20261003/individual-platform`.
SHA-256 manifest.json : `d38e0c16cf1bb7604811538f015d14bd38c47743b49268e331c81871c6ff9027`.
Moteur installé séparément via le wheel déjà documenté. Python/dépendances non
copiés par le constructeur : ce dossier seul n'est pas un runtime autonome.

**8 tests réussis en 1,27 s**, zéro skip/échec, un avertissement Starlette/httpx
connu. Allowlist, écrasement, altération, ajout, omission, lien simulé, changement
en cours de copie et snapshot réel HTTP vérifiés. Trace `C:/Users/Administrateur/AppData/Local/Temp/devcore-bundle-test-c7b7eb54876e43cfa823704c08042fc6/tests-final.txt` ;
SHA-256 `4db24201ba6111b5f3365e1bae8d7da429490cc4d66d12391fa93a99e48efcba`. Contrôle natif de jonction source non rejoué ici.

Un second contrôle hors dépôt, sans PYTHONPATH, charge bien le moteur installé
site-packages avec le snapshot serveur : /project et /project.js répondent 200,
/api/settings 403 et tâches sans credential 401. Aucune racine de données créée.
Profil individual explicitement imposé avant imports, racines temporaires et
magasin absent de recette ; aucun serveur actif démarré et aucun port lié.

Ce snapshot n'est pas activé. Les scripts conservent leurs profils legacy par
défaut : ne pas les lancer directement avec un environnement incomplet. Un
lanceur fermé par défaut, les parcours authentifiés HTTP/MCP depuis ce snapshot,
les identités privées, le service Windows, la charge et le retour arrière doivent
être qualifiés avant bascule. Seul le profil individuel est dans ce candidat.

Extension : [lanceur HTTP individuel et parcours authentifie sur snapshot](lanceur-individuel-2026-10-04.md). MCP snapshot et activation restent ouverts.
