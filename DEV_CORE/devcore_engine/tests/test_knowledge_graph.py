"""
test_knowledge_graph.py -- Python Native Unit Test for KnowledgeGraph Service
"""

import tempfile
import unittest
from pathlib import Path

from devcore_engine.services.knowledge import KnowledgeGraph


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="devcore_kg_test_"))
        self.db_path = self.tmp_dir / "devcore.db"
        self.kg = KnowledgeGraph(self.db_path)

    def test_stats(self):
        stats = self.kg.get_stats()
        self.assertIn("nodes", stats)
        self.assertIn("edges", stats)


if __name__ == "__main__":
    unittest.main()
