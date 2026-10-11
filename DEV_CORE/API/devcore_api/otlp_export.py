"""Explicit, bounded OTLP/HTTP export. No queue, environment activation or retry."""
import asyncio
import json
import uuid
from urllib.parse import urlsplit

import httpx

from .llmops import LlmOpsClient


class OtlpExporter:
    def __init__(self, endpoint, *, public_key, secret_key, timeout=2.0, allow_local_http=False):
        url = urlsplit(endpoint)
        if (url.username or url.password or url.query or url.fragment or not url.hostname
            or url.path not in ('/v1/traces', '/api/public/otel/v1/traces')
            or not (url.scheme == 'https' or (allow_local_http is True and url.scheme == 'http'
                and url.hostname in ('127.0.0.1', '::1')))):
            raise ValueError('Explicit HTTPS trace endpoint required')
        if type(timeout) not in (int, float) or not 0 < timeout <= 10:
            raise ValueError('Export timeout must be positive and at most ten seconds')
        if any(not isinstance(key, str) or not 1 <= len(key) <= 256
               or any(ord(c) < 33 or ord(c) > 126 for c in key) for key in (public_key, secret_key)):
            raise ValueError('Explicit export credentials required')
        self.endpoint, self.timeout = endpoint, timeout
        self.busy = self.closed = False
        self.client = httpx.AsyncClient(auth=httpx.BasicAuth(public_key, secret_key),
            timeout=timeout, follow_redirects=False, trust_env=False,
            headers={'content-type': 'application/json', 'accept-encoding': 'identity',
                'x-langfuse-ingestion-version': '4'})

    @staticmethod
    def payload(event, start_ns, end_ns):
        LlmOpsClient._payload(event)
        if any(type(v) is not int or not 0 < v < (1 << 63) for v in (start_ns, end_ns)) or end_ns < start_ns:
            raise ValueError('Explicit valid span timing required')
        trace_id = uuid.UUID(event.trace_id).hex
        if trace_id == '0' * 32:
            raise ValueError('Nonzero OTLP trace ID required')
        attributes = {'langfuse.observation.type': 'generation', 'gen_ai.request.model': event.model,
            'devcore.usage_source': 'caller_declared', 'devcore.trace_id': event.trace_id,
            'devcore.prompt_tokens': str(event.usage.prompt_tokens),
            'devcore.completion_tokens': str(event.usage.completion_tokens),
            'devcore.cost_usd': str(event.usage.cost_usd)}
        for key in ('run_id', 'task_id', 'project_id'):
            if getattr(event, key) is not None:
                attributes['devcore.' + key] = getattr(event, key)
        span = {'traceId': trace_id, 'spanId': uuid.uuid4().hex[:16], 'name': event.name,
            'kind': 1, 'startTimeUnixNano': str(start_ns), 'endTimeUnixNano': str(end_ns),
            'attributes': [{'key': key, 'value': {'stringValue': value}} for key, value in attributes.items()]}
        body = json.dumps({'resourceSpans': [{'resource': {'attributes': [
            {'key': 'service.name', 'value': {'stringValue': 'devcore'}}]},
            'scopeSpans': [{'scope': {'name': 'devcore.llmops'}, 'spans': [span]}]}]}).encode()
        if len(body) > 8192:
            raise ValueError('Export payload exceeds byte limit')
        return body

    async def export(self, event, *, start_ns, end_ns):
        if self.closed:
            return 'closed'
        if self.busy:
            return 'busy'
        try:
            body = self.payload(event, start_ns, end_ns)
        except (ValueError, TypeError, OverflowError):
            return 'invalid'
        self.busy = True
        try:
            async with asyncio.timeout(self.timeout):
                async with self.client.stream('POST', self.endpoint, content=body) as response:
                    if response.status_code != 200:
                        return 'http_error'
                    if (response.headers.get('content-type', '').split(';')[0].strip() != 'application/json'
                        or response.headers.get('content-encoding', 'identity') != 'identity'):
                        return 'invalid_response'
                    raw = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=1024):
                        if len(raw) + len(chunk) > 8192:
                            return 'oversized_response'
                        raw.extend(chunk)
                    try:
                        result = json.loads(raw)
                        if not isinstance(result, dict) or set(result) - {'partialSuccess'}:
                            return 'invalid_response'
                        if 'partialSuccess' in result:
                            partial = result['partialSuccess']
                            if not isinstance(partial, dict):
                                return 'invalid_response'
                            rejected = partial.get('rejectedSpans', '0')
                            if type(rejected) not in (int, str) or str(rejected) not in ('0', '1'):
                                return 'invalid_response'
                            if str(rejected) == '1':
                                return 'partial_rejected'
                            return 'accepted_warning'
                    except (ValueError, RecursionError):
                        return 'invalid_response'
                    return 'accepted'
        except TimeoutError:
            return 'timeout'
        except httpx.TimeoutException:
            return 'timeout'
        except httpx.HTTPError:
            return 'transport_error'
        finally:
            self.busy = False

    async def aclose(self):
        if self.busy:
            return False  # Never silently cancel an in-flight export.
        self.closed = True
        await self.client.aclose()
        return True
