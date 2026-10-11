"""Snapshot identities for SSE resynchronization; not a SQL replay cursor."""
import json
import re


def parse_snapshot_cursor(value):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r'snapshot:[0-9a-f]{32}', value):
        raise ValueError('Invalid Last-Event-ID snapshot cursor')
    return value


def event_frame(event, payload, cursor=None):
    if event not in ('message', 'dashboard.delta'):
        raise ValueError('Unknown dashboard SSE event')
    parse_snapshot_cursor(cursor)
    prefix = f'id: {cursor}\n' if cursor is not None else ''
    data = payload if event == 'message' and payload == 'Connected' else json.dumps(payload, allow_nan=False)
    return prefix + f'event: {event}\ndata: {data}\n\n'
