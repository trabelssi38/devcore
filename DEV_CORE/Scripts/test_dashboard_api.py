import importlib.util
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest


MODULE_PATH = Path(__file__).with_name("dashboard_api.py")


def load_dashboard_api():
    spec = importlib.util.spec_from_file_location("dashboard_api_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_dashboard_payload_uses_stable_json_contract(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)
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
    payload_path = dashboard_api.get_cached_dashboard_payload_path()
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with patch.object(dashboard_api.subprocess, "run") as run:
        result = dashboard_api.build_dashboard_payload()
    run.assert_not_called()


    assert result["schema_version"] == 1
    assert result["sections"]["tasks_pipeline"] == "<div>tasks</div>"
    assert result["sections"]["context_composition"] == "<div>context</div>"
    assert result["sections"]["metrics_service_summary"] == "<div>metrics</div>"
    assert result["sections"]["event_bus_recent"] == "<div>events</div>"
    assert result["sections"]["knowledge_graph_summary"] == "<div>knowledge</div>"
    assert result["sections"]["plugin_status"] == "<div>plugins</div>"
    assert result["task_details"]["devcore_T-113"] == "details"


def test_build_dashboard_payload_rejects_unknown_schema(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)
    payload_path = dashboard_api.get_cached_dashboard_payload_path()
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")

    try:
        dashboard_api.build_dashboard_payload()
    except RuntimeError as exc:
        assert "Unsupported dashboard schema" in str(exc)
    else:
        raise AssertionError("build_dashboard_payload should reject unknown schemas")


def test_load_dashboard_read_model_uses_runtime_snapshot(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)
    snapshot_path = tmp_path / "Dashboard" / "read_model.json"
    snapshot_path.parent.mkdir(parents=True)
    snapshot_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": {"cursor": {"total_events": 3}},
                "dashboard": {"last_refresh": {"status": "success"}},
            }
        ),
        encoding="utf-8",
    )

    model = dashboard_api.load_dashboard_read_model()

    assert model["schema_version"] == 1
    assert model["events"]["cursor"]["total_events"] == 3


