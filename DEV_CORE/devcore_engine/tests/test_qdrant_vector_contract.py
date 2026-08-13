import os
import unittest
import sqlite3
from pathlib import Path

class TestQdrantVectorContract(unittest.TestCase):
    def test_vector_contract(self):
        from devcore_engine.db import get_db_path
        db_path = get_db_path()
        if not db_path.exists():
            data_root = os.environ.get("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA")
            fallback = Path(data_root) / "devcore.db"
            if fallback.exists():
                db_path = fallback
        self.assertTrue(db_path.exists(), f"Unified devcore.db does not exist at {db_path}")

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()

        vec_ok = any(t.startswith("vec_") or "vec" in t for t in tables)
        self.assertTrue(vec_ok, "SQLite Vector DB unifiée has no vec0 / vec_ sémantique tables initialized.")


if __name__ == "__main__":
    unittest.main()
