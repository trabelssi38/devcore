import json
import os
from pathlib import Path


DEV_CORE = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", r"C:\devcore\DEV_CORE"))
DEFAULT_REGISTRY_PATH = DEV_CORE / "Config" / "ai_capability_registry.json"


def normalize(value):
    return str(value or "").strip().lower()


def normalize_list(values):
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    return [normalize(value) for value in values if normalize(value)]


def load_capability_registry(path=DEFAULT_REGISTRY_PATH):
    target = Path(path)
    if not target.exists():
        return {
            "schema_version": 1,
            "default_candidate": "devcore-coding",
            "candidates": {
                "devcore-coding": {
                    "enabled": True,
                    "backend_model": "gemini-2.5-pro",
                    "workflow_modes": ["coding"],
                    "context_tokens": 1048576,
                    "cost_tier": 3,
                    "speed_tier": 3,
                    "quality_tier": 4,
                }
            },
            "aliases": {},
            "mode_defaults": {"coding": "devcore-coding"},
        }
    with target.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def candidate_id_for_request(registry, requested_model=None, mode=None):
    aliases = registry.get("aliases", {}) if isinstance(registry.get("aliases"), dict) else {}
    mode_defaults = registry.get("mode_defaults", {}) if isinstance(registry.get("mode_defaults"), dict) else {}
    requested = normalize(requested_model)
    requested_mode = normalize(mode)
    if requested:
        return normalize(aliases.get(requested, requested))
    if requested_mode and requested_mode in mode_defaults:
        return normalize(mode_defaults[requested_mode])
    return normalize(registry.get("default_candidate") or "")


def hydrate_candidate(candidate_id, raw):
    item = dict(raw or {})
    item["id"] = candidate_id
    item["enabled"] = bool(item.get("enabled", True))
    item["backend_model"] = item.get("backend_model") or candidate_id
    item["workflow_modes"] = normalize_list(item.get("workflow_modes"))
    item["languages"] = normalize_list(item.get("languages"))
    item["specialties"] = normalize_list(item.get("specialties"))
    item["context_tokens"] = int(item.get("context_tokens") or 0)
    item["cost_tier"] = int(item.get("cost_tier") or 3)
    item["speed_tier"] = int(item.get("speed_tier") or 3)
    item["quality_tier"] = int(item.get("quality_tier") or 3)
    return item


def all_candidates(registry):
    candidates = registry.get("candidates", {}) if isinstance(registry.get("candidates"), dict) else {}
    return [hydrate_candidate(normalize(candidate_id), raw) for candidate_id, raw in candidates.items()]


def matches_requirements(candidate, mode, requirements):
    if not candidate.get("enabled"):
        return False
    requested_mode = normalize(mode)
    modes = candidate.get("workflow_modes") or []
    if requested_mode and modes and requested_mode not in modes:
        return False
    min_context = int((requirements or {}).get("min_context_tokens") or 0)
    if min_context and int(candidate.get("context_tokens") or 0) < min_context:
        return False
    required_languages = set(normalize_list((requirements or {}).get("languages")))
    if required_languages and not required_languages.intersection(set(candidate.get("languages") or [])):
        return False
    required_specialties = set(normalize_list((requirements or {}).get("specialties")))
    if required_specialties and not required_specialties.intersection(set(candidate.get("specialties") or [])):
        return False
    return True


def score_candidate(candidate, requirements):
    optimize_for = normalize((requirements or {}).get("optimize_for") or "balanced")
    quality = int(candidate.get("quality_tier") or 3)
    speed = int(candidate.get("speed_tier") or 3)
    cost = int(candidate.get("cost_tier") or 3)
    context = int(candidate.get("context_tokens") or 0)
    if optimize_for == "cost":
        return ((6 - cost) * 10) + speed + quality + min(context // 100000, 10)
    if optimize_for == "speed":
        return (speed * 10) + quality + (6 - cost) + min(context // 100000, 10)
    if optimize_for == "context":
        return min(context // 10000, 1000) + quality + speed + (6 - cost)
    return (quality * 8) + (speed * 4) + (6 - cost) + min(context // 100000, 10)


def fallback_candidate(registry):
    candidates_by_id = {candidate["id"]: candidate for candidate in all_candidates(registry) if candidate.get("enabled")}
    default_id = normalize(registry.get("default_candidate") or "")
    selected = candidates_by_id.get(default_id) or next(iter(candidates_by_id.values()), None)
    if selected:
        selected = dict(selected)
        selected["selection_reason"] = "fallback_default"
    return selected


def select_candidate(registry, mode=None, requested_model=None, requirements=None):
    requirements = requirements or {}
    candidates_by_id = {candidate["id"]: candidate for candidate in all_candidates(registry) if candidate.get("enabled")}
    requested_candidate_id = candidate_id_for_request(registry, requested_model=requested_model, mode=mode)
    direct = candidates_by_id.get(requested_candidate_id)
    if direct and matches_requirements(direct, mode if not requested_model else None, requirements):
        selected = dict(direct)
        selected["selection_reason"] = "requested" if requested_model else "mode_default"
        return selected

    matches = [
        candidate
        for candidate in candidates_by_id.values()
        if matches_requirements(candidate, mode, requirements)
    ]
    if matches:
        selected = max(matches, key=lambda candidate: (score_candidate(candidate, requirements), candidate["id"]))
        selected = dict(selected)
        selected["selection_reason"] = "best_capability"
        return selected
    return fallback_candidate(registry)


def requirements_from_request(body):
    raw = {}
    for key in ("capability_requirements", "requirements", "workflow_requirements"):
        if isinstance(body.get(key), dict):
            raw.update(body[key])
    if body.get("language"):
        raw.setdefault("languages", [body.get("language")])
    if body.get("specialty"):
        raw.setdefault("specialties", [body.get("specialty")])
    if body.get("optimize_for"):
        raw["optimize_for"] = body.get("optimize_for")
    if body.get("min_context_tokens"):
        raw["min_context_tokens"] = body.get("min_context_tokens")
    return raw


def select_backend_model(body, registry=None):
    registry = registry or load_capability_registry()
    mode = body.get("workflow_step") or body.get("mode")
    requested_model = body.get("model")
    selected = select_candidate(
        registry,
        mode=mode,
        requested_model=requested_model,
        requirements=requirements_from_request(body),
    )
    if not selected:
        return None
    return selected.get("backend_model"), selected
