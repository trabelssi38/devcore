"""Retention must stay inside the selected local root."""

import importlib.util
import json
import os
import time
from pathlib import Path


SCRIPT = Path(__file__).with_name("rotate_logs_and_backups.py")


def load_rotation():
    spec = importlib.util.spec_from_file_location("rotate_local_state_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rotation_uses_local_root_and_preserves_shared_files(tmp_path):
    rotation = load_rotation()
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    old_log = local / "Logs" / "scripts" / "old.log"
    shared_log = shared / "Logs" / "scripts" / "old.log"
    for path in (old_log, shared_log):
        path.parent.mkdir(parents=True)
        path.write_text("preserved only when shared", encoding="utf-8")
        old_time = time.time() - 40 * 86400
        os.utime(path, (old_time, old_time))
    assert rotation.rotate_script_logs(root=local) == 1
    assert not old_log.exists()
    assert shared_log.is_file()

    backups = local / "Backups" / "auto"
    backups.mkdir(parents=True)
    for index in range(3):
        path = backups / f"state_{index}.zip"
        path.write_bytes(bytes([index]))
        os.utime(path, (time.time() - (3 - index) * 86400,) * 2)
    shared_backup = shared / "Backups" / "auto" / "state_0.zip"
    shared_backup.parent.mkdir(parents=True)
    shared_backup.write_bytes(b"shared")
    assert rotation.rotate_auto_backups(keep_max=1, root=local) == 2
    assert sorted(path.name for path in backups.iterdir()) == ["state_2.zip"]
    assert shared_backup.read_bytes() == b"shared"

    report = local / "Logs" / "token_reports" / "token_metrics_summary.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({"sessions": [
        {"id": "old", "date": "2020-01-01"},
        {"id": "fresh", "date": "2099-01-01"}]}), encoding="utf-8")
    shared_report = shared / "Logs" / "token_reports" / "token_metrics_summary.json"
    shared_report.parent.mkdir(parents=True)
    shared_report.write_text("shared report", encoding="utf-8")
    rotation.bound_token_metrics(root=local)
    assert [item["id"] for item in json.loads(report.read_text(encoding="utf-8"))["sessions"]] == ["fresh"]
    archive = next((report.parent / "archive").glob("*.json"))
    assert json.loads(archive.read_text(encoding="utf-8"))[0]["id"] == "old"
    assert shared_report.read_text(encoding="utf-8") == "shared report"
