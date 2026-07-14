import sys
from pathlib import Path


RELEASE_ROOT = Path(__file__).resolve().parent
DEV_CORE_ROOT = RELEASE_ROOT.parent
if str(RELEASE_ROOT) not in sys.path:
    sys.path.insert(0, str(RELEASE_ROOT))


def test_release_manifest_is_reproducible_and_excludes_runtime_state() -> None:
    from release_packaging import build_release_manifest

    manifest = build_release_manifest(DEV_CORE_ROOT, git_sha="abc123", created_at="2026-07-14T00:00:00Z")
    second = build_release_manifest(DEV_CORE_ROOT, git_sha="abc123", created_at="2026-07-14T00:00:00Z")

    assert manifest == second
    assert manifest["schema_version"] == 1
    assert manifest["name"] == "DEV_CORE"
    assert manifest["version"] == "10.0"
    assert manifest["git_sha"] == "abc123"
    assert manifest["archive"]["format"] == "zip"
    assert manifest["archive"]["compression"] == "deflate"
    assert manifest["archive"]["reproducible"] is True
    assert manifest["files"] == sorted(manifest["files"], key=lambda item: item["path"])

    paths = {item["path"] for item in manifest["files"]}
    assert "Config/platform.json" in paths
    assert "Security/sbom.cyclonedx.json" in paths
    assert not any(path.startswith("node_modules/") for path in paths)
    assert not any(path.startswith("../") for path in paths)
    assert not any("__pycache__" in path for path in paths)


def test_release_notes_group_commits_and_include_validation() -> None:
    from release_packaging import build_release_notes

    commits = [
        "953b7d8 feat: add release backup rollback procedure plan [T-212]",
        "a04f0db security: add sbom and review gate [T-211]",
        "a706da9 test: add local failure drills [T-210]",
    ]
    notes = build_release_notes(version="10.0", git_sha="abc123", commits=commits)

    assert "# DEV_CORE v10.0 Release Notes" in notes
    assert "Git SHA: `abc123`" in notes
    assert "## Features" in notes
    assert "- `T-212` add release backup rollback procedure plan" in notes
    assert "## Security" in notes
    assert "- `T-211` add sbom and review gate" in notes
    assert "## Tests" in notes
    assert "- `T-210` add local failure drills" in notes
    assert "## Validation" in notes
    assert "ci_python_tests.ps1" in notes


def test_release_artifacts_are_written_with_stable_names(tmp_path) -> None:
    from release_packaging import write_release_artifacts

    artifacts = write_release_artifacts(
        DEV_CORE_ROOT,
        tmp_path,
        git_sha="abc123",
        commits=["953b7d8 feat: add release backup rollback procedure plan [T-212]"],
    )

    assert artifacts["manifest"].name == "release-manifest.json"
    assert artifacts["notes"].name == "RELEASE_NOTES.md"
    assert artifacts["manifest"].read_text(encoding="utf-8").endswith("\n")
    assert artifacts["notes"].read_text(encoding="utf-8").endswith("\n")
