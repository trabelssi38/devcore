from __future__ import annotations

from typing import Any


def evaluate_slo_budget(*, policy: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    breaches: list[str] = []

    latency_limit = policy.get("alerts", {}).get("latency_p95_ms")
    if latency_limit is not None and snapshot.get("latency_p95_ms", 0) > latency_limit:
        breaches.append("latency_p95_ms")

    daily_budget = policy.get("cost_budgets", {}).get("daily_usd")
    if daily_budget is not None and snapshot.get("daily_cost_usd", 0.0) > daily_budget:
        breaches.append("daily_usd")

    return {"status": "breach" if breaches else "ok", "breaches": breaches}
