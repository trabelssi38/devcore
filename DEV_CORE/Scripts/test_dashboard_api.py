import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("dashboard_api.py")


def load_dashboard_api():
    spec = importlib.util.spec_from_file_location("dashboard_api_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_dashboard_payload_uses_stable_json_contract():
    dashboard_api = load_dashboard_api()
    payload = {
        "schema_version": 1,
        "generated_at": "2026-07-09T10:00:00+01:00",
        "sections": {
            "project_cards": "<div>projects</div>",
            "tasks_pipeline": "<div>tasks</div>",
            "services_monitoring": "<div>services</div>",
            "automation_hooks": "<div>hooks</div>",
            "token_activity_report": "<details>tokens</details>",
        },
        "task_details": {"devcore_T-113": "details"},
        "token_metrics": {"total": {"tokens": 10}},
    }

    with patch.object(dashboard_api.subprocess, "run") as run:
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

        result = dashboard_api.build_dashboard_payload()

    assert result["schema_version"] == 1
    assert result["sections"]["tasks_pipeline"] == "<div>tasks</div>"
    assert result["task_details"]["devcore_T-113"] == "details"
    command = run.call_args.args[0]
    assert "gen_dashboard.ps1" in command[5]
    assert "-Json" in command
    assert "-SkipTokenRefresh" in command


def test_build_dashboard_payload_rejects_unknown_schema():
    dashboard_api = load_dashboard_api()
    with patch.object(dashboard_api.subprocess, "run") as run:
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"schema_version": 999}),
            stderr="",
        )

        try:
            dashboard_api.build_dashboard_payload()
        except RuntimeError as exc:
            assert "Unsupported dashboard schema" in str(exc)
        else:
            raise AssertionError("build_dashboard_payload should reject unknown schemas")
