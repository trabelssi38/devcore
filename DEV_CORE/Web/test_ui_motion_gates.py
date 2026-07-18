import re
from pathlib import Path

WEB_ROOT = Path(__file__).parent

def test_no_transition_all():
    """Verify that 'transition: all' is not used in any stylesheet or component."""
    pattern = re.compile(r'transition:\s*all\b', re.IGNORECASE)
    
    # Check styles
    for path in WEB_ROOT.glob("**/*.css"):
        if any(part in path.parts for part in (".next", "node_modules", "out", "dist", "build")):
            continue
        content = path.read_text(encoding="utf-8")
        assert not pattern.search(content), f"Forbidden 'transition: all' found in {path.name}"

    # Check components
    for path in (WEB_ROOT / "src" / "components").glob("*.tsx"):
        content = path.read_text(encoding="utf-8")
        assert not pattern.search(content), f"Forbidden 'transition: all' found in {path.name}"


def test_prefers_reduced_motion():
    """Verify that prefers-reduced-motion reset is declared in globals.css."""
    globals_css = WEB_ROOT / "src" / "app" / "globals.css"
    assert globals_css.exists(), "globals.css not found"
    
    content = globals_css.read_text(encoding="utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in content, (
        "prefers-reduced-motion reset is missing in globals.css"
    )


def test_no_layout_transitions():
    """Verify that layout changing properties are not animated in transitions."""
    forbidden_props = ["width", "height", "top", "left", "right", "bottom", "margin", "padding"]
    
    # Regex matching transition rules (e.g. transition: width 150ms)
    pattern = re.compile(r'transition:\s*([^;}]+)', re.IGNORECASE)

    for path in WEB_ROOT.glob("**/*.css"):
        if any(part in path.parts for part in (".next", "node_modules", "out", "dist", "build")):
            continue
        content = path.read_text(encoding="utf-8")
        matches = pattern.findall(content)
        for transition_val in matches:
            for prop in forbidden_props:
                # Ensure the property name is matched as a word boundary
                prop_pattern = re.compile(rf'\b{prop}\b', re.IGNORECASE)
                assert not prop_pattern.search(transition_val), (
                    f"Forbidden transition of layout property '{prop}' in {path.name}: '{transition_val.strip()}'"
                )
