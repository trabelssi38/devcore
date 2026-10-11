import sys
import unittest
import subprocess
import os
import tempfile


class TestDcDispatch(unittest.TestCase):
    def test_cli_dispatch_diagnose(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "diagnose"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dc diagnose failed: {res.stderr}")

    def test_cli_dispatch_task(self):
        with tempfile.TemporaryDirectory(prefix="devcore-dispatch-") as root:
            env = os.environ.copy()
            env["DEVCORE_LOCAL_ROOT"] = os.path.join(root, "local")
            env["DEVCORE_DATA_ROOT"] = os.path.join(root, "shared")
            res = subprocess.run(
                [sys.executable, "-m", "devcore_engine.cli", "task", "board", "--project", "devcore"],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(res.returncode, 0, f"dc task board failed: {res.stderr}")

    def test_cli_dispatch_plugin(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "plugins", "list"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dc plugins list failed: {res.stderr}")



if __name__ == "__main__":
    unittest.main()
