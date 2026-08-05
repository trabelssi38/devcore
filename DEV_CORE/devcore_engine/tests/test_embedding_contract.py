import unittest
from devcore_engine.services.embedding import EmbeddingService


class TestEmbeddingContract(unittest.TestCase):
    def test_contract_properties(self):
        contract = EmbeddingService.get_contract()
        self.assertEqual(contract["dimensions"], 768)
        self.assertEqual(contract["model"], "gemini-embedding-001")
        self.assertEqual(contract["query_model"], "gemini-embedding-001")
        self.assertIn("decisions", contract["qdrant_collections"])

    def test_request_body_sync(self):
        body = EmbeddingService.create_request_body("sync text", is_query=False)
        self.assertEqual(body["model"], "gemini-embedding-001")
        self.assertEqual(body["dimensions"], 768)

    def test_request_body_query(self):
        body = EmbeddingService.create_request_body("query text", is_query=True)
        self.assertEqual(body["model"], "gemini-embedding-001")
        self.assertEqual(body["dimensions"], 768)

    def test_validate_vector_valid(self):
        vec = [0.1] * 768
        self.assertTrue(EmbeddingService.validate_vector(vec, context="unit"))

    def test_validate_vector_invalid(self):
        vec = [0.1] * 3072
        with self.assertRaises(ValueError) as ctx:
            EmbeddingService.validate_vector(vec, context="unit")
        self.assertIn("expected 768, got 3072", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
