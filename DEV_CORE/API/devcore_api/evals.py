from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def load_eval_dataset(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        raise ValueError("Unsupported eval dataset version")
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Eval dataset must define cases")
    return payload


def evaluate_cases(cases: list[dict[str, Any]], *, predictor: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    if total == 0:
        return {"total": 0, "route_accuracy": 0.0, "context_recall": 0.0}

    route_hits = 0
    context_scores: list[float] = []
    for case in cases:
        prediction = predictor(case)
        if prediction.get("route") == case.get("expected_route"):
            route_hits += 1

        required_context = set(case.get("required_context") or [])
        predicted_context = set(prediction.get("context") or [])
        if not required_context:
            context_scores.append(1.0)
        else:
            context_scores.append(len(required_context & predicted_context) / len(required_context))

    return {
        "total": total,
        "route_accuracy": route_hits / total,
        "context_recall": sum(context_scores) / total,
    }
