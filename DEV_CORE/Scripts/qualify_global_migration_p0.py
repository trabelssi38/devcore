"""Run read-only P0 checks for the global migration on copies and localhost."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


DEFAULT_PORTS = {
    "individual_api": 20129,
    "gateway": 20131,
    "gemini_router": 20130,
    "headroom_native": 8787,
    "headroom_auxiliary": 8789,
    "repowise": 7337,
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_runtime(python: Path) -> Check:
    if not python.is_file() or python.is_symlink() or python.is_junction():
        return Check("python_runtime", "blocked", f"missing_or_linked:{python}")
    try:
        result = subprocess.run([str(python), "--version"], capture_output=True,
                                text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return Check("python_runtime", "blocked", f"probe_error:{exc}")
    version = (result.stdout or result.stderr).strip()
    return Check("python_runtime", "pass", version)


def check_artifact(name: str, path: Path, required: tuple[str, ...] = ()) -> Check:
    if not path.is_file() or path.is_symlink() or path.is_junction():
        return Check(name, "blocked", f"missing_or_linked:{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Check(name, "blocked", f"invalid_json:{exc}")
    missing = [key for key in required if key not in payload]
    if missing:
        return Check(name, "blocked", f"missing_keys:{','.join(missing)}")
    return Check(name, "pass", f"sha256={_sha256(path)}")


def probe_http(name: str, port: int, timeout: float = 1.0) -> Check:
    url = f"http://127.0.0.1:{port}/"
    try:
        with urlopen(url, timeout=timeout) as response:
            return Check(name, "pass", f"http_{response.status}")
    except HTTPError as exc:
        return Check(name, "pass", f"http_{exc.code}")
    except (OSError, URLError, TimeoutError) as exc:
        return Check(name, "blocked", f"unreachable:{type(exc).__name__}")


def probe_tcp(name: str, port: int, timeout: float = 1.0) -> Check:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return Check(name, "pass", "tcp_open")
    except OSError as exc:
        return Check(name, "blocked", f"closed:{type(exc).__name__}")


def qualify(repo_root: Path, artifact_root: Path, python: Path,
            ports: dict[str, int] | None = None) -> dict:
    repo_root = repo_root.resolve(strict=True)
    artifact_root = artifact_root.resolve(strict=True)
    if not artifact_root.is_relative_to(repo_root) and not artifact_root.is_relative_to(Path("E:/DevCoreRuntime")):
        raise ValueError("artifact root must be a non-active qualification root")
    ports = ports or DEFAULT_PORTS
    checks = [check_runtime(python)]
    checks.extend([
        check_artifact("fusion_cutover_checklist", artifact_root / "fusion-cutover-checklist-2026-10-12.json",
                       ("ready_for_cutover", "blockers")),
        check_artifact("global_migration_proposals", artifact_root / "global-migration-proposals-2026-10-12.json",
                       ("status", "ready_for_cutover")),
        check_artifact("scheduler_archive", artifact_root / "scheduler-archive-2026-10-12.json"),
    ])
    checks.extend(probe_http(name, port) for name, port in ports.items())
    blocked = [check.name for check in checks if check.status == "blocked"]
    report = {
        "phase": "P0",
        "status": "blocked" if blocked else "pass",
        "ready_for_cutover": False,
        "read_only": True,
        "checks": [asdict(check) for check in checks],
        "blocked_checks": blocked,
        "artifact_hashes": {
            path.name: _sha256(path)
            for path in artifact_root.glob("*-2026-10-12.json")
            if path.is_file()
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).parents[2])
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path("E:/DevCoreRuntime/releases/devcore-py313-20261002/Scripts/python.exe"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.repo_root, args.artifact_root, args.python)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
