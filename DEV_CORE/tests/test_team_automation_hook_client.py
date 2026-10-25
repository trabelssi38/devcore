"""The candidate client cannot send credentials away from loopback."""

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "Scripts" / "team_automation_hook.py"
spec = importlib.util.spec_from_file_location("team_automation_hook_client", SCRIPT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


@pytest.mark.parametrize("url", ["https://elsewhere.invalid", "http://user@127.0.0.1:20131",
                                 "http://127.0.0.1:20131/other", "http://127.0.0.1:20131?x=1"])
def test_api_origin_must_be_bare_loopback(url):
    with pytest.raises(ValueError):
        client.local_api_url(url)


def test_session_start_fetches_context_before_publishing(tmp_path, monkeypatch, capsys):
    token = tmp_path / "token.txt"
    token.write_text("fixture-token", encoding="utf-8")
    calls = []

    def fake_request(opener, url, bearer, *, payload=None):
        calls.append((url, bearer, payload))
        return {"project": "alpha"} if payload is None else {"created": True, "event": {"status": "succeeded"}}

    monkeypatch.setattr(client, "request_json", fake_request)
    assert client.main(["--token-file", str(token), "--project", "alpha", "--hook", "session_start",
                        "--source", "codex", "--session", "s-1"]) == 0
    assert len(calls) == 2 and calls[0][0].endswith("project=alpha&budget_bytes=12000")
    assert calls[1][2]["session"] == "s-1"
    assert all(item[1] == "fixture-token" for item in calls)
    assert "fixture-token" not in capsys.readouterr().out


def test_client_refuses_missing_token_and_redirect(tmp_path):
    assert client.main(["--token-file", str(tmp_path / "missing"), "--project", "alpha",
                        "--hook", "session_start", "--source", "codex", "--session", "s-1"]) == 2
    assert client.NoRedirect().redirect_request(None, None, 302, "move", {},
                                                 "https://elsewhere.invalid") is None
