import sys
import os
import subprocess
from pathlib import Path

# Setup paths dynamically
scheduler_dir = Path(__file__).resolve().parent
platform_root = scheduler_dir.parent
tools_dir = platform_root / "Tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python run_job.py <command_type: python|powershell> <script_path> [args...]", file=sys.stderr)
        sys.exit(1)

    cmd_type = sys.argv[1].lower()
    script_rel_path = sys.argv[2]
    job_args = sys.argv[3:]

    paths = get_paths()
    # Resolve absolute path based on platform root
    script_abs_path = paths.platform_root.parent / script_rel_path

    if script_rel_path != "-c" and not script_abs_path.exists():
        print(f"Error: Script file not found at {script_abs_path}", file=sys.stderr)
        sys.exit(2)

    # Resolve interpreter
    if cmd_type == "python":
        if script_rel_path == "-c":
            cmd = [sys.executable, "-c"] + job_args
        else:
            cmd = [sys.executable, str(script_abs_path)] + job_args
    elif cmd_type == "powershell":
        if os.name == "nt":
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script_abs_path)] + job_args
        else:
            # On Linux container, use pwsh
            cmd = ["pwsh", "-File", str(script_abs_path)] + job_args
    else:
        print(f"Error: Unknown command type: {cmd_type}", file=sys.stderr)
        sys.exit(3)

    # Execute
    print(f"Executing: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True
        )
        sys.exit(proc.returncode)
    except Exception as e:
        print(f"Exception raised during job execution: {e}", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
