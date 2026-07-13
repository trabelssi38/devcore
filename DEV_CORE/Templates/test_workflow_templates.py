import json
import sys
from pathlib import Path


TEMPLATES_ROOT = Path(__file__).resolve().parent
if str(TEMPLATES_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_ROOT))


def test_workflow_template_registry_declares_versioned_templates() -> None:
    from workflow_templates import load_workflow_template_registry, validate_workflow_template_registry

    registry = load_workflow_template_registry(TEMPLATES_ROOT / "workflow_templates.json")
    validate_workflow_template_registry(registry)

    assert registry["schema_version"] == 1
    assert registry["registry_version"] == "2026.07.13"
    template_ids = {template["id"] for template in registry["templates"]}
    assert {"bugfix-safe", "feature-sprint", "release-hardening"}.issubset(template_ids)

    for template in registry["templates"]:
        assert template["version"].count(".") == 2
        assert template["status"] in {"active", "deprecated"}
        assert template["steps"], f"template {template['id']} must declare steps"
        assert all(step["id"] and step["title"] for step in template["steps"])


def test_workflow_template_registry_rejects_duplicate_version_keys(tmp_path) -> None:
    from workflow_templates import WorkflowTemplateValidationError, validate_workflow_template_registry

    registry = {
        "schema_version": 1,
        "registry_version": "2026.07.13",
        "templates": [
            {
                "id": "feature-sprint",
                "version": "1.0.0",
                "status": "active",
                "description": "A",
                "inputs": [],
                "steps": [{"id": "plan", "title": "Plan", "type": "manual"}],
            },
            {
                "id": "feature-sprint",
                "version": "1.0.0",
                "status": "active",
                "description": "B",
                "inputs": [],
                "steps": [{"id": "plan", "title": "Plan", "type": "manual"}],
            },
        ],
    }

    try:
        validate_workflow_template_registry(registry)
    except WorkflowTemplateValidationError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate template id/version should be rejected")


def test_workflow_template_registry_file_is_stable_json() -> None:
    source = TEMPLATES_ROOT / "workflow_templates.json"
    parsed = json.loads(source.read_text(encoding="utf-8"))
    encoded = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    assert source.read_text(encoding="utf-8") == encoded
