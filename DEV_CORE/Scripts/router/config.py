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

from .policy import MODEL_MAP

# Modes describe auxiliary tasks only; a model alias is still mandatory.
MODE_MODEL_MAP = {name.removeprefix("devcore-"): name for name in MODEL_MAP}

BUDGET_THRESHOLDS = {
    "coding": 500000,
    "reasoning": 2000000,
    "bulk": 1000000
}

GEMINI_BASE_URL = os.environ.get(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai",
)
GEMINI_BASE_URL = GEMINI_BASE_URL.rstrip("/")
if GEMINI_BASE_URL != "https://generativelanguage.googleapis.com/v1beta/openai":
    raise ValueError("Gemini Router requires the native Google OpenAI-compatible endpoint; provider changes require an explicit fallback request")

# Auxiliary accounting paths. No machine-global active project is consulted.
ALERTS_LOG = Path(DEV_CORE_DATA) / "Logs" / "scripts" / "alerts.log"
STATS_PATH = Path(DEV_CORE_DATA) / "Metrics" / "gemini_auxiliary_stats.json"
NETWORK_CONFIG_PATH = Path(DEV_CORE) / "Config" / "network.json"
