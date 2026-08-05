import unittest
from pathlib import Path


class TestTestExitContract(unittest.TestCase):
    def test_exit_contract(self):
        scripts_dir = Path(__file__).resolve().parent.parent.parent / "Scripts"
        violations = []
        for p in scripts_dir.glob("test_*.ps1"):
            if p.name == "test_agent_conformity.ps1":
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "python -m unittest" in text:
                continue
            if "[FAIL]" in text and not ("exit 1" in text or "exit $LASTEXITCODE" in text or "throw" in text):
                violations.append(p.name)

        self.assertEqual(len(violations), 0, f"Test scripts without explicit exit contract: {violations}")


if __name__ == "__main__":
    unittest.main()
