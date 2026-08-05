import os, subprocess, sys
from pathlib import Path

# Resolve GEMINI_API_KEY
gemini_key = os.environ.get("GEMINI_API_KEY")
if not gemini_key:
    devcore_root = Path("C:/devcore/DEV_CORE")
    key_file = devcore_root / "Config" / "gemini_api_key.txt"
    if key_file.exists():
        gemini_key = key_file.read_text(encoding="utf-8").strip()

env = os.environ.copy()
if gemini_key:
    env["GEMINI_API_KEY"] = gemini_key

# Set up log files
log_out = open("C:/Users/trb_m/repowise_serve_out.log", "wb")
log_err = open("C:/Users/trb_m/repowise_serve_err.log", "wb")

# Use CREATE_NO_WINDOW (0x08000000) and DETACHED_PROCESS (0x00000008)
flags = 0x08000000 | 0x00000008
try:
    p = subprocess.Popen(
        [r"C:\Program Files\Python313\Scripts\repowise.exe", "serve", "--host", "127.0.0.1", "--port", "7337", "--no-ui"],
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
