# API Versioning Policy

DEV_CORE API Gateway expose ses contrats publics sous un prefixe majeur explicite.

## Version courante

- Version API publique : `/api/v1`
- Schema OpenAPI versionne : `DEV_CORE/Schemas/openapi-v1.json`
- Client public genere : `DEV_CORE/API/clients/typescript/devcore-api-client.ts`

## Regles de compatibilite

- Toute route publique doit etre exposee sous `/api/v1`.
- Un changement compatible garde `/api/v1` :
  - ajout d'un endpoint ;
  - ajout d'un champ optionnel ;
  - ajout d'une valeur non bloquante quand les clients existants restent valides.
- Un breaking change exige une nouvelle version majeure (`/api/v2`) :
  - suppression ou renommage d'un endpoint ;
  - suppression ou renommage d'un champ ;
  - changement de type ou de semantique d'un champ existant ;
  - changement d'enveloppe d'erreur.

## Process obligatoire

1. Mettre a jour les modeles Pydantic et les tests contractuels.
2. Regenerer OpenAPI avec `python DEV_CORE/API/export_openapi.py`.
3. Regenerer le TypeScript client via le meme script.
4. Executer `DEV_CORE/Scripts/ci_python_tests.ps1`.
5. Documenter la migration si un breaking change introduit `/api/v2`.

## Gate CI

Les tests doivent verifier :

- `info.version == "v1"` dans OpenAPI ;
- toutes les routes publiques commencent par `/api/v1/` ;
- le schema OpenAPI versionne committe reste coherent avec le runtime ;
- la politique de versioning mentionne OpenAPI, le TypeScript client et la gestion des breaking change.
