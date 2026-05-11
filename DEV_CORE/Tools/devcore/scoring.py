import json

from devcore.paths import get_paths


def score_engine_effectiveness(events: list[dict]) -> dict:
    scores: dict[str, dict] = {}
    for event in events:
        engine = event["engine"]
        bucket = scores.setdefault(
            engine,
            {"completed": 0, "failed": 0, "rework_count": 0, "rework_rate": 0.0},
        )
        if event.get("status") == "completed":
            bucket["completed"] += 1
        if event.get("status") == "failed":
            bucket["failed"] += 1
        if event.get("rework"):
            bucket["rework_count"] += 1

    for bucket in scores.values():
        total_completed = bucket["completed"]
        bucket["rework_rate"] = (
            bucket["rework_count"] / total_completed if total_completed else 0.0
        )
    return scores


def score_prompt_patterns(events: list[dict]) -> dict:
    scores: dict[str, dict] = {}
    for event in events:
        pattern = event["prompt_pattern"]
        bucket = scores.setdefault(
            pattern,
            {"uses": 0, "completed": 0, "failed": 0},
        )
        bucket["uses"] += 1
        if event.get("status") == "completed":
            bucket["completed"] += 1
        if event.get("status") == "failed":
            bucket["failed"] += 1
    return scores


def write_score_snapshots(engine_scores: dict, prompt_scores: dict) -> dict:
    paths = get_paths()
    engine_path = paths.scoring_log_root / "engine-scores.json"
    prompt_path = paths.scoring_log_root / "prompt-scores.json"
    engine_path.write_text(json.dumps(engine_scores, indent=2), encoding="utf-8")
    prompt_path.write_text(json.dumps(prompt_scores, indent=2), encoding="utf-8")
    return {
        "engine_scores": engine_path,
        "prompt_scores": prompt_path,
    }
