# embedding.py -- Native Python embedding contract service
from typing import Dict, Any, List


class EmbeddingService:
    DIMENSIONS = 768
    MODEL = "gemini-embedding-001"
    QUERY_MODEL = "gemini-embedding-001"
    QDRANT_COLLECTIONS = ["decisions", "architecture", "code", "documentation"]

    @classmethod
    def get_contract(cls) -> Dict[str, Any]:
        return {
            "dimensions": cls.DIMENSIONS,
            "model": cls.MODEL,
            "query_model": cls.QUERY_MODEL,
            "qdrant_collections": cls.QDRANT_COLLECTIONS,
        }

    @classmethod
    def create_request_body(cls, text: str, is_query: bool = False) -> Dict[str, Any]:
        model = cls.QUERY_MODEL if is_query else cls.MODEL
        return {
            "model": model,
            "dimensions": cls.DIMENSIONS,
            "contents": [{"parts": [{"text": text}]}],
        }

    @classmethod
    def validate_vector(cls, vector: List[float], context: str = "unit") -> bool:
        if len(vector) != cls.DIMENSIONS:
            raise ValueError(f"Embedding vector dimension mismatch in {context}: expected {cls.DIMENSIONS}, got {len(vector)}")
        return True
