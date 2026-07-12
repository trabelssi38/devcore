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
            "event_bus_recent": "<div>events</div>",
            "knowledge_graph_summary": "<div>knowledge</div>",
            "plugin_status": "<div>plugins</div>",
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
    assert result["sections"]["event_bus_recent"] == "<div>events</div>"
    assert result["sections"]["knowledge_graph_summary"] == "<div>knowledge</div>"
    assert result["sections"]["plugin_status"] == "<div>plugins</div>"
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


def test_run_plugin_check_invokes_dc_plugin_check_json():
    dashboard_api = load_dashboard_api()
    with patch.object(dashboard_api.subprocess, "run") as run:
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"ok": True, "action": "Check", "plugin": {"id": "python-fastapi"}}),
            stderr="",
        )

        result = dashboard_api.run_plugin_check("python-fastapi")

    assert result["ok"] is True
    assert result["plugin"]["id"] == "python-fastapi"
    command = run.call_args.args[0]
    assert any("dc.ps1" in str(part) for part in command)
    assert "plugin check python-fastapi --json" in command
    assert run.call_args.kwargs["timeout"] >= 45


def test_run_plugin_check_rejects_invalid_id():
    dashboard_api = load_dashboard_api()
    try:
        dashboard_api.run_plugin_check("../bad")
    except ValueError as exc:
        assert "Invalid plugin id" in str(exc)
    else:
        raise AssertionError("run_plugin_check should reject path-like plugin ids")


def test_dashboard_api_defaults_to_loopback_bind():
    dashboard_api = load_dashboard_api()
    assert dashboard_api.get_bind_host() == "127.0.0.1"


def test_dashboard_api_rejects_wildcard_bind_without_explicit_opt_in():
    dashboard_api = load_dashboard_api()
    previous = os.environ.get("DEVCORE_DASHBOARD_BIND")
    os.environ["DEVCORE_DASHBOARD_BIND"] = "0.0.0.0"
    try:
        try:
            dashboard_api.get_bind_host()
        except ValueError as exc:
            assert "DEVCORE_ALLOW_PUBLIC_BIND" in str(exc)
        else:
            raise AssertionError("wildcard bind should require explicit opt-in")
    finally:
        if previous is None:
            os.environ.pop("DEVCORE_DASHBOARD_BIND", None)
        else:
            os.environ["DEVCORE_DASHBOARD_BIND"] = previous


