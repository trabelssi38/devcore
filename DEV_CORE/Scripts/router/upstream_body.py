"""Read uncompressed successful provider bodies with a byte capacity."""
import asyncio
import httpx


class UpstreamBodyRefusal(Exception):
    pass


def validate_response_headers(headers, max_bytes):
    """Return a small declared length, refusing ambiguous or oversized headers."""
    if headers.get('content-encoding', 'identity').lower() != 'identity':
        raise UpstreamBodyRefusal('Compressed provider response refused')
    length = headers.get('content-length')
    if length is None:
        return None
    length = length.strip(' \t')
    if not length or any(char < '0' or char > '9' for char in length):
        raise UpstreamBodyRefusal('Invalid provider response length')
    significant = length.lstrip('0') or '0'
    capacity = str(max_bytes)
    if len(significant) > len(capacity) or (len(significant) == len(capacity) and significant > capacity):
        raise UpstreamBodyRefusal('Provider response exceeds byte capacity')
    return int(significant)


async def post_bounded(client, url, *, json, headers, max_bytes=16 * 1024 * 1024):
    if type(max_bytes) is not int or not 1 <= max_bytes <= 16 * 1024 * 1024:
        raise ValueError('Invalid upstream response capacity')
    try:
        async with client.stream('POST', url, json=json,
            headers={**headers, 'Accept-Encoding': 'identity'}, follow_redirects=False) as response:
            if response.status_code != 200:
                # Status and retry headers suffice; never retain an error body.
                return httpx.Response(response.status_code, headers=response.headers,
                    content=b'', request=response.request)
            declared = validate_response_headers(response.headers, max_bytes)
            body = bytearray()
            batch_chunks = batch_bytes = 0
            async for chunk in response.aiter_raw():
                if len(body) + len(chunk) > max_bytes:
                    raise UpstreamBodyRefusal('Provider response exceeds byte capacity')
                if declared is not None and len(body) + len(chunk) > declared:
                    raise UpstreamBodyRefusal('Provider response length mismatch')
                body.extend(chunk)
                batch_chunks += 1
                batch_bytes += len(chunk)
                if batch_chunks >= 64 or batch_bytes >= 65536:
                    # Buffered transports need not suspend while iterating.
                    await asyncio.sleep(0)
                    batch_chunks = batch_bytes = 0
            if declared is not None and len(body) != declared:
                raise UpstreamBodyRefusal('Provider response length mismatch')
            return httpx.Response(200, headers=response.headers, content=bytes(body), request=response.request)
    except httpx.RemoteProtocolError as exc:
        raise UpstreamBodyRefusal('Invalid provider response framing') from exc
