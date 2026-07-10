import importlib.util
import json
import os
from pathlib import Path
import subprocess
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
            "context_composition": "<div>context</div>",
            "metrics_service_summary": "<div>metrics</div>",
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
    assert result["sections"]["context_composition"] == "<div>context</div>"
    assert result["sections"]["metrics_service_summary"] == "<div>metrics</div>"
    assert result["task_details"]["devcore_T-113"] == "details"
    command = run.call_args.args[0]
    assert "gen_dashboard.ps1" in command[5]
    assert "-Json" in command
    assert "-SkipTokenRefresh" in command
    assert run.call_args.kwargs["timeout"] >= 45


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


def test_gen_dashboard_payload_includes_context_composition(tmp_path):
    platform_root = MODULE_PATH.parents[1]
    data_root = tmp_path / "DEV_CORE_DATA"
    memory_root = data_root / "Memory"
    project_root = memory_root / "devcore"
    scenario_root = memory_root / "Scenarios"
    project_root.mkdir(parents=True)
    scenario_root.mkdir(parents=True)
    (memory_root / "persona.md").write_text("api persona preference", encoding="utf-8")
    (scenario_root / "coding.md").write_text("coding api context composition", encoding="utf-8")
    (project_root / "tasks.json").write_text(
        json.dumps(
            {
                "project": "devcore",
                "current_task": "T-117",
                "tasks": [
                    {
                        "id": "T-117",
                        "title": "api context composition",
                        "mode": "coding",
                        "status": "active",
                        "steps_done": 0,
                        "steps_total": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(platform_root)
    env["DEVCORE_DATA_ROOT"] = str(data_root)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(platform_root / "Scripts" / "gen_dashboard.ps1"),
            "-Json",
            "-SkipTokenRefresh",
        ],
        cwd=platform_root.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    payload = json.loads(result.stdout)
    context_html = payload["sections"]["context_composition"]
    assert "Composition du Contexte" in context_html
    assert "L3:persona" in context_html
    assert "L2:scenario:coding" in context_html
    assert "Metrics Service" in payload["sections"]["metrics_service_summary"]
