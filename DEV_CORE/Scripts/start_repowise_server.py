import os, subprocess, sys, shutil
from pathlib import Path

# Resolve DEV_CORE root
devcore_root = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", Path(__file__).resolve().parent.parent))

# Resolve GEMINI_API_KEY
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    key_file = devcore_root / "Config" / "gemini_api_key.txt"
    if key_file.exists():
        gemini_key = key_file.read_text(encoding="utf-8").strip()

env = os.environ.copy()
if gemini_key:
    env["GEMINI_API_KEY"] = gemini_key

# Set up log files in user home
home_dir = Path.home()
log_out = open(home_dir / "repowise_serve_out.log", "wb")
log_err = open(home_dir / "repowise_serve_err.log", "wb")

# Resolve repowise executable
repowise_exe = shutil.which("repowise")
if not repowise_exe:
    candidates = [
        Path(sys.prefix) / "Scripts" / "repowise.exe",
        home_dir / "AppData" / "Roaming" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts" / "repowise.exe",
        home_dir / "AppData" / "Roaming" / "Python" / "Python314" / "Scripts" / "repowise.exe",
        home_dir / "AppData" / "Roaming" / "Python" / "Python313" / "Scripts" / "repowise.exe",
        home_dir / "AppData" / "Roaming" / "Python" / "Scripts" / "repowise.exe",
        Path("C:/Python314/Scripts/repowise.exe"),
        Path("C:/Python313/Scripts/repowise.exe"),
        Path(r"C:\Program Files\Python313\Scripts\repowise.exe"),
    ]
    for c in candidates:
        if c.exists():
            repowise_exe = str(c)
            break
if not repowise_exe:
    repowise_exe = "repowise"

# Use CREATE_NO_WINDOW (0x08000000) only to prevent any console window popup
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
try:
    p = subprocess.Popen(
        [repowise_exe, "serve", "--host", "127.0.0.1", "--port", "7337", "--no-ui"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=log_out,
        stderr=log_err,
        creationflags=flags
    )
    p.stdin.write(b"\n")
    p.stdin.flush()
    print(f"STARTED PID: {p.pid}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
