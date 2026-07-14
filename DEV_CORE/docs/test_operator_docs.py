from pathlib import Path


DOCS_ROOT = Path(__file__).resolve().parent
API_REFERENCE = DOCS_ROOT / "API_REFERENCE.md"
OPERATOR_GUIDE = DOCS_ROOT / "OPERATOR_GUIDE.md"


def test_api_reference_documents_public_gateway_contracts() -> None:
    text = API_REFERENCE.read_text(encoding="utf-8")

    for required in [
        "# DEV_CORE API Reference",
        "OpenAPI",
        "DEV_CORE/Schemas/openapi-v1.json",
        "GET /api/v1/health",
        "GET /api/v1/contracts",
        "GET /api/v1/tasks",
        "POST /api/v1/integrations/github/webhook",
        "X-Hub-Signature-256",
        "DevCoreApiClient",
    ]:
        assert required in text


def test_operator_guide_documents_onboarding_diagnostic_recovery() -> None:
    text = OPERATOR_GUIDE.read_text(encoding="utf-8")

    for required in [
        "# DEV_CORE Operator Guide",
        "First run",
        "dc launch",
        "dc guide onboarding",
        "dc guide diagnostic",
        "dc guide recovery",
        "dc check --gate",
        "dc check --fix --dry-run",
        "endday.ps1 -SkipBackup",
        "DEV_CORE_DATA\\Logs\\scripts",
    ]:
        assert required in text


def test_docs_cross_link_each_other_and_platform_docs() -> None:
    api_text = API_REFERENCE.read_text(encoding="utf-8")
    operator_text = OPERATOR_GUIDE.read_text(encoding="utf-8")

    assert "OPERATOR_GUIDE.md" in api_text
    assert "API_REFERENCE.md" in operator_text
    assert "PLATFORM_DOCUMENTATION.md" in api_text
    assert "PLATFORM_DOCUMENTATION.md" in operator_text
