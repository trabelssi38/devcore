from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent


def test_dashboard_components_exist_for_core_domains() -> None:
    components = WEB_ROOT / "src" / "components"

    expected = [
        "ProjectSummary.tsx",
        "TaskList.tsx",
        "RunTimeline.tsx",
        "HealthPanel.tsx",
    ]

    for filename in expected:
        assert (components / filename).exists(), filename


def test_home_page_composes_core_domain_components() -> None:
    page = (WEB_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

    for component in ["ProjectSummary", "TaskList", "RunTimeline", "HealthPanel"]:
        assert component in page


def test_components_use_accessible_labels_and_status_text() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (WEB_ROOT / "src" / "components").glob("*.tsx")
    )

    assert "aria-label=\"Résumé projet\"" in source
    assert "aria-label=\"Liste des tâches\"" in source
    assert "aria-label=\"Chronologie des runs\"" in source
    assert "aria-label=\"Santé plateforme\"" in source
    assert "statusText" in source
