"""The real-user gate follows attributed counters across presentation changes."""
import copy
import importlib.util
from pathlib import Path
import sys
import pytest


def load(monkeypatch, tmp_path):
    for name in ("DEVCORE_LOCAL_ROOT", "DEVCORE_DATA_ROOT"):
        monkeypatch.setenv(name, str(tmp_path / name))
    scripts = Path(__file__).resolve().parents[1] / "Scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("real_user_gate", scripts / "verify_global_real_users.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(report, tokens=6):
    return {"project": "devcore", "sections": {"token_activity_report": report},
            "token_metrics": {"totals": {"tokens": tokens},
                              "projects": {"devcore": {"tokens": tokens}}}}


def test_actual_restored_usage_panel_passes(monkeypatch, tmp_path):
    gate = load(monkeypatch, tmp_path)
    from devcore_engine.services.cockpit_presentation import usage_panel
    report = usage_panel((1, 5, 1, 0), [("google-gemini", "gemini-2.5-flash", 1, 5, 1)], [], "")
    assert "appel(s) Gemini attribué(s)" not in report
    gate.verify_attributed_usage(snapshot(report), "devcore")
    gate.verify_attributed_usage(snapshot(usage_panel((0, 0, 0, 0), [], [], ""), 0), "devcore")


@pytest.mark.parametrize("fault", ["missing", "cross_project", "mismatch", "negative", "boolean", "wrong_project"])
def test_counters_fail_closed(monkeypatch, tmp_path, fault):
    gate = load(monkeypatch, tmp_path)
    data = snapshot("Aucun appel LLM attribué")
    if fault == "missing":
        data.pop("token_metrics")
    elif fault == "cross_project":
        data["token_metrics"]["projects"]["scripts"] = {"tokens": 1}
    elif fault == "mismatch":
        data["token_metrics"]["totals"]["tokens"] = 7
    elif fault == "negative":
        data = snapshot("Aucun appel LLM attribué", -1)
    elif fault == "boolean":
        data = snapshot("Aucun appel LLM attribué", True)
    else:
        data["project"] = "scripts"
    with pytest.raises(RuntimeError):
        gate.verify_attributed_usage(data, "devcore")


def test_missing_report_rejected(monkeypatch, tmp_path):
    gate = load(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError):
        gate.verify_attributed_usage(snapshot("unavailable"), "devcore")
