"""Windows service host for the pinned individual Dashboard candidate."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


SERVICE_NAME = "DevCoreIndividual"


def _relative(base: Path, value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("Relative service data path required")
    part = Path(value)
    if part.is_absolute() or part.drive or any(item in (".", "..") for item in part.parts):
        raise ValueError("Service data path must be relative to runtime base")
    resolved = (base / part).resolve()
    if not resolved.is_relative_to(base):
        raise ValueError("Service data path escapes runtime base")
    return resolved


def load_profile(release: Path) -> dict:
    release = Path(release).resolve(strict=True)
    if release.parent.name.lower() != "releases":
        raise ValueError("Versioned release directory required")
    base = release.parent.parent
    config_path = release / "individual-service.json"
    if config_path.is_symlink() or not config_path.is_file() or config_path.stat().st_size > 4096:
        raise ValueError("Missing or invalid service configuration")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") not in (1, 2):
        raise ValueError("Unsupported service configuration")
    expected = {"schema_version", "local_relative", "data_relative", "bundle_manifest_sha256"}
    if config["schema_version"] == 2:
        expected.add("windows_startup")
    if set(config) != expected:
        raise ValueError("Unexpected service configuration field")
    startup = config.get("windows_startup", "automatic")
    if startup not in ("automatic", "manual"):
        raise ValueError("Windows startup must be automatic or manual")
    local = _relative(base, config["local_relative"])
    data = _relative(base, config["data_relative"])
    if local == data or local.is_relative_to(data) or data.is_relative_to(local):
        raise ValueError("Separate local and data roots required")
    if not local.is_dir() or not data.is_dir():
        raise ValueError("Service data roots must already exist")
    identity = local / "Security" / "identity.db"
    if identity.is_symlink() or not identity.is_file():
        raise ValueError("Private identity store must be initialized before service start")
    bundle = release / "individual-platform-v2"
    pin = config["bundle_manifest_sha256"]
    if (not isinstance(pin, str) or len(pin) != 64 or any(c not in "0123456789abcdef" for c in pin)
            or hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest() != pin):
        raise ValueError("Snapshot manifest differs from service pin")
    python = release / "Scripts" / "python.exe"
    controls = release / "controls" / "Scripts"
    if not python.is_file() or not controls.is_dir():
        raise ValueError("Candidate runtime controls are missing")
    return {"release": release, "local": local, "data": data, "identity": identity,
            "bundle": bundle, "pin": pin, "python": python, "controls": controls,
            "windows_startup": startup}


def candidate_command(profile: dict) -> list[str]:
    return [str(profile["python"]), "-I", str(profile["controls"] / "launch_individual_candidate.py"),
            "--bundle", str(profile["bundle"]), "--manifest-sha256", profile["pin"],
            "--local-root", str(profile["local"]), "--data-root", str(profile["data"]),
            "--identity-store", str(profile["identity"]), "--port", "20129", "--managed"]


if os.name == "nt":
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

    class DevCoreIndividualService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = "DevCore Individual Dashboard"
        _svc_description_ = "Pinned local DevCore individual Dashboard with cooperative shutdown"

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=45000)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            release = Path(__file__).resolve().parents[3]
            process = None
            log = None
            try:
                profile = load_profile(release)
                env = dict(os.environ, DEVCORE_LOCAL_ROOT=str(profile["local"]),
                           DEVCORE_DATA_ROOT=str(profile["data"]))
                verify = subprocess.run([str(profile["python"]), "-I",
                    str(profile["controls"] / "verify_engine_release.py"), "--release", str(release)],
                    env=env, cwd=release, capture_output=True, timeout=30)
                if verify.returncode:
                    raise RuntimeError("Release attestation failed before service start")
                log_dir = profile["local"] / "Logs" / "service"
                log_dir.mkdir(parents=True, exist_ok=True)
                log = (log_dir / "dashboard.log").open("ab")
                process = subprocess.Popen(candidate_command(profile), env=env, cwd=release,
                    stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
                import httpx
                with httpx.Client(base_url="http://127.0.0.1:20129", trust_env=False, timeout=1) as client:
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                            break
                        if process.poll() is not None:
                            raise RuntimeError("Dashboard exited during service startup")
                        try:
                            if client.get("/project").status_code == 200:
                                self.ReportServiceStatus(win32service.SERVICE_RUNNING)
                                break
                        except httpx.TransportError:
                            pass
                        time.sleep(.2)
                    else:
                        raise RuntimeError("Dashboard service readiness timeout")
                while process.poll() is None and win32event.WaitForSingleObject(self.stop_event, 500) != win32event.WAIT_OBJECT_0:
                    pass
                if process.poll() is not None and win32event.WaitForSingleObject(self.stop_event, 0) != win32event.WAIT_OBJECT_0:
                    raise RuntimeError(f"Dashboard exited without stop request: {process.returncode}")
                if process.poll() is None:
                    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=45000)
                    stop = subprocess.run([str(profile["python"]), "-I",
                        str(profile["controls"] / "stop_service.py"), "--local-root", str(profile["local"]),
                        "--data-root", str(profile["data"]), "--platform-root", str(profile["bundle"]),
                        "--service", "dashboard", "--wait-seconds", "30"],
                        env=env, cwd=release, capture_output=True, timeout=35)
                    process.wait(timeout=10)
                    if stop.returncode or process.returncode:
                        raise RuntimeError("Dashboard did not stop cleanly")
            except Exception as exc:
                servicemanager.LogErrorMsg(f"{SERVICE_NAME}: {exc}")
                raise
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                if log is not None:
                    log.close()
