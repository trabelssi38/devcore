"""Exercise candidate Dashboard startup and cooperative stop on temporary roots."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def qualify(release: Path) -> dict:
    release = release.resolve(strict=True)
    python = release / "Scripts" / "python.exe"
    controls = release / "controls" / "Scripts"
    bundle = release / "individual-platform-v2"
    if not python.is_file() or not controls.is_dir() or not bundle.is_dir():
        raise ValueError("Incomplete candidate release")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 20129)) == 0:
            raise ValueError("Dashboard port 20129 is already in use")

    with tempfile.TemporaryDirectory(prefix="devcore-l9-managed-") as scratch:
        root = Path(scratch)
        local, data = root / "local", root / "data"
        (local / "Security").mkdir(parents=True)
        data.mkdir()
        identity = local / "Security" / "identity.db"
        env = dict(os.environ, DEVCORE_LOCAL_ROOT=str(local), DEVCORE_DATA_ROOT=str(data))
        fixture = subprocess.run([str(python), "-I", "-c",
            "import sys; from devcore_engine.security.private_store import initialize_private_store; initialize_private_store(sys.argv[1])",
            str(identity)], env=env, cwd=root, capture_output=True, timeout=30)
        if fixture.returncode:
            raise RuntimeError("Temporary private identity initialization failed")

        pin = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
        command = [str(python), "-I", str(controls / "launch_individual_candidate.py"),
                   "--bundle", str(bundle), "--manifest-sha256", pin,
                   "--local-root", str(local), "--data-root", str(data),
                   "--identity-store", str(identity), "--port", "20129", "--managed"]
        log_path = root / "dashboard.log"
        with log_path.open("wb") as log:
            process = subprocess.Popen(command, env=env, cwd=root, stdout=log, stderr=log)
            try:
                import httpx
                with httpx.Client(base_url="http://127.0.0.1:20129", trust_env=False, timeout=1) as client:
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise RuntimeError(f"Dashboard exited during startup: {process.returncode}")
                        try:
                            if client.get("/project").status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        time.sleep(.2)
                    else:
                        raise RuntimeError("Dashboard readiness timeout")
                stop = subprocess.run([str(python), "-I", str(controls / "stop_service.py"),
                    "--local-root", str(local), "--data-root", str(data),
                    "--platform-root", str(bundle), "--service", "dashboard",
                    "--wait-seconds", "30"], env=env, cwd=root,
                    capture_output=True, text=True, timeout=35)
                process.wait(timeout=10)
                result = json.loads(stop.stdout) if stop.stdout else {}
                if (stop.returncode or process.returncode or not result.get("shutdown_completed")):
                    raise RuntimeError(f"Managed stop failed: exit={stop.returncode}, process={process.returncode}, result={result}")
                return {"success": True, "release": str(release), "port": 20129,
                        "temporary_roots": True, "stop": result["status"], "exit_code": process.returncode}
            except Exception as exc:
                log.flush()
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(f"{exc}; dashboard log tail: {detail}") from exc
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = qualify(args.release)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
