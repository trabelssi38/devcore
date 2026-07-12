from pathlib import Path


SKILL = Path(__file__).resolve().parent / "ui-ux" / "SKILL.md"


def test_ui_ux_skill_has_devcore_dashboard_decision_rules() -> None:
    content = SKILL.read_text(encoding="utf-8")

    assert "## Règles DEV_CORE Dashboard" in content
    assert "Dark Tech opérationnel" in content
    assert "ne pas ajouter de dépendance runtime" in content
    assert "EventSource" in content
    assert "WCAG AA" in content


def test_ui_ux_skill_locks_design_token_contract() -> None:
    content = SKILL.read_text(encoding="utf-8")

    for token in [
        "--color-bg",
        "--color-surface",
        "--color-border",
        "--color-accent",
        "--font-sans",
        "--font-mono",
        "4 / 8 / 12 / 16 / 24 / 32 / 48",
    ]:
        assert token in content
