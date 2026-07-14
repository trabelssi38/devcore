import json
import sys
from pathlib import Path


SECURITY_ROOT = Path(__file__).resolve().parent
DEV_CORE_ROOT = SECURITY_ROOT.parent
if str(SECURITY_ROOT) not in sys.path:
    sys.path.insert(0, str(SECURITY_ROOT))


def test_sbom_contains_python_and_node_dependency_inventory() -> None:
    from security_review import build_sbom

    sbom = build_sbom(DEV_CORE_ROOT)

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["metadata"]["component"]["name"] == "DEV_CORE"
    refs = {component["bom-ref"] for component in sbom["components"]}
    assert "npm:next" in refs
    assert "npm:react" in refs
    assert "npm:@toon-format/cli" in refs
    assert "pypi:requests" in refs
    assert "pypi:mcp" in refs


def test_security_review_policy_requires_secret_scan_sbom_and_no_high_findings() -> None:
    from security_review import build_security_review

    review = build_security_review(DEV_CORE_ROOT)

    assert review["schema_version"] == 1
    assert review["status"] == "pass"
    assert review["required_controls"]["secret_scan"] is True
    assert review["required_controls"]["sbom"] is True
    assert review["findings"]["critical"] == 0
    assert review["findings"]["high"] == 0
    assert review["sbom"]["component_count"] >= 5


def test_security_artifacts_are_written_as_stable_json(tmp_path) -> None:
    from security_review import write_security_artifacts

    paths = write_security_artifacts(DEV_CORE_ROOT, tmp_path)

    sbom = json.loads(paths["sbom"].read_text(encoding="utf-8"))
    review = json.loads(paths["review"].read_text(encoding="utf-8"))

    assert paths["sbom"].name == "sbom.cyclonedx.json"
    assert paths["review"].name == "security-review.json"
    assert sbom["components"] == sorted(sbom["components"], key=lambda item: item["bom-ref"])
    assert review["status"] == "pass"
