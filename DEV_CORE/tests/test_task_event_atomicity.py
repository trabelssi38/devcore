"""Task admission and selection publish their local event in the same commit."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading

import pytest

from devcore_engine.services.tasks import TaskService
from devcore_engine.services.tasks import StaleTaskVersion
from devcore_engine.context import RequestContext


@pytest.mark.parametrize('operation', ['add', 'next'])
def test_event_insert_failure_rolls_back_task_import_and_version(tmp_path, operation):
    service = TaskService(tmp_path)
    try:
        if operation == 'next':
            original = service.add_task('fixture', project_id='alpha')
        else:
            original = None
        service.conn.execute("""CREATE TRIGGER reject_fixture_event BEFORE INSERT ON bus_events
            BEGIN SELECT RAISE(ABORT, 'fixture event rejected'); END;""")
        service.conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            if operation == 'add':
                service.add_task('fixture', project_id='alpha', idempotency_key='fixture-import')
            else:
                service.next_task('alpha')
        assert not service.conn.in_transaction
        if operation == 'add':
            assert service.conn.execute('SELECT count(*) FROM tasks').fetchone()[0] == 0
            assert service.conn.execute('SELECT count(*) FROM task_imports').fetchone()[0] == 0
            assert service.conn.execute('SELECT count(*) FROM projects').fetchone()[0] == 0
        else:
            assert service.get_task(original['id'], 'alpha') == original
        service.conn.execute('DROP TRIGGER reject_fixture_event')
        service.conn.commit()
        if operation == 'add':
            task = service.add_task('fixture', project_id='alpha', idempotency_key='fixture-import')
            assert task['id'] == 'T-01'
            assert service.add_task('ignored', project_id='alpha', idempotency_key='fixture-import')['id'] == task['id']
        else:
            task = service.next_task('alpha')
            assert task['version'] == original['version'] + 1
            assert service.next_task('alpha')['version'] == task['version']
        events = service.event_bus.read(project='alpha')
        assert sum(event['event_type'] == 'TaskAdded' for event in events) == 1
        assert sum(event['event_type'] == 'TaskNext' for event in events) == (operation == 'next')
    finally:
        service.conn.close()


def test_append_requires_transaction_and_is_not_visible_until_commit(tmp_path):
    service = TaskService(tmp_path)
    observer = sqlite3.connect(tmp_path / 'devcore.db')
    try:
        with pytest.raises(RuntimeError, match='active transaction'):
            service.event_bus.append_in_transaction('fixture', {})
        service.conn.execute('BEGIN IMMEDIATE')
        service.event_bus.append_in_transaction('fixture', {}, project='alpha')
        assert observer.execute('SELECT count(*) FROM bus_events').fetchone()[0] == 0
        service.conn.rollback()
        assert service.event_bus.read(project='alpha') == []
        service.conn.execute('BEGIN IMMEDIATE')
        service.event_bus.append_in_transaction('fixture', {}, project='alpha')
        service.conn.commit()
        assert observer.execute('SELECT count(*) FROM bus_events').fetchone()[0] == 1
    finally:
        observer.close()
        service.conn.close()


def test_concurrent_selection_returns_one_active_task_and_one_event_per_project(tmp_path):
    service = TaskService(tmp_path)
    for project in ('alpha', 'beta'):
        for i in range(3):
            service.add_task(f'fixture {i}', project_id=project)
    service.conn.close()
    barrier = threading.Barrier(4)
    def select(project):
        worker = TaskService(tmp_path)
        try:
            barrier.wait(timeout=5)
            return project, worker.next_task(project)
        finally:
            worker.conn.close()
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(select, ['alpha', 'beta', 'alpha', 'beta']))
    service = TaskService(tmp_path)
    try:
        for project in ('alpha', 'beta'):
            tasks = [task for selected_project, task in results if selected_project == project]
            assert len({task['id'] for task in tasks}) == 1
            assert tasks[0]['version'] == tasks[1]['version'] == 2
            assert len(service.event_bus.read(event_type='TaskNext', project=project)) == 1
            assert sum(task['status'] == 'in_progress' for task in service.get_board(project)['tasks']) == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize('operation,event', [
    ('complete_task', 'TaskCompleted'), ('delete_task', 'TaskDeleted'),
    ('step_task', 'TaskStepDone'), ('edit_task', 'TaskEdited'),
    ('pause_task', 'TaskPaused'), ('skip_task', 'TaskSkipped'), ('resume_task', 'TaskResumed'),
])
def test_mutation_event_failure_rolls_back_state_version_and_author_audit(tmp_path, operation, event):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('fixture', project_id='alpha', steps=3)
        service.add_task('other project', project_id='beta')
        if operation in ('pause_task', 'skip_task', 'resume_task'):
            service.next_task('alpha')
        if operation == 'resume_task':
            service.pause_task(task['id'], project_id='alpha')
        original = service.get_task(task['id'], 'alpha')
        events_before = service.conn.execute('SELECT count(*) FROM bus_events').fetchone()[0]
        service.conn.execute("""CREATE TRIGGER reject_fixture_event BEFORE INSERT ON bus_events
            BEGIN SELECT RAISE(ABORT, 'fixture event rejected'); END;""")
        service.conn.commit()
        kwargs = {'project_id': 'alpha', 'expected_version': original['version']}
        if operation in ('complete_task', 'delete_task', 'pause_task', 'resume_task'):
            kwargs['context'] = RequestContext('alpha', user_id='alice', trace_id='trace-fixture')
        if operation == 'edit_task': kwargs['title'] = 'updated fixture'
        def invoke():
            return getattr(service, operation)(task['id'], **kwargs)
        with pytest.raises(sqlite3.IntegrityError): invoke()
        assert not service.conn.in_transaction
        assert service.get_task(task['id'], 'alpha') == original
        assert service.conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 0
        assert service.conn.execute('SELECT count(*) FROM bus_events').fetchone()[0] == events_before
        assert service.get_task('T-01', 'beta')['version'] == 1
        service.conn.execute('DROP TRIGGER reject_fixture_event')
        service.conn.commit()
        invoke()
        stored = dict(service.conn.execute("SELECT * FROM tasks WHERE project_id='alpha' AND id=?", (task['id'],)).fetchone())
        assert stored['version'] == original['version'] + 1
        assert service.conn.execute('SELECT count(*) FROM bus_events').fetchone()[0] == events_before + 1
        assert service.event_bus.read(project='alpha', limit=1)[0]['event_type'] == event
        assert service.conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == (operation in ('complete_task', 'delete_task', 'pause_task', 'resume_task'))
    finally:
        service.conn.close()


@pytest.mark.parametrize('operation', ['pause_task', 'skip_task', 'resume_task'])
def test_no_transition_produces_no_event(tmp_path, operation):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('todo', project_id='alpha')
        assert getattr(service, operation)(task['id'], project_id='alpha') is None
        assert service.get_task(task['id'], 'alpha') == task
        assert len(service.event_bus.read(project='alpha')) == 1
    finally:
        service.conn.close()


def test_direct_step_cannot_activate_second_task_in_same_project(tmp_path):
    service = TaskService(tmp_path)
    try:
        service.add_task('first', project_id='alpha', steps=3)
        other = service.add_task('second', project_id='alpha', steps=3)
        service.add_task('independent', project_id='beta', steps=3)
        service.next_task('alpha')
        before_events = len(service.event_bus.read(project='alpha'))
        with pytest.raises(ValueError, match='already active'):
            service.step_task(other['id'], project_id='alpha', expected_version=other['version'])
        assert service.get_task(other['id'], 'alpha') == other
        assert len(service.event_bus.read(project='alpha')) == before_events
        assert not service.conn.in_transaction
        assert service.step_task('T-01', project_id='beta')['status'] == 'in_progress'
        assert service.step_task('T-01', project_id='alpha')['steps_done'] == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize('invalid', [True, 1.5, '1', 0, -1])
def test_invalid_step_number_refused_without_implicit_selection(tmp_path, invalid):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('fixture', project_id='alpha', steps=3)
        with pytest.raises(ValueError, match='positive integer'):
            service.step_task(project_id='alpha', step_number=invalid)
        assert service.get_task(task['id'], 'alpha') == task
        assert len(service.event_bus.read(project='alpha')) == 1
        assert not service.conn.in_transaction
    finally:
        service.conn.close()


def test_concurrent_direct_steps_cannot_create_two_active_tasks(tmp_path):
    service = TaskService(tmp_path)
    first = service.add_task('first', project_id='alpha', steps=3)
    second = service.add_task('second', project_id='alpha', steps=3)
    service.conn.close()
    barrier = threading.Barrier(2)
    def step(task_id):
        worker = TaskService(tmp_path)
        try:
            barrier.wait(timeout=5)
            try:
                return worker.step_task(task_id, project_id='alpha')
            except ValueError as exc:
                assert 'already active' in str(exc)
                return None
        finally:
            worker.conn.close()
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(step, [first['id'], second['id']]))
    service = TaskService(tmp_path)
    try:
        assert sum(result is not None for result in results) == 1
        tasks = service.get_board('alpha')['tasks']
        assert sorted((task['status'], task['steps_done'], task['version']) for task in tasks) == [
            ('in_progress', 1, 2), ('todo', 0, 1)]
        assert len(service.event_bus.read(event_type='TaskStepDone', project='alpha')) == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize('status', ['paused', 'skipped'])
@pytest.mark.parametrize('step_number', [None, 3])
def test_step_cannot_implicitly_resume_paused_or_skipped_task(tmp_path, status, step_number):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('fixture', project_id='alpha', steps=3)
        service.next_task('alpha')
        getattr(service, 'pause_task' if status == 'paused' else 'skip_task')(task['id'], project_id='alpha')
        original = service.get_task(task['id'], 'alpha')
        events = len(service.event_bus.read(project='alpha'))
        with pytest.raises(ValueError, match='before stepping'):
            service.step_task(task['id'], step_number=step_number, project_id='alpha', expected_version=original['version'])
        assert service.get_task(task['id'], 'alpha') == original
        assert len(service.event_bus.read(project='alpha')) == events
        assert not service.conn.in_transaction
        if status == 'paused':
            resumed = service.resume_task(task['id'], project_id='alpha', expected_version=original['version'])
            assert service.step_task(task['id'], project_id='alpha', expected_version=resumed['version'])['steps_done'] == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize('completed', [False, True])
def test_repeated_explicit_step_is_noop_and_stale_version_still_refused(tmp_path, completed):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('fixture', project_id='alpha', steps=3)
        current = service.step_task(task['id'], step_number=3 if completed else 2, project_id='alpha')
        events = len(service.event_bus.read(project='alpha'))
        for number in (1, 2, 3 if completed else 2):
            assert service.step_task(task['id'], step_number=number, project_id='alpha', expected_version=current['version']) == current
        if completed:
            assert service.step_task(task['id'], project_id='alpha') == current
        assert len(service.event_bus.read(project='alpha')) == events
        with pytest.raises(StaleTaskVersion):
            service.step_task(task['id'], step_number=1, project_id='alpha', expected_version=task['version'])
        assert service.get_task(task['id'], 'alpha') == current
    finally:
        service.conn.close()


def test_concurrent_same_final_step_has_one_event_and_one_version_increment(tmp_path):
    service = TaskService(tmp_path)
    task = service.add_task('fixture', project_id='alpha', steps=3)
    service.conn.close()
    barrier = threading.Barrier(2)
    def advance(_):
        worker = TaskService(tmp_path)
        try:
            barrier.wait(timeout=5)
            return worker.step_task(task['id'], step_number=3, project_id='alpha')
        finally:
            worker.conn.close()
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(advance, range(2)))
    assert all((result['status'], result['version']) == ('done', 2) for result in results)
    service = TaskService(tmp_path)
    try:
        assert len(service.event_bus.read(event_type='TaskStepDone', project='alpha')) == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize('operation,event', [('complete_task', 'TaskCompleted'), ('step_task', 'TaskStepDone')])
@pytest.mark.parametrize('existing_active', [False, True])
def test_implicit_selection_rolls_back_with_failed_mutation_event(tmp_path, operation, event, existing_active):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('fixture', project_id='alpha', steps=3)
        if existing_active:
            service.next_task('alpha')
        original = service.get_task(task['id'], 'alpha')
        events_before = len(service.event_bus.read(project='alpha'))
        # Permit TaskNext, reject only the following mutation event.
        service.conn.execute(f"""CREATE TRIGGER reject_mutation_event BEFORE INSERT ON bus_events
            WHEN NEW.event_type = '{event}'
            BEGIN SELECT RAISE(ABORT, 'fixture mutation rejected'); END;""")
        service.conn.commit()
        kwargs = {'project_id': 'alpha'}
        if operation == 'complete_task':
            kwargs['context'] = RequestContext('alpha', user_id='alice')
        with pytest.raises(sqlite3.IntegrityError):
            getattr(service, operation)(**kwargs)
        assert service.get_task(task['id'], 'alpha') == original
        assert len(service.event_bus.read(project='alpha')) == events_before
        assert service.conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 0
        assert not service.conn.in_transaction
        service.conn.execute('DROP TRIGGER reject_mutation_event')
        service.conn.commit()
        updated = getattr(service, operation)(**kwargs)
        assert updated['version'] == original['version'] + (1 if existing_active else 2)
        assert len(service.event_bus.read(event_type='TaskNext', project='alpha')) == 1
        assert len(service.event_bus.read(event_type=event, project='alpha')) == 1
    finally:
        service.conn.close()


def test_completion_replay_does_not_change_audit_event_version_or_timestamp(tmp_path):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('fixture', project_id='alpha')
        completed = service.complete_task(task['id'], project_id='alpha', expected_version=1,
            context=RequestContext('alpha', user_id='alice'))
        assert service.complete_task(task['id'], project_id='alpha', expected_version=completed['version'],
            context=RequestContext('alpha', user_id='bob')) == completed
        assert service.complete_task(task['id'], project_id='alpha') == completed
        with pytest.raises(StaleTaskVersion):
            service.complete_task(task['id'], project_id='alpha', expected_version=task['version'])
        assert service.conn.execute('SELECT actor FROM audit_log').fetchall()[0]['actor'] == 'alice'
        assert service.conn.execute('SELECT count(*) FROM audit_log').fetchone()[0] == 1
        assert len(service.event_bus.read(event_type='TaskCompleted', project='alpha')) == 1
    finally:
        service.conn.close()


@pytest.mark.parametrize('operation', ['complete_task', 'step_task'])
def test_implicit_mutation_with_no_eligible_task_has_no_effect(tmp_path, operation):
    service = TaskService(tmp_path)
    try:
        task = service.add_task('blocked', project_id='alpha', depends_on='T-99')
        assert getattr(service, operation)(project_id='alpha') is None
        assert service.get_task(task['id'], 'alpha') == task
        assert len(service.event_bus.read(project='alpha')) == 1
        assert not service.conn.in_transaction
    finally:
        service.conn.close()


@pytest.mark.parametrize('dependency_state', ['pending', 'missing', 'other_project', 'deleted'])
@pytest.mark.parametrize('step_number', [None, 3])
def test_direct_step_cannot_bypass_same_project_dependency(tmp_path, dependency_state, step_number):
    service = TaskService(tmp_path)
    try:
        dependency_id = 'T-99'
        if dependency_state in ('pending', 'deleted'):
            dependency_id = service.add_task('dependency', project_id='alpha')['id']
            if dependency_state == 'deleted':
                service.complete_task(dependency_id, project_id='alpha')
                service.delete_task(dependency_id, project_id='alpha')
        if dependency_state == 'other_project':
            dependency_id = service.add_task('private foreign title', project_id='beta')['id']
            service.complete_task(dependency_id, project_id='beta')
        task = service.add_task('blocked', project_id='alpha', depends_on=dependency_id, steps=3)
        events = len(service.event_bus.read(project='alpha'))
        with pytest.raises(ValueError, match='same project before stepping') as refusal:
            service.step_task(task['id'], project_id='alpha', step_number=step_number, expected_version=task['version'])
        assert 'private foreign title' not in str(refusal.value)
        assert service.get_task(task['id'], 'alpha') == task
        assert len(service.event_bus.read(project='alpha')) == events
        assert not service.conn.in_transaction
    finally:
        service.conn.close()


def test_completed_local_dependency_allows_progress_after_refusal(tmp_path):
    service = TaskService(tmp_path)
    try:
        dependency = service.add_task('dependency', project_id='alpha')
        task = service.add_task('dependent', project_id='alpha', depends_on=dependency['id'], steps=3)
        with pytest.raises(ValueError, match='dependency'):
            service.step_task(task['id'], project_id='alpha')
        service.complete_task(dependency['id'], project_id='alpha')
        updated = service.step_task(task['id'], project_id='alpha', expected_version=task['version'])
        assert (updated['steps_done'], updated['status'], updated['version']) == (1, 'in_progress', 2)
    finally:
        service.conn.close()


@pytest.mark.parametrize('dependency_state', ['pending', 'missing', 'other_project', 'deleted'])
@pytest.mark.parametrize('explicit', [False, True])
def test_paused_dependency_blocks_resume_until_resolved(tmp_path, dependency_state, explicit):
    service = TaskService(tmp_path)
    try:
        dependency_id = 'T-99'
        if dependency_state in ('pending', 'deleted'):
            dependency_id = service.add_task('dependency', project_id='alpha')['id']
            if dependency_state == 'deleted':
                service.complete_task(dependency_id, project_id='alpha')
                service.delete_task(dependency_id, project_id='alpha')
        if dependency_state == 'other_project':
            dependency_id = service.add_task('private foreign title', project_id='beta')['id']
            service.complete_task(dependency_id, project_id='beta')
        task = service.add_task('legacy paused', project_id='alpha', depends_on=dependency_id, steps=3)
        # Disposable fixture reproduces legacy inconsistent state; no live data.
        service.conn.execute("UPDATE tasks SET status='paused' WHERE project_id='alpha' AND id=?", (task['id'],))
        service.conn.commit()
        original = service.get_task(task['id'], 'alpha')
        events_before = len(service.event_bus.read(project='alpha'))
        kwargs = {'project_id': 'alpha'}
        if explicit:
            kwargs.update(task_id=task['id'], expected_version=original['version'])
        with pytest.raises(ValueError, match='same project before resuming') as refusal:
            service.resume_task(**kwargs)
        assert 'private foreign title' not in str(refusal.value)
        assert service.get_task(task['id'], 'alpha') == original
        assert len(service.event_bus.read(project='alpha')) == events_before
        assert not service.conn.in_transaction
        if dependency_state == 'pending':
            service.complete_task(dependency_id, project_id='alpha')
            resumed = service.resume_task(**kwargs)
            assert (resumed['status'], resumed['version']) == ('in_progress', original['version'] + 1)
            assert len(service.event_bus.read(event_type='TaskResumed', project='alpha')) == 1
    finally:
        service.conn.close()
