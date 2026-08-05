import unittest
from pathlib import Path
from devcore_engine.infra.diagnose import DiagnosticEngine


class TestPlatformVersion(unittest.TestCase):
    def test_platform_info(self):
        import devcore_engine
        self.assertTrue(devcore_engine.__version__.startswith("10."), f"Expected 10.x version, got {devcore_engine.__version__}")


    def test_no_legacy_v9_strings(self):
        scripts_dir = Path(__file__).resolve().parent.parent.parent / "Scripts"
        for p in scripts_dir.rglob("*.py"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("DEV_CORE v9.0", text, f"{p.name} contains legacy version string 'DEV_CORE v9.0'")


if __name__ == "__main__":
    unittest.main()
