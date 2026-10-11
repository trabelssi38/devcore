"""Memory vector search uses one validated embedding, never a zero placeholder."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from devcore_engine.services.embedding import EmbeddingService


def json_response(status, payload):
    return httpx.Response(status, stream=httpx.ByteStream(json.dumps(payload).encode()))


def load_dashboard():
    path = Path(__file__).resolve().parents[1] / 'Scripts' / 'dashboard_api.py'
    spec = importlib.util.spec_from_file_location('memory_dashboard_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('kind', ['valid', 'zero', 'dimension', 'bool', 'nan', 'inf', 'model', 'cardinality', 'offline'])
def test_pipeline_uses_validated_768_vector_or_declares_unavailable(kind):
    async def scenario():
        dashboard = load_dashboard()
        calls, vectors = [], []
        vector = [0.1] * 768
        if kind == 'zero': vector = [0] * 768
        if kind == 'dimension': vector = [0.1] * 384
        if kind in ('bool', 'nan', 'inf'): vector[0] = {'bool': True, 'nan': float('nan'), 'inf': float('inf')}[kind]
        def handle(request):
            calls.append(request.url.path)
            body = json.loads(request.content)
            if request.url.port == 20130:
                assert body == EmbeddingService.create_request_body('alpha decision', is_query=True)
                data = [{'index': 0, 'embedding': vector}]
                return json_response(503 if kind == 'offline' else 200, {
                    'model': 'wrong' if kind == 'model' else EmbeddingService.MODEL,
                    'data': data * (2 if kind == 'cardinality' else 1)})
            vectors.append(body['vector'])
            return json_response(200, {'result': [{'id': 'fixture', 'score': 0.8, 'payload': {'text': 'decision'}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await dashboard.search_memory_pipeline_async('alpha decision', ['decisions', 'lessons'], client=client)
        if kind == 'valid':
            assert len(calls) == 3 and vectors == [vector, vector]
            assert result['total_hits'] == 2 and result['search_mode'] == 'vector' and not result['degraded']
            assert result['embedding']['dimensions'] == 768
        else:
            assert calls == ['/v1/embeddings'] and vectors == []
            assert result['total_hits'] == 0 and result['degraded'] and result['search_mode'] == 'unavailable'
    asyncio.run(scenario())


@pytest.mark.parametrize('query,collections,limit', [('', None, 5), ('x', ['../private'], 5),
    ('x', ['decisions', 'decisions'], 5), ('x', None, True), ('x', None, 21)])
def test_invalid_arguments_refused_before_network(query, collections, limit):
    dashboard = load_dashboard()
    with pytest.raises(dashboard.HTTPException) as refusal:
        asyncio.run(dashboard.search_memory_pipeline_async(query, collections, limit))
    assert refusal.value.status_code == 400


def test_embedding_cancellation_closes_response_and_propagates():
    async def scenario():
        entered, closed = asyncio.Event(), []
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                entered.set()
                await asyncio.Event().wait()
                yield b'{}'
            async def aclose(self):
                closed.append(1)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream()))) as client:
            task = asyncio.create_task(EmbeddingService.embed_query(client, 'fixture'))
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
        assert closed == [1]
    asyncio.run(scenario())


def test_backend_failure_is_degraded_without_private_error_details():
    async def scenario():
        dashboard = load_dashboard()
        def handle(request):
            if request.url.port == 20130:
                return json_response(200, {'data': [{'embedding': [0.1] * 768}]})
            raise RuntimeError('PRIVATE backend details')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await dashboard.search_memory_pipeline_async('fixture', ['decisions'], client=client)
        assert result['degraded'] and result['total_hits'] == 0
        assert 'PRIVATE' not in json.dumps(result)
    asyncio.run(scenario())


@pytest.mark.parametrize('kind', ['oversized', 'compressed', 'utf8'])
def test_embedding_response_bounds_close_transport(kind):
    async def scenario():
        closed = []
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'x' * (EmbeddingService.MAX_RESPONSE_BYTES + 1) if kind == 'oversized' else b'\xff'
            async def aclose(self): closed.append(1)
        def handle(request):
            return httpx.Response(200, headers={'Content-Encoding': 'gzip'} if kind == 'compressed' else {}, stream=Stream())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(ValueError): await EmbeddingService.embed_query(client, 'fixture')
        assert closed == [1]
    asyncio.run(scenario())


@pytest.mark.parametrize('kind', ['no_id', 'bool_id', 'negative_id', 'large_id', 'long_id',
    'no_score', 'bool_score', 'nan_score', 'inf_score', 'range_score', 'payload_type',
    'payload_inf', 'surrogate', 'duplicate_id', 'ascending', 'duplicate_key',
    'depth', 'payload_bytes', 'payload_nodes', 'status_error'])
def test_invalid_backend_hits_refuse_collection_without_losing_valid_collection(kind):
    async def scenario():
        dashboard = load_dashboard()
        hit = {'id': 'fixture', 'score': 0.8, 'payload': {'text': 'PRIVATE invalid result'}}
        hits = [hit]
        if kind == 'no_id': hit.pop('id')
        if kind == 'bool_id': hit['id'] = True
        if kind == 'negative_id': hit['id'] = -1
        if kind == 'large_id': hit['id'] = 2**64
        if kind == 'long_id': hit['id'] = 'x' * 129
        if kind == 'no_score': hit.pop('score')
        if kind == 'bool_score': hit['score'] = True
        if kind == 'nan_score': hit['score'] = float('nan')
        if kind == 'inf_score': hit['score'] = float('inf')
        if kind == 'range_score': hit['score'] = 1.5
        if kind == 'payload_type': hit['payload'] = []
        if kind == 'payload_inf': hit['payload']['value'] = float('inf')
        if kind == 'surrogate': hit['payload']['text'] = '\ud800'
        if kind == 'duplicate_id': hits.append(dict(hit))
        if kind == 'ascending': hits.append({'id': 'other', 'score': 0.9})
        if kind == 'payload_bytes': hit['payload']['text'] = 'x' * 65537
        if kind == 'payload_nodes': hit['payload']['nodes'] = [0] * 4096
        body = json.dumps({'result': hits, 'status': 'error' if kind == 'status_error' else 'ok'}).encode()
        if kind == 'duplicate_key': body = b'{"result": [], "result": []}'
        if kind == 'depth': body = b'{"result":[' + b'[' * 65 + b'0' + b']' * 65 + b']}'
        closed = []
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self): yield body
            async def aclose(self): closed.append(1)
        def handle(request):
            if request.url.port == 20130:
                return json_response(200, {'data': [{'embedding': [0.1] * 768}]})
            if 'decisions' in request.url.path:
                return httpx.Response(200, stream=Stream())
            return json_response(200, {'result': [{'id': 'valid', 'score': 0.5, 'payload': {'text': 'accepted'}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await dashboard.search_memory_pipeline_async('fixture', ['decisions', 'lessons'], client=client)
        assert result['degraded'] and result['total_hits'] == 1 and result['search_mode'] == 'vector'
        assert result['collections']['decisions']['hits'] == []
        assert result['collections']['lessons']['status'] == 'ok'
        assert 'PRIVATE' not in json.dumps(result) and closed == [1]
    asyncio.run(scenario())


def test_valid_cosine_hits_are_projected_with_null_payload_and_tied_scores():
    from devcore_engine.services.memory_results import decode_memory_hits
    hits = [{'id': 2**64 - 1, 'score': 1, 'payload': None, 'vector': [42], 'debug': 'PRIVATE'},
            {'id': 'other', 'score': 1, 'payload': {'text': 'safe'}}, {'id': 0, 'score': -1}]
    result = asyncio.run(decode_memory_hits(json.dumps({'result': hits}).encode(), 5))
    assert len(result) == 3 and result[0]['payload'] == {} and result[2]['payload'] == {}
    assert all(set(hit) == {'id', 'score', 'payload'} for hit in result)
    assert 'PRIVATE' not in json.dumps(result)


def test_memory_decoder_scan_is_cancellable():
    from devcore_engine.services.memory_results import decode_memory_hits
    async def scenario():
        task = asyncio.create_task(decode_memory_hits(b'{"result": [], "padding":"' + b'x' * 200000 + b'"}', 5))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(scenario())
