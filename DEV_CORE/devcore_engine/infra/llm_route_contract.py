"""Shared route configuration and fail-closed health validation, without I/O."""
PORTS = {"native": 8787, "auxiliary": 8789}
NATIVE_TARGETS = {
    "openai_api_url": "https://api.openai.com",
    "anthropic_api_url": "https://api.anthropic.com",
    "gemini_api_url": "https://generativelanguage.googleapis.com",
    "cloudcode_api_url": "https://cloudcode-pa.googleapis.com",
    "vertex_api_url": "https://us-central1-aiplatform.googleapis.com",
}


def profile(route: str) -> dict:
    if route not in PORTS:
        raise ValueError("Unknown route")
    targets = NATIVE_TARGETS if route == "native" else {
        key: "http://127.0.0.1:20130" for key in NATIVE_TARGETS
    }
    return dict(targets, host="127.0.0.1", port=PORTS[route], backend="anthropic",
                model_router=None, stateless=True, memory_enabled=False,
                disable_kompress=True, lossless=True, ccr_inject_tool=False,
                ccr_inject_marker=False, ccr_handle_responses=False)


def validate_health(payload: dict, route: str) -> bool:
    expected = profile(route)
    if not isinstance(payload, dict):
        return False
    if (payload.get("service") != "headroom-devcore" or payload.get("route") != route
            or payload.get("status") != "ready" or type(payload.get("port")) is not int
            or payload["port"] != PORTS[route]):
        return False
    actual = payload.get("profile")
    if not isinstance(actual, dict):
        return False
    return all(key in actual and type(actual[key]) is type(value) and actual[key] == value
               for key, value in expected.items())
