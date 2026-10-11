"""Local simulator refuses incompatible vectors and preserves stored evidence."""
import importlib.util
import json
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest


@pytest.fixture
def simulator(tmp_path, monkeypatch):
    for name in ('DEVCORE_LOCAL_ROOT', 'DEVCORE_DATA_ROOT', 'DEVCORE_PLATFORM_ROOT'):
        monkeypatch.setenv(name, str(tmp_path / name))
    path = Path(__file__).resolve().parents[1] / 'Scripts' / 'qdrant_server.py'
    spec = importlib.util.spec_from_file_location('qdrant_simulator_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not module.STORAGE_FILE.exists()  # Import is read-only.
    module.store = module.QdrantStore(tmp_path / 'store.json')
    module.store.create_collection('fixture', 2)
    return module


@pytest.mark.parametrize('kind', ['dimension', 'zero', 'bool', 'nan', 'inf', 'huge_integer'])
def test_invalid_batch_and_query_preserve_store(simulator, kind):
    invalid = {'dimension': [1], 'zero': [0, 0], 'bool': [True, 1],
               'nan': [float('nan'), 1], 'inf': [float('inf'), 1],
               'huge_integer': [10 ** 1000, 1]}[kind]
    store = simulator.store
    before = store.storage_file.read_bytes()
    with pytest.raises(ValueError):
        store.upsert_points('fixture', [{'id': 1, 'vector': [1, 0]}, {'id': 2, 'vector': invalid}])
    assert store.storage_file.read_bytes() == before
    assert not store.collections['fixture']['points']
    with pytest.raises(ValueError):
        store.search('fixture', invalid)


def test_cosine_order_and_extreme_finite_values(simulator):
    store = simulator.store
    store.upsert_points('fixture', [{'id': 1, 'vector': [1e300, 0]},
                                   {'id': 2, 'vector': [0, 1]}, {'id': 3, 'vector': [-1, 0]}])
    before = store.storage_file.read_bytes()
    hits = store.search('fixture', [1e300, 0])
    assert [(hit['id'], hit['score']) for hit in hits] == [(1, 1), (2, 0), (3, -1)]
    assert store.storage_file.read_bytes() == before
    with pytest.raises(ValueError):
        store.create_collection('fixture', 3)
    assert store.collections['fixture']['vector_size'] == 2


def test_invalid_legacy_vector_refuses_entire_search(simulator):
    store = simulator.store
    data = {'collections': {'fixture': {'vector_size': 2, 'distance': 'Cosine',
            'points': {'1': {'id': 1, 'vector': [1], 'payload': {}}}}}}
    store.storage_file.write_text(json.dumps(data))
    before = store.storage_file.read_bytes()
    reloaded = simulator.QdrantStore(store.storage_file)
    with pytest.raises(RuntimeError, match='stored_vector_invalid'):
        reloaded.search('fixture', [1, 0])
    assert store.storage_file.read_bytes() == before


@pytest.mark.parametrize('content', ['broken-json', '{"collections": []}'])
def test_corrupt_store_never_resets_or_accepts_writes(simulator, content):
    path = simulator.store.storage_file
    path.write_text(content)
    store = simulator.QdrantStore(path)
    for operation in (lambda: store.create_collection('new'), lambda: store.delete_collection('fixture'),
                      lambda: store.search('fixture', [1, 0])):
        with pytest.raises(RuntimeError, match='storage_unavailable'):
            operation()
    assert path.read_text() == content


def test_replace_failure_rolls_back_and_cleans_temporary(simulator, monkeypatch):
    store = simulator.store
    before = store.storage_file.read_bytes()
    def fail(*args):
        raise OSError('private-storage-detail')
    monkeypatch.setattr(simulator.os, 'replace', fail)
    with pytest.raises(OSError):
        store.upsert_points('fixture', [{'id': 1, 'vector': [1, 0]}])
    assert store.storage_file.read_bytes() == before
    assert not store.collections['fixture']['points']
    assert list(store.storage_file.parent.glob('tmp*')) == []


def test_concurrent_writers_do_not_lose_points(simulator):
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda i: simulator.store.upsert_points('fixture', [{'id': i, 'vector': [1, 0]}]), range(16)))
    reloaded = simulator.QdrantStore(simulator.store.storage_file)
    assert len(reloaded.collections['fixture']['points']) == 16


def test_scroll_does_not_claim_truncated_collection_complete(simulator):
    simulator.store.upsert_points('fixture', [{'id': i, 'vector': [1, 0]} for i in range(2)])
    with pytest.raises(ValueError, match='scroll_pagination_unsupported'):
        simulator.store.scroll('fixture', limit=1)


def test_http_refusals_reads_and_real_search(simulator):
    server = simulator.http.server.ThreadingHTTPServer(('127.0.0.1', 0), simulator.QdrantHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}', trust_env=False, timeout=3) as client:
            before = simulator.store.storage_file.read_bytes()
            assert client.get('/').json()['simulator'] is True
            assert client.get('/collections/missing').status_code == 404
            assert simulator.store.storage_file.read_bytes() == before
            assert client.put('/collections/fixture/points', json={'points': [{'id': 1, 'vector': [1, 0]}]}).status_code == 200
            assert client.post('/collections/fixture/points/search', json={'vector': [1, 0]}).json()['result'][0]['score'] == 1
            assert client.post('/collections/fixture/points/search', json={'vector': [1]}).status_code == 400
            assert client.post('/collections/fixture/points/search', json={'vector': [1, 0], 'filter': {}}).status_code == 400
            assert client.post('/collections/fixture/points/search', content=b'[]').status_code == 400
            assert client.post('/collections/fixture/points/scroll', json={}).json()['result']['points'][0]['id'] == 1
            simulator.store.collections['fixture']['points']['1']['vector'] = [0, 0]
            assert client.post('/collections/fixture/points/search', json={'vector': [1, 0]}).status_code == 503
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)
