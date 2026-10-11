"""Explicit auxiliary routing policy. No credentials, state or network access."""
import logging

MODEL_MAP = {
    "devcore-writing": "gemini-2.5-flash",
    "devcore-documentation": "gemini-2.5-flash",
    "devcore-summary": "gemini-2.5-flash",
    "devcore-bulk": "gemini-2.5-flash",
}
TASK_TYPES = {name: name.removeprefix("devcore-") for name in MODEL_MAP}
EMBEDDING_MODEL = "gemini-embedding-001"


def validate_auxiliary(body: dict, *, is_chat: bool = True) -> str:
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object")
    model = body.get("model")
    allowed = MODEL_MAP if is_chat else {EMBEDDING_MODEL: EMBEDDING_MODEL}
    if not isinstance(model, str) or model not in allowed:
        raise ValueError("Model refused: use an explicit auxiliary alias or the embedding model; native models belong on port 8787")
    fallbacks = body.get("fallback_providers", [])
    if not isinstance(fallbacks, list) or any(p not in ("cerebras", "nvidia") for p in fallbacks):
        raise ValueError("fallback_providers must be a list containing only cerebras and/or nvidia")
    if fallbacks and (not is_chat or body.get("stream")):
        raise ValueError("Fallback is supported only for non-streaming auxiliary completions")
    if body.get("task_type") not in (None, TASK_TYPES.get(model, "embedding")):
        raise ValueError("task_type conflicts with the explicit model alias")
    return model


def route_headers(body: dict, resolved_model: str, provider: str, *, is_chat: bool = True) -> dict:
    model = validate_auxiliary(body, is_chat=is_chat)
    logging.getLogger("devcore.routing").info(
        "route=auxiliary requested_model=%s resolved_model=%s provider=%s task_type=%s stage=resolution",
        model, resolved_model, provider, TASK_TYPES.get(model, "embedding"))
    return {
        "X-DevCore-Route": "auxiliary",
        "X-DevCore-Requested-Model": model,
        "X-DevCore-Resolved-Model": resolved_model,
        "X-DevCore-Provider": provider,
        "X-DevCore-Task-Type": TASK_TYPES.get(model, "embedding"),
    }


def strip_controls(body: dict) -> dict:
    return {key: value for key, value in body.items() if key not in {
        "fallback_providers", "task_type", "mode", "workflow_step",
        "capability_requirements", "requirements", "workflow_requirements",
        "language", "specialty", "optimize_for", "min_context_tokens",
    }}
