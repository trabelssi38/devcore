from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parent


def test_web_api_client_wraps_generated_openapi_client() -> None:
    api_client = (WEB_ROOT / "src" / "lib" / "apiClient.ts").read_text(encoding="utf-8")

    assert "DevCoreApiClient" in api_client
    assert "devcore-api-client" in api_client
    assert "getHealth" in api_client
    assert "getTasks" in api_client


def test_sse_hook_uses_eventsource_and_cleans_up() -> None:
    hook = (WEB_ROOT / "src" / "hooks" / "useDevCoreEvents.ts").read_text(encoding="utf-8")

    assert "new EventSource" in hook
    assert "/api/v1/events" in hook
    assert "source.close()" in hook
    assert "useEffect" in hook


def test_home_page_wires_api_and_sse_modules() -> None:
    page = (WEB_ROOT / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "getHealth" in page
    assert "useDevCoreEvents" in page
