from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent


def test_css_declares_responsive_breakpoints_and_touch_targets() -> None:
    css = (WEB_ROOT / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 480px)" in css
    assert "min-height: 44px" in css
    assert "min-width: 44px" in css


def test_css_keeps_visible_focus_and_non_color_status_cues() -> None:
    css = (WEB_ROOT / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert ":focus-visible" in css
    assert "outline: 2px solid var(--color-accent)" in css
    assert ".badge::before" in css
    assert "content: \"•\"" in css


def test_components_expose_accessible_text_not_color_only() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (WEB_ROOT / "src" / "components").glob("*.tsx")
    )

    assert "aria-label" in source
    assert "statusText" in source
    assert "sr-only" in source
