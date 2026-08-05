import unittest
from pathlib import Path


class TestCiWorkflow(unittest.TestCase):
    def test_workflow_exists(self):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        wf_path = repo_root / ".github" / "workflows" / "ci.yml"
        self.assertTrue(wf_path.exists(), f"CI workflow does not exist at {wf_path}")

        content = wf_path.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("ci_lint.ps1", content)
        self.assertIn("ci_python_tests.ps1", content)
        self.assertIn("secret_scan.ps1", content)


if __name__ == "__main__":
    unittest.main()
