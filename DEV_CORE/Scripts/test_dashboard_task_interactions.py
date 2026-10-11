import hashlib
import importlib.util
import json
import re
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard.task_interactions import index_git_files, index_task_events, repository_project, scoped_task_metrics


def test_events_require_explicit_project_and_preserve_duplicate_subjects():
    rows = [
        ("a", "Edit", "alpha", "t-01", '{"title":"Same"}', "now"),
        ("b", "Edit", "beta", "T-01", '{"title":"Same"}', "now"),
        ("c", "Step", "alpha", None, '{"task_id":"T-02","title":"Same"}', "now"),
        ("d", "Unknown", None, "T-01", '{"project":"beta","title":"Orphan"}', "now"),
        ("e", "Edit", "alpha", "T-03", 'invalid JSON', "now"),
    ]
    events, subjects = index_task_events(rows)
    assert events[("alpha", "T-01")][0]["details"] == "Same"
    assert len(events[("beta", "T-01")]) == 1
    assert events[("alpha", "T-02")][0]["event_type"] == "Step"
    assert subjects[("alpha", "same")] == {("alpha", "T-01"), ("alpha", "T-02")}
    assert subjects[("beta", "same")] == {("beta", "T-01")}
    assert ("beta", "orphan") not in subjects
    assert sum(map(len, events.values())) == 4


def test_git_associations_stay_in_repository_project_and_omit_ambiguity():
    projects = [
        {"name": "alpha", "tasks": [{"id": "T-01", "title": "Same"}, {"id": "T-02", "title": "Same"}]},
        {"name": "beta", "tasks": [{"id": "T-01", "title": "Unique Beta"}]},
    ]
    log = """abcdef1 [T-01] Tagged
alpha.py
abcdef2 Same
ambiguous.py
abcdef3 Unique Beta
beta.py
abcdef4 [T-01] [T-02] Multiple
multiple.py
abcdef5 [T-99] Unknown
unknown.py
abcdef6 Adopted
adopted.py
"""
    subjects = {("alpha", "adopted"): {("alpha", "T-02")}, ("beta", "adopted"): {("beta", "T-01")}}
    assert index_git_files(log, "alpha", projects, subjects) == {
        ("alpha", "T-01"): ["alpha.py"], ("alpha", "T-02"): ["adopted.py"]
    }
    assert index_git_files(log, None, projects, subjects) == {}


def test_repository_requires_its_own_valid_manifest(tmp_path):
    (tmp_path / ".devcore").mkdir()
    manifest = tmp_path / ".devcore" / "project.json"
    manifest.write_text('{"name":"alpha"}')
    assert repository_project(tmp_path) == "alpha"
    child = tmp_path / "child"
    child.mkdir()
    assert repository_project(child) is None
    for value in ([], {}, None, "../alpha", "", "beta/alpha"):
        manifest.write_text(json.dumps({"name": value}))
        assert repository_project(tmp_path) is None
    manifest.write_text("invalid JSON")
    assert repository_project(tmp_path) is None


def test_metrics_never_borrow_task_only_keys_or_another_project():
    metrics = {"T-01": {"tokens": 999}, "beta_T-1": {"tokens": 11}, "alpha_t-1": {"tokens": 7}}
    assert scoped_task_metrics(metrics, "alpha", "T-01") == {"tokens": 7}
    assert scoped_task_metrics(metrics, "beta", "T-01") == {"tokens": 11}
    assert scoped_task_metrics(metrics, "other", "T-01") is None
    assert scoped_task_metrics(metrics, "Alpha", "T-01") is None


