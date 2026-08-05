import os
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path
from devcore_engine.infra.secret_scanner import scan_repository


class TestSecretScan(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="devcore-secret-scan-test-"))
        try:
            subprocess.run(["git", "-C", str(self.temp_dir), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(self.temp_dir), "config", "user.name", "Test"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(self.temp_dir), "config", "user.email", "test@test.com"], check=True, capture_output=True)
        except Exception as e:
            self.skipTest(f"git init failed: {e}")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_repo(self):
        safe_file = self.temp_dir / "safe.txt"
        safe_file.write_text("no secrets here", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.temp_dir), "add", "safe.txt"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.temp_dir), "commit", "-m", "initial"], check=True, capture_output=True)

        findings = scan_repository(str(self.temp_dir))
        self.assertEqual(len(findings), 0)

    def test_leaked_secret(self):
        fake_secret = "sk-" + ("a" * 24)
        leak_file = self.temp_dir / "leak.txt"
        leak_file.write_text(f"token={fake_secret}", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.temp_dir), "add", "leak.txt"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.temp_dir), "commit", "-m", "leak"], check=True, capture_output=True)

        findings = scan_repository(str(self.temp_dir))
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0]["file"], "leak.txt")


if __name__ == "__main__":
    unittest.main()