def test_dashboard_resource_paginates_read_model_list(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)
    snapshot_path = tmp_path / "Dashboard" / "read_model.json"
    snapshot_path.parent.mkdir(parents=True)
    snapshot_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": {
                    "recent": [
                        {"id": "evt-1"},
                        {"id": "evt-2"},
                        {"id": "evt-3"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    with patch.object(dashboard_api.subprocess, "run") as run:
        page = dashboard_api.build_dashboard_resource("read_model.events.recent", page=2, page_size=2)

    assert page["resource"] == "read_model.events.recent"
    assert page["page"] == 2
    assert page["page_size"] == 2
    assert page["total"] == 3
    assert page["has_next"] is False
    assert [item["id"] for item in page["items"]] == ["evt-3"]
    run.assert_not_called()


def test_dashboard_resource_rejects_invalid_pagination(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    try:
        dashboard_api.build_dashboard_resource("read_model.events.recent", page=0, page_size=500)
    except ValueError as exc:
        assert "page" in str(exc)
    else:
        raise AssertionError("invalid pagination should be rejected")


def test_dashboard_get_paths_do_not_call_powershell_subprocess():
    dashboard_api = load_dashboard_api()

    assert "subprocess.run" not in dashboard_api.build_dashboard_payload.__code__.co_names
    assert "subprocess.run" not in dashboard_api.build_dashboard_resource.__code__.co_names


def test_cached_json_response_returns_304_for_matching_etag():
    dashboard_api = load_dashboard_api()
    payload = {"schema_version": 1, "items": [{"id": "evt-1"}]}

    first = dashboard_api.build_cached_json_response(payload, {})
    second = dashboard_api.build_cached_json_response(payload, {"If-None-Match": first["headers"]["ETag"]})

    assert first["status"] == 200
    assert first["headers"]["ETag"].startswith('"sha256-')
    assert second["status"] == 304
    assert second["body"] == b""
    assert second["headers"]["ETag"] == first["headers"]["ETag"]


def test_cached_json_response_gzips_when_client_accepts_gzip():
    dashboard_api = load_dashboard_api()
    payload = {"items": [{"text": "x" * 2048}]}

    response = dashboard_api.build_cached_json_response(payload, {"Accept-Encoding": "br, gzip"})

    assert response["status"] == 200
    assert response["headers"]["Content-Encoding"] == "gzip"
    assert response["headers"]["Vary"] == "Accept-Encoding"
    assert json.loads(gzip.decompress(response["body"]).decode("utf-8")) == payload


def test_dashboard_delta_detects_changed_top_level_read_model_keys():
    dashboard_api = load_dashboard_api()
    previous = {"events": {"cursor": {"total_events": 1}}, "tasks": {"active": "T-1"}}
    current = {"events": {"cursor": {"total_events": 2}}, "tasks": {"active": "T-1"}}

    delta = dashboard_api.build_dashboard_delta(previous, current)

    assert delta["schema_version"] == 1
    assert delta["has_changes"] is True
    assert delta["changed_keys"] == ["events"]
    assert delta["read_model"]["events"]["cursor"]["total_events"] == 2


def test_sse_event_format_uses_named_event_and_json_data():
    dashboard_api = load_dashboard_api()

    event = dashboard_api.format_sse_event("dashboard.delta", {"changed_keys": ["events"]}, event_id="abc")

    assert event.endswith(b"\n\n")
    assert b"id: abc\n" in event
    assert b"event: dashboard.delta\n" in event
    assert b'data: {"changed_keys":["events"]}\n' in event


def test_dashboard_cached_payload_response_stays_under_transport_budget(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)
    payload_path = dashboard_api.get_cached_dashboard_payload_path()
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "Dashboard" / "read_model.json").write_text(
        json.dumps({"schema_version": 1, "events": {"recent": [{"id": "evt-1"}]}}),
        encoding="utf-8",
    )
    payload_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-07-12T10:00:00+01:00",
                "sections": {f"section_{idx}": "x" * 65536 for idx in range(8)},
                "task_details": {},
                "token_metrics": {},
            }
        ),
        encoding="utf-8",
    )

    started = time.perf_counter()
    payload = dashboard_api.build_dashboard_payload()
    response = dashboard_api.build_cached_json_response(payload, {"Accept-Encoding": "gzip"})
    elapsed = time.perf_counter() - started

    assert payload["cache"]["hit"] is True
    assert response["headers"]["Content-Encoding"] == "gzip"
    assert int(response["headers"]["Content-Length"]) < 50 * 1024
    assert elapsed < 0.5


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
    assert dashboard_api.requires_authentication("/favicon.ico") is False
    assert dashboard_api.requires_authentication("/api/status") is False
    assert dashboard_api.requires_authentication("/api/settings") is True
    assert dashboard_api.requires_authentication("/api/done") is True


def test_dashboard_template_token_report_is_null_safe():
    template = (MODULE_PATH.parents[1] / "Dashboard" / "template.html").read_text(encoding="utf-8")

    assert "metrics.totals.tokens" not in template
    assert "const totals = metrics.totals || {};" in template
    assert "Number(totals.tokens || 0)" in template


def test_dashboard_template_password_inputs_have_hidden_username_context():
    template = (MODULE_PATH.parents[1] / "Dashboard" / "template.html").read_text(encoding="utf-8")

    assert 'autocomplete="username"' in template
    assert 'value="devcore-dashboard-settings"' in template


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

    settings = dashboard_api.get_settings()

    assert "gemini_api_key" not in settings
    assert "anthropic_api_key" not in settings


