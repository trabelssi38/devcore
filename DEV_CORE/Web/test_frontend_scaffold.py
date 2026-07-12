import json
from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent


def test_frontend_package_declares_next_react_typescript() -> None:
    package = json.loads((WEB_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["dev"] == "next dev"
    assert package["scripts"]["build"] == "next build"
    assert package["dependencies"]["next"]
    assert package["dependencies"]["react"]
    assert package["dependencies"]["react-dom"]
    assert package["devDependencies"]["typescript"]


def test_design_tokens_are_defined_as_css_variables() -> None:
    tokens = (WEB_ROOT / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    for token in [
        "--color-bg",
        "--color-surface",
        "--color-border",
        "--color-accent",
        "--color-success",
        "--color-warning",
        "--color-danger",
        "--font-sans",
        "--space-4",
        "--radius-card",
    ]:
        assert token in tokens


def test_app_shell_uses_accessible_landmarks() -> None:
    layout = (WEB_ROOT / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
    page = (WEB_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "lang=\"fr\"" in layout
    assert "<main" in page
    assert "aria-label=\"Vue synthétique DEV_CORE\"" in page
    assert "DEV_CORE Platform" in page
