import sys
import unittest
import subprocess


class TestDcDispatch(unittest.TestCase):
    def test_cli_dispatch_diagnose(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "diagnose"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dc diagnose failed: {res.stderr}")

    def test_cli_dispatch_task(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "task", "board"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dc task board failed: {res.stderr}")

    def test_cli_dispatch_plugin(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "plugins", "list"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dc plugins list failed: {res.stderr}")



if __name__ == "__main__":
    unittest.main()
