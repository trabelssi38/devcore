import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("token_report.py")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_multi_client_token_report(tmp_path):
    home = tmp_path / "home"
    data = tmp_path / "data"
    memory = data / "Memory" / "devcore"
    reports = data / "Logs" / "token_reports"
    config = tmp_path / "DEV_CORE" / "Config"
    memory.mkdir(parents=True)
    reports.mkdir(parents=True)
    config.mkdir(parents=True)
    (config / "model_pricing.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "default_model": "default-current",
                "models": {
                    "default-current": {"pricing_per_million_usd": {"input": 3.0, "cached_input": 0.45, "output": 15.0}},
                    "gpt-5.3-codex": {"pricing_per_million_usd": {"input": 1.75, "cached_input": 0.175, "output": 14.0}},
                    "gpt-5.5": {"pricing_per_million_usd": {"input": 2.0, "cached_input": 0.2, "output": 16.0}},
                    "claude-haiku-4-5": {"pricing_per_million_usd": {"input": 1.0, "cached_input": 0.1, "output": 5.0}},
                },
                "aliases": {},
                "client_defaults": {"codex desktop": "gpt-5.3-codex"},
            }
        ),
        encoding="utf-8",
    )
    (memory / "tasks.json").write_text(
        json.dumps(
            {
                "project": "devcore",
                "current_task": None,
                "tasks": [
                    {"id": "T-96", "title": "codex dispatcher", "status": "done"},
                    {"id": "T-97", "title": "codex secrets", "status": "done"},
                    {"id": "T-42", "title": "claude task", "status": "done"},
                    {"id": "T-99", "title": "antigravity model switch", "status": "done"},
                ],
            }
        ),
        encoding="utf-8",
    )

    write_jsonl(
        home / ".codex" / "sessions" / "2026" / "07" / "09" / "rollout-test.jsonl",
        [
            {
                "timestamp": "2026-07-09T00:10:00Z",
                "type": "session_meta",
                "payload": {"id": "codex-session", "cwd": str(tmp_path / "devcore"), "originator": "Codex Desktop"},
            },
            {
                "timestamp": "2026-07-09T00:10:30Z",
                "type": "turn_context",
                "payload": {"model": "gpt-5.5"},
            },
            {
                "timestamp": "2026-07-09T00:11:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "done [T-96] then [T-97]"}],
                    "token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 250,
                        "output_tokens": 200,
                        "total_tokens": 1200,
                    },
                },
            },
        ],
    )

    write_jsonl(
        home / ".gemini" / "antigravity" / "brain" / "ag-session" / ".system_generated" / "logs" / "transcript.jsonl",
        [
            {
                "created_at": "2026-07-09T00:30:00Z",
                "source": "USER_EXPLICIT",
                "type": "USER_INPUT",
                "model": "comment on this change if the user doesn't ask about it",
                "content": (
                    "<USER_REQUEST>continue [T-99]</USER_REQUEST>\n"
                    "<USER_SETTINGS_CHANGE>\n"
                    "The user changed setting `Model Selection` from None to Gemini 3.5 Flash (Medium). "
                    "No need to comment on this change if the user doesn't ask about it. "
                    "If reporting what model you are, please use a human readable name instead of the exact string.\n"
                    "</USER_SETTINGS_CHANGE>"
                ),
            },
            {
                "created_at": "2026-07-09T00:31:00Z",
                "source": "MODEL",
                "type": "PLANNER_RESPONSE",
                "content": "done [T-99]",
            },
        ],
    )

    write_jsonl(
        home / ".claude" / "projects" / "C--devcore" / "claude-session.jsonl",
        [
            {
                "timestamp": "2026-07-09T00:20:00Z",
                "type": "assistant",
                "message": {"model": "claude-haiku-4-5", "content": [{"type": "text", "text": "finished T-42"}]},
                "usage": {"input_tokens": 300, "cache_read_input_tokens": 30, "output_tokens": 70},
                "cwd": str(tmp_path / "devcore"),
            }
        ],
    )

    env = os.environ.copy()
    env["USERPROFILE"] = str(home)
    env["DEVCORE_DATA_ROOT"] = str(data)
    env["DEVCORE_PLATFORM_ROOT"] = str(tmp_path / "DEV_CORE")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--date", "2026-07-09"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "token_metrics_summary.json" in result.stdout

    summary = json.loads((reports / "token_metrics_summary.json").read_text(encoding="utf-8"))
    assert summary["tasks"]["devcore_T-96"]["tokens"] > 0
    assert summary["tasks"]["devcore_T-97"]["tokens"] > 0
    assert summary["tasks"]["devcore_T-42"]["tokens"] > 0

    sources = {session["client"] for session in summary["sessions"]}
    assert "codex" in sources
    assert "claude" in sources
    assert "antigravity" in sources

    codex_session = next(session for session in summary["sessions"] if session["client"] == "codex")
    claude_session = next(session for session in summary["sessions"] if session["client"] == "claude")
    antigravity_session = next(session for session in summary["sessions"] if session["client"] == "antigravity")
    assert codex_session["models"] == ["gpt-5.5"]
    assert claude_session["models"] == ["claude-haiku-4-5"]
    assert antigravity_session["models"] == ["gemini-3.5-flash"]
    assert codex_session["pricing_profiles"] == ["gpt-5.5"]
    assert claude_session["pricing_profiles"] == ["claude-haiku-4-5"]
    assert codex_session["cost_usd"] == 0.0047
    assert claude_session["cost_usd"] == 0.0006
    assert codex_session["model_turns"][0]["model"] == "gpt-5.5"
    assert codex_session["model_turns"][0]["source"] == "timeline"
    assert claude_session["model_turns"][0]["model"] == "claude-haiku-4-5"
    assert claude_session["model_turns"][0]["source"] == "payload"
    assert antigravity_session["model_turns"][0]["model"] == "gemini-3.5-flash"
    assert antigravity_session["model_turns"][0]["source"] == "timeline"
    assert summary["totals"]["model_usage"]["gpt-5.5"]["sources"]["timeline"] == 1
    assert summary["totals"]["model_usage"]["claude-haiku-4-5"]["sources"]["payload"] == 1
    assert summary["totals"]["model_usage"]["gemini-3.5-flash"]["sources"]["timeline"] == 1
    assert summary["tasks"]["devcore_T-96"]["model_usage"]["gpt-5.5"]["turns"] == 1
    assert summary["tasks"]["devcore_T-99"]["model_usage"]["gemini-3.5-flash"]["turns"] == 1
    assert summary["totals"]["cost_by_model"]["gpt-5.5"] == 0.0047
    assert summary["projects"]["devcore"]["cost_by_model"]["gpt-5.5"] == 0.0047
    assert summary["projects"]["devcore"]["cost_by_model"]["claude-haiku-4-5"] == 0.0006
    assert summary["model_costs"]["global"]["gemini-3.5-flash"] > 0
    assert summary["model_costs"]["projects"]["devcore"]["gemini-3.5-flash"] > 0
    assert all("no-need-to-comment" not in model for model in summary["model_costs"]["global"])
    assert all("comment-on-this-change" not in model for model in summary["model_costs"]["global"])
    assert all("ask-about-it" not in model for model in summary["model_costs"]["global"])
