import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("ai_capability_registry.py")


def load_registry_module():
    spec = importlib.util.spec_from_file_location("ai_capability_registry", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_registry(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "default_candidate": "balanced",
                "candidates": {
                    "balanced": {
                        "enabled": True,
                        "backend_model": "gemini-2.5-pro",
                        "workflow_modes": ["coding", "reasoning"],
                        "languages": ["python", "powershell"],
                        "specialties": ["implementation", "architecture"],
                        "context_tokens": 1048576,
                        "cost_tier": 3,
                        "speed_tier": 3,
                        "quality_tier": 4,
                    },
                    "cheap-fast": {
                        "enabled": True,
                        "backend_model": "gemini-2.5-flash",
                        "workflow_modes": ["bulk", "coding"],
                        "languages": ["javascript", "python"],
                        "specialties": ["bulk-edit", "tests"],
                        "context_tokens": 1048576,
                        "cost_tier": 1,
                        "speed_tier": 5,
                        "quality_tier": 3,
                    },
                    "disabled": {
                        "enabled": False,
                        "backend_model": "disabled-model",
                        "workflow_modes": ["coding"],
                    },
                },
                "aliases": {"devcore-coding": "balanced"},
                "mode_defaults": {"bulk": "cheap-fast"},
            }
        ),
        encoding="utf-8",
    )


def test_selects_mode_default_and_alias(tmp_path):
    registry_module = load_registry_module()
    registry_path = tmp_path / "ai_capability_registry.json"
    write_registry(registry_path)
    registry = registry_module.load_capability_registry(registry_path)

    selected = registry_module.select_candidate(registry, mode="bulk")
    assert selected["id"] == "cheap-fast"
    assert selected["backend_model"] == "gemini-2.5-flash"

    selected = registry_module.select_candidate(registry, requested_model="devcore-coding")
    assert selected["id"] == "balanced"


def test_selects_by_required_specialty_language_and_optimizer(tmp_path):
    registry_module = load_registry_module()
    registry_path = tmp_path / "ai_capability_registry.json"
    write_registry(registry_path)
    registry = registry_module.load_capability_registry(registry_path)

    selected = registry_module.select_candidate(
        registry,
        mode="coding",
        requirements={"languages": ["javascript"], "specialties": ["tests"], "optimize_for": "speed"},
    )

    assert selected["id"] == "cheap-fast"


def test_falls_back_when_no_candidate_matches(tmp_path):
    registry_module = load_registry_module()
    registry_path = tmp_path / "ai_capability_registry.json"
    write_registry(registry_path)
    registry = registry_module.load_capability_registry(registry_path)

    selected = registry_module.select_candidate(
        registry,
        mode="coding",
        requirements={"languages": ["rust"], "min_context_tokens": 2_000_000},
    )

    assert selected["id"] == "balanced"
    assert selected["selection_reason"] == "fallback_default"
