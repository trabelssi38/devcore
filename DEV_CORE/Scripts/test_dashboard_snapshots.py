"""Committed snapshot fault injection on temporary roots only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from dashboard import snapshots


def artifacts(label):
    payload = json.dumps({'schema_version': 1, 'sections': {}, 'label': label})
    return {'dashboard_payload.json': payload, 'payload_hash.txt': hashlib.sha256(payload.encode()).hexdigest(),
            'index.html': '<html>' + label + '</html>', 'index_terminal.html': '<html>terminal ' + label + '</html>'}


@pytest.mark.parametrize('failure', sorted(snapshots.NAMES) + ['manifest.json', 'current.json'])
def test_failed_stage_or_commit_retains_previous_generation(tmp_path, monkeypatch, failure):
    previous = snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    original = snapshots.atomic_write_text
    def refused(path, text):
        if path.name == failure:
            raise OSError('fixture stage refused')
        original(path, text)
    monkeypatch.setattr(snapshots, 'atomic_write_text', refused)
    with pytest.raises(OSError):
        snapshots.publish_snapshot(tmp_path, artifacts('candidate'))
    pinned = snapshots.resolve_snapshot(tmp_path)
    assert pinned[1]['generation'] == previous
    assert {name: snapshots.read_snapshot_artifact(pinned, name) for name in snapshots.NAMES} == artifacts('previous')


def test_pinned_reader_keeps_one_generation_across_commit(tmp_path):
    snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    pinned = snapshots.resolve_snapshot(tmp_path)
    snapshots.publish_snapshot(tmp_path, artifacts('candidate'))
    assert {name: snapshots.read_snapshot_artifact(pinned, name) for name in snapshots.NAMES} == artifacts('previous')
    current = snapshots.resolve_snapshot(tmp_path)
    assert {name: snapshots.read_snapshot_artifact(current, name) for name in snapshots.NAMES} == artifacts('candidate')


@pytest.mark.parametrize('altered', ['pointer', 'manifest', 'artifact'])
def test_corrupt_committed_snapshot_is_refused(tmp_path, altered):
    snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    pinned = snapshots.resolve_snapshot(tmp_path)
    if altered == 'pointer':
        (tmp_path / 'current.json').write_text('{"schema_version":1,"generation":"../foreign"}')
    elif altered == 'manifest':
        (pinned[0] / 'manifest.json').write_text('{}')
    else:
        (pinned[0] / 'index.html').write_text('altered')
    with pytest.raises(RuntimeError):
        current = snapshots.resolve_snapshot(tmp_path)
        snapshots.read_snapshot_artifact(current, 'index.html')


def test_api_prefers_committed_payload_and_pages_over_legacy(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    spec = importlib.util.spec_from_file_location('snapshot_api_fixture', Path(__file__).with_name('dashboard_api.py'))
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    root = api.get_local_path('Dashboard')
    generation = snapshots.publish_snapshot(root, artifacts('committed'))
    (root / 'dashboard_payload.json').write_text('{"schema_version":1,"label":"legacy partial"}')
    assert api.read_cached_dashboard_payload()['label'] == 'committed'
    assert api.get_cached_dashboard_payload_path().parent.name == generation
    assert api.read_dashboard_html('index.html') == artifacts('committed')['index.html']
    assert api.read_dashboard_html('index_terminal.html') == artifacts('committed')['index_terminal.html']
    (root / 'current.json').write_text('{}')
    with pytest.raises(RuntimeError):
        api.read_cached_dashboard_payload()
    with pytest.raises(RuntimeError):
        api.read_dashboard_html('index.html')



def test_generation_admission_limit_preserves_current_and_pinned_reader(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshots, 'MAX_SNAPSHOT_GENERATIONS', 2)
    snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    pinned = snapshots.resolve_snapshot(tmp_path)
    current_id = snapshots.publish_snapshot(tmp_path, artifacts('current'))
    before = (tmp_path / 'current.json').read_bytes()
    with pytest.raises(snapshots.SnapshotCapacityError, match='generation limit'):
        snapshots.publish_snapshot(tmp_path, artifacts('refused'))
    assert (tmp_path / 'current.json').read_bytes() == before
    assert snapshots.resolve_snapshot(tmp_path)[1]['generation'] == current_id
    assert len(list((tmp_path / 'generations').iterdir())) == 2
    assert snapshots.read_snapshot_artifact(pinned, 'index.html') == artifacts('previous')['index.html']


def test_byte_limit_counts_abandoned_staging_and_creates_nothing(tmp_path, monkeypatch):
    snapshots.publish_snapshot(tmp_path, artifacts('current'))
    orphan = tmp_path / 'generations' / ('a' * 32)
    orphan.mkdir()
    (orphan / 'index.html').write_bytes(b'x' * 20000)
    before = (tmp_path / 'current.json').read_bytes()
    monkeypatch.setattr(snapshots, 'MAX_SNAPSHOT_STORAGE_BYTES', 20000)
    with pytest.raises(snapshots.SnapshotCapacityError, match='byte limit'):
        snapshots.publish_snapshot(tmp_path, artifacts('refused'))
    assert (tmp_path / 'current.json').read_bytes() == before
    assert len(list((tmp_path / 'generations').iterdir())) == 2
    assert (orphan / 'index.html').stat().st_size == 20000


def test_candidate_peak_budget_refused_before_any_directory_created(tmp_path, monkeypatch):
    root = tmp_path / 'new-store'
    monkeypatch.setattr(snapshots, 'MAX_SNAPSHOT_STORAGE_BYTES', 1)
    with pytest.raises(snapshots.SnapshotCapacityError, match='byte limit'):
        snapshots.publish_snapshot(root, artifacts('refused'))
    assert not root.exists()


@pytest.mark.parametrize('entry_kind', ['unexpected-name', 'nested-directory', 'too-many-files'])
def test_unexpected_store_shape_refused_without_deletion(tmp_path, entry_kind):
    generations = tmp_path / 'generations'
    generations.mkdir()
    directory = generations / ('foreign' if entry_kind == 'unexpected-name' else 'a' * 32)
    directory.mkdir()
    if entry_kind == 'nested-directory':
        (directory / 'nested').mkdir()
    if entry_kind == 'too-many-files':
        for index in range(snapshots.MAX_GENERATION_FILES + 1):
            (directory / str(index)).write_text('fixture')
    with pytest.raises(snapshots.SnapshotCapacityError):
        snapshots.publish_snapshot(tmp_path, artifacts('refused'))
    assert directory.exists()
    assert not (tmp_path / 'current.json').exists()



def test_owned_reader_handles_survive_next_commit_and_close_on_exit(tmp_path):
    snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    with snapshots.pin_snapshot(tmp_path) as pinned:
        with snapshots.SnapshotCatalogLock(tmp_path, wait_timeout=0):
            pass  # Actual I/O does not monopolize the admission gate.
        snapshots.publish_snapshot(tmp_path, artifacts('candidate'))
        for name in snapshots.NAMES:
            assert snapshots.read_snapshot_artifact(pinned, name) == artifacts('previous')[name]
        handles = list(pinned.streams.values())
        assert all(not stream.closed for stream in handles)
    assert all(stream.closed for stream in handles)
    with pytest.raises(RuntimeError, match='reader is closed'):
        snapshots.read_snapshot_artifact(pinned, 'index.html')


def test_reader_exception_closes_handles_and_releases_catalog(tmp_path):
    snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    with pytest.raises(ValueError, match='fixture failed'):
        with snapshots.pin_snapshot(tmp_path) as pinned:
            handles = list(pinned.streams.values())
            raise ValueError('fixture failed')
    assert all(stream.closed for stream in handles)
    with snapshots.SnapshotCatalogLock(tmp_path, wait_timeout=0):
        pass


def test_handle_acquisition_failure_closes_previous_files(tmp_path, monkeypatch):
    snapshots.publish_snapshot(tmp_path, artifacts('previous'))
    original = Path.open
    opened = []
    def refusal(path, *args, **kwargs):
        if path.name == 'index_terminal.html':
            raise OSError('fixture open failed')
        stream = original(path, *args, **kwargs)
        if path.name in snapshots.NAMES:
            opened.append(stream)
        return stream
    monkeypatch.setattr(Path, 'open', refusal)
    with pytest.raises(OSError, match='fixture open failed'):
        with snapshots.pin_snapshot(tmp_path):
            pytest.fail('partially opened reader returned')
    assert opened and all(stream.closed for stream in opened)
    with snapshots.SnapshotCatalogLock(tmp_path, wait_timeout=0):
        pass


def test_legacy_reader_does_not_create_a_catalog(tmp_path):
    root = tmp_path / 'absent'
    with snapshots.pin_snapshot(root) as pinned:
        assert pinned is None
    assert not root.exists()



def test_collection_keeps_current_even_if_its_directory_timestamp_is_old(tmp_path):
    import os
    generations = [snapshots.publish_snapshot(tmp_path, artifacts(str(i))) for i in range(6)]
    current = snapshots.resolve_snapshot(tmp_path)
    os.utime(current[0], (1, 1))
    result = snapshots.collect_snapshots(tmp_path, keep_recent=2)
    assert generations[-1] in result['retained']
    assert len(result['removed']) == 3
    assert snapshots.read_snapshot_artifact(snapshots.resolve_snapshot(tmp_path), 'index.html') == artifacts('5')['index.html']


def test_collection_preserves_open_reader_then_can_retry_after_close(tmp_path):
    import os
    snapshots.publish_snapshot(tmp_path, artifacts('reader'))
    with snapshots.pin_snapshot(tmp_path) as reader:
        old = reader.directory.name
        for i in range(4):
            snapshots.publish_snapshot(tmp_path, artifacts(str(i)))
        result = snapshots.collect_snapshots(tmp_path, keep_recent=2)
        assert old in (result['deferred'] if os.name == 'nt' else result['removed'])
        for name in snapshots.NAMES:
            assert snapshots.read_snapshot_artifact(reader, name) == artifacts('reader')[name]
    result = snapshots.collect_snapshots(tmp_path, keep_recent=2)
    assert not (tmp_path / 'generations' / old).exists()
    assert not result['deferred']


def test_collection_removes_old_abandoned_stage_and_restores_capacity(tmp_path, monkeypatch):
    import os
    snapshots.publish_snapshot(tmp_path, artifacts('current'))
    stage = tmp_path / 'generations' / ('a' * 32)
    stage.mkdir()
    (stage / 'index.html').write_text('abandoned')
    os.utime(stage, (1, 1))
    for i in range(3):
        snapshots.publish_snapshot(tmp_path, artifacts(str(i)))
    monkeypatch.setattr(snapshots, 'MAX_SNAPSHOT_GENERATIONS', 5)
    with pytest.raises(snapshots.SnapshotCapacityError):
        snapshots.check_snapshot_capacity(tmp_path, artifacts('next'))
    result = snapshots.collect_snapshots(tmp_path, keep_recent=2)
    assert stage.name in result['removed']
    snapshots.publish_snapshot(tmp_path, artifacts('next'))
    assert json.loads(snapshots.read_snapshot_artifact(snapshots.resolve_snapshot(tmp_path), 'dashboard_payload.json'))['label'] == 'next'


def test_collection_refuses_unknown_file_before_any_removal(tmp_path):
    import os
    old = snapshots.publish_snapshot(tmp_path, artifacts('old'))
    bad = tmp_path / 'generations' / old
    (bad / 'foreign.txt').write_text('must survive')
    os.utime(bad, (1, 1))
    for i in range(3):
        snapshots.publish_snapshot(tmp_path, artifacts(str(i)))
    before = {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    with pytest.raises(snapshots.SnapshotCapacityError):
        snapshots.collect_snapshots(tmp_path, keep_recent=2)
    after = {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file() and path.name != 'catalog.lock'}
    assert after == before


def test_collection_without_committed_pointer_does_nothing(tmp_path):
    stage = tmp_path / 'generations' / ('a' * 32)
    stage.mkdir(parents=True)
    (stage / 'index.html').write_text('uncommitted')
    assert snapshots.collect_snapshots(tmp_path) == {'removed': [], 'deferred': [], 'retained': []}
    assert (stage / 'index.html').read_text() == 'uncommitted'