def test_dashboard_settings_separate_config_secrets_and_runtime_state(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.PLATFORM_ROOT = str(tmp_path / "DEV_CORE")
    dashboard_api.DATA_ROOT = str(tmp_path / "DEV_CORE_DATA")

    dashboard_api.save_settings(
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
    if os.environ.get("DEVCORE_SKIP_DASHBOARD") == "1":
        pytest.skip("dashboard generation integration is skipped in bounded CI")

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


def test_gen_dashboard_html_generation_writes_api_payload_cache(tmp_path):
    if os.environ.get("DEVCORE_SKIP_DASHBOARD") == "1":
        pytest.skip("dashboard generation integration is skipped in bounded CI")

    source_platform_root = MODULE_PATH.parents[1]
    platform_root = tmp_path / "DEV_CORE"
    data_root = tmp_path / "DEV_CORE_DATA"
    dashboard_root = platform_root / "Dashboard"
    memory_root = data_root / "Memory"
    project_root = memory_root / "devcore"
    scenario_root = memory_root / "Scenarios"
    dashboard_root.mkdir(parents=True)
    project_root.mkdir(parents=True)
    scenario_root.mkdir(parents=True)
    shutil.copyfile(source_platform_root / "Dashboard" / "template.html", dashboard_root / "template.html")
    (memory_root / "persona.md").write_text("api persona preference", encoding="utf-8")
    (scenario_root / "coding.md").write_text("coding api context composition", encoding="utf-8")
    (project_root / "tasks.json").write_text(
        json.dumps(
            {
                "project": "devcore",
                "current_task": "T-199",
                "tasks": [
                    {
                        "id": "T-199",
                        "title": "dashboard cache contract",
                        "mode": "coding",
                        "status": "done",
                        "steps_done": 1,
                        "steps_total": 1,
                        "completed_at": "2026-07-13T12:30:00+01:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DEVCORE_PLATFORM_ROOT"] = str(platform_root)
    env["DEVCORE_DATA_ROOT"] = str(data_root)

    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(source_platform_root / "Scripts" / "gen_dashboard.ps1"),
            "-SkipTokenRefresh",
        ],
        cwd=source_platform_root.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )

    payload_path = data_root / "Dashboard" / "dashboard_payload.json"
    assert (dashboard_root / "index.html").exists()
    assert payload_path.exists()
    payload = json.loads(payload_path.read_text(encoding="utf-8-sig"))
    assert payload["schema_version"] == 1
    assert "T-199" in payload["sections"]["tasks_pipeline"]
    assert "Composition du Contexte" in payload["sections"]["context_composition"]
    assert payload["sections"]["metrics_service_summary"]
    assert payload["sections"]["event_bus_recent"]


def test_complete_task_active_task_updates_status_case_insensitively(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    memory_root = tmp_path / "Memory" / "devcore"
    memory_root.mkdir(parents=True)
    tasks_json = memory_root / "tasks.json"
    tasks_json.write_text(
        json.dumps({
            "project": "devcore",
            "current_task": "T-301",
            "tasks": [
                {
                    "id": "T-301",
                    "title": "Active Task Test",
                    "status": "active",
                    "steps_done": 0,
                    "steps_total": 2
                }
            ]
        }),
        encoding="utf-8"
    )

    success, msg = dashboard_api.complete_task("devcore", "t-301")
    assert success is True

    updated_board = json.loads(tasks_json.read_text(encoding="utf-8"))
    task = updated_board["tasks"][0]
    assert task["status"] == "done"
    assert task["steps_done"] == 2
    assert "completed_at" in task


def test_delete_task_case_insensitive_matching(tmp_path):
    dashboard_api = load_dashboard_api()
    dashboard_api.DATA_ROOT = str(tmp_path)

    memory_root = tmp_path / "Memory" / "devcore"
    memory_root.mkdir(parents=True)
    tasks_json = memory_root / "tasks.json"
    tasks_json.write_text(
        json.dumps({
            "project": "devcore",
            "current_task": "T-302",
            "tasks": [
                {
                    "id": "T-302",
                    "title": "Task To Delete",
                    "status": "todo",
                    "steps_done": 0,
                    "steps_total": 1
                }
            ]
        }),
        encoding="utf-8"
    )

    success, msg = dashboard_api.delete_task("DEVCORE", "t-302")
    assert success is True

    updated_board = json.loads(tasks_json.read_text(encoding="utf-8"))
    assert len(updated_board["tasks"]) == 0
    assert updated_board["current_task"] is None


def test_async_memory_pipeline_structure():
    import asyncio
    dashboard_api = load_dashboard_api()

    async def run_test():
        res = await dashboard_api.search_memory_pipeline_async("test query", collections=["decisions", "lessons"])
        assert res["query"] == "test query"
        assert "collections" in res
        assert "decisions" in res["collections"]
        assert "lessons" in res["collections"]

    asyncio.run(run_test())


