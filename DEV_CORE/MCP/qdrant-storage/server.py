# MCP Server for Qdrant Vector Database
# Permet a Hermes de rechercher et stocker dans Qdrant

import json
import os
import requests
from typing import Any, Optional

# Qdrant configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTIONS = ["decisions", "patterns", "lessons", "codebase"]


def qdrant_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make a request to Qdrant API."""
    url = f"{QDRANT_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"error": f"Unknown method: {method}"}

        return {
            "success": response.ok,
            "status_code": response.status_code,
            "data": response.json() if response.ok else None,
            "error": response.text if not response.ok else None
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Qdrant non accessible. Verifier que le service tourne sur port 6333."}
    except Exception as e:
        return {"error": str(e)}


# Tool definitions
TOOLS = [
    {
        "name": "qdrant_collections",
        "description": "Liste toutes les collections Qdrant",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "qdrant_search",
        "description": "Recherche semantique dans une collection Qdrant",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Nom de la collection (decisions, patterns, lessons, codebase)",
                    "enum": COLLECTIONS
                },
                "query": {
                    "type": "string",
                    "description": "Texte de la recherche"
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de resultats (defaut: 5)",
                    "default": 5
                },
                "score_threshold": {
                    "type": "number",
                    "description": "Seuil de similarite minimum (0-1)",
                    "default": 0.7
                }
            },
            "required": ["collection", "query"]
        }
    },
    {
        "name": "qdrant_upsert",
        "description": "Stocke un document dans Qdrant",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Nom de la collection",
                    "enum": COLLECTIONS
                },
                "id": {
                    "type": "string",
                    "description": "ID unique du document"
                },
                "vector": {
                    "type": "array",
                    "description": "Vecteur d'embedding (768 dimensions pour nomic-embed-text)"
                },
                "payload": {
                    "type": "object",
                    "description": "Metadonnees du document (titre, contenu, tags, etc.)"
                }
            },
            "required": ["collection", "id", "payload"]
        }
    },
    {
        "name": "qdrant_delete",
        "description": "Supprime un point d'une collection",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Nom de la collection",
                    "enum": COLLECTIONS
                },
                "id": {
                    "type": "string",
                    "description": "ID du point a supprimer"
                }
            },
            "required": ["collection", "id"]
        }
    },
    {
        "name": "qdrant_create_collection",
        "description": "Cree une nouvelle collection Qdrant",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom de la nouvelle collection"
                },
                "vector_size": {
                    "type": "integer",
                    "description": "Taille des vecteurs (768 pour nomic-embed-text)",
                    "default": 768
                },
                "distance": {
                    "type": "string",
                    "description": "Metrique de distance",
                    "enum": ["Cosine", "Euclid", "Dot"],
                    "default": "Cosine"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "qdrant_health",
        "description": "Verifie l'etat de sante de Qdrant",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    }
]


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle tool call from Hermes."""
    handlers = {
        "qdrant_collections": lambda args: qdrant_request("GET", "/collections"),
        "qdrant_health": lambda args: qdrant_request("GET", "/"),

        "qdrant_search": lambda args: qdrant_request("POST", f"/collections/{args['collection']}/points/search", {
            "vector": args.get("vector", []),
            "limit": args.get("limit", 5),
            "score_threshold": args.get("score_threshold", 0.7)
        }),

        "qdrant_upsert": lambda args: qdrant_request("PUT", f"/collections/{args['collection']}/points", {
            "points": [{
                "id": args["id"],
                "vector": args.get("vector", [0] * 768),
                "payload": args["payload"]
            }]
        }),

        "qdrant_delete": lambda args: qdrant_request("DELETE",
            f"/collections/{args['collection']}/points/delete",
            {"points": [args["id"]]}
        ),

        "qdrant_create_collection": lambda args: qdrant_request("PUT", f"/collections/{args['name']}", {
            "vectors": {
                "size": args.get("vector_size", 768),
                "distance": args.get("distance", "Cosine")
            }
        })
    }

    if tool_name in handlers:
        return handlers[tool_name](arguments)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def main():
    """Main entry point for MCP server."""
    print("Qdrant MCP Server started")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Collections: {COLLECTIONS}")

    # Check health
    health = qdrant_request("GET", "/")
    if health.get("success"):
        print("Qdrant: CONNECTED")
    else:
        print(f"Qdrant: DISCONNECTED - {health.get('error', 'Unknown error')}")

    print(f"Available tools: {len(TOOLS)}")
    for tool in TOOLS:
        print(f"  - {tool['name']}: {tool['description']}")


if __name__ == "__main__":
    main()