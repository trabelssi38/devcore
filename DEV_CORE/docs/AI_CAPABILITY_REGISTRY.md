# DEV_CORE AI Capability Registry

Documentation du registry declaratif de capacites IA ajoute en T-222.

## 1. Probleme resolu

Avant, les workflows DEV_CORE etaient lies a des profils ou modeles fixes :

- `reasoning` -> `devcore-reasoning` -> `gemini-2.5-pro`
- `coding` -> `devcore-coding` -> `gemini-2.5-pro`
- `bulk` -> `devcore-bulk` -> `gemini-2.5-flash`

Ce modele est simple, mais il oblige a modifier les workflows ou mappings quand un nouvel agent/modele arrive.

Le AI Capability Registry ajoute une abstraction :

- les workflows declarent ce dont ils ont besoin;
- les candidats declarent ce qu'ils savent faire;
- le runtime choisit le candidat adapte.

## 2. Fichiers

| Fichier | Role |
|---|---|
| `DEV_CORE\Config\ai_capability_registry.json` | Source declarative des candidats |
| `DEV_CORE\Scripts\ai_capability_registry.py` | Resolver Python et scoring |
| `DEV_CORE\Scripts\routing_profile.ps1` | Exposition PowerShell dans les profils DEV_CORE |
| `DEV_CORE\Scripts\gemini_router.py` | Selection runtime pour appels chat |
| `DEV_CORE\Scripts\test_ai_capability_registry.py` | Tests unitaires du resolver |
| `DEV_CORE\Scripts\test_gemini_router_routing_profile.py` | Tests integration router |
| `DEV_CORE\Scripts\test_routing_profile.ps1` | Tests integration PowerShell |

## 3. Schema logique

```json
{
  "schema_version": 1,
  "default_candidate": "devcore-coding",
  "mode_defaults": {
    "reasoning": "devcore-reasoning",
    "coding": "devcore-coding",
    "bulk": "devcore-bulk"
  },
  "aliases": {
    "devcore-coding": "devcore-coding",
    "gemini-flash": "devcore-bulk"
  },
  "candidates": {
    "devcore-coding": {
      "type": "model",
      "provider": "google",
      "backend_model": "gemini-2.5-pro",
      "enabled": true,
      "workflow_modes": ["coding"],
      "languages": ["python", "powershell", "typescript"],
      "specialties": ["implementation", "tdd", "debug"],
      "context_tokens": 1048576,
      "cost_tier": 3,
      "speed_tier": 3,
      "quality_tier": 4
    }
  }
}
```

## 4. Champs candidat

| Champ | Type | Description |
|---|---|---|
| `type` | string | `model`, `agent`, `tool-agent` futur |
| `provider` | string | Fournisseur logique : `google`, `openai`, `anthropic`, local, etc. |
| `backend_model` | string | Nom envoye au backend actuel |
| `enabled` | bool | Active ou non le candidat |
| `workflow_modes` | string[] | Modes compatibles : `reasoning`, `coding`, `bulk`, `plan` |
| `languages` | string[] | Langages forts |
| `specialties` | string[] | Capacites metier : `tests`, `architecture`, `bulk-edit`, etc. |
| `context_tokens` | int | Fenetre maximale declaree |
| `cost_tier` | int | 1 = bas cout, 5 = cher |
| `speed_tier` | int | 1 = lent, 5 = rapide |
| `quality_tier` | int | 1 = faible, 5 = fort |
| `notes` | string | Commentaire operateur |

## 5. Selection runtime

Priorite du resolver :

1. Si `model` est explicitement demande et mappe par alias, utiliser ce candidat si actif.
2. Sinon, utiliser le candidat par defaut du mode si compatible.
3. Sinon, filtrer tous les candidats actifs par requirements.
4. Scorer les candidats restants selon `optimize_for`.
5. Si aucun candidat ne match, revenir a `default_candidate`.

Optimiseurs supportes :

- `balanced` : qualite prioritaire, puis vitesse, cout, contexte.
- `speed` : vitesse prioritaire.
- `cost` : cout bas prioritaire.
- `context` : contexte maximal prioritaire.

## 6. Requirements workflow

Exemple pour un workflow de tests JavaScript rapide :

```json
{
  "mode": "coding",
  "capability_requirements": {
    "languages": ["javascript"],
    "specialties": ["tests"],
    "optimize_for": "speed"
  }
}
```

Avec le registry actuel, ce cas peut basculer vers `devcore-bulk` / `gemini-2.5-flash`, meme si le mode de base est `coding`.

## 7. Ajouter un nouveau modele

1. Ajouter une entree dans `Config\ai_capability_registry.json`.
2. Ajouter des aliases si le modele peut etre appele par plusieurs noms.
3. Laisser `enabled=false` si aucun backend direct ne sait l'appeler.
4. Ajouter un test dans `test_ai_capability_registry.py` si la selection doit changer.
5. Lancer :

```powershell
python -m pytest DEV_CORE/Scripts/test_ai_capability_registry.py DEV_CORE/Scripts/test_gemini_router_routing_profile.py
powershell -ExecutionPolicy Bypass -NonInteractive -File DEV_CORE/Scripts/test_routing_profile.ps1
```

## 8. Ajouter un agent specialise

Un agent futur peut etre declare comme candidat tant que le runtime sait traduire `backend_model` ou un futur champ adapter.

Exemple conceptuel :

```json
{
  "type": "agent",
  "provider": "workspace-agent",
  "backend_model": "agent://security-reviewer",
  "enabled": false,
  "workflow_modes": ["reasoning", "coding"],
  "languages": ["python", "typescript"],
  "specialties": ["security-review", "threat-modeling"],
  "context_tokens": 200000,
  "cost_tier": 2,
  "speed_tier": 3,
  "quality_tier": 5
}
```

Ne pas activer tant qu'un adapter `agent://` n'existe pas.

## 9. Limites actuelles

- `gemini_router.py` envoie encore les appels vers un backend Gemini compatible OpenAI.
- Les candidats OpenAI/Anthropic observes peuvent etre decrits, mais doivent rester desactives si le router ne peut pas les appeler directement.
- Les tiers cout/vitesse/qualite sont declaratifs et doivent etre recalibres avec les metriques reelles.
- Les workflows existants continuent a marcher via `routing_profiles.json`.

## 10. Contrats de non-regression

- `test_selects_mode_default_and_alias`
- `test_selects_by_required_specialty_language_and_optimizer`
- `test_falls_back_when_no_candidate_matches`
- `test_capability_requirements_can_override_mode_default`
- `test_routing_profile.ps1` pour exposition PowerShell
