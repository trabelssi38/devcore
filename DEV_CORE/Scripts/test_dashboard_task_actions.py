"""Execute the actual template handlers without a browser or live server."""

import json
import hashlib
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard.task_actions import render_task_action_buttons


class Buttons(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.buttons = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "button":
            self.buttons.append(dict(attrs))


@pytest.mark.parametrize("version", [None, True, "7", 0, -1, 1.5, 2**53])
def test_unversioned_or_inexact_snapshot_disables_actions(version):
    buttons = Buttons("".join(render_task_action_buttons("alpha", "T-01", "todo", version))).buttons
    assert len(buttons) == 2
    assert all("disabled" in button and "onclick" not in button for button in buttons)


def test_completed_snapshot_only_offers_versioned_delete():
    done, delete = render_task_action_buttons("alpha", "T-01", "done", 8)
    assert done == ""
    assert Buttons(delete).buttons[0]["onclick"] == 'deleteTask("alpha", "T-01", event, 8)'


@pytest.mark.parametrize("failure", [None, "index.html", "index_terminal.html",
    "dashboard_payload.json", "payload_hash.txt", "missing-standard", "missing-terminal", "nonfinite", "json-success", "capacity"])
def test_generator_connects_sql_snapshot_to_both_temporary_views(tmp_path, monkeypatch, capsys, failure):
    from dashboard.data_loader import load_projects_and_tasks
    scripts = Path(__file__).resolve().parent
    platform = tmp_path / "platform"
    local = tmp_path / "local"
    shared = tmp_path / "shared"
    local.mkdir()
    shared.mkdir()
    (platform / "Dashboard").mkdir(parents=True)
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(platform))
    for template in ("template.html", "template_terminal.html"):
        shutil.copyfile(scripts.parent / "Dashboard" / template, platform / "Dashboard" / template)
    database = local / "devcore.db"
    with sqlite3.connect(database) as conn:
        conn.execute("""CREATE TABLE tasks(id TEXT, project_id TEXT, title TEXT,
            status TEXT, mode TEXT, steps_total INTEGER, steps_done INTEGER,
            metadata TEXT, started_at TEXT, completed_at TEXT, created_at TEXT,
            updated_at TEXT, version INTEGER)""")
        for project, version in (("alpha", 7), ("beta", 11), ("historical", None)):
            conn.execute("INSERT INTO tasks VALUES ('T-01',?,'Snapshot','todo','coding',1,0,'','','','','',?)", (project, version))
    original = hashlib.sha256(database.read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location("gen_dashboard_version_test", scripts / "gen_dashboard.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    for name, value in (("LOCAL_ROOT", local), ("DATA_ROOT", shared), ("PLATFORM_ROOT", platform)):
        monkeypatch.setattr(generator, name, value)
    monkeypatch.setattr(generator, "load_projects_and_tasks", lambda *_: load_projects_and_tasks(shared, platform, local_root=local))
    monkeypatch.setattr(generator, "load_token_metrics", lambda *_: {})
    monkeypatch.setattr(generator, "load_plugins_registry", lambda *_: {})
    monkeypatch.setattr(generator, "check_port", lambda *_: False)
    monkeypatch.setattr(generator, "get_active_project", lambda: "alpha")
    monkeypatch.setattr(generator.subprocess, "check_output", lambda *_, **__: "")
    for name in ("get_services_html", "get_hooks_html", "get_context_composition_html",
                 "get_metrics_service_summary_html", "get_knowledge_graph_summary_html", "get_plugin_status_html"):
        monkeypatch.setattr(generator, name, lambda *_: "")
    monkeypatch.setattr(sys, "argv", [str(scripts / "gen_dashboard.py"), "--skip-token-refresh"])
    json_mode = failure == 'json-success'
    if json_mode:
        monkeypatch.setattr(sys, 'argv', [str(scripts / 'gen_dashboard.py'), '--json', '--skip-token-refresh'])
        import io
        monkeypatch.setattr(sys, 'stdout', io.TextIOWrapper(io.BytesIO(), encoding='utf-8'))
        failure = None
    if failure:
        if failure.startswith("missing-"):
            terminal = failure == "missing-terminal"
            (platform / "Dashboard" / ("template_terminal.html" if terminal else "template.html")).unlink()
            failed_name = "index_terminal.html" if terminal else "index.html"
        else:
            failed_name = 'dashboard_payload.json' if failure in ('nonfinite', 'capacity') else failure
        prepare_failure = failure.startswith('missing-') or failure in ('nonfinite', 'capacity')
        if failure == 'capacity':
            from dashboard import snapshots
            monkeypatch.setattr(snapshots, 'MAX_SNAPSHOT_STORAGE_BYTES', 1)
        if failure == 'nonfinite':
            monkeypatch.setattr(generator, 'load_token_metrics', lambda *_: {'cost': float('nan')})
        previous_paths = [local / 'Dashboard' / name for name in ('dashboard_payload.json', 'payload_hash.txt')]
        previous_paths += [platform / 'Dashboard' / name for name in ('index.html', 'index_terminal.html')]
        if prepare_failure:
            for path in previous_paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'previous fixture snapshot')
        target_root = local if failed_name in ("dashboard_payload.json", "payload_hash.txt") else platform
        target = target_root / "Dashboard" / failed_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"previous fixture snapshot")
        if not prepare_failure:
            import dashboard.publication as publication
            original_replace = publication.os.replace
            def refuse_target(source, destination):
                if Path(destination) == target:
                    raise OSError("fixture destination refused")
                return original_replace(source, destination)
            monkeypatch.setattr(publication.os, "replace", refuse_target)
        with pytest.raises((RuntimeError, OSError, ValueError)):
            generator.main()
        with generator.DashboardLock(wait_timeout=0):
            pass  # A failed full generation releases its lock before returning.
        assert target.read_bytes() == b"previous fixture snapshot"
        if prepare_failure:
            assert all(path.read_bytes() == b'previous fixture snapshot' for path in previous_paths)
        assert not list(target.parent.glob(".*.tmp"))
        assert failed_name + " generated successfully" not in capsys.readouterr().out
        assert hashlib.sha256(database.read_bytes()).hexdigest() == original
        return
    from dashboard import snapshots
    history = []
    for index in range(6):
        previous = json.dumps({'schema_version': 1, 'label': str(index)})
        history.append(snapshots.publish_snapshot(local / 'Dashboard', {
            'dashboard_payload.json': previous, 'payload_hash.txt': hashlib.sha256(previous.encode()).hexdigest(),
            'index.html': '<html>previous</html>', 'index_terminal.html': '<html>previous</html>',
        }))
    generator.main()
    assert len(list((local / 'Dashboard' / 'generations').iterdir())) == 4
    assert not (local / 'Dashboard' / 'generations' / history[0]).exists()
    with generator.DashboardLock(wait_timeout=0):
        pass
    cache_bytes = (local / 'Dashboard' / 'dashboard_payload.json').read_bytes()
    assert (local / 'Dashboard' / 'payload_hash.txt').read_text() == hashlib.sha256(cache_bytes).hexdigest()
    from dashboard.snapshots import resolve_snapshot, read_snapshot_artifact
    snapshot = resolve_snapshot(local / 'Dashboard')
    assert json.loads(read_snapshot_artifact(snapshot, 'dashboard_payload.json')) == json.loads(cache_bytes)
    for output in ("index.html", "index_terminal.html"):
        html = read_snapshot_artifact(snapshot, output)
        if not json_mode:
            assert html == (platform / 'Dashboard' / output).read_text(encoding='utf-8')
        buttons = Buttons(html).buttons
        mutations = [b["onclick"] for b in buttons if b.get("onclick", "").startswith(("completeTask(", "deleteTask("))]
        assert set(mutations) == {
            f'{action}("{project}", "T-01", event, {version})'
            for action in ("completeTask", "deleteTask") for project, version in (("alpha", 7), ("beta", 11))
        }
        assert len([b for b in buttons if "disabled" in b and "Version indisponible" in b.get("title", "")]) == 2
    assert hashlib.sha256(database.read_bytes()).hexdigest() == original


