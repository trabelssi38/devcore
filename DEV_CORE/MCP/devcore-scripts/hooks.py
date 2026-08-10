# MCP Tool Hooks Engine for DEV_CORE
# Implements pre-hook and post-hook interceptors for MCP tools (telemetry, audit, circuit breaker, RTK compression)

import os
import time
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Callable

DEVCORE_ROOT = Path(os.environ.get("DEVCORE_PLATFORM_ROOT", "C:/devcore/DEV_CORE"))
try:
    from devcore_engine.db import get_data_root, get_local_data_root
    DEVCORE_DATA = get_data_root()
    DEVCORE_LOCAL = get_local_data_root()
except Exception:
    DEVCORE_DATA = Path(os.environ.get("DEVCORE_DATA_ROOT", "C:/devcore/DEV_CORE_DATA"))
    env_loc = os.environ.get("DEVCORE_LOCAL_ROOT")
    DEVCORE_LOCAL = Path(env_loc) if env_loc else DEVCORE_DATA
CONFIG_PATH = DEVCORE_ROOT / "Config" / "mcp_hooks.json"

class CircuitBreakerOpenError(Exception):
    def __init__(self, tool_name: str, message: str = None):
        self.tool_name = tool_name
        self.message = message or f"Circuit breaker OPEN for tool '{tool_name}'. Tool execution blocked due to repeated failures."
        super().__init__(self.message)

class CircuitBreaker:
    def __init__(self, max_failures: int = 3, reset_timeout: int = 60):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.state: Dict[str, Dict[str, Any]] = {}

    def check(self, tool_name: str):
        info = self.state.get(tool_name)
        if not info:
            return

        if info.get("is_open"):
            elapsed = time.time() - info.get("last_failure_time", 0)
            if elapsed < self.reset_timeout:
                raise CircuitBreakerOpenError(tool_name)
            else:
                # Half-open / reset
                info["is_open"] = False
                info["failures"] = 0

    def record_failure(self, tool_name: str):
        info = self.state.setdefault(tool_name, {"failures": 0, "last_failure_time": 0, "is_open": False})
        info["failures"] += 1
        info["last_failure_time"] = time.time()
        if info["failures"] >= self.max_failures:
            info["is_open"] = True

    def record_success(self, tool_name: str):
        if tool_name in self.state:
            self.state[tool_name]["failures"] = 0
            self.state[tool_name]["is_open"] = False

# Global CircuitBreaker instance
circuit_breaker_instance = CircuitBreaker()

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "circuit_breaker": {
            "max_consecutive_failures": 3,
            "reset_timeout_seconds": 60
        },
        "enabled_pre_hooks": [
            "execution_timer",
            "circuit_breaker",
            "token_budget_check",
            "audit_log_entry"
        ],
        "enabled_post_hooks": [
            "rtk_compress",
            "token_usage_log",
            "quality_score_update",
            "audit_log_exit"
        ]
    }

# --- Built-in Pre-Hooks ---

def pre_execution_timer(tool_name: str, arguments: dict, context: dict):
    context["start_time"] = time.time()
    context["timestamp"] = datetime.now().isoformat()

def pre_circuit_breaker(tool_name: str, arguments: dict, context: dict):
    circuit_breaker_instance.check(tool_name)

def pre_token_budget_check(tool_name: str, arguments: dict, context: dict):
    alerts_file = DEVCORE_LOCAL / "Logs" / "scripts" / "alerts.log"
    if alerts_file.exists():
        try:
            lines = alerts_file.read_text(encoding="utf-8").strip().splitlines()
            if lines and "CRITICAL_BUDGET_EXCEEDED" in lines[-1]:
                context["budget_warning"] = "Critical token budget alert active"
        except Exception:
            pass

