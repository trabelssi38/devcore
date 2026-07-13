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

_PERMISSION_SCOPES = ("filesystem", "network", "secrets", "process")
_FILESYSTEM_SCOPES = ("workspace", "project", "data", "cache", "templates", "logs", "vault")
_NETWORK_TARGET_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?:\d{1,5}$"
)
_SECRET_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_PROCESS_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


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
    permissions_map = _require_mapping(permissions, "permissions")
    missing = [scope for scope in _PERMISSION_SCOPES if scope not in permissions_map]
    if missing:
        raise ManifestValidationError(f"missing permission scope(s): {', '.join(missing)}")

    unknown = sorted(set(permissions_map) - set(_PERMISSION_SCOPES))
    if unknown:
        raise ManifestValidationError(
            "unknown permission scope(s): "
            + ", ".join(f"permissions.{scope}" for scope in unknown)
        )

    _validate_filesystem_permissions(permissions_map["filesystem"])
    _validate_network_permissions(permissions_map["network"])
    _validate_secret_permissions(permissions_map["secrets"])
    _validate_process_permissions(permissions_map["process"])


def _require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ManifestValidationError(f"{field} must be a list")

    result = []
    for item in value:
        result.append(_require_string(item, f"{field}[]"))
    return result


def _validate_filesystem_permissions(filesystem: Any) -> None:
    filesystem_map = _require_mapping(filesystem, "permissions.filesystem")
    unknown = sorted(set(filesystem_map) - {"read", "write"})
    if unknown:
        raise ManifestValidationError(
            "unknown filesystem permission field(s): "
            + ", ".join(f"permissions.filesystem.{field}" for field in unknown)
        )

    for field in ("read", "write"):
        scopes = _require_string_list(filesystem_map.get(field, []), f"permissions.filesystem.{field}")
        for scope in scopes:
            if scope not in _FILESYSTEM_SCOPES:
                raise ManifestValidationError(
                    f"permissions.filesystem.{field} contains unsupported scope: {scope}"
                )


def _validate_network_permissions(network: Any) -> None:
    network_map = _require_mapping(network, "permissions.network")
    unknown = sorted(set(network_map) - {"allow"})
    if unknown:
        raise ManifestValidationError(
            "unknown network permission field(s): "
            + ", ".join(f"permissions.network.{field}" for field in unknown)
        )

    targets = _require_string_list(network_map.get("allow", []), "permissions.network.allow")
    for target in targets:
        if target == "*" or not _NETWORK_TARGET_RE.match(target):
            raise ManifestValidationError(
                "permissions.network.allow entries must be explicit host:port targets"
            )


def _validate_secret_permissions(secrets: Any) -> None:
    secrets_map = _require_mapping(secrets, "permissions.secrets")
    unknown = sorted(set(secrets_map) - {"read"})
    if unknown:
        raise ManifestValidationError(
            "unknown secrets permission field(s): "
            + ", ".join(f"permissions.secrets.{field}" for field in unknown)
        )

    names = _require_string_list(secrets_map.get("read", []), "permissions.secrets.read")
    for name in names:
        if name == "*" or not _SECRET_NAME_RE.match(name):
            raise ManifestValidationError(
                "permissions.secrets.read entries must be explicit environment-style names"
            )


def _validate_process_permissions(process: Any) -> None:
    process_map = _require_mapping(process, "permissions.process")
    unknown = sorted(set(process_map) - {"allow", "allow_shell"})
    if unknown:
        raise ManifestValidationError(
            "unknown process permission field(s): "
            + ", ".join(f"permissions.process.{field}" for field in unknown)
        )

    allow_shell = process_map.get("allow_shell", False)
    if not isinstance(allow_shell, bool):
        raise ManifestValidationError("permissions.process.allow_shell must be boolean")
    if allow_shell:
        raise ManifestValidationError("permissions.process.allow_shell must remain false")

    commands = _require_string_list(process_map.get("allow", []), "permissions.process.allow")
    for command in commands:
        if command == "*" or not _PROCESS_NAME_RE.match(command):
            raise ManifestValidationError(
                "permissions.process.allow entries must be explicit executable names"
            )


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
