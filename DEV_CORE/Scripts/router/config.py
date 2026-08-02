import os
from pathlib import Path

DEV_CORE = os.environ.get("DEVCORE_PLATFORM_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE"))
DEV_CORE_DATA = os.environ.get("DEVCORE_DATA_ROOT", str(Path(__file__).resolve().parents[3] / "DEV_CORE_DATA"))

KEY_PATH = os.environ.get(
    "GEMINI_API_KEY_FILE",
    os.path.join(DEV_CORE, "Config", "gemini_api_key.txt"),
)

def load_api_key() -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        return api_key.strip()
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def load_cerebras_key() -> str:
    key = os.environ.get("CEREBRAS_API_KEY")
    if key:
        return key.strip()
    path = os.path.join(DEV_CORE, "Config", "cerebras_api_key.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def load_nvidia_key() -> str:
    key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVAPI_KEY")
    if key:
        return key.strip()
    path = os.path.join(DEV_CORE, "Config", "nvidia_api_key.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

API_KEY = load_api_key()
CEREBRAS_API_KEY = load_cerebras_key()
NVIDIA_API_KEY = load_nvidia_key()

PUBLIC_BIND_HOSTS = {"0.0.0.0", "::", ""}

MODEL_MAP = {
    "claude-3-5-sonnet": "gemini-2.5-flash",
    "claude-3-5-sonnet-20241022": "gemini-2.5-flash",
    "claude-3-opus": "gemini-2.5-flash",
    "claude-3-haiku": "gemini-2.5-flash",
    "gpt-4o": "gemini-2.5-flash",
    "gpt-4o-mini": "gemini-2.5-flash",
    "devcore-always-on": "gemini-2.5-flash",
    "devcore-reasoning": "gemini-2.5-flash",
    "devcore-coding": "gemini-2.5-flash",
    "devcore-bulk": "gemini-2.5-flash",
}

MODE_MODEL_MAP = {
    "reasoning": "devcore-reasoning",
    "coding": "devcore-coding",
    "bulk": "devcore-bulk",
    "plan": "devcore-reasoning",
}

BUDGET_THRESHOLDS = {
    "coding": 500000,
    "reasoning": 2000000,
    "bulk": 1000000
}

GEMINI_BASE_URL = os.environ.get(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/v1",
)

# Paths resolving via env variables correctly
ACTIVE_PROJECT_PATH = Path(DEV_CORE_DATA) / "Runtime" / "active_project.txt"
TASKS_DIR = Path(DEV_CORE_DATA) / "Memory"
ALERTS_LOG = Path(DEV_CORE_DATA) / "Logs" / "scripts" / "alerts.log"
STATS_PATH = Path(DEV_CORE_DATA) / "Metrics" / "headroom_stats.json"
EPHEMERAL_PATH = Path(DEV_CORE_DATA) / "Runtime" / "ephemeral_session.json"
PROTOCOL_LOG = Path(DEV_CORE_DATA) / "Logs" / "scripts" / "protocol_violations.log"
NETWORK_CONFIG_PATH = Path(DEV_CORE) / "Config" / "network.json"
