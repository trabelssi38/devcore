from pathlib import Path


DOCS_ROOT = Path(__file__).resolve().parent
API_REFERENCE = DOCS_ROOT / "API_REFERENCE.md"
OPERATOR_GUIDE = DOCS_ROOT / "OPERATOR_GUIDE.md"
SYSTEM_OVERVIEW = DOCS_ROOT / "SYSTEM_OVERVIEW.md"
IMPLEMENTATION_HISTORY = DOCS_ROOT / "IMPLEMENTATION_HISTORY.md"
ARCHITECTURE_DECISIONS = DOCS_ROOT / "ARCHITECTURE_DECISIONS.md"
AI_CAPABILITY_REGISTRY = DOCS_ROOT / "AI_CAPABILITY_REGISTRY.md"


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
    assert "SYSTEM_OVERVIEW.md" in api_text
    assert "SYSTEM_OVERVIEW.md" in operator_text
    assert "IMPLEMENTATION_HISTORY.md" in operator_text
    assert "ARCHITECTURE_DECISIONS.md" in api_text
    assert "ARCHITECTURE_DECISIONS.md" in operator_text
    assert "AI_CAPABILITY_REGISTRY.md" in api_text
    assert "AI_CAPABILITY_REGISTRY.md" in operator_text


def test_system_documentation_suite_exists_and_covers_core_subsystems() -> None:
    overview = SYSTEM_OVERVIEW.read_text(encoding="utf-8")
    history = IMPLEMENTATION_HISTORY.read_text(encoding="utf-8")
    decisions = ARCHITECTURE_DECISIONS.read_text(encoding="utf-8")
    registry = AI_CAPABILITY_REGISTRY.read_text(encoding="utf-8")

    for required in [
        "Task lifecycle",
        "Routage IA",
        "Dashboard/cockpit",
        "Event bus/read model",
        "API v1",
        "Database",
        "Plugins",
        "Skills",
    ]:
        assert required in overview

    for required in ["T-100", "T-155", "T-178", "T-194", "T-222"]:
        assert required in history

    for required in ["ADR-001", "ADR-005", "ADR-011", "AI Capability Registry"]:
        assert required in decisions

    for required in [
        "ai_capability_registry.json",
        "capability_requirements",
        "optimize_for",
    ]:
        assert required in registry
