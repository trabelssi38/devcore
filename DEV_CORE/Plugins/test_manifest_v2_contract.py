from pathlib import Path
import sys


PLUGIN_ROOT = Path(__file__).resolve().parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


from manifest_v2 import ManifestValidationError, is_compatible, validate_manifest_v2


def valid_manifest(**overrides):
    manifest = {
        "manifest_version": 2,
        "id": "example-plugin",
        "name": "Example Plugin",
        "version": "1.2.3",
        "description": "Example DEV_CORE plugin.",
        "devcore_min_version": "10.0.0",
        "devcore_max_version": "10.99.0",
        "entrypoint": {
            "type": "command",
            "command": "python -m example_plugin",
        },
        "capabilities": {
            "commands": ["example:health"],
            "hooks": [],
            "skills": [],
            "health_checks": [],
            "widgets": [],
            "templates": [],
        },
        "permissions": {
            "filesystem": {
                "read": ["workspace"],
                "write": ["data"],
            },
            "network": {
                "allow": ["api.openai.com:443"],
            },
            "secrets": {
                "read": ["GEMINI_API_KEY"],
            },
            "process": {
                "allow": ["python"],
                "allow_shell": False,
            },
        },
    }
    manifest.update(overrides)
    return manifest


def test_manifest_v2_accepts_compatible_manifest():
    normalized = validate_manifest_v2(valid_manifest(), current_version="10.2.0")

    assert normalized["manifest_version"] == 2
    assert normalized["id"] == "example-plugin"
    assert is_compatible(normalized, current_version="10.2.0") is True


def test_manifest_v2_rejects_legacy_schema_version():
    legacy = valid_manifest(schema_version=1)
    legacy.pop("manifest_version")

    try:
        validate_manifest_v2(legacy, current_version="10.2.0")
    except ManifestValidationError as exc:
        assert "manifest_version" in str(exc)
    else:
        raise AssertionError("legacy manifest must be rejected")


def test_manifest_v2_rejects_core_version_outside_supported_range():
    too_new_required = valid_manifest(devcore_min_version="11.0.0")
    too_old_only = valid_manifest(devcore_max_version="9.9.9")

    assert is_compatible(too_new_required, current_version="10.2.0") is False
    assert is_compatible(too_old_only, current_version="10.2.0") is False


def test_manifest_v2_rejects_missing_required_contract_fields():
    manifest = valid_manifest()
    manifest.pop("entrypoint")

    try:
        validate_manifest_v2(manifest, current_version="10.2.0")
    except ManifestValidationError as exc:
        assert "entrypoint" in str(exc)
    else:
        raise AssertionError("missing entrypoint must be rejected")


def test_manifest_v2_accepts_explicit_permission_scopes():
    normalized = validate_manifest_v2(valid_manifest(), current_version="10.2.0")

    assert normalized["permissions"]["filesystem"]["read"] == ["workspace"]
    assert normalized["permissions"]["network"]["allow"] == ["api.openai.com:443"]
    assert normalized["permissions"]["secrets"]["read"] == ["GEMINI_API_KEY"]
    assert normalized["permissions"]["process"]["allow"] == ["python"]


def test_manifest_v2_rejects_unknown_permission_scope():
    manifest = valid_manifest()
    manifest["permissions"]["admin"] = {"allow": True}

    try:
        validate_manifest_v2(manifest, current_version="10.2.0")
    except ManifestValidationError as exc:
        assert "permissions.admin" in str(exc)
    else:
        raise AssertionError("unknown permission scopes must be rejected")


def test_manifest_v2_rejects_wildcard_filesystem_scope():
    manifest = valid_manifest()
    manifest["permissions"]["filesystem"]["read"] = ["*"]

    try:
        validate_manifest_v2(manifest, current_version="10.2.0")
    except ManifestValidationError as exc:
        assert "filesystem" in str(exc)
    else:
        raise AssertionError("filesystem wildcards must be rejected")


def test_manifest_v2_rejects_shell_process_permission():
    manifest = valid_manifest()
    manifest["permissions"]["process"]["allow_shell"] = True

    try:
        validate_manifest_v2(manifest, current_version="10.2.0")
    except ManifestValidationError as exc:
        assert "allow_shell" in str(exc)
    else:
        raise AssertionError("plugins must not request shell execution in Manifest v2")
