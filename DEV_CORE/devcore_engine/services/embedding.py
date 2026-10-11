# embedding.py -- Native Python embedding contract service
import json
import math

from typing import Dict, Any, List


class EmbeddingService:
    ENDPOINT = "http://127.0.0.1:20130/v1/embeddings"
    DIMENSIONS = 768
    CONTRACT_VERSION = "gemini-embedding-001:768:v1"
    MAX_RESPONSE_BYTES = 128 * 1024
    MODEL = "gemini-embedding-001"
    QUERY_MODEL = "gemini-embedding-001"
    QDRANT_COLLECTIONS = ["decisions", "architecture", "code", "documentation"]

    @classmethod
    def get_contract(cls) -> Dict[str, Any]:
        return {
            "endpoint": cls.ENDPOINT,
            "version": cls.CONTRACT_VERSION,
            "dimensions": cls.DIMENSIONS,
            "model": cls.MODEL,
            "query_model": cls.QUERY_MODEL,
            "qdrant_collections": cls.QDRANT_COLLECTIONS,
        }

    @classmethod
    def create_request_body(cls, text: str, is_query: bool = False) -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 32768:
            raise ValueError('Embedding input must be nonempty UTF-8 text <=32768 bytes')
        model = cls.QUERY_MODEL if is_query else cls.MODEL
        return {
            "model": model,
            "dimensions": cls.DIMENSIONS,
            "input": text,
        }

    @classmethod
    def validate_vector(cls, vector: List[float], context: str = "unit") -> bool:
        if not isinstance(vector, (list, tuple)):
            raise ValueError('Embedding vector must be a numeric sequence')
        if len(vector) != cls.DIMENSIONS:
            raise ValueError(f"Embedding vector dimension mismatch in {context}: expected {cls.DIMENSIONS}, got {len(vector)}")
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
            raise ValueError('Embedding vector must contain finite numbers')
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm == 0:
            raise ValueError('Embedding vector norm must be finite and nonzero')
        return True

    @classmethod
    async def embed_query(cls, client, text):
        body = cls.create_request_body(text, is_query=True)
        async with client.stream('POST', cls.ENDPOINT, json=body,
            headers={'Accept-Encoding': 'identity'}, follow_redirects=False, timeout=3.0) as response:
            if response.status_code != 200 or response.headers.get('content-encoding', 'identity').lower() != 'identity':
                raise ValueError('Embedding provider unavailable')
            raw = bytearray()
            chunks = 0
            async for chunk in response.aiter_raw():
                if len(raw) + len(chunk) > cls.MAX_RESPONSE_BYTES:
                    raise ValueError('Embedding response exceeds capacity')
                raw.extend(chunk)
                chunks += 1
                if chunks % 64 == 0:
                    import asyncio
                    await asyncio.sleep(0)
        try:
            payload = json.loads(raw.decode('utf-8'))
            if payload.get('model', cls.QUERY_MODEL) != cls.QUERY_MODEL:
                raise ValueError('Embedding model mismatch')
            data = payload['data']
            if not isinstance(data, list) or len(data) != 1 or data[0].get('index', 0) != 0:
                raise ValueError('Embedding result cardinality mismatch')
            vector = data[0]['embedding']
            cls.validate_vector(vector, context='query')
        except (ValueError, KeyError, TypeError, AttributeError, RecursionError, OverflowError) as exc:
            raise ValueError('Invalid embedding provider response') from exc
        return vector
