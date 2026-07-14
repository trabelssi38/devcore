import importlib.util
from pathlib import Path


def load_router():
    path = Path(__file__).with_name("gemini_router.py")
    spec = importlib.util.spec_from_file_location("gemini_router", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mode_profile_selects_gemini_model():
    router = load_router()

    reasoning = router.map_for_gemini({"messages": [], "mode": "reasoning"}, is_chat=True)
    assert reasoning["model"] == "gemini-2.5-pro"

    coding = router.map_for_gemini({"messages": [], "mode": "coding"}, is_chat=True)
    assert coding["model"] == "gemini-2.5-pro"

    bulk = router.map_for_gemini({"messages": [], "mode": "bulk"}, is_chat=True)
    assert bulk["model"] == "gemini-2.5-flash"


def test_model_profile_names_are_supported():
    router = load_router()

    mapped = router.map_for_gemini({"messages": [], "model": "devcore-bulk"}, is_chat=True)
    assert mapped["model"] == "gemini-2.5-flash"

    mapped = router.map_for_gemini({"messages": [], "model": "devcore-reasoning"}, is_chat=True)
    assert mapped["model"] == "gemini-2.5-pro"


def test_capability_requirements_can_override_mode_default():
    router = load_router()

    mapped = router.map_for_gemini(
        {
            "messages": [],
            "mode": "coding",
            "capability_requirements": {
                "languages": ["javascript"],
                "specialties": ["tests"],
                "optimize_for": "speed",
            },
        },
        is_chat=True,
    )

    assert mapped["model"] == "gemini-2.5-flash"
    assert "capability_requirements" not in mapped
