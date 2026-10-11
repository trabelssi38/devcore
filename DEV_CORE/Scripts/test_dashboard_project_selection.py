"""Shared legacy runtime selection must not steer another generator process."""
import importlib.util
import json
import re
from pathlib import Path

import pytest


def load_utils():
    path = Path(__file__).parent / 'dashboard' / 'utils.py'
    spec = importlib.util.spec_from_file_location('dashboard_selection_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shared_selection_is_ignored_and_preserved(tmp_path, monkeypatch):
    monkeypatch.delenv('DEVCORE_ACTIVE_PROJECT_NAME', raising=False)
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    module = load_utils()
    for root in (module.LOCAL_ROOT, module.DATA_ROOT):
        runtime = root / 'Runtime'
        runtime.mkdir(parents=True)
        (runtime / 'active_project.txt').write_text('foreign-project')
    assert module.get_active_project() == ''
    assert module.get_active_project(tmp_path / 'unused') == ''
    monkeypatch.setenv('DEVCORE_ACTIVE_PROJECT_NAME', ' alpha ')
    assert module.get_active_project() == 'alpha'
    monkeypatch.setenv('DEVCORE_ACTIVE_PROJECT_NAME', 'beta')
    assert module.get_active_project() == 'beta'  # No module-level cached preference.
    for root in (module.LOCAL_ROOT, module.DATA_ROOT):
        assert (root / 'Runtime' / 'active_project.txt').read_text() == 'foreign-project'


@pytest.mark.parametrize('selected', ['', ' ', '../beta', 'a/b', 'a\\b', 'E:beta'])
def test_invalid_explicit_selection_does_not_fall_back(tmp_path, monkeypatch, selected):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    monkeypatch.setenv('DEVCORE_ACTIVE_PROJECT_NAME', selected)
    with pytest.raises(ValueError, match='explicit dashboard project'):
        load_utils().get_active_project()


@pytest.mark.parametrize('template_name', ['template.html', 'template_terminal.html'])
@pytest.mark.parametrize('selected', [None, 'alpha', '\";window.fixtureInjected=1;\"', 'mémoire<&>\u2028\u2029projet'])
def test_inline_project_assignment_is_single_json_value(tmp_path, monkeypatch, template_name, selected):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    if selected is None:
        monkeypatch.delenv('DEVCORE_ACTIVE_PROJECT_NAME', raising=False)
    else:
        monkeypatch.setenv('DEVCORE_ACTIVE_PROJECT_NAME', selected)
    template = (Path(__file__).parents[1] / 'Dashboard' / template_name).read_text(encoding='utf-8')
    result = load_utils().render_active_project(template)
    value = re.search(r'window\.devcoreActiveProject = (.*);', result).group(1)
    assert json.loads(value) == (selected or '')
    assert not any(char in value for char in '<>&\u2028\u2029')
    assert '{{ACTIVE_PROJECT_NAME}}' not in result
    # Only this assignment is changed; no other inline script/template rendering.
    assert result.split('window.devcoreActiveProject = ')[0] == template.split('window.devcoreActiveProject = ')[0]


def test_unsafe_unquoted_placeholder_refused(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    monkeypatch.setenv('DEVCORE_ACTIVE_PROJECT_NAME', 'alpha')
    with pytest.raises(ValueError, match='complete quoted'):
        load_utils().render_active_project('window.devcoreActiveProject = {{ACTIVE_PROJECT_NAME}};')


@pytest.mark.parametrize('template_name', ['template.html', 'template_terminal.html'])
def test_script_data_preserves_payload_without_html_breakout(tmp_path, monkeypatch, template_name):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    payload = {'title': '</script><script>window.fixtureInjected=1</script>&mémoire\u2028\u2029',
               'steps': [0, None, True], 'quote': '"', '{{TASK_DETAILS_MAP}}': '{{TASK_INTERACTIONS_MAP}} {{TOKEN_METRICS_JSON}}'}
    template = (Path(__file__).parents[1] / 'Dashboard' / template_name).read_text(encoding='utf-8')
    result = load_utils().render_dashboard_data(template, payload, {'events': [payload]}, {'metrics': payload})
    for element_id, expected in [('task-details-data', payload),
                                 ('task-interactions-data', {'events': [payload]}),
                                 ('token-metrics-data', {'metrics': payload})]:
        bodies = re.findall(r'<script id="' + element_id + r'" type="application/json">(.*?)</script>', result)
        assert bodies
        for body in bodies:
            assert json.loads(body) == expected
            assert not any(char in body for char in '<>&\u2028\u2029')
    assert result.count('<script') == template.count('<script')
    assert result.count('</script>') == template.count('</script>')


@pytest.mark.parametrize('nonfinite', [float('nan'), float('inf'), float('-inf')])
def test_non_json_metrics_refused(tmp_path, monkeypatch, nonfinite):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    with pytest.raises(ValueError, match='JSON compliant'):
        load_utils().render_dashboard_data('{{TOKEN_METRICS_JSON}}', {}, {}, {'cost': nonfinite})
