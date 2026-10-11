"""Rehearse candidate-to-fallback rollback on one isolated L9 data copy."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

sys.dont_write_bytecode = True


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def database_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(target)) as copy:
            original.backup(copy)
    with closing(sqlite3.connect(f"{target.as_uri()}?mode=ro", uri=True)) as copy:
        if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or copy.execute("PRAGMA foreign_key_check").fetchone():
            raise RuntimeError(f"Invalid copied database: {target}")


def verified_release(release: Path, env: dict[str, str]) -> dict:
    python = release / "Scripts/python.exe"
    verifier = release / "controls/Scripts/verify_engine_release.py"
    launcher = release / "controls/Scripts/launch_individual_candidate.py"
    bundle = release / "individual-platform-v2"
    for path in (python, verifier, launcher, bundle / "manifest.json"):
        if not path.is_file() or path.is_symlink() or path.is_junction():
            raise ValueError(f"Missing or linked release component: {path}")
    result = subprocess.run([str(python), "-I", str(verifier), "--release", str(release)],
                            env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"Release verification refused: {release.name}")
    return json.loads(result.stdout)


def clean_bundle(release: Path, destination: Path) -> Path:
    source = release / "individual-platform-v2"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Bundle manifest inventory required")
    destination.mkdir(parents=True)
    shutil.copy2(source / "manifest.json", destination / "manifest.json")
    for name, expected in files.items():
        relative = Path(name)
        if (relative.is_absolute() or ".." in relative.parts or not isinstance(expected, str)
                or len(expected) != 64):
            raise ValueError("Invalid bundle manifest entry")
        original = source / relative
        if not original.is_file() or original.is_symlink() or original.is_junction() or digest(original) != expected:
            raise ValueError(f"Bundle source differs: {name}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        if digest(target) != expected:
            raise RuntimeError(f"Bundle copy differs: {name}")
    return destination


def preflight(release: Path, bundle: Path, local: Path, data: Path, identity: Path,
              port: int, env: dict[str, str]) -> dict:
    command = [str(release / "Scripts/python.exe"), "-I",
               str(release / "controls/Scripts/launch_individual_candidate.py"),
               "--bundle", str(bundle), "--manifest-sha256", digest(bundle / "manifest.json"),
               "--local-root", str(local), "--data-root", str(data),
               "--identity-store", str(identity), "--port", str(port), "--check"]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"Dashboard preflight refused: {release.name}")
    return json.loads(result.stdout)


def run_probe(qualification_root: Path, root: Path, release: Path, bundle: Path,
              previous_run_id: str | None) -> dict:
    # This function runs in the selected release's isolated Python process.
    qualification_root = qualification_root.resolve(strict=True)
    root = root.resolve(strict=True)
    release = release.resolve(strict=True)
    bundle = bundle.resolve(strict=True)
    qualified_embedded = (release.is_relative_to(qualification_root)
                          and bundle == release / "individual-platform-v2")
    if not root.is_relative_to(qualification_root) or not (bundle.is_relative_to(root) or qualified_embedded):
        raise ValueError("Probe roots must remain inside qualification")
    local, data = root / "local", root / "data"
    os.environ.update({"DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                       "DEVCORE_PLATFORM_ROOT": str(bundle),
                       "DEVCORE_IDENTITY_STORE": str(local / "Security/identity.db"),
                       "DEVCORE_DASHBOARD_AUTH_PROFILE": "individual",
                       "DEVCORE_DASHBOARD_BIND": "127.0.0.1"})
    from devcore_engine.runs.engine import DurableRunEngine
    from devcore_engine.runs.models import RunSubmission
    import httpx

    sys.path.insert(0, str(bundle / "Scripts"))
    spec = importlib.util.spec_from_file_location("candidate_dashboard", bundle / "Scripts/dashboard_api.py")
    dashboard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard)

    async def check_dashboard() -> dict:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=dashboard.app),
                                     base_url="http://127.0.0.1:20135") as client:
            page = await client.get("/project")
            denied = await client.get("/api/dashboard/tasks?project=devcore")
            if page.status_code != 200 or denied.status_code != 401:
                raise RuntimeError("Dashboard access contract failed")
            return {"project_page": page.status_code, "anonymous_tasks": denied.status_code}

    dashboard_status = asyncio.run(check_dashboard())
    engine = DurableRunEngine()
    previous = engine.get_run(previous_run_id) if previous_run_id else None
    if previous_run_id and (previous is None or previous.status != "succeeded"):
        raise RuntimeError("Prior run not durable across release switch")
    label = "candidate" if previous_run_id is None else "fallback"
    record, created = engine.submit_run(RunSubmission(
        project_id="devcore", title=f"L9 {label} rollback probe",
        command=[sys.executable, "-I", "-c", f"print('l9-{label}-ok')"],
        timeout_seconds=10, actor="l9-rollback-copy",
        idempotency_key=f"l9-v240-{label}",
    ))
    if not created:
        raise RuntimeError("Probe run already exists")
    engine.start_worker(poll_interval=.05)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            completed = engine.get_run(record.id)
            if completed is not None and completed.is_terminal():
                break
            time.sleep(.1)
        else:
            raise RuntimeError("Probe run timed out")
    finally:
        engine.stop_worker(timeout=5)
    if completed.status != "succeeded" or completed.exit_code != 0 or f"l9-{label}-ok" not in completed.output:
        raise RuntimeError("Probe run did not succeed")
    return {"release": str(release), "dashboard": dashboard_status,
            "previous_run_visible": previous_run_id is None or previous.status == "succeeded",
            "run_id": completed.id, "run_status": completed.status,
            "run_exit_code": completed.exit_code}


def qualify(qualification_root: Path, source_root: Path, output_root: Path,
            candidate: Path, fallback: Path, *, embedded_bundles: bool = False) -> dict:
    qualification_root = qualification_root.resolve(strict=True)
    source_root = source_root.resolve(strict=True)
    output_root = output_root.resolve()
    candidate = candidate.resolve(strict=True)
    fallback = fallback.resolve(strict=True)
    if (not source_root.is_relative_to(qualification_root) or output_root.parent != qualification_root
            or output_root.exists() or candidate == fallback or not candidate.is_relative_to(qualification_root)):
        raise ValueError("Isolated source, new sibling output and separate candidate required")
    source_local = source_root / "local"
    names = ("devcore.db", "runs/runs.db", "Security/identity.db")
    source_files = [source_local / name for name in names]
    if any(not path.is_file() or path.is_symlink() or path.is_junction() for path in source_files):
        raise ValueError("Missing or linked source database")
    source_hashes = {name: digest(source_local / name) for name in names}
    local, data = output_root / "local", output_root / "data"
    output_root.mkdir()
    (local / "Security").mkdir(parents=True)
    data.mkdir()
    for name in names[:2]:
        database_copy(source_local / name, local / name)
    os.environ.update({"DEVCORE_LOCAL_ROOT": str(local), "DEVCORE_DATA_ROOT": str(data),
                       "DEVCORE_IDENTITY_STORE": str(local / "Security/identity.db")})
    from devcore_engine.security.identity_backup import restore_identity_store
    from devcore_engine.security.private_store import check_store_protection

    check_store_protection(source_local / names[2])
    restore_identity_store(source_local / names[2], local / names[2], source_hashes[names[2]])
    if embedded_bundles:
        if not fallback.is_relative_to(qualification_root):
            raise ValueError("Embedded fallback must be inside qualification")
        bundles = {"candidate": candidate / "individual-platform-v2",
                   "fallback": fallback / "individual-platform-v2"}
    else:
        bundles = {"candidate": clean_bundle(candidate, output_root / "bundles/candidate"),
                   "fallback": clean_bundle(fallback, output_root / "bundles/fallback")}
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    attestations = {"candidate": verified_release(candidate, env),
                    "fallback": verified_release(fallback, env)}
    checks = {"candidate": preflight(candidate, bundles["candidate"], local, data,
                                      local / names[2], 20135, env),
              "fallback": preflight(fallback, bundles["fallback"], local, data,
                                     local / names[2], 20135, env)}
    phases = []
    for label, release, previous in (("candidate", candidate, None), ("fallback", fallback, "previous")):
        prior_id = phases[-1]["run_id"] if previous else None
        result = subprocess.run([str(release / "Scripts/python.exe"), "-I", str(Path(__file__).resolve()),
                                 "--probe", "--qualification-root", str(qualification_root),
                                 "--root", str(output_root), "--release", str(release),
                                 "--bundle", str(bundles[label]),
                                 *( ["--previous-run-id", prior_id] if prior_id else [] )],
                                env=env, capture_output=True, text=True, timeout=70)
        if result.returncode:
            raise RuntimeError(f"Rollback probe refused: {release.name}: {result.stderr[-1200:]}")
        phases.append(json.loads(result.stdout))
    with closing(sqlite3.connect(f"{(local / 'runs/runs.db').as_uri()}?mode=ro", uri=True)) as conn:
        statuses = [conn.execute("SELECT status FROM runs WHERE id=?", (row["run_id"],)).fetchone()[0]
                    for row in phases]
    if statuses != ["succeeded", "succeeded"]:
        raise RuntimeError("Run history did not survive rollback")
    if {name: digest(source_local / name) for name in names} != source_hashes:
        raise RuntimeError("Qualification source changed")
    report = {"source": str(source_root), "root": str(output_root),
              "attestations": attestations, "dashboard_preflights": checks,
              "embedded_bundles": embedded_bundles,
              "phases": phases, "run_statuses_after_rollback": statuses,
              "source_unchanged": True, "rollback_on_copy_passed": True,
              "operationally_qualified": False}
    (output_root / "qualification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-root", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--fallback", type=Path)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--previous-run-id")
    parser.add_argument("--embedded-bundles", action="store_true")
    args = parser.parse_args()
    if args.probe:
        if any(value is None for value in (args.qualification_root, args.root,
                                            args.release, args.bundle)):
            parser.error("Probe qualification root, data root, release and bundle required")
        print(json.dumps(run_probe(args.qualification_root, args.root, args.release, args.bundle,
                                   args.previous_run_id), ensure_ascii=False))
    else:
        if any(value is None for value in (args.qualification_root, args.source, args.output,
                                            args.candidate, args.fallback)):
            parser.error("Qualification paths required")
        print(json.dumps(qualify(args.qualification_root, args.source, args.output,
                                 args.candidate, args.fallback,
                                 embedded_bundles=args.embedded_bundles), ensure_ascii=False))


if __name__ == "__main__":
    main()
