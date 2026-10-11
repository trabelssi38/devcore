"""Republish two pinned L9 releases without generated Python bytecode.

Copies only code/runtime artifacts into a new qualification root. No service,
active state, or source release is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Linked release member refused: {path}")
        if path.is_file():
            relative = path.relative_to(root)
            if "__pycache__" in relative.parts or path.suffix == ".pyc":
                continue
            result[relative.as_posix()] = digest(path)
    return result


def verify_release(release: Path, local: Path, data: Path, env: dict[str, str]) -> dict:
    python = release / "Scripts/python.exe"
    verifier = release / "controls/Scripts/verify_engine_release.py"
    launcher = release / "controls/Scripts/launch_individual_candidate.py"
    bundle = release / "individual-platform-v2"
    manifest = bundle / "manifest.json"
    verify = subprocess.run([str(python), "-I", str(verifier), "--release", str(release)],
                            capture_output=True, text=True, env=env, timeout=90)
    if verify.returncode:
        raise RuntimeError(f"Release verification failed: {release.name}: {verify.stderr[-800:]}")
    check = subprocess.run([
        str(python), "-I", str(launcher), "--bundle", str(bundle),
        "--manifest-sha256", digest(manifest), "--local-root", str(local),
        "--data-root", str(data), "--identity-store", str(local / "Security/identity.db"),
        "--port", "20135", "--check",
    ], capture_output=True, text=True, env=env, timeout=90)
    if check.returncode:
        raise RuntimeError(f"Embedded bundle preflight failed: {release.name}: {check.stderr[-800:]}")
    return {"release": json.loads(verify.stdout), "dashboard": json.loads(check.stdout)}


def publish(qualification_root: Path, output_root: Path, sources: tuple[Path, Path],
            local: Path, data: Path) -> dict:
    qualification_root = qualification_root.resolve(strict=True)
    output_root = output_root.resolve()
    local, data = local.resolve(strict=True), data.resolve(strict=True)
    sources = tuple(path.resolve(strict=True) for path in sources)
    if (output_root.exists() or output_root.parent != qualification_root
            or not local.is_relative_to(qualification_root)
            or not data.is_relative_to(qualification_root)
            or len(set(sources)) != 2):
        raise ValueError("New qualification output, distinct sources and isolated data roots required")
    if not (local / "Security/identity.db").is_file():
        raise ValueError("Qualification identity required")
    originals = {source.name: inventory(source) for source in sources}
    if len(originals) != 2:
        raise ValueError("Distinct source release names required")
    output_root.mkdir()
    release_root = output_root / "runtime/releases"
    release_root.mkdir(parents=True)
    env = os.environ.copy()
    env.update({"DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                "PYTHONDONTWRITEBYTECODE": "1"})
    results = {}
    for source in sources:
        target = release_root / (source.name + "-clean-v241")
        shutil.copytree(source, target,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        copied = inventory(target)
        if copied != originals[source.name]:
            raise RuntimeError(f"Republished release differs: {source.name}")
        results[source.name] = {
            "target": str(target), "files": len(copied),
            "bytes": sum((target / name).stat().st_size for name in copied),
            "checks": verify_release(target, local, data, env),
        }
    if {source.name: inventory(source) for source in sources} != originals:
        raise RuntimeError("Source release changed during publication")
    report = {"root": str(output_root), "results": results,
              "sources_unchanged": True, "service_changed": False,
              "operationally_qualified": False}
    (output_root / "qualification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--fallback", type=Path, required=True)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.qualification_root, args.output,
                             (args.candidate, args.fallback),
                             args.local_root, args.data_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
