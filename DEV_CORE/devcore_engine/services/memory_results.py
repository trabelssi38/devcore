"""Bounded wire contract for the Cockpit's Cosine search results, not an ACL."""
import asyncio
import json
import math

MAX_JSON_DEPTH = 64
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_PAYLOAD_NODES = 4096


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Nonfinite JSON number')


async def decode_memory_hits(raw, limit):
    """Validate the entire collection before publishing any hit."""
    text = raw.decode('utf-8')
    depth, quoted, escaped = 0, False, False
    for start in range(0, len(text), 64 * 1024):
        for char in text[start:start + 64 * 1024]:
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in '[{':
                depth += 1
                if depth > MAX_JSON_DEPTH:
                    raise ValueError('Excessive JSON nesting')
            elif char in ']}':
                depth -= 1
        await asyncio.sleep(0)
    data = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(data, dict) or data.get('status', 'ok') != 'ok':
        raise ValueError('Invalid search response')
    hits = data.get('result')
    if not isinstance(hits, list) or len(hits) > limit:
        raise ValueError('Invalid hit count')
    validated, identifiers, previous_score = [], set(), 1.0
    nodes = 0
    for hit in hits:
        if not isinstance(hit, dict):
            raise ValueError('Invalid hit')
        identifier = hit.get('id')
        if type(identifier) is int:
            if not 0 <= identifier <= 2**64 - 1:
                raise ValueError('Invalid point identifier')
        elif type(identifier) is str:
            if not identifier or len(identifier.encode('utf-8')) > 128 or any(ord(char) < 32 for char in identifier):
                raise ValueError('Invalid point identifier')
        else:
            raise ValueError('Invalid point identifier')
        identity = (type(identifier), identifier)
        if identity in identifiers:
            raise ValueError('Duplicate point identifier')
        identifiers.add(identity)
        score = hit.get('score')
        if type(score) not in (int, float) or not math.isfinite(score) or not -1 <= score <= previous_score:
            raise ValueError('Invalid Cosine score or order')
        previous_score = score
        payload = hit.get('payload')
        payload = {} if payload is None else payload
        if not isinstance(payload, dict):
            raise ValueError('Invalid point payload')
        stack = [payload]
        while stack:
            item = stack.pop()
            nodes += 1
            if nodes > MAX_PAYLOAD_NODES:
                raise ValueError('Payload node capacity exceeded')
            if isinstance(item, dict):
                stack.extend(item.keys())
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, str):
                item.encode('utf-8')  # Refuse lone escaped surrogates.
            elif type(item) is float and not math.isfinite(item):
                raise ValueError('Nonfinite payload number')
            if nodes % 64 == 0:
                await asyncio.sleep(0)
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise ValueError('Payload byte capacity exceeded')
        # Upstream vector, debug data and unknown hit fields are not forwarded.
        validated.append({'id': identifier, 'score': score, 'payload': payload})
    return validated
