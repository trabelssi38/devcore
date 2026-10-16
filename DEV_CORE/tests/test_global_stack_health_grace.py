"""A busy Headroom route must not tear down the global stack on one probe miss."""

import importlib.util
from pathlib import Path


def test_transient_headroom_health_loss_has_bounded_grace(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(tmp_path / "platform"))
    path = Path(__file__).resolve().parents[1] / "Scripts/global_postgres_stack.py"
    spec = importlib.util.spec_from_file_location("global_postgres_stack_health_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    first = {}
    assert module.overdue_health_failures({"headroom-auxiliary": False}, first, 10) == []
    assert module.overdue_health_failures({"headroom-auxiliary": False}, first, 159) == []
    assert module.overdue_health_failures({"headroom-auxiliary": True}, first, 160) == []
    assert first == {}
    assert module.overdue_health_failures({"headroom-auxiliary": False}, first, 200) == []
    assert module.overdue_health_failures({"headroom-auxiliary": False}, first, 350) == [
        "headroom-auxiliary"]

    first = {}
    assert module.overdue_health_failures({"gateway": False}, first, 0) == []
    assert module.overdue_health_failures({"gateway": False}, first, 30) == ["gateway"]
