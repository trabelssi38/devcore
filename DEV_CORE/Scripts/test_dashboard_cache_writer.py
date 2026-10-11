"""The API enriches responses without becoming a second projection writer."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_response_cursor_comes_from_pinned_generation_not_latest_pointer(runtime, monkeypatch):
    from dashboard import snapshots
    module, cache = runtime
    root = cache.parent
    def publish(label):
        text = json.dumps({'schema_version': 1, 'label': label,
                           'cache': {'snapshot_cursor': 'snapshot:' + 'f' * 32}})
        return snapshots.publish_snapshot(root, {
            'dashboard_payload.json': text,
            'payload_hash.txt': hashlib.sha256(text.encode()).hexdigest(),
            'index.html': '<html>fixture</html>', 'index_terminal.html': '<html>fixture</html>',
        })
    generation_a = publish('A')
    original_read = module.read_snapshot_artifact
    published = []
    def publish_during_read(snapshot, name):
        assert snapshot.manifest['generation'] == generation_a
        published.append(publish('B'))
        return original_read(snapshot, name)
    monkeypatch.setattr(module, 'read_snapshot_artifact', publish_during_read)
    monkeypatch.setattr(module, 'load_dashboard_read_model', lambda: {})
    # Resolving the latest pointer independently would attach B's id to A's bytes.
    monkeypatch.setattr(module, 'get_dashboard_snapshot_cursor',
                        lambda: pytest.fail('response cursor resolved independently of pinned bytes'))
    response = module.read_cached_dashboard_payload()
    assert response['label'] == 'A'
    assert response['cache']['snapshot_cursor'] == 'snapshot:' + generation_a
    assert snapshots.resolve_snapshot(root)[1]['generation'] == published[0]
    assert published[0] != generation_a
    on_disk = json.loads((root / 'generations' / generation_a / 'dashboard_payload.json').read_text())
    assert on_disk['cache']['snapshot_cursor'] == 'snapshot:' + 'f' * 32
    assert cache.read_bytes() == b'previous fixture cache'


def test_fallback_does_not_claim_a_committed_snapshot(runtime, monkeypatch):
    module, _ = runtime
    monkeypatch.setattr(module, 'load_dashboard_read_model', lambda: {})
    response = module.build_fallback_dashboard_payload()
    assert response['cache'] == {'hit': False, 'snapshot_cursor': None}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    spec = importlib.util.spec_from_file_location('dashboard_cache_writer_fixture', Path(__file__).with_name('dashboard_api.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cache = module.get_cached_dashboard_payload_path()
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b'previous fixture cache')
    (cache.parent / 'payload_hash.txt').write_bytes(b'previous fixture hash')
    def forbidden_write(*args):
        pytest.fail('API attempted a second cache write')
    monkeypatch.setattr(module, 'write_json_with_retry', forbidden_write)
    return module, cache


def test_refresh_enrichment_does_not_modify_generator_cache_or_hash(runtime, monkeypatch):
    module, cache = runtime
    generated = {'schema_version': 1, 'sections': {}, 'task_details': {}, 'token_metrics': {}}
    text = json.dumps(generated, indent=2, ensure_ascii=False)
    def generated_process(*args, **kwargs):
        cache.write_bytes(text.encode('utf-8'))  # Simulated producer, isolated root only.
        (cache.parent / 'payload_hash.txt').write_text(hashlib.sha256(cache.read_bytes()).hexdigest())
        return SimpleNamespace(returncode=0, stdout=text + '\n', stderr='')
    monkeypatch.setattr(module.subprocess, 'run', generated_process)
    monkeypatch.setattr(module, 'load_dashboard_read_model', lambda: {'cursor': 'fixture'})
    response = module.refresh_dashboard_payload_cache()
    assert response['read_model'] == {'cursor': 'fixture'}
    assert json.loads(cache.read_bytes()) == generated
    assert (cache.parent / 'payload_hash.txt').read_text() == hashlib.sha256(cache.read_bytes()).hexdigest()


@pytest.mark.parametrize('failure', ['process', 'empty', 'invalid-json', 'schema'])
def test_failed_refresh_never_writes_an_api_cache(runtime, monkeypatch, failure):
    module, cache = runtime
    stdout = {'process': '', 'empty': '', 'invalid-json': '{', 'schema': '{"schema_version":999}'}[failure]
    monkeypatch.setattr(module.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(
        returncode=1 if failure == 'process' else 0, stdout=stdout, stderr='fixture process failed'))
    with pytest.raises((RuntimeError, json.JSONDecodeError)):
        module.refresh_dashboard_payload_cache()
    assert cache.read_bytes() == b'previous fixture cache'
    assert (cache.parent / 'payload_hash.txt').read_bytes() == b'previous fixture hash'



@pytest.mark.parametrize('committed', [False, True])
def test_fresh_cache_contents_and_timestamp_use_open_descriptor(runtime, monkeypatch, committed):
    module, cache = runtime
    payload = {'schema_version': 1, 'label': 'same-file',
               'cache': {'snapshot_cursor': 'snapshot:' + 'f' * 32}}
    text = json.dumps(payload)
    if committed:
        from dashboard import snapshots
        generation = snapshots.publish_snapshot(cache.parent, {
            'dashboard_payload.json': text, 'payload_hash.txt': hashlib.sha256(text.encode()).hexdigest(),
            'index.html': '<html>fixture</html>', 'index_terminal.html': '<html>fixture</html>',
        })
        cache = cache.parent / 'generations' / generation / 'dashboard_payload.json'
    else:
        cache.write_text(text)
    original_stat = Path.stat
    def no_payload_stat(path, *args, **kwargs):
        if path == cache:
            pytest.fail('freshness used an unreserved payload path')
        return original_stat(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', no_payload_stat)
    monkeypatch.setattr(module, 'get_cached_dashboard_payload_path', lambda: pytest.fail('unreserved helper used'))
    monkeypatch.setattr(module, 'refresh_dashboard_payload_cache', lambda: pytest.fail('fresh cache regenerated'))
    response = module.build_dashboard_payload()
    assert response['label'] == 'same-file'
    assert response['cache']['modified_at'] > 0
    assert response['cache']['snapshot_cursor'] == ('snapshot:' + generation if committed else None)


@pytest.mark.parametrize('timestamp', [1, 4102444800])
def test_old_or_future_cache_requests_refresh(runtime, monkeypatch, timestamp):
    import os
    module, cache = runtime
    cache.write_text('{"schema_version":1,"label":"previous"}')
    os.utime(cache, (timestamp, timestamp))
    refreshed = []
    def refresh():
        refreshed.append(True)
        cache.write_text('{"schema_version":1,"label":"updated"}')
    monkeypatch.setattr(module, 'refresh_dashboard_payload_cache', refresh)
    response = module.build_dashboard_payload()
    assert refreshed == [True]
    assert response['label'] == 'updated'
