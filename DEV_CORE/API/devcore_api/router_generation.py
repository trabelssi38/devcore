"""Bounded adapter for successful, non-streaming auxiliary chat responses.

Correlation and cost are explicitly supplied by the application. Legacy router
token estimates and active-project files are never consulted by this adapter.
"""
import json

from .llmops import LangfuseEvent, LlmUsage, LlmOpsClient


def event_from_chat_response(response, *, correlation, cost_usd):
    if response.status_code != 200 or response.headers.get('x-devcore-route') != 'auxiliary':
        raise ValueError('Successful auxiliary response required')
    body = response.body
    if type(body) is not bytes or len(body) > 65536:
        raise ValueError('Observation response exceeds byte limit')
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError('Invalid response schema')
    model = response.headers.get('x-devcore-resolved-model')
    if payload.get('model', model) != model:
        raise ValueError('Response model conflicts with resolved model')
    usage = payload.get('usage')
    if not isinstance(usage, dict):
        raise ValueError('Explicit response usage required')
    event = LangfuseEvent(name='router.generation', model=model,
        trace_id=correlation.trace_id, run_id=correlation.run_id,
        task_id=correlation.task_id, project_id=correlation.project_id,
        usage=LlmUsage(prompt_tokens=usage.get('prompt_tokens'),
            completion_tokens=usage.get('completion_tokens'),
            total_tokens=usage.get('total_tokens'), cost_usd=cost_usd))
    LlmOpsClient._payload(event)
    return event
