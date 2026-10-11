"""Real Edge/HTTP qualification with isolated browser profile and fixture server."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('view', ['standard', 'terminal'])
def test_browser_reconnects_with_cursor_and_applies_snapshot(tmp_path, view):
    browser = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    if not browser.is_file():
        pytest.skip('This local browser qualification requires installed Microsoft Edge')
    node = shutil.which('node')
    assert node, 'Node 24 is required for the browser fixture transport'
    directory = Path(__file__).parents[1] / 'Dashboard'
    filename = 'template.html' if view == 'standard' else 'template_terminal.html'
    source = (directory / filename).read_text(encoding='utf-8')
    morph_end = source.index('function updateTimestamp()') if view == 'standard' else source.index('/* ── CLOCK ── */')
    morph = source[source.index('function morphDOM('):morph_end]
    refresh_end = source.index('function checkPlugin(') if view == 'standard' else source.index('const REFRESH_RATE=')
    refresh = source[source.index('let dashboardRefreshPromise = null;'):refresh_end]
    if view == 'standard':
        stream = source[source.index('function handleDashboardSseEvent('):source.index('setupRefresh(60000);')]
        prelude = 'let dashboardStreamAbort=null,dashboardStreamRetryId=null,dashboardLastEventId=null;'
        connect = 'startDashboardSynchronization();'
    else:
        stream = source[source.index('function connectStream() {'):source.index('function showInteractions(')]
        prelude = ''
        connect = 'connectStream();'
    elements = ['project-cards', 'tasks-pipeline', 'api-ok', 'sys-status', 'task-count']
    html = '<!doctype html><meta charset="utf-8">' + ''.join(
        '<div id="' + name + '">initial</div>' for name in elements
    ) + ''.join('<script type="application/json" id="' + name + '">{}</script>' for name in
                ['task-details-data', 'task-interactions-data', 'token-metrics-data'])
    html += '<script>const API_BASE="";window.activeFilteredProject=null;window.fixtureErrors=[];'
    html += 'window.addEventListener("error",e=>window.fixtureErrors.push(e.message));'
    html += 'function updateTokenReport(){}function updateRepowiseHealth(){}' + prelude
    html += morph + refresh + stream
    html += (connect if view == 'standard' else 'refreshDashboard().then(()=>{' + connect + '});') + '</script>'
    fixture = tmp_path / 'fixture.json'
    fixture.write_text(json.dumps({'html': html, 'fail_snapshot_once': True}), encoding='utf-8')
    env = os.environ.copy()
    for name in ['DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT']:
        env[name] = str(tmp_path / name.lower())
    result = subprocess.run([node, str(Path(__file__).with_name('dashboard_browser_stream.cjs')),
                             str(browser), str(tmp_path), str(fixture)],
                            capture_output=True, text=True, timeout=105, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    print(json.dumps({'view': view, 'browser': report['browser'],
                      'last_event_id': report['last_event_id'],
                      'snapshot_reads': report['snapshot_reads'], 'failed_snapshots': report['failed_snapshots']}))
    assert report['last_event_id'] == 'snapshot:' + 'a' * 32
    assert report['snapshot_reads'] == 3
    assert report['failed_snapshots'] == 1
    assert report['dom']['tasks'] == 'version2 équipe'
    assert report['dom']['details'] == {'alpha_T1': 'version2'}
    assert report['dom']['interactions']['alpha_T1']['title'] == 'version2'
    assert report['dom']['errors'] == []