@pytest.mark.parametrize("binding,root_matches", [("alpha", True), (None, True), ("beta", True), ("alpha", False)])
def test_generator_isolates_sql_events_git_files_and_metrics(tmp_path, monkeypatch, binding, root_matches):
    from dashboard.data_loader import load_projects_and_tasks
    scripts = Path(__file__).resolve().parent
    platform, local, shared = tmp_path / "platform", tmp_path / "local", tmp_path / "shared"
    platform.mkdir()
    local.mkdir()
    shared.mkdir()
    monkeypatch.setenv("DEVCORE_LOCAL_ROOT", str(local))
    monkeypatch.setenv("DEVCORE_DATA_ROOT", str(shared))
    monkeypatch.setenv("DEVCORE_PLATFORM_ROOT", str(platform))
    (platform / "Dashboard").mkdir()
    for template in ("template.html", "template_terminal.html"):
        shutil.copyfile(scripts.parent / "Dashboard" / template, platform / "Dashboard" / template)
    dangerous_suffix = '</script><img src=x onerror="fail()">'
    if binding:
        (tmp_path / ".devcore").mkdir()
        (tmp_path / ".devcore" / "project.json").write_text(json.dumps({"name": binding}))
    database = local / "devcore.db"
    with sqlite3.connect(database) as conn:
        conn.execute("""CREATE TABLE tasks(id TEXT, project_id TEXT, title TEXT, status TEXT,
            mode TEXT, steps_total INTEGER, steps_done INTEGER, metadata TEXT, started_at TEXT,
            completed_at TEXT, created_at TEXT, updated_at TEXT, version INTEGER)""")
        conn.execute("""CREATE TABLE bus_events(id TEXT, source TEXT, event_type TEXT, project TEXT,
            task_id TEXT, correlation_id TEXT, payload TEXT, created_at TEXT)""")
        for project in ("alpha", "beta"):
            conn.execute("INSERT INTO tasks VALUES ('T-01',?,'Same','todo','coding',1,0,'','','','','',1)", (project,))
            conn.execute("INSERT INTO bus_events VALUES (?, 'test','Edit',?,'T-01',NULL,?,'now')", (project, project, json.dumps({"title": project + " event" + dangerous_suffix})))
        conn.execute("INSERT INTO bus_events VALUES ('orphan','test','Edit',NULL,'T-01',NULL,'{\"title\":\"Unattributed\"}','now')")
    original = hashlib.sha256(database.read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location("gen_dashboard_interactions_test", scripts / "gen_dashboard.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    for name, value in (("LOCAL_ROOT", local), ("DATA_ROOT", shared), ("PLATFORM_ROOT", platform)):
        monkeypatch.setattr(generator, name, value)
    monkeypatch.setattr(generator, "load_projects_and_tasks", lambda *_: load_projects_and_tasks(shared, platform, local_root=local))
    monkeypatch.setattr(generator, "load_token_metrics", lambda *_: {"tasks": {
        "alpha_T-01": {"tokens": 7}, "beta_T-01": {"tokens": 11}, "T-01": {"tokens": 999}
    }})
    monkeypatch.setattr(generator, "load_plugins_registry", lambda *_: {})
    monkeypatch.setattr(generator, "check_port", lambda *_: False)
    monkeypatch.setattr(generator, "get_active_project", lambda: "alpha")
    git_calls = []
    def git(command, **kwargs):
        git_calls.append(command)
        if command[1] == "rev-parse":
            return str(tmp_path if root_matches else tmp_path.parent)
        return "abcdef1 [T-01] Same\nrepository.py\n"
    monkeypatch.setattr(generator.subprocess, "check_output", git)
    for name in ("get_services_html", "get_hooks_html", "get_context_composition_html",
                 "get_metrics_service_summary_html", "get_knowledge_graph_summary_html", "get_plugin_status_html"):
        monkeypatch.setattr(generator, name, lambda *_: "")
    monkeypatch.setattr(sys, "argv", [str(scripts / "gen_dashboard.py"), "--skip-token-refresh"])
    generator.main()
    payload = json.loads((local / "Dashboard" / "dashboard_payload.json").read_text(encoding="utf-8"))
    for project, tokens in (("alpha", 7), ("beta", 11)):
        task = payload["task_interactions"][project + "_T-01"]
        assert [event["details"] for event in task["events"]] == [project + " event" + dangerous_suffix]
        assert task["metrics"]["tokens"] == tokens
        assert task["files"] == (["repository.py"] if binding == project and root_matches else [])
    assert len(git_calls) == (0 if binding is None else 2 if root_matches else 1)
    for output in ("index.html", "index_terminal.html"):
        html = (platform / "Dashboard" / output).read_text(encoding="utf-8")
        scripts_json = re.findall(r'<script id="task-interactions-data" type="application/json">(.*?)</script>', html, re.DOTALL)
        assert scripts_json
        assert all(json.loads(script) == payload["task_interactions"] for script in scripts_json)
        assert dangerous_suffix not in html
    assert hashlib.sha256(database.read_bytes()).hexdigest() == original


@pytest.mark.parametrize("template", ["template.html", "template_terminal.html"])
def test_actual_interaction_modal_rejects_unscoped_or_mismatched_data(template):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the template JavaScript")
    source = (Path(__file__).resolve().parents[1] / "Dashboard" / template).read_text(encoding="utf-8")
    start = source.index("function showInteractions(")
    handlers = source[start:source.index("function closeInteractionsModal", start)]
    script = r'''
const assert = require('node:assert/strict'), vm = require('node:vm');
const handlers = HANDLERS;
function render(map) {
  const elements = {
    'task-interactions-data': {textContent: JSON.stringify(map)},
    'interactions-modal': {style: {}, classList: {add: () => {}}},
    'interactions-title': {}, 'interactions-body': {}
  };
  const sandbox = {document: {getElementById: id => elements[id]}, console: {log: () => {}, error: () => {}}};
  vm.createContext(sandbox); vm.runInContext(handlers, sandbox);
  vm.runInContext('showInteractions("alpha", "T-01", null, null)', sandbox);
  return elements;
}
const other = {project: 'beta', task_id: 'T-01', events: [{event_type: 'Edit', details: 'BETA_SECRET'}]};
for (const map of [{T01: other, 'T-01': other}, {alpha_T01: other, 'alpha_T-01': other}]) {
  const elements = render(map);
  assert.match(elements['interactions-title'].textContent, /alpha/);
  assert.doesNotMatch(elements['interactions-body'].innerHTML, /BETA_SECRET/);
}
const own = {...other, project: 'alpha', events: [{event_type: 'Edit', details: 'ALPHA_EVENT'}]};
const elements = render({'alpha_T-01': own});
assert.match(elements['interactions-body'].innerHTML, /ALPHA_EVENT/);
const malicious = {...own, files: ['<img src=x>.py'], modules: ['<iframe>'],
  events: [{event_type: '<svg>', details: '<img src=x onerror="fail()">', created_at: '<b>'}]};
const escaped = render({'alpha_T-01': malicious})['interactions-body'].innerHTML;
assert.doesNotMatch(escaped, /<img|<iframe|<svg|<b>/);
assert.match(escaped, /&lt;img/);
assert.match(escaped, /&lt;iframe/);
assert.match(escaped, /&lt;svg/);
'''.replace("HANDLERS", json.dumps(handlers))
    result = subprocess.run([node, "-"], input=script, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
