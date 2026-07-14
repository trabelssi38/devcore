# DEV_CORE API Reference

Référence publique du gateway API DEV_CORE v1. Le contrat canonique est l'OpenAPI versionné `DEV_CORE/Schemas/openapi-v1.json`; cette page sert de guide opérable pour les intégrations humaines et clients.

Voir aussi : `OPERATOR_GUIDE.md` pour les commandes d'exploitation et `PLATFORM_DOCUMENTATION.md` pour l'architecture globale.

## Artefacts versionnés

| Artefact | Rôle |
|---|---|
| `DEV_CORE/Schemas/openapi-v1.json` | OpenAPI 3.1 généré depuis les modèles FastAPI/Pydantic. |
| `DEV_CORE/API/clients/typescript/devcore-api-client.ts` | Client TypeScript généré pour les consommateurs web et outils internes. |
| `DEV_CORE/API/test_openapi_client_generation.py` | Test de non-régression entre schéma OpenAPI et client. |
| `DEV_CORE/API/test_api_v1.py` | Contrats HTTP de base. |
| `DEV_CORE/API/test_github_webhooks.py` | Signature, idempotence et réponse webhook GitHub. |

## Convention générale

- Base locale par défaut : `http://127.0.0.1:<port>` selon le service API lancé.
- Version API : préfixe `/api/v1`.
- Format : JSON UTF-8.
- Traçabilité : `trace_id` est propagé dans les réponses critiques et le client peut envoyer `X-Trace-Id`.
- Erreurs client : enveloppe `DevCoreError` côté `DevCoreApiClient`.

## Endpoints v1

### GET /api/v1/health

Contrôle minimal du gateway.

Réponse `200` :

```json
{
  "schema_version": 1,
  "api_version": "v1",
  "service": "devcore-api",
  "status": "ok",
  "trace_id": "..."
}
```

Usage TypeScript :

```ts
const client = new DevCoreApiClient("http://127.0.0.1:20129");
const health = await client.health();
```

### GET /api/v1/contracts

Expose le catalogue de contrats domaine : `Task`, `Run`, `Event`, `Plugin`, `Health`, `User`, `Organization`, `Workspace`, `WorkspaceMembership`, `WorkspaceQuota`.

Réponse `200` : `ContractCatalog` avec `schema_version: 1` et `api_version: "v1"`.

Usage TypeScript :

```ts
const contracts = await client.contracts();
```

### GET /api/v1/tasks

Liste les tâches d'un projet DEV_CORE.

Paramètres :

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `project` | string | `devcore` | Projet lu dans `DEV_CORE_DATA\Memory\<project>\tasks.json`. |

Exemple :

```http
GET /api/v1/tasks?project=devcore
```

Réponse `200` : `TaskListResponse`.

Réponse `422` : erreur de validation FastAPI si le paramètre est invalide.

### POST /api/v1/integrations/github/webhook

Point d'entrée webhook GitHub. Le corps doit être le payload brut signé par GitHub.

Headers requis :

| Header | Description |
|---|---|
| `X-GitHub-Event` | Type d'événement GitHub. |
| `X-GitHub-Delivery` | ID unique de livraison, utilisé pour l'idempotence. |
| `X-Hub-Signature-256` | Signature HMAC SHA-256 du payload. |

Réponse `202` :

```json
{
  "schema_version": 1,
  "provider": "github",
  "event": "push",
  "delivery_id": "...",
  "accepted": true
}
```

Usage TypeScript :

```ts
await client.githubWebhook(rawBody, {
  event: "push",
  deliveryId: deliveryId,
  signature256: "sha256=..."
});
```

## Client TypeScript

`DevCoreApiClient` centralise :

- `health()` -> `GET /api/v1/health`
- `contracts()` -> `GET /api/v1/contracts`
- `tasks(project)` -> `GET /api/v1/tasks`
- `githubWebhook(body, headers)` -> `POST /api/v1/integrations/github/webhook`

Les erreurs HTTP non `2xx` lèvent `DevCoreApiError` avec `status` et payload `DevCoreError`.

## Politique de compatibilité

- Toute rupture de forme JSON doit passer par un changement de version API.
- Les champs `schema_version` restent obligatoires sur les contrats versionnés.
- Les tests Python et le client généré doivent passer avant publication.
- L'OpenAPI est la source de vérité; ne pas modifier le client généré à la main.
