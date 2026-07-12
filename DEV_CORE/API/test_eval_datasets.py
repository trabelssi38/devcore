import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def test_routing_dataset_is_versioned_and_loadable() -> None:
    from devcore_api.evals import load_eval_dataset

    dataset = load_eval_dataset(ROOT / "DEV_CORE" / "Evals" / "routing_context_dataset.json")

    assert dataset["version"] == 1
    assert len(dataset["cases"]) >= 3
    assert {"id", "input", "expected_route", "required_context"}.issubset(dataset["cases"][0])


def test_eval_runner_scores_route_and_context_matches() -> None:
    from devcore_api.evals import evaluate_cases

    cases = [
        {
            "id": "case-1",
            "input": "Need API work",
            "expected_route": "python_api",
            "required_context": ["trace_id", "project_id"],
        }
    ]

    result = evaluate_cases(
        cases,
        predictor=lambda case: {"route": "python_api", "context": ["trace_id", "project_id", "extra"]},
    )

    assert result["total"] == 1
    assert result["route_accuracy"] == 1.0
    assert result["context_recall"] == 1.0


def test_dataset_file_is_valid_json() -> None:
    dataset_path = ROOT / "DEV_CORE" / "Evals" / "routing_context_dataset.json"
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))

    assert payload["name"] == "routing_context_eval"
