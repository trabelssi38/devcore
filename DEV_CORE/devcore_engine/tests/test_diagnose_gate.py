import sys
import unittest
import subprocess
from devcore_engine.infra.diagnose import DiagnosticEngine


class TestDiagnoseGate(unittest.TestCase):
    def test_engine_gate_current_env(self):
        engine = DiagnosticEngine()
        report = engine.run_diagnostics()
        fails = [c for c in report.get("checks", []) if c.get("status") == "FAIL"]
        self.assertEqual(len(fails), 0, f"Diagnostic engine gate failed with items: {fails}")

    def test_cli_gate(self):
        res = subprocess.run([sys.executable, "-m", "devcore_engine.cli", "diagnose", "--gate"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dc diagnose --gate failed: {res.stderr}")



if __name__ == "__main__":
    unittest.main()
