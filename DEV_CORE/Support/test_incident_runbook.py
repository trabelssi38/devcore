import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUPPORT_DIR = ROOT / "DEV_CORE" / "Support"
RUNBOOK_PATH = SUPPORT_DIR / "INCIDENT_RUNBOOK.md"
POLICY_PATH = SUPPORT_DIR / "support_policy.json"
SPRINT_PLAN_PATH = ROOT / "docs" / "DEV_CORE_PLAN_SPRINTS_2026.md"
PLATFORM_DOC_PATH = ROOT / "DEV_CORE" / "docs" / "PLATFORM_DOCUMENTATION.md"


def test_incident_runbook_covers_operational_contracts():
    assert RUNBOOK_PATH.exists()
    content = RUNBOOK_PATH.read_text(encoding="utf-8")

    required_sections = [
        "# DEV_CORE Incident Runbook",
        "Severity matrix",
        "SEV1",
        "SEV2",
        "SEV3",
        "Triage workflow",
        "Escalation",
        "Evidence bundle",
        "Support acceptance criteria",
    ]
    for marker in required_sections:
        assert marker in content

    required_commands = [
        "dc health --json",
        "dc check --gate",
        "dc guide diagnostic",
        "dc guide recovery",
        "endday.ps1 -SkipBackup",
    ]
    for command in required_commands:
        assert command in content

    required_references = [
        "support_policy.json",
        "PLATFORM_DOCUMENTATION.md",
        "OPERATOR_GUIDE.md",
        "API_REFERENCE.md",
        "DEV_CORE_DATA\\Logs\\scripts",
        "DEV_CORE_DATA\\Logs\\hermes",
        "DEV_CORE\\Security\\security-review.json",
        "DEV_CORE\\Release\\release-manifest.json",
    ]
    for reference in required_references:
        assert reference in content


def test_support_policy_is_machine_readable_and_actionable():
    assert POLICY_PATH.exists()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    assert policy["schema_version"] == "1.0"
    assert policy["owner"] == "DEV_CORE"
    assert policy["timezone"] == "Africa/Lagos"
    assert set(policy["severity_matrix"]) == {"SEV1", "SEV2", "SEV3"}

    for severity, contract in policy["severity_matrix"].items():
        assert contract["description"]
        assert contract["examples"]
        assert contract["initial_response_target_minutes"] > 0
        assert contract["status_update_interval_minutes"] > 0
        assert contract["resolution_target_hours"] > 0

    required_evidence = {
        "dc health --json",
        "dc check --gate",
        "latest_script_logs",
        "hermes_cron_state",
        "release_manifest",
        "security_review",
    }
    assert required_evidence.issubset(set(policy["required_evidence"]))
    assert policy["accepted_issue_types"]
    assert policy["unsupported_issue_types"]
    assert policy["escalation"]["owner"]
    assert policy["escalation"]["handoff_required_fields"]


def test_support_docs_are_linked_from_platform_and_sprint_plan():
    platform_doc = PLATFORM_DOC_PATH.read_text(encoding="utf-8")
    sprint_plan = SPRINT_PLAN_PATH.read_text(encoding="utf-8")

    assert "DEV_CORE\\Support\\INCIDENT_RUNBOOK.md" in platform_doc
    assert "DEV_CORE\\Support\\support_policy.json" in platform_doc
    assert "- [x] `S11-06`" in sprint_plan
