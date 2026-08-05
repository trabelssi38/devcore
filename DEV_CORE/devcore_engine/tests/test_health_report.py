"""
test_health_report.py -- Python Native Unit Test for DiagnosticEngine / Health Report
"""

import unittest
from devcore_engine.infra.diagnose import DiagnosticEngine


class TestHealthReport(unittest.TestCase):
    def test_health_diagnostics(self):
        diag = DiagnosticEngine()
        report = diag.run_diagnostics()

        self.assertIn("overall_status", report)
        self.assertIn("checks", report)
        self.assertGreater(len(report["checks"]), 0)


if __name__ == "__main__":
    unittest.main()
