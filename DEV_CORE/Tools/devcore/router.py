# router.py — DEV_CORE v7.3
# Routing IA avec scoring + mission awareness + skills routing

from devcore.contracts import validate_contract


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


def recommend_engine(task_type: str, urgency: str, volume: str) -> dict:
    scores = {"claude": 0, "codex": 0, "gemini": 0}

    if task_type in {"bugfix", "refactor", "coding"}:
        scores["codex"] += 3
    if task_type in {"architecture", "incident", "review"}:
        scores["claude"] += 3
    if task_type in {"migration", "bulk", "automation"}:
        scores["gemini"] += 3

    if urgency == "urgent":
        scores["claude"] += 2
    if volume == "large":
        scores["gemini"] += 2
    if volume == "small":
        scores["codex"] += 1

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    recommended_skill = SKILL_ROUTING.get(task_type)

    decision = {
        "engine": ranked[0][0],
        "confidence": round(ranked[0][1] / max(sum(scores.values()), 1), 2),
        "fallback": ranked[1][0],
        "reason": f"task_type={task_type}, urgency={urgency}, volume={volume}",
        "recommended_skill": recommended_skill,
    }
    validate_contract("router-decision", decision)
    return decision