def pre_audit_log_entry(tool_name: str, arguments: dict, context: dict):
    try:
        bus_dir = DEVCORE_LOCAL / "Bus" / "events"
        bus_dir.mkdir(parents=True, exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        evt_file = bus_dir / f"{ts_str}_mcp_pre_{tool_name}.json"
        
        evt_data = {
            "event_type": "MCP_TOOL_CALL_PRE",
            "timestamp": context.get("timestamp", datetime.now().isoformat()),
            "tool_name": tool_name,
            "arguments": arguments,
            "source": "mcp-server"
        }
        evt_file.write_text(json.dumps(evt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

# --- Built-in Post-Hooks ---

def post_rtk_compress(tool_name: str, arguments: dict, result: dict, context: dict) -> dict:
    # RTK compression is handled when stdout string is returned
    stdout = result.get("stdout")
    if isinstance(stdout, str) and len(stdout) > 500:
        lines = stdout.splitlines()
        if len(lines) > 500:
            head = lines[:200]
            tail = lines[-200:]
            trunc_count = len(lines) - 400
            compressed = "\n".join(head + [f"\n... [RTK TRUNCATED {trunc_count} LINES] ...\n"] + tail)
            result["stdout"] = compressed
    return result

def post_token_usage_log(tool_name: str, arguments: dict, result: dict, context: dict) -> dict:
    try:
        metrics_dir = DEVCORE_LOCAL / "Logs" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        usage_log = metrics_dir / "mcp_token_usage.log"
        
        duration = time.time() - context.get("start_time", time.time())
        status = "SUCCESS" if result.get("success", True) else "FAILED"
        log_line = f"[{datetime.now().isoformat()}] TOOL={tool_name} DURATION={duration:.3f}s STATUS={status}\n"
        
        with open(usage_log, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass
    return result

def post_quality_score_update(tool_name: str, arguments: dict, result: dict, context: dict) -> dict:
    if result.get("success") is False:
        circuit_breaker_instance.record_failure(tool_name)
    else:
        circuit_breaker_instance.record_success(tool_name)
    return result

def post_audit_log_exit(tool_name: str, arguments: dict, result: dict, context: dict) -> dict:
    try:
        bus_dir = DEVCORE_LOCAL / "Bus" / "events"
        bus_dir.mkdir(parents=True, exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        evt_file = bus_dir / f"{ts_str}_mcp_post_{tool_name}.json"
        
        duration = time.time() - context.get("start_time", time.time())
        evt_data = {
            "event_type": "MCP_TOOL_CALL_POST",
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "duration_seconds": round(duration, 4),
            "success": result.get("success", True),
            "source": "mcp-server"
        }
        evt_file.write_text(json.dumps(evt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return result

# Register maps
PRE_HOOK_REGISTRY: Dict[str, Callable] = {
    "execution_timer": pre_execution_timer,
    "circuit_breaker": pre_circuit_breaker,
    "token_budget_check": pre_token_budget_check,
    "audit_log_entry": pre_audit_log_entry,
}

POST_HOOK_REGISTRY: Dict[str, Callable] = {
    "rtk_compress": post_rtk_compress,
    "token_usage_log": post_token_usage_log,
    "quality_score_update": post_quality_score_update,
    "audit_log_exit": post_audit_log_exit,
}

class HookManager:
    def __init__(self):
        self.config = load_config()
        cb_cfg = self.config.get("circuit_breaker", {})
        circuit_breaker_instance.max_failures = cb_cfg.get("max_consecutive_failures", 3)
        circuit_breaker_instance.reset_timeout = cb_cfg.get("reset_timeout_seconds", 60)

    def run_pre_hooks(self, tool_name: str, arguments: dict) -> dict:
        context = {}
        enabled = self.config.get("enabled_pre_hooks", list(PRE_HOOK_REGISTRY.keys()))
        
        for hook_name in enabled:
            func = PRE_HOOK_REGISTRY.get(hook_name)
            if func:
                try:
                    func(tool_name, arguments, context)
                except CircuitBreakerOpenError:
                    raise
                except Exception as e:
                    # Non-blocking error in pre-hook
                    context[f"pre_hook_error_{hook_name}"] = str(e)
        return context

    def run_post_hooks(self, tool_name: str, arguments: dict, result: dict, context: dict) -> dict:
        enabled = self.config.get("enabled_post_hooks", list(POST_HOOK_REGISTRY.keys()))
        current_result = result
        
        for hook_name in enabled:
            func = POST_HOOK_REGISTRY.get(hook_name)
            if func:
                try:
                    mod_res = func(tool_name, arguments, current_result, context)
                    if isinstance(mod_res, dict):
                        current_result = mod_res
                except Exception as e:
                    # Non-blocking error in post-hook
                    current_result[f"post_hook_error_{hook_name}"] = str(e)
                    
        return current_result
