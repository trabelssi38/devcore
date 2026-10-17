"""Foreground supervisor for the PostgreSQL global stack; never starts legacy launch.ps1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

SCRIPTS = Path(__file__).resolve().parent
DEV_CORE = SCRIPTS.parent
REPO = DEV_CORE.parent
sys.path.insert(0, str(DEV_CORE))
sys.path.insert(0, str(DEV_CORE / "API"))
sys.path.insert(0, str(DEV_CORE / "Scheduler"))

from devcore_engine.runs.postgres_schedules import PostgresScheduleDispatcher
from devcore_engine.infra.llm_route_contract import validate_health


PORTS = {"router": 20130, "headroom-native": 8787,
         "headroom-auxiliary": 8789, "gateway": 20131, "repowise": 7337}
HEALTH_GRACE_SECONDS = {"headroom-native": 150, "headroom-auxiliary": 150}


def overdue_health_failures(health: dict[str, bool], failing_since: dict[str, float],
                            now: float) -> list[str]:
    """Keep transient request load visible without killing every child on one miss."""
    for name, ready in health.items():
        if ready:
            failing_since.pop(name, None)
        else:
            failing_since.setdefault(name, now)
    return [name for name, started in failing_since.items()
            if now - started >= HEALTH_GRACE_SECONDS.get(name, 30)]


def _json_probe(port: int, path: str) -> dict:
    opener = build_opener(ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
        raw = response.read(32769)
        if response.status != 200 or len(raw) > 32768:
            raise ValueError("Health response invalid")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Health JSON object required")
        return result


def _ready(name: str) -> bool:
    try:
        if name == "router":
            result = _json_probe(20130, "/healthz")
            return result.get("service") == "gemini-router" and result.get("route") == "auxiliary" and result.get("port") == 20130
        if name.startswith("headroom-"):
            route = name.removeprefix("headroom-")
            return validate_health(_json_probe(PORTS[name], "/healthz"), route)
        if name == "gateway":
            result = _json_probe(20131, "/api/v1/health")
            return result.get("service") == "devcore-api" and result.get("status") == "ok"
        if name == "repowise":
            result = _json_probe(7337, "/health")
            return result.get("status") == "healthy" and result.get("db") == "ok"
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return False


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(.3)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def _listener_pid(port: int) -> int | None:
    if os.name != "nt":
        return None
    result = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        return None
    address = f"127.0.0.1:{port}"
    for line in result.stdout.splitlines():
        fields = line.split()
        if (len(fields) == 5 and fields[0] == "TCP" and fields[1] == address
                and fields[3] == "LISTENING" and fields[4].isdecimal()):
            return int(fields[4])
    return None


def _repowise_fresh(executable: str) -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, timeout=45).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO, text=True, timeout=45)
    if dirty.strip():
        raise RuntimeError("RepoWise index cannot cover the dirty working tree")
    result = subprocess.run([executable, "status", "--format", "json", "--no-workspace"],
                            cwd=REPO, capture_output=True, text=True, timeout=90, check=True)
    status = json.loads(result.stdout)
    if not status.get("indexed") or status.get("state", {}).get("last_sync_commit") != head:
        raise RuntimeError("RepoWise index is not aligned with the current commit")
    return {"commit": head, "indexed_commit": status["state"]["last_sync_commit"]}


def _preflight(skip_repowise: bool, headroom_python: Path) -> tuple[dict, str | None]:
    from devcore_engine.runs.postgres_store import PostgresRunStore

    roots = {key: os.environ.get(key, "").strip() for key in
             ("DEVCORE_LOCAL_ROOT", "DEVCORE_DATA_ROOT", "DEVCORE_PLATFORM_ROOT")}
    if any(not value or not Path(value).is_absolute() for value in roots.values()):
        raise RuntimeError("Explicit absolute local, data and platform roots required")
    if os.environ.get("DEVCORE_TASK_READ_MODE") != "postgres" or os.environ.get("DEVCORE_IDENTITY_READ_MODE") != "postgres":
        raise RuntimeError("PostgreSQL task and identity modes required")
    if os.environ.get("DEVCORE_REQUIRE_AUTH") != "1":
        raise RuntimeError("Gateway authorization must be enforced")
    if not headroom_python.is_file():
        raise RuntimeError("Headroom runtime missing")
    dsn = os.environ.get("DEVCORE_DATABASE_URL", "").strip()
    PostgresRunStore(dsn).verify_ready()
    PostgresScheduleDispatcher(dsn).verify_ready()
    selected_ports = {key: value for key, value in PORTS.items() if key != "repowise" or not skip_repowise}
    occupied = [port for port in selected_ports.values() if not _port_free(port)]
    if occupied:
        raise RuntimeError(f"Global stack ports already occupied: {occupied}")
    repowise = None
    if not skip_repowise:
        repowise = shutil.which("repowise")
        if not repowise:
            raise RuntimeError("RepoWise executable missing")
        import_check = subprocess.run([str(headroom_python), "-c",
                                       "from repowise.cli.main import cli"],
                                      capture_output=True, text=True, timeout=90)
        if import_check.returncode:
            raise RuntimeError("RepoWise package unavailable in the supervised Python runtime")
        _repowise_fresh(repowise)
    return roots, repowise


def _write_manifest(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    deadline = time.monotonic() + 5
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.05)


def _stop_managed(name: str, roots: dict) -> bool:
    from service_runtime import request_stop

    try:
        result = request_stop(roots["DEVCORE_LOCAL_ROOT"], roots["DEVCORE_DATA_ROOT"],
                              roots["DEVCORE_PLATFORM_ROOT"], name, wait_seconds=15)
        return result.get("shutdown_completed") is True
    except (OSError, ValueError):
        return False


def _supervise(roots: dict, repowise: str | None, headroom_python: Path) -> int:
    from service_runtime import request_stop  # ensure the managed runtime is available before launching
    from windows_process_identity import process_identity

    runtime = Path(roots["DEVCORE_LOCAL_ROOT"]) / "GlobalStack"
    runtime.mkdir(parents=True, exist_ok=True)
    manifest_path = runtime / "candidate-processes.json"
    stop_path = runtime / "candidate-stop.json"
    stop_token = uuid4().hex
    scheduler_stop_path = runtime / f"scheduler-stop-{stop_token[:8]}.json"
    repowise_stop_path = runtime / f"repowise-stop-{stop_token[:8]}.json"
    env = os.environ.copy()
    env["DEVCORE_GLOBAL_STACK_MANIFEST"] = str(manifest_path)
    runtime_python = Path(sys._base_executable)
    release_packages = Path(sys.prefix) / "Lib" / "site-packages"
    env["PYTHONPATH"] = os.pathsep.join((str(DEV_CORE), str(DEV_CORE / "API"), str(release_packages),
                                          env.get("PYTHONPATH", "")))
    env["DEVCORE_GEMINI_ROUTER_BIND"] = "127.0.0.1"
    env["DEVCORE_SCHEDULER_STOP_TOKEN"] = stop_token
    env["DEVCORE_REPOWISE_STOP_TOKEN"] = stop_token
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    external_env = env.copy()
    external_env["PYTHONPATH"] = str(DEV_CORE)
    specs = [
        ("router", [str(runtime_python), str(SCRIPTS / "gemini_router.py")], REPO),
        ("headroom-native", [str(headroom_python), str(SCRIPTS / "headroom_routes.py"), "--route", "native"], REPO),
        ("headroom-auxiliary", [str(headroom_python), str(SCRIPTS / "headroom_routes.py"), "--route", "auxiliary"], REPO),
        ("gateway", [str(runtime_python), str(SCRIPTS / "launch_postgres_gateway.py")], REPO),
        ("scheduler", [str(runtime_python), str(SCRIPTS / "postgres_schedule_daemon.py"),
                       "--stop-file", str(scheduler_stop_path)], REPO),
    ]
    if repowise:
        specs.append(("repowise", [str(headroom_python), str(SCRIPTS / "launch_managed_repowise.py"),
                                    "--stop-file", str(repowise_stop_path), "serve", "--host", "127.0.0.1",
                                    "--port", "7337", "--no-ui"], REPO))
    started: list[tuple[str, subprocess.Popen, object]] = []
    manifest = {"status": "starting", "created_utc": datetime.now(timezone.utc).isoformat(),
                "roots": roots, "processes": {}, "supervisor_pid": os.getpid(),
                "supervisor_identity": process_identity(os.getpid()), "stop_token": stop_token}
    stop = False

    def request_shutdown(*_):
        nonlocal stop
        stop = True

    for kind in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", signal.SIGINT)):
        signal.signal(kind, request_shutdown)
    try:
        for name, command, cwd in specs:
            log_path = runtime / f"{name}-{stop_token[:8]}.log"
            log = log_path.open("ab", buffering=0)
            creationflags = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0
            child_env = external_env if name.startswith("headroom-") or name == "repowise" else env
            process = subprocess.Popen(command, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, creationflags=creationflags)
            started.append((name, process, log))
            manifest["processes"][name] = {"pid": process.pid, "port": PORTS.get(name),
                                           "log": str(log_path)}
            _write_manifest(manifest_path, manifest)
            deadline = time.monotonic() + (180 if name == "repowise" else 90)
            while time.monotonic() < deadline and process.poll() is None and not stop:
                if name == "scheduler":
                    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-10:]:
                        try:
                            state = json.loads(line)
                        except ValueError:
                            continue
                        if state.get("status") == "postgres_schedule_started" and state.get("pid") == process.pid:
                            break
                    else:
                        time.sleep(.25)
                        continue
                    break
                elif _ready(name):
                    if _listener_pid(PORTS[name]) != process.pid:
                        raise RuntimeError(f"{name} listener is not owned by the launched process")
                    break
                time.sleep(.25)
            else:
                raise RuntimeError(f"{name} failed readiness or exited")
        manifest["status"] = "ready"
        manifest["health"] = {name: True for name, _, _ in started}
        manifest["heartbeat_utc"] = datetime.now(timezone.utc).isoformat()
        _write_manifest(manifest_path, manifest)
        print(json.dumps({"status": "global_stack_candidate_ready", "manifest": str(manifest_path)}), flush=True)
        next_health_check = 0.0
        failing_since: dict[str, float] = {}
        while not stop:
            try:
                request = json.loads(stop_path.read_text(encoding="utf-8"))
                if request.get("token") == stop_token:
                    stop = True
                    break
            except (OSError, ValueError, AttributeError):
                pass
            for name, process, _ in started:
                if process.poll() is not None:
                    raise RuntimeError(f"{name} exited unexpectedly: {process.returncode}")
            if time.monotonic() >= next_health_check:
                health = {name: (True if name == "scheduler" else
                                 _ready(name) and _listener_pid(PORTS[name]) == process.pid)
                          for name, process, _ in started}
                manifest["health"] = health
                manifest["heartbeat_utc"] = datetime.now(timezone.utc).isoformat()
                _write_manifest(manifest_path, manifest)
                overdue = overdue_health_failures(health, failing_since, time.monotonic())
                if overdue:
                    raise RuntimeError(f"Global health lost beyond grace period: {overdue}")
                next_health_check = time.monotonic() + 2
            time.sleep(.5)
        return 0
    finally:
        manifest["status"] = "stopping"
        manifest_error = None
        try:
            _write_manifest(manifest_path, manifest)
        except OSError as exc:
            manifest_error = exc
        outcomes = {}
        for name, process, log in reversed(started):
            graceful = False
            if process.poll() is None and name == "repowise":
                _write_manifest(repowise_stop_path, {"pid": process.pid, "token": stop_token})
                try:
                    process.wait(timeout=20)
                    graceful = process.returncode == 0
                except subprocess.TimeoutExpired:
                    pass
            if process.poll() is None and name == "scheduler":
                _write_manifest(scheduler_stop_path, {"pid": process.pid, "token": stop_token})
                try:
                    process.wait(timeout=10)
                    graceful = process.returncode == 0
                except subprocess.TimeoutExpired:
                    pass
            if process.poll() is None and name in {"router", "headroom-native", "headroom-auxiliary", "gateway"}:
                graceful = _stop_managed(name, roots)
            if process.poll() is None and not graceful:
                if os.name == "nt":
                    try:
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        process.wait(timeout=10)
                        graceful = process.returncode == 0
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                if process.poll() is None:
                    process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            outcomes[name] = {"exit_code": process.returncode, "graceful": graceful}
            log.close()
        manifest["status"] = "stopped" if all(item["graceful"] for item in outcomes.values()) else "shutdown_incomplete"
        manifest["shutdown"] = outcomes
        try:
            _write_manifest(manifest_path, manifest)
            manifest_error = None
        except OSError as exc:
            manifest_error = exc
        try:
            if json.loads(stop_path.read_text(encoding="utf-8")).get("token") == stop_token:
                stop_path.unlink()
        except (OSError, ValueError, AttributeError):
            pass
        print(json.dumps({"status": manifest["status"], "manifest": str(manifest_path)}), flush=True)
        if manifest_error is not None:
            raise RuntimeError("Global children stopped but manifest update failed") from manifest_error


def _request_stop(local_root: Path) -> int:
    from windows_process_identity import process_identity

    runtime = local_root / "GlobalStack"
    manifest_path = runtime / "candidate-processes.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pid = manifest.get("supervisor_pid")
    if (manifest.get("status") != "ready" or type(pid) is not int
            or manifest.get("supervisor_identity") != process_identity(pid)):
        raise RuntimeError("Global supervisor identity is not live")
    token = manifest.get("stop_token")
    if not isinstance(token, str) or len(token) != 32:
        raise RuntimeError("Global supervisor stop token invalid")
    _write_manifest(runtime / "candidate-stop.json", {"token": token})
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        current = json.loads(manifest_path.read_text(encoding="utf-8"))
        if current.get("stop_token") == token and current.get("status") in {"stopped", "shutdown_incomplete"}:
            print(json.dumps({"status": current["status"], "shutdown": current.get("shutdown", {})}))
            return 0 if current["status"] == "stopped" else 1
        time.sleep(.25)
    raise RuntimeError("Global supervisor did not publish shutdown result")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--skip-repowise", action="store_true", help="Isolated component rehearsal only")
    parser.add_argument("--headroom-python", type=Path, default=Path("C:/Python314/python.exe"))
    args = parser.parse_args()
    try:
        if args.stop:
            local_root = Path(os.environ.get("DEVCORE_LOCAL_ROOT", ""))
            if not local_root.is_absolute():
                raise RuntimeError("Explicit local root required to stop")
            return _request_stop(local_root)
        roots, repowise = _preflight(args.skip_repowise, args.headroom_python)
        if args.check:
            print(json.dumps({"status": "global_stack_preflight_ready",
                              "repowise_included": not args.skip_repowise}))
            return 0
        return _supervise(roots, repowise, args.headroom_python)
    except Exception as exc:
        print(json.dumps({"status": "global_stack_refused", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
