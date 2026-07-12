import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_slo_policy_file_defines_alerts_and_cost_budgets() -> None:
    policy_path = ROOT / "DEV_CORE" / "Config" / "slo_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    assert policy["version"] == 1
    assert policy["slo"]["api_availability_target"] >= 0.99
    assert policy["alerts"]["latency_p95_ms"] > 0
    assert policy["cost_budgets"]["daily_usd"] > 0


def test_slo_budget_evaluator_flags_latency_and_cost() -> None:
    from devcore_api.slo import evaluate_slo_budget

    result = evaluate_slo_budget(
        policy={
            "alerts": {"latency_p95_ms": 1000},
            "cost_budgets": {"daily_usd": 5.0},
        },
        snapshot={"latency_p95_ms": 1500, "daily_cost_usd": 6.0},
    )

    assert result["status"] == "breach"
    assert "latency_p95_ms" in result["breaches"]
    assert "daily_usd" in result["breaches"]


def test_slo_budget_evaluator_passes_within_budget() -> None:
    from devcore_api.slo import evaluate_slo_budget

    result = evaluate_slo_budget(
        policy={
            "alerts": {"latency_p95_ms": 1000},
            "cost_budgets": {"daily_usd": 5.0},
        },
        snapshot={"latency_p95_ms": 500, "daily_cost_usd": 3.0},
    )

    assert result == {"status": "ok", "breaches": []}
