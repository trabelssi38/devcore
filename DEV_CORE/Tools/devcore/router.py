# router.py — DEV_CORE v10.0
# Declarative Routing IA via Config/harness_profiles.json

import json
from pathlib import Path
from devcore.contracts import validate_contract
from devcore.paths import get_paths


SKILL_ROUTING = {
    "vault":        "obsidian",
    "memory":       "qdrant",
    "ui":           "ui-ux",
    "design":       "ui-ux",
    "incident":     "fabric-patterns",
    "analysis":     "fabric-patterns",
    "postmortem":   "fabric-patterns",
    "coding":       "dev-methodology",
    "bugfix":       "dev-methodology",
    "architecture": "dev-methodology",
    "review":       "dev-methodology",
    "android":      "android_release",
    "python":       "python_api",
    "web":          "web_ui",
}


def load_harness_profiles() -> dict:
    """Load declarative harness profiles from configuration."""
    try:
        paths = get_paths()
        config_path = paths.platform_root / "Config" / "harness_profiles.json"
        if config_path.exists():
            return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    # Fallback default configuration if file is missing or corrupted
    return {
        "default_harness": "coding",
        "harnesses": {
            "reasoning": {"engine": "gemini", "fallback_harness": "coding"},
            "coding": {"engine": "gemini", "fallback_harness": "reasoning"},
            "bulk": {"engine": "gemini", "fallback_harness": "coding"},
            "claude_sonnet": {"engine": "claude", "fallback_harness": "reasoning"},
            "gemini_flash": {"engine": "gemini", "fallback_harness": "bulk"}
        },
        "routing_rules": [
            {"criteria": {"task_type": "architecture"}, "recommended_harness": "reasoning"},
            {"criteria": {"task_type": "review"}, "recommended_harness": "claude_sonnet"},
            {"criteria": {"task_type": "incident"}, "recommended_harness": "claude_sonnet"},
            {"criteria": {"task_type": "bugfix"}, "recommended_harness": "coding"},
            {"criteria": {"task_type": "refactor"}, "recommended_harness": "coding"},
            {"criteria": {"task_type": "coding"}, "recommended_harness": "coding"},
            {"criteria": {"task_type": "bulk"}, "recommended_harness": "bulk"},
            {"criteria": {"task_type": "migration"}, "recommended_harness": "bulk"},
            {"criteria": {"volume": "large"}, "recommended_harness": "gemini_flash"},
            {"criteria": {"urgency": "urgent"}, "recommended_harness": "coding"}
        ]
    }


def recommend_engine(task_type: str, urgency: str, volume: str) -> dict:
    """Select the harness and resolve the engine using declarative routing rules."""
    config = load_harness_profiles()
    harnesses = config.get("harnesses", {})
    rules = config.get("routing_rules", [])
    default_harness_name = config.get("default_harness", "coding")

    selected_harness_name = None
    match_reason = "default fallback"
    confidence = 0.5

    # Evaluate rules sequentially
    for rule in rules:
        criteria = rule.get("criteria", {})
        is_match = True
        for key, val in criteria.items():
            if key == "task_type" and task_type != val:
                is_match = False
            elif key == "urgency" and urgency != val:
                is_match = False
            elif key == "volume" and volume != val:
                is_match = False
        
        if is_match and criteria:
            selected_harness_name = rule.get("recommended_harness")
            criteria_str = ",".join(f"{k}={v}" for k, v in criteria.items())
            match_reason = f"rule matched ({criteria_str})"
            confidence = 1.0
            break

    if not selected_harness_name:
        selected_harness_name = default_harness_name

    # Resolve details of recommended harness
    harness = harnesses.get(selected_harness_name, {})
    engine = harness.get("engine", "gemini")
    fallback_harness_name = harness.get("fallback_harness", "coding")
    
    fallback_harness = harnesses.get(fallback_harness_name, {})
    fallback_engine = fallback_harness.get("engine", "gemini")

    recommended_skill = SKILL_ROUTING.get(task_type)

    decision = {
        "engine": engine,
        "confidence": confidence,
        "fallback": fallback_engine,
        "reason": f"task_type={task_type}, urgency={urgency}, volume={volume} -> profile={selected_harness_name} ({match_reason})",
        "recommended_skill": recommended_skill,
    }
    
    validate_contract("router-decision", decision)
    return decision
