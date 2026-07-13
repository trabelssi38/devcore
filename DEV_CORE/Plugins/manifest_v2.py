import copy
import re
from typing import Any


CURRENT_DEVCORE_VERSION = "10.0.0"
SUPPORTED_MANIFEST_VERSION = 2

_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")

_REQUIRED_FIELDS = (
    "manifest_version",
    "id",
    "name",
    "version",
    "description",
    "devcore_min_version",
    "devcore_max_version",
    "entrypoint",
    "capabilities",
    "permissions",
)

_CAPABILITY_FIELDS = (
    "commands",
    "hooks",
    "skills",
    "health_checks",
    "widgets",
    "templates",
)


class ManifestValidationError(ValueError):
    """Raised when a DEV_CORE plugin manifest does not satisfy Manifest v2."""


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{field} must be an object")
    return value


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _parse_semver(value: Any, field: str) -> tuple[int, int, int]:
    text = _require_string(value, field)
    match = _SEMVER_RE.match(text)
    if not match:
        raise ManifestValidationError(f"{field} must use semantic version format MAJOR.MINOR.PATCH")
    return tuple(int(part) for part in match.groups())


def _validate_entrypoint(entrypoint: Any) -> None:
    entrypoint_map = _require_mapping(entrypoint, "entrypoint")
    entrypoint_type = _require_string(entrypoint_map.get("type"), "entrypoint.type")
    if entrypoint_type not in {"command", "python_module", "powershell_script"}:
        raise ManifestValidationError(
            "entrypoint.type must be one of command, python_module, powershell_script"
        )

    if entrypoint_type == "command":
        _require_string(entrypoint_map.get("command"), "entrypoint.command")
    elif entrypoint_type == "python_module":
        _require_string(entrypoint_map.get("module"), "entrypoint.module")
    else:
        _require_string(entrypoint_map.get("script"), "entrypoint.script")


def _validate_capabilities(capabilities: Any) -> None:
    capabilities_map = _require_mapping(capabilities, "capabilities")
    for field in _CAPABILITY_FIELDS:
        value = capabilities_map.get(field)
        if not isinstance(value, list):
            raise ManifestValidationError(f"capabilities.{field} must be a list")

    for command in capabilities_map["commands"]:
        _require_string(command, "capabilities.commands[]")


def _validate_permissions(permissions: Any) -> None:
    _require_mapping(permissions, "permissions")


def is_compatible(manifest: dict[str, Any], current_version: str = CURRENT_DEVCORE_VERSION) -> bool:
    current = _parse_semver(current_version, "current_version")
    minimum = _parse_semver(manifest.get("devcore_min_version"), "devcore_min_version")
    maximum = _parse_semver(manifest.get("devcore_max_version"), "devcore_max_version")
    return minimum <= current <= maximum


def validate_manifest_v2(
    manifest: dict[str, Any],
    current_version: str = CURRENT_DEVCORE_VERSION,
) -> dict[str, Any]:
    manifest_map = _require_mapping(manifest, "manifest")
    missing = [field for field in _REQUIRED_FIELDS if field not in manifest_map]
    if missing:
        raise ManifestValidationError(f"missing required Manifest v2 field(s): {', '.join(missing)}")

    if manifest_map["manifest_version"] != SUPPORTED_MANIFEST_VERSION:
        raise ManifestValidationError("manifest_version must be 2")

    plugin_id = _require_string(manifest_map["id"], "id")
    if not _ID_RE.match(plugin_id):
        raise ManifestValidationError("id must be lowercase kebab-case and 3-64 characters")

    _require_string(manifest_map["name"], "name")
    _require_string(manifest_map["description"], "description")
    _parse_semver(manifest_map["version"], "version")
    _parse_semver(manifest_map["devcore_min_version"], "devcore_min_version")
    _parse_semver(manifest_map["devcore_max_version"], "devcore_max_version")
    _validate_entrypoint(manifest_map["entrypoint"])
    _validate_capabilities(manifest_map["capabilities"])
    _validate_permissions(manifest_map["permissions"])

    if not is_compatible(manifest_map, current_version=current_version):
        raise ManifestValidationError(
            f"plugin {plugin_id} is not compatible with DEV_CORE {current_version}"
        )

    return copy.deepcopy(manifest_map)

