import sys
import unittest
import subprocess


class TestVerifyCi(unittest.TestCase):
    def test_verify_gate_cli(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "diagnose", "--gate"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"verify gate failed: {res.stderr}")



if __name__ == "__main__":
    unittest.main()
