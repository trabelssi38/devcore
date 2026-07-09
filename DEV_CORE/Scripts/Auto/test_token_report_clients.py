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
    memory.mkdir(parents=True)
    reports.mkdir(parents=True)
    (memory / "tasks.json").write_text(
        json.dumps(
            {
                "project": "devcore",
                "current_task": None,
                "tasks": [
                    {"id": "T-96", "title": "codex dispatcher", "status": "done"},
                    {"id": "T-97", "title": "codex secrets", "status": "done"},
                    {"id": "T-42", "title": "claude task", "status": "done"},
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
        home / ".claude" / "projects" / "C--devcore" / "claude-session.jsonl",
        [
            {
                "timestamp": "2026-07-09T00:20:00Z",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "finished T-42"}]},
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
