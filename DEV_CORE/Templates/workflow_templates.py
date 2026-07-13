from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
TEMPLATE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
ALLOWED_STATUS = {"active", "deprecated"}
ALLOWED_STEP_TYPES = {"manual", "script", "gate", "notification"}


class WorkflowTemplateValidationError(ValueError):
    """Raised when a workflow template registry violates the public contract."""


def load_workflow_template_registry(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_workflow_template_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema_version") != 1:
        raise WorkflowTemplateValidationError("schema_version must be 1")
    if not SEMVER_RE.match(str(registry.get("registry_version", ""))):
        # The registry is date-versioned as YYYY.MM.DD, which has the same
        # numeric three-part shape as semver without implying API compatibility.
        raise WorkflowTemplateValidationError("registry_version must use YYYY.MM.DD numeric format")

    templates = registry.get("templates")
    if not isinstance(templates, list) or not templates:
        raise WorkflowTemplateValidationError("templates must be a non-empty list")

    seen: set[tuple[str, str]] = set()
    for template in templates:
        _validate_template(template)
        key = (template["id"], template["version"])
        if key in seen:
            raise WorkflowTemplateValidationError(f"duplicate workflow template: {template['id']}@{template['version']}")
        seen.add(key)


def _validate_template(template: Any) -> None:
    if not isinstance(template, dict):
        raise WorkflowTemplateValidationError("template must be an object")

    template_id = _require_string(template, "id")
    if not TEMPLATE_ID_RE.match(template_id):
        raise WorkflowTemplateValidationError("template.id must be lowercase kebab-case")
    version = _require_string(template, "version")
    if not SEMVER_RE.match(version):
        raise WorkflowTemplateValidationError("template.version must use MAJOR.MINOR.PATCH")
    if template.get("status") not in ALLOWED_STATUS:
        raise WorkflowTemplateValidationError("template.status must be active or deprecated")
    _require_string(template, "description")

    inputs = template.get("inputs")
    if not isinstance(inputs, list):
        raise WorkflowTemplateValidationError("template.inputs must be a list")
    for item in inputs:
        _validate_input(item)

    steps = template.get("steps")
    if not isinstance(steps, list) or not steps:
        raise WorkflowTemplateValidationError("template.steps must be a non-empty list")
    step_ids: set[str] = set()
    for step in steps:
        step_id = _validate_step(step)
        if step_id in step_ids:
            raise WorkflowTemplateValidationError(f"duplicate step id: {step_id}")
        step_ids.add(step_id)


def _validate_input(item: Any) -> None:
    if not isinstance(item, dict):
        raise WorkflowTemplateValidationError("template.inputs[] must be an object")
    _require_string(item, "name")
    _require_string(item, "type")
    _require_string(item, "description")
    if not isinstance(item.get("required"), bool):
        raise WorkflowTemplateValidationError("template.inputs[].required must be boolean")


def _validate_step(step: Any) -> str:
    if not isinstance(step, dict):
        raise WorkflowTemplateValidationError("template.steps[] must be an object")
    step_id = _require_string(step, "id")
    _require_string(step, "title")
    step_type = _require_string(step, "type")
    if step_type not in ALLOWED_STEP_TYPES:
        raise WorkflowTemplateValidationError(f"unsupported step type: {step_type}")
    return step_id


def _require_string(mapping: dict[str, Any], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowTemplateValidationError(f"{field} must be a non-empty string")
    return value.strip()
