"""Launch the pinned Git snapshot of the PostgreSQL global supervisor.

This wrapper reads the installed service profile locally. It never accepts a
database password on the command line and does not copy operational data.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from global_restart_budget import RestartBudget


PINNED_COMMITS = frozenset({
    "d6cac930c68d8a14206f91bfdf9be508332d5e34",  # Agent pilot retirement, approved 2026-10-26.
    "d4dbfe28531518fc4e8ca05116cbb8245a74fd27",  # Opt-in DevCore agent pilot.
    "1f5ec0f6e9d31898d11f0f41dc5d2682d916b7c6",  # Display verified context snapshots in Cockpit.
    "f3fee3dffb1bf33125a1fcb614bac545ef4ef780",  # Scheduled verifiable project context snapshots.
    "c8ab7979f25695169f21fa5b821e9e7968690a21",  # Retry transient cold-boot RepoWise status failures.
    "657de6b136fb5e100f71d38450e38a7c941c5575",  # Project-only refresh after stream reconnect.
    "5eff4ac03cd865fd8b2dde05326d3d8d0208712a",  # Last dispatched Cockpit schedule attempt.
    "ea06de8974ac3d99f3ccf3d907f8fbbce28c9f20",  # Tunisia presentation and managed runtime command.
    "0bfa7942b6fc3d0cf3fab415d46ba07e0b0004b0",  # Tunisia Cockpit time presentation candidate.
    "355e6dfc4215de547d9f8e70cca9488ce68dd57a",  # Qualified project automation candidate.
    "ea9ba2ee140f1967818741c5090a1204d4da12e0",  # Show scoped context sources in the Cockpit.
    "ce4b464d65666e6be4d806a2858f20f098f39248",  # Explain missing project sources in the Cockpit sidebar.
    "d442d77c602b946ea16ce62e9fc180f56b63d80b",  # Select Cockpit projects by clicking their cards.
    "4d90fea6d9650dc6fea471ad5d357c32b44d6596",  # Header profile and stable project actions.
    "638a13649a8282121422af985acb226bf9d08ec6",  # Compact Cockpit tabs with scoped project updates.
    "9b4e94f35def0c35e9024e5ec1ae07807a91ad96",  # Restrict archive changes to project write roles.
    "b0c0ae6aa732890364681aac412b1b1d08b95442",  # Show projects in a paged, combined Cockpit list.
    "49e50e8694cd97e1a37d18661d001b95068ba309",  # Verify the paged combined project list UI.
    "7c809c77e2a4fc75297011a9835454f0a42dc2ad",  # Git-filtered projects and per-project archive controls.
    "d029391f58289adf6e7f72feb7f79b05d8699a04",  # Include projects awaiting review.
    "dabcd77b7c95c05f4db77438bebacb0e44eca82d",  # Accessible project navigation.
    "8d95af86fbe2741ae3367c94bef041ae3c54f13f",  # Authenticated Cockpit user display.
    "cb8f971af46a4a739fe3ae55a4275c9054c75573",  # Cockpit login redirects.
    "891218981164082f00fe614d1fb41af4fd247492",  # Cold RepoWise status budget.
    "e8b8775d507e341fdc52eafe10da2dd12657de6f",  # Project Cockpit presentation parity.
    "b8d10d6bb909ae6a06cc53cb24149f2ad5d9712f",  # Previous task; retained for rollback.
    "f6ef6840a4ef9ef62ed30521018426934282f170",  # Headroom health grace.
    "f9d4995e3a13117430780f2fb53e83b28d020540",  # Project-scoped Cockpit reads.
    "525d14a011eacb822ce9005ab670c6250fe83444",  # Cold boot RepoWise preflight.
    "af3b646e2a2cbbdc461a0a48809c9b8ca96a9ced",  # Full project Cockpit.
    "ba9f9a9024ec357033a0d4442c447964cad4f7eb",  # RepoWise cold boot fix.
    "24ccb4685804e494d207c3c58af3af81c8c17c8a",  # Team Cockpit settings request fix.
})


def _git_output(source: Path, *arguments: str) -> str:
    command = ["git", *arguments]
    for attempt in range(3):
        try:
            return subprocess.check_output(command, cwd=source, text=True,
                                           timeout=45)
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise
            time.sleep(2)
    raise AssertionError("Unreachable Git retry state")


def _snapshot(source: Path, expected_commit: str) -> Path:
    source = source.resolve(strict=True)
    script = source / "DEV_CORE" / "Scripts" / "global_postgres_stack.py"
    if not script.is_file() or expected_commit not in PINNED_COMMITS:
        raise ValueError("Global source or full commit pin invalid")
    head = _git_output(source, "rev-parse", "HEAD").strip()
    dirty = _git_output(source, "status", "--porcelain")
    if head != expected_commit or dirty.strip():
        raise ValueError("Global source commit differs from the clean pin")
    return script


def _profile(release: Path, config_path: Path) -> tuple[Path, dict[str, str]]:
    release = release.resolve(strict=True)
    if release.parent.name.lower() != "releases":
        raise ValueError("Versioned release directory required")
    config_path = config_path.resolve(strict=True)
    if config_path != release / "individual-service.json":
        raise ValueError("Configuration must belong to the selected release")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    service_env = config.get("environment", {})
    if (not isinstance(service_env, dict) or
            service_env.get("DEVCORE_TASK_READ_MODE") != "postgres" or
            service_env.get("DEVCORE_IDENTITY_READ_MODE") != "postgres" or
            service_env.get("DEVCORE_REQUIRE_AUTH") != "1" or
            not service_env.get("DEVCORE_DATABASE_URL", "").startswith("postgresql://")):
        raise ValueError("Installed PostgreSQL service profile is required")
    base = release.parent.parent
    roots = {}
    for key, field in (("DEVCORE_LOCAL_ROOT", "local_relative"),
                       ("DEVCORE_DATA_ROOT", "data_relative")):
        value = config.get(field)
        if not isinstance(value, str):
            raise ValueError("Service profile root missing")
        part = Path(value)
        if part.is_absolute() or any(segment in (".", "..") for segment in part.parts):
            raise ValueError("Service profile root escapes runtime")
        root = (base / part).resolve(strict=True)
        if not root.is_relative_to(base):
            raise ValueError("Service profile root escapes runtime")
        roots[key] = str(root)
    platform = release / "individual-platform-v2"
    if not platform.is_dir():
        raise ValueError("Installed platform bundle missing")
    roots["DEVCORE_PLATFORM_ROOT"] = str(platform)
    return release / "Scripts" / "python.exe", {**service_env, **roots}


def _check_schema(python: Path, schema_script: Path, config_path: Path,
                  source: Path, env: dict[str, str]) -> tuple[int, str, int]:
    """Wait briefly for PostgreSQL on cold boot; never retry a schema mismatch."""
    command = [str(python), str(schema_script), "--config", str(config_path)]
    for attempt in range(1, 13):
        try:
            # A cold Windows boot may delay interpreter startup while the
            # physical disk is saturated, even after PostgreSQL is listening.
            result = subprocess.run(command, cwd=source, env=env,
                                    capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            code, output = 1, ""
        else:
            code, output = result.returncode, result.stdout.strip()
        if code in (0, 2) or attempt == 12:
            return code, output, attempt
        time.sleep(5)
    raise AssertionError("Unreachable schema retry state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--stop", action="store_true")
    group.add_argument("--validate-source", action="store_true")
    group.add_argument("--budget-status", action="store_true")
    group.add_argument("--reset-restart-budget", action="store_true")
    parser.add_argument("--reason", help="Operator reason required to reset an exhausted budget")
    args = parser.parse_args()
    phase = "arguments"
    diagnostic = args.release.parent.parent / "state" / "local" / "GlobalStack" / "task-launcher-diagnostic.jsonl"
    if not all(path.is_absolute() for path in (args.source, args.release, args.config)):
        parser.error("Source, release and configuration paths must be absolute")
    if args.reset_restart_budget and not args.reason:
        parser.error("--reason is required with --reset-restart-budget")
    if args.reason and not args.reset_restart_budget:
        parser.error("--reason requires --reset-restart-budget")
    budget = RestartBudget(diagnostic.parent)
    budget_armed = False
    failure_record_attempted = False
    started_at = time.time()
    try:
        if args.budget_status or args.reset_restart_budget:
            phase = "profile"
            _profile(args.release, args.config)
            if args.reset_restart_budget:
                budget.reset(reason=args.reason, at=time.time())
            print(json.dumps({"status": "global_restart_budget", "budget": budget.read()}))
            return 0
        if not (args.check or args.stop or args.validate_source):
            phase = "restart_budget"
            if not budget.allow():
                print(json.dumps({"status": "global_restart_budget_exhausted",
                                  "reason": "Operator reset required"}))
                return 75
            budget_armed = True
        phase = "source"
        script = _snapshot(args.source, args.expected_commit)
        if args.validate_source:
            print(json.dumps({"status": "global_source_verified",
                              "commit": args.expected_commit}))
            return 0
        phase = "profile"
        python, profile_env = _profile(args.release, args.config)
        if not python.is_file():
            raise ValueError("Pinned release Python missing")
        env = os.environ.copy()
        env.update(profile_env)
        env.pop("GEMINI_API_KEY", None)
        env.pop("GOOGLE_API_KEY", None)
        env.pop("GEMINI_API_KEY_FILE", None)
        key_file = Path(profile_env["DEVCORE_LOCAL_ROOT"]) / "GlobalStack" / "gemini_api_key.txt"
        if key_file.is_file():
            if key_file.is_symlink() or not 20 <= key_file.stat().st_size <= 1024:
                raise ValueError("Private Gemini key file is invalid")
            env["GEMINI_API_KEY_FILE"] = str(key_file)
        # S4U startup tasks may omit APPDATA even for the installed user.
        repowise_roots = [Path(os.environ["APPDATA"])] if os.environ.get("APPDATA") else []
        repowise_roots.append(Path.home() / "AppData" / "Roaming")
        repowise_roots.append(Path("C:/Users/Administrateur/AppData/Roaming"))
        for root in repowise_roots:
            repowise = root / "Python" / "Python314" / "Scripts" / "repowise.exe"
            if repowise.is_file():
                env["PATH"] = str(repowise.parent) + os.pathsep + env.get("PATH", "")
                break
        if not args.stop:
            phase = "schema"
            schema_script = script.parent / "check_global_postgres_schema.py"
            schema_code, schema_output, schema_attempts = _check_schema(
                python, schema_script, args.config, args.source, env)
            if schema_code:
                if budget_armed:
                    failure_record_attempted = True
                    budget.record_failure(started_at=started_at, finished_at=time.time(),
                                          phase=phase, exit_code=schema_code)
                diagnostic.parent.mkdir(parents=True, exist_ok=True)
                with diagnostic.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                        "phase": phase, "exit_code": schema_code,
                        "attempts": schema_attempts}) + "\n")
                print(schema_output or json.dumps({"status": "global_schema_check_failed"}))
                return schema_code
        phase = "supervisor"
        command = [str(python), str(script)]
        if args.check:
            command.append("--check")
        elif args.stop:
            command.append("--stop")
        if args.check or args.stop:
            result = subprocess.call(command, cwd=args.source, env=env)
            if result:
                diagnostic.parent.mkdir(parents=True, exist_ok=True)
                with diagnostic.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                        "phase": phase, "exit_code": result}) + "\n")
            return result
        log_path = Path(profile_env["DEVCORE_LOCAL_ROOT"]) / "GlobalStack" / "task-supervisor.log"
        with log_path.open("ab", buffering=0) as log:
            result = subprocess.call(command, cwd=args.source, env=env,
                                     stdout=log, stderr=subprocess.STDOUT)
        if result:
            if budget_armed:
                failure_record_attempted = True
                budget.record_failure(started_at=started_at, finished_at=time.time(),
                                      phase=phase, exit_code=result)
            diagnostic.parent.mkdir(parents=True, exist_ok=True)
            with diagnostic.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                    "phase": phase, "exit_code": result}) + "\n")
        elif budget_armed:
            budget.record_success()
        return result
    except Exception as exc:
        if budget_armed and not failure_record_attempted:
            try:
                failure_record_attempted = True
                budget.record_failure(started_at=started_at, finished_at=time.time(),
                                      phase=phase)
            except (OSError, ValueError):
                pass
        try:
            diagnostic.parent.mkdir(parents=True, exist_ok=True)
            with diagnostic.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                    "phase": phase, "error_type": type(exc).__name__,
                    "git_operation": exc.cmd[1] if isinstance(exc, subprocess.TimeoutExpired)
                        and isinstance(exc.cmd, (list, tuple)) and len(exc.cmd) > 1 else None,
                    "appdata_available": bool(os.environ.get("APPDATA")),
                    "repowise_on_path": bool(shutil.which("repowise"))}) + "\n")
        except OSError:
            pass
        print(json.dumps({"status": "global_operational_launcher_refused",
                          "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
