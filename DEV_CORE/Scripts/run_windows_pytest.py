"""Run isolated pytest fixtures on Windows hosts where mode 0700 locks out the caller.

Usage: python DEV_CORE/Scripts/run_windows_pytest.py [pytest arguments]
The default target is the Windows service profile suite.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4


def main() -> int:
    if os.name != "nt":
        raise SystemExit("This runner is for the Windows pytest ACL issue only")

    repo = Path(__file__).resolve().parents[2]
    root = repo / f"pytest-isolated-{uuid4().hex}"
    root.mkdir(mode=0o750)
    for name in ("local", "data", "platform"):
        (root / name).mkdir(mode=0o750)

    os.environ.update({
        "TEMP": str(root),
        "TMP": str(root),
        "DEVCORE_LOCAL_ROOT": str(root / "local"),
        "DEVCORE_DATA_ROOT": str(root / "data"),
        "DEVCORE_PLATFORM_ROOT": str(root / "platform"),
        "PYTHONPATH": str(repo / "DEV_CORE"),
    })
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "DEV_CORE"))

    # On this host, Python's mode 0700 maps to a Windows ACL that prevents
    # even the test process from traversing its own pytest directories.
    # Change only those mkdir calls inside this newly created test root.
    original_mkdir = Path.mkdir
    original_os_mkdir = os.mkdir

    def mode_for_test_root(path: Path | str, mode: int) -> int:
        try:
            inside = Path(path).absolute().is_relative_to(root)
        except (OSError, ValueError):
            inside = False
        return 0o750 if inside and mode == 0o700 else mode

    def os_mkdir_for_test_root(path: str | bytes | os.PathLike[str], mode: int = 0o777,
                               *, dir_fd: int | None = None) -> None:
        original_os_mkdir(path, mode_for_test_root(path, mode), dir_fd=dir_fd)

    def mkdir_for_test_root(path: Path, mode: int = 0o777,
                            parents: bool = False, exist_ok: bool = False) -> None:
        mode = mode_for_test_root(path, mode)
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    Path.mkdir = mkdir_for_test_root
    os.mkdir = os_mkdir_for_test_root
    import pytest

    args = sys.argv[1:]
    if not any(not arg.startswith("-") for arg in args):
        args.append("DEV_CORE/tests/test_windows_service_profile.py")
    if any(arg == "--basetemp" or arg.startswith("--basetemp=") for arg in args):
        raise SystemExit("--basetemp is managed by this runner")
    try:
        return int(pytest.main([
            "-p", "no:cacheprovider", "--basetemp", str(root / "pytest-work"), *args,
        ]))
    finally:
        Path.mkdir = original_mkdir
        os.mkdir = original_os_mkdir
        # Only this UUID directory, created above, may be removed.
        if root.resolve().parent == repo and root.name.startswith("pytest-isolated-"):
            try:
                shutil.rmtree(root)
            except OSError as exc:
                print(f"Test root retained for inspection: {root} ({exc})", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