def test_local_auth_token_lifecycle(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    token = dashboard_api.ensure_api_token()
    assert len(token) >= 32
    assert dashboard_api.validate_api_token(token) is True
    assert dashboard_api.validate_api_token("bad-token") is False

    rotated = dashboard_api.rotate_api_token()
    assert rotated != token
    assert dashboard_api.validate_api_token(rotated) is True
    assert dashboard_api.validate_api_token(token) is False


def test_authorization_header_requires_bearer_token(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)
    token = dashboard_api.ensure_api_token()

    assert dashboard_api.is_authorized({"Authorization": f"Bearer {token}"}) is True
    assert dashboard_api.is_authorized({"Authorization": token}) is False
    assert dashboard_api.is_authorized({}) is False


def test_public_paths_do_not_require_authentication():
    dashboard_api = load_dashboard_api()
    assert dashboard_api.requires_authentication("/") is False
    assert dashboard_api.requires_authentication("/index.html") is False
    assert dashboard_api.requires_authentication("/api/status") is False
    assert dashboard_api.requires_authentication("/api/settings") is True
    assert dashboard_api.requires_authentication("/api/done") is True


def test_cors_defaults_to_local_allowlist():
    dashboard_api = load_dashboard_api()
    origins = dashboard_api.get_allowed_origins()
    assert "*" not in origins
    assert "http://127.0.0.1:20129" in origins
    assert "http://localhost:20129" in origins
    assert dashboard_api.is_origin_allowed("http://127.0.0.1:20129") is True
    assert dashboard_api.is_origin_allowed("https://evil.example") is False


def test_csrf_token_lifecycle(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    token = dashboard_api.ensure_csrf_token()
    assert len(token) >= 32
    assert dashboard_api.validate_csrf_token(token) is True
    assert dashboard_api.validate_csrf_token("bad-token") is False


def test_mutating_requests_require_csrf():
    dashboard_api = load_dashboard_api()
    assert dashboard_api.requires_csrf("GET", "/api/dashboard") is False
    assert dashboard_api.requires_csrf("OPTIONS", "/api/done") is False
    assert dashboard_api.requires_csrf("POST", "/api/done") is True
    assert dashboard_api.requires_csrf("DELETE", "/api/delete") is True


def test_request_body_limit_is_bounded():
    dashboard_api = load_dashboard_api()
    assert dashboard_api.get_max_request_body_bytes() <= 1024 * 1024
    assert dashboard_api.is_request_too_large({"Content-Length": str(1024 * 1024 + 1)}) is True
    assert dashboard_api.is_request_too_large({"Content-Length": "128"}) is False


def test_project_tasks_file_rejects_path_traversal(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    try:
        dashboard_api.get_project_tasks_file("../outside")
    except ValueError as exc:
        assert "Invalid project" in str(exc)
    else:
        raise AssertionError("project path traversal should be rejected")


def test_project_tasks_file_is_confined_to_memory_root(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    tasks_file = dashboard_api.get_project_tasks_file("devcore")

    assert tasks_file == (tmp_path / "Memory" / "devcore" / "tasks.json").resolve()
    assert tasks_file.relative_to((tmp_path / "Memory").resolve())


def test_dashboard_settings_do_not_return_secret_keys(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.PLATFORM_ROOT = str(tmp_path / "DEV_CORE")
    dashboard_api.DATA_ROOT = str(tmp_path / "DEV_CORE_DATA")

    handler = object.__new__(dashboard_api.DashboardAPIHandler)
    settings = handler.get_settings()

    assert "gemini_api_key" not in settings
    assert "anthropic_api_key" not in settings


def test_dashboard_settings_separate_config_secrets_and_runtime_state(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.PLATFORM_ROOT = str(tmp_path / "DEV_CORE")
    dashboard_api.DATA_ROOT = str(tmp_path / "DEV_CORE_DATA")

    handler = object.__new__(dashboard_api.DashboardAPIHandler)
    handler.save_settings(
        {
            "active_client": "codex",
            "auto_refresh_seconds": 30,
            "gemini_api_key": "GEMINI_SECRET_VALUE",
            "anthropic_api_key": "ANTHROPIC_SECRET_VALUE",
            "services": {"dashboard_api": True},
        }
    )

    config_text = (tmp_path / "DEV_CORE" / "Config" / "settings.json").read_text(encoding="utf-8")
    config = json.loads(config_text)
    secrets = json.loads(
        (tmp_path / "DEV_CORE_DATA" / "Security" / "dashboard_settings_secrets.json").read_text(encoding="utf-8")
    )
    active_client = (tmp_path / "DEV_CORE_DATA" / "Runtime" / "active_client.txt").read_text(encoding="utf-8")

    assert "GEMINI_SECRET_VALUE" not in config_text
    assert "ANTHROPIC_SECRET_VALUE" not in config_text
    assert "gemini_api_key" not in config
    assert "anthropic_api_key" not in config
    assert secrets["gemini_api_key"] == "GEMINI_SECRET_VALUE"
    assert secrets["anthropic_api_key"] == "ANTHROPIC_SECRET_VALUE"
    assert active_client == "codex"
    assert not (tmp_path / "DEV_CORE" / "Config" / "active_client.txt").exists()


def test_gen_dashboard_payload_includes_context_composition(tmp_path):
    platform_root = MODULE_PATH.parents[1]
    data_root = tmp_path / "DEV_CORE_DATA"
    memory_root = data_root / "Memory"
    project_root = memory_root / "devcore"
    scenario_root = memory_root / "Scenarios"
    project_root.mkdir(parents=True)
    scenario_root.mkdir(parents=True)
    plugins_root = data_root / "Plugins"
    plugins_root.mkdir(parents=True)
    checks_root = plugins_root / "checks"
    checks_root.mkdir(parents=True)
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
    (plugins_root / "plugins_registry.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-07-11T10:00:00+01:00",
                "plugins_count": 1,
                "plugins": [
                    {
                        "id": "python-fastapi",
                        "name": "Python FastAPI",
                        "version": "0.1.0",
                        "enabled": True,
                        "capabilities": {
                            "commands": ["python-api:new-endpoint"],
                            "skills": ["python_api"],
                            "health_checks": [
                                {
                                    "id": "python-version",
                                    "command": "Write-Output 'python-ok'",
                                    "required": True,
                                    "timeout_seconds": 5,
                                }
                            ],
                            "widgets": [],
                            "templates": ["fastapi-endpoint"],
                        },
                        "permissions": {
                            "write_roots": ["data"],
                            "allow_out_of_scope_write": False,
                        },
                        "installed_manifest_path": str(plugins_root / "installed" / "python-fastapi" / "plugin.json"),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (checks_root / "python-fastapi-last.json").write_text(
        json.dumps(
            {
                "ok": True,
                "checked_at": "2026-07-11T16:55:00+01:00",
                "plugin": {"id": "python-fastapi"},
                "health_checks_count": 1,
                "required_failures": 0,
                "health_checks": [],
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
    assert "Event Bus" in payload["sections"]["event_bus_recent"]
    assert "Knowledge Graph" in payload["sections"]["knowledge_graph_summary"]
    plugin_html = payload["sections"]["plugin_status"]
    assert "Plugin SDK" in plugin_html
    assert "python-fastapi" in plugin_html
    assert "Health checks" in plugin_html
    assert "Last check" in plugin_html
    assert "data-plugin-id=\"python-fastapi\"" in plugin_html
    assert "checkPlugin" in plugin_html
