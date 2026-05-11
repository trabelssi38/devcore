---
name: python_api
description: Utiliser pour toute API Python : FastAPI, endpoints, Pydantic, async, middleware, tests pytest.
compatibility: Claude Code · Codex · Gemini · Qwen
---
# Skill — Python API

## Règles fondamentales
- Toujours utiliser async routes sur FastAPI
- Validation : Pydantic v2 (model_validator, field_validator)
- Typage : annotations complètes, pas de Any implicite
- Tests : pytest + httpx AsyncClient
- Erreurs : HTTPException avec codes HTTP sémantiques
- Deps : Poetry ou pip-tools, jamais de requirements.txt manuel

## Structure FastAPI recommandée
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class RequestModel(BaseModel):
    field: str

@app.post("/endpoint", response_model=ResponseModel)
async def endpoint(body: RequestModel) -> ResponseModel:
    ...
```

## Checklist API
- [ ] Routes async
- [ ] Modèles Pydantic v2
- [ ] Tests httpx AsyncClient
- [ ] Gestion erreurs HTTPException
- [ ] Pas de secrets hardcodés
