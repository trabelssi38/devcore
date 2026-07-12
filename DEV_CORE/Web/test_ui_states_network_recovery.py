from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent


def test_ui_state_components_cover_loading_empty_error_and_retry() -> None:
    state_file = (WEB_ROOT / "src" / "components" / "UiStates.tsx").read_text(encoding="utf-8")

    for component in ["LoadingState", "EmptyState", "ErrorState", "RetryButton"]:
        assert f"function {component}" in state_file

    assert "aria-live=\"polite\"" in state_file
    assert "Réessayer" in state_file
    assert "min-height: 44" not in state_file


def test_api_resource_hook_exposes_network_recovery_state() -> None:
    hook = (WEB_ROOT / "src" / "hooks" / "useApiResource.ts").read_text(encoding="utf-8")

    for token in ["loading", "empty", "error", "retry", "AbortController"]:
        assert token in hook

    assert "navigator.onLine" in hook
    assert "online" in hook


def test_home_page_wires_loading_empty_error_states() -> None:
    page = (WEB_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "LoadingState" in page
    assert "EmptyState" in page
    assert "ErrorState" in page
    assert "retry" in page
