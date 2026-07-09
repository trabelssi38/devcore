import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("model_pricing_sync.py")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def registry_payload(manual_override=False):
    return {
        "schema_version": 1,
        "default_model": "default-current",
        "models": {
            "gpt-5.5": {
                "provider": "openai",
                "manual_override": manual_override,
                "pricing_per_million_usd": {
                    "input": 1.75,
                    "cached_input": 0.175,
                    "output": 14.0,
                },
            },
            "gemini-3.5-flash": {
                "provider": "google",
                "pricing_per_million_usd": {
                    "input": 0.3,
                    "cached_input": 0.03,
                    "output": 2.5,
                },
            },
        },
        "sources": {"openai": "unused"},
        "sync": {"auto_apply": False},
    }


def remote_payload():
    return {
        "models": {
            "gpt-5.5": {
                "pricing_per_million_usd": {
                    "input": 2.0,
                    "cached_input": 0.2,
                    "output": 16.0,
                }
            },
            "gemini-3.5-flash": {
                "pricing_per_million_usd": {
                    "input": 0.3,
                    "cached_input": 0.03,
                    "output": 2.5,
                }
            },
        }
    }


def run_sync(tmp_path, apply=False, manual_override=False):
    registry = tmp_path / "model_pricing.json"
    remote = tmp_path / "remote_catalog.json"
    report = tmp_path / "report.json"
    write_json(registry, registry_payload(manual_override=manual_override))
    write_json(remote, remote_payload())

    command = [
        sys.executable,
        str(SCRIPT),
        "--registry",
        str(registry),
        "--report-out",
        str(report),
        "--source",
        str(remote),
    ]
    if apply:
        command.append("--apply")
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result, json.loads(registry.read_text(encoding="utf-8")), json.loads(report.read_text(encoding="utf-8"))


def test_pricing_sync_reports_changes_without_apply(tmp_path):
    _, registry, report = run_sync(tmp_path)

    assert report["changes_count"] == 1
    assert report["applied"] is False
    assert report["changes"]["gpt-5.5"]["proposed"]["input"] == 2.0
    assert registry["models"]["gpt-5.5"]["pricing_per_million_usd"]["input"] == 1.75


def test_pricing_sync_applies_changes(tmp_path):
    _, registry, report = run_sync(tmp_path, apply=True)

    assert report["applied"] is True
    assert registry["models"]["gpt-5.5"]["pricing_per_million_usd"]["input"] == 2.0
    assert registry["models"]["gpt-5.5"]["last_updated_at"]


def test_pricing_sync_skips_manual_override(tmp_path):
    _, registry, report = run_sync(tmp_path, apply=True, manual_override=True)

    assert report["changes_count"] == 0
    assert "gpt-5.5" in report["skipped_manual"]
    assert registry["models"]["gpt-5.5"]["pricing_per_million_usd"]["input"] == 1.75


def test_pricing_sync_does_not_apply_text_scrape_by_default(tmp_path):
    registry = tmp_path / "model_pricing.json"
    remote = tmp_path / "remote_page.html"
    report = tmp_path / "report.json"
    write_json(registry, registry_payload())
    remote.write_text(
        "<html><body>gpt-5.5 input $2.00 cached input $0.20 output $16.00</body></html>",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--registry",
            str(registry),
            "--report-out",
            str(report),
            "--source",
            str(remote),
            "--apply",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    updated = json.loads(registry.read_text(encoding="utf-8"))
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["changes_count"] == 1
    assert payload["applied"] is False
    assert updated["models"]["gpt-5.5"]["pricing_per_million_usd"]["input"] == 1.75
