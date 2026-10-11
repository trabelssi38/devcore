"""Real loopback HTTP export, never Langfuse Cloud or active state."""
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from devcore_api.correlation import CorrelationContext
from devcore_api.llmops import LangfuseEvent
from devcore_api.otlp_export import OtlpExporter


def event():
    return LangfuseEvent.from_generation(name='generation', model='gpt-test', prompt_tokens=1,
        completion_tokens=2, cost_usd=.01, correlation=CorrelationContext(trace_id='1' * 32, project_id='fixture'))


@contextmanager
def receiver(body=b'{}', status=200, delayed=False, extra_headers=()):
    calls, entered, release = [], threading.Event(), threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            calls.append((self.path, dict(self.headers), self.rfile.read(int(self.headers['Content-Length']))))
            entered.set()
            if delayed:
                release.wait(3)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            for key, value in extra_headers:
                self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/api/public/otel/v1/traces', calls, entered, release
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(2)


def exporter(endpoint, **kwargs):
    return OtlpExporter(endpoint, public_key='pk-fixture', secret_key='sk-fixture', allow_local_http=True, **kwargs)


@pytest.mark.parametrize('body,status,headers,outcome', [
    (b'{}', 200, (), 'accepted'),
    (b'{"partialSuccess":{"rejectedSpans":"1","errorMessage":"private"}}', 200, (), 'partial_rejected'),
    (b'{"partialSuccess":{"rejectedSpans":"0","errorMessage":"private"}}', 200, (), 'accepted_warning'),
    (b'private', 500, (), 'http_error'),
    (b'{}', 302, (('Location', 'http://127.0.0.1:1/private'),), 'http_error'),
    (b'x' * 8193, 200, (), 'oversized_response'),
    (b'bad JSON', 200, (), 'invalid_response'),
    (b'{}', 200, (('Content-Encoding', 'gzip'),), 'invalid_response'),
], ids=['accepted', 'partial', 'warning', 'http-error', 'redirect', 'oversized', 'invalid-json', 'encoding'])
def test_real_http_export_checks_acknowledgement(body, status, headers, outcome):
    with receiver(body, status, extra_headers=headers) as (endpoint, calls, _, _):
        async def scenario():
            client = exporter(endpoint)
            try:
                assert await client.export(event(), start_ns=1, end_ns=2) == outcome
            finally:
                assert await client.aclose()
        asyncio.run(scenario())
        assert len(calls) == 1
        path, sent_headers, raw = calls[0]
        sent_headers = {key.lower(): value for key, value in sent_headers.items()}
        assert path == '/api/public/otel/v1/traces' and len(raw) < 8192
        assert sent_headers['x-langfuse-ingestion-version'] == '4'
        assert sent_headers['authorization'].startswith('Basic ')
        span = json.loads(raw)['resourceSpans'][0]['scopeSpans'][0]['spans'][0]
        assert span['traceId'] == '1' * 32 and len(span['spanId']) == 16
        attrs = {a['key']: a['value']['stringValue'] for a in span['attributes']}
        assert attrs['devcore.usage_source'] == 'caller_declared'
        assert attrs['devcore.project_id'] == 'fixture'
        assert b'sk-fixture' not in raw and b'prompt' not in raw.replace(b'prompt_tokens', b'')


@pytest.mark.parametrize('action', ['finish', 'timeout', 'cancel'])
def test_slow_receiver_is_nonblocking_bounded_and_no_retry(action):
    with receiver(delayed=True) as (endpoint, calls, entered, release):
        async def scenario():
            client = exporter(endpoint, timeout=.1 if action == 'timeout' else 2)
            task = asyncio.create_task(client.export(event(), start_ns=1, end_ns=2))
            try:
                assert await asyncio.to_thread(entered.wait, 1)
                assert await client.export(event(), start_ns=1, end_ns=2) == 'busy'
                assert not await client.aclose()
                await asyncio.sleep(.01)
                assert not task.done()  # Other coroutines run during network wait.
                if action == 'finish':
                    release.set()
                    assert await task == 'accepted'
                elif action == 'timeout':
                    assert await task == 'timeout'
                else:
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
                assert not client.busy
                assert len(calls) == 1
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
                assert await client.aclose()
            assert await client.export(event(), start_ns=1, end_ns=2) == 'closed'
        asyncio.run(scenario())


@pytest.mark.parametrize('endpoint', ['http://example.com/v1/traces', 'https://host/v1/traces?key=private',
    'https://user:private@host/v1/traces', 'https://host/api/public/ingestion'])
def test_unsafe_or_legacy_endpoint_refused(endpoint):
    with pytest.raises(ValueError):
        exporter(endpoint)


def test_invalid_timing_or_trace_never_sent():
    with receiver() as (endpoint, calls, _, _):
        async def scenario():
            client = exporter(endpoint)
            try:
                assert await client.export(event(), start_ns=2, end_ns=1) == 'invalid'
                from dataclasses import replace
                assert await client.export(replace(event(), trace_id='logical-name'), start_ns=1, end_ns=2) == 'invalid'
            finally:
                await client.aclose()
        asyncio.run(scenario())
        assert calls == []