@pytest.mark.parametrize("template", ["template.html", "template_terminal.html"])
def test_actual_template_sends_observed_version_and_never_retries_conflicts(template):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the template JavaScript")
    source = (Path(__file__).resolve().parents[1] / "Dashboard" / template).read_text(encoding="utf-8")
    start = source.index("const API_BASE =")
    end_marker = "function refreshDashboardLegacy" if template == "template.html" else "/* ── Settings"
    handlers = source[start:source.index(end_marker, start)]
    # Quotes and HTML delimiters must survive attribute decoding as JS strings.
    project = 'alpha\'"<>'
    task_id = 'T-01\'"<>'
    actions = [b["onclick"] for b in Buttons("".join(
        render_task_action_buttons(project, task_id, "todo", 7)
    )).buttons]
    script = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fixture = FIXTURE;
function environment(response, cancelled = false) {
  const requests = [], alerts = [], pending = [];
  let refreshes = 0, confirms = 0, stops = 0;
  const sandbox = {
    window: {location: {protocol: 'http:'}},
    event: {stopPropagation: () => stops++},
    alert: message => alerts.push(message),
    refreshDashboard: () => refreshes++,
    confirm: () => { confirms++; return !cancelled; },
    showConfirmModal: (title, message, danger, callback) => {
      confirms++; if (!cancelled) pending.push(callback());
    },
    fetch: (url, options) => {
      requests.push({url, method: options.method, body: JSON.parse(options.body)});
      return response instanceof Error ? Promise.reject(response) : Promise.resolve(response);
    }
  };
  vm.createContext(sandbox);
  vm.runInContext(fixture.handlers, sandbox);
  return {sandbox, requests, alerts,
    state: () => ({refreshes, confirms, stops}),
    invoke: async action => {
      const result = vm.runInContext(action, sandbox);
      await result; await Promise.all(pending.splice(0));
    }
  };
}
function response(status, data, json = true) {
  return {status, ok: status >= 200 && status < 300,
    headers: {get: () => json ? 'application/json' : 'text/plain'},
    json: async () => data};
}
(async () => {
  for (let i = 0; i < fixture.actions.length; i++) {
    const action = fixture.actions[i];
    const e = environment(response(200, {success: true}));
    await e.invoke(action);
    assert.equal(e.requests.length, 1);
    assert.equal(e.requests[0].url, i === 0 ? '/api/done' : '/api/delete');
    assert.equal(e.requests[0].method, i === 0 ? 'POST' : 'DELETE');
    assert.deepEqual(e.requests[0].body, {
      project: fixture.project, id: fixture.task_id, expected_version: 7
    });
    assert.equal(e.state().refreshes, 1);
    assert.equal(e.state().stops, 1);
    const stale = environment(response(409, {detail: {code: 'stale_task_version', message: 'stale'}}));
    await stale.invoke(action);
    assert.equal(stale.requests.length, 1); // no automatic mutation after refresh
    assert.equal(stale.requests[0].body.expected_version, 7);
    assert.equal(stale.state().refreshes, 1);
    assert.match(stale.alerts[0], /a changé/);
    const unavailable = environment(response(409, {detail: {code: 'task_version_unavailable', message: 'Version absente'}}));
    await unavailable.invoke(action);
    assert.equal(unavailable.requests.length, 1);
    assert.equal(unavailable.state().refreshes, 0);
    assert.equal(unavailable.alerts[0], 'Erreur : Version absente');
    const forbidden = environment(response(403, {detail: 'Accès refusé'}));
    await forbidden.invoke(action);
    assert.equal(forbidden.state().refreshes, 0);
    assert.equal(forbidden.alerts[0], 'Erreur : Accès refusé');
    const cancelled = environment(response(200, {success: true}), true);
    await cancelled.invoke(action);
    assert.equal(cancelled.requests.length, 0);
    const failed = environment(new Error('offline'));
    await failed.invoke(action);
    assert.equal(failed.requests.length, 1);
    assert.equal(failed.state().refreshes, 0);
    assert.match(failed.alerts[0], /Impossible de joindre/);
    const functionName = i === 0 ? 'completeTask' : 'deleteTask';
    for (const invalid of ['undefined', 'null', 'true', '0', '-1', '"7"', '1.5', '9007199254740992']) {
      const blocked = environment(response(200, {success: true}));
      await blocked.invoke(`${functionName}("alpha", "T-01", event, ${invalid})`);
      assert.equal(blocked.requests.length, 0);
      assert.equal(blocked.state().confirms, 0);
      assert.match(blocked.alerts[0], /Version de tâche indisponible/);
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
'''.replace("FIXTURE", json.dumps({"handlers": handlers, "actions": actions, "project": project, "task_id": task_id}))
    result = subprocess.run([node, "-"], input=script, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
