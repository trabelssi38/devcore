"""Historical task payloads and project code-health output on isolated fixtures."""
import json
import sqlite3
from datetime import datetime, timezone

from devcore_engine.services.cockpit_presentation import (
    task_cards, project_code_health, code_health_card, display, _date,
)


def test_aware_cockpit_dates_use_tunisia_timezone():
    assert _date(datetime(2026, 10, 20, 10, 44, tzinfo=timezone.utc)) == \
        '2026-10-20 11:44:00+01:00'


def test_historical_array_steps_and_actions_remain_scoped():
    now = datetime.now(timezone.utc)
    row = ('T-341', 'uuid', '<script>titre</script>', 'done', 'coding', 4, 1, 2,
           now, None, [{'title': 'Étape <b>un</b>', 'done': True}, {'title': 'Deux', 'done': False}], None, now)
    html, details, interactions = task_cards('alpha', [row], 90, [('TaskDone', now, 'uuid'), ('Other', now, 'other')])
    assert 'active-task' not in html
    assert 'Worktree : Non renseigné' in html
    assert '&lt;script&gt;titre&lt;/script&gt;' in html
    assert '&lt;b&gt;un&lt;/b&gt;' in html
    assert 'btn-details' in html and 'btn-interactions' in html and 'btn-delete' in html
    assert 'btn-done' not in html
    assert details['alpha_T-341'] == '[v] Étape <b>un</b>\n[ ] Deux'
    assert len(interactions['alpha_T-341']['events']) == 1
    assert 'cost_usd' not in interactions['alpha_T-341']
    assert 'task_offset=60' in html and 'Tâches plus anciennes' in html


def test_code_health_reads_only_the_registered_index_and_never_invents_scores(tmp_path):
    root = tmp_path / 'alpha'
    index = root / '.repowise'
    index.mkdir(parents=True)
    db = index / 'wiki.db'
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE health_file_metrics(file_path,score,maintainability_score,performance_score)')
        connection.executemany('INSERT INTO health_file_metrics VALUES(?,?,?,?)',
                               [('safe.py', 9, 8, 10), ('<img>.py', 3, 4, 2)])
    (index / 'state.json').write_text(json.dumps({'last_sync_commit': 'abc123'}))
    before = db.read_bytes()
    health = project_code_health(root)
    assert health['count'] == 2 and health['score'] == 6
    assert health['bands'] == (1, 0, 1)
    rendered = code_health_card('alpha', health)
    assert '6.0/10' in rendered and 'abc123' in rendered
    assert '&lt;img&gt;.py' in rendered and '<img>' not in rendered
    assert 'data-project="alpha"' in rendered
    assert db.read_bytes() == before
    assert project_code_health(tmp_path / 'beta') is None
    assert '/10' not in code_health_card('beta', None)


def test_historical_encoding_repair_is_display_only_and_preserves_valid_text():
    damaged = 'Sécurisation des clés'.encode('utf-8').decode('cp1256')
    assert display(damaged) == 'Sécurisation des clés'
    assert display('Sécurisation des clés') == 'Sécurisation des clés'
    assert display('أهلا') == 'أهلا'
