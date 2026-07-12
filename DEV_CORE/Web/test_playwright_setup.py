import json
from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent


def test_package_declares_component_and_e2e_test_scripts() -> None:
    package = json.loads((WEB_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["test:components"] == "playwright test --project=components"
    assert package["scripts"]["test:e2e"] == "playwright test --project=e2e"
    assert package["devDependencies"]["@playwright/test"]


def test_playwright_config_defines_component_and_e2e_projects() -> None:
    config = (WEB_ROOT / "playwright.config.ts").read_text(encoding="utf-8")

    assert "name: \"components\"" in config
    assert "name: \"e2e\"" in config
    assert "baseURL" in config


def test_component_and_e2e_specs_cover_dashboard_shell() -> None:
    component_spec = (WEB_ROOT / "tests" / "components" / "dashboard.spec.ts").read_text(encoding="utf-8")
    e2e_spec = (WEB_ROOT / "tests" / "e2e" / "dashboard.spec.ts").read_text(encoding="utf-8")

    assert "ProjectSummary" in component_spec
    assert "TaskList" in component_spec
    assert "getByRole(\"main\"" in e2e_spec
    assert "DEV_CORE Platform" in e2e_spec
