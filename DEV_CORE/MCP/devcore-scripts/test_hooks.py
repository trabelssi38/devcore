# Unit tests for MCP Tool Hooks Engine (Sprint 19)
import os
import sys
import time
import json
import unittest
from pathlib import Path

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from hooks import HookManager, CircuitBreaker, CircuitBreakerOpenError, circuit_breaker_instance
import server

class TestMCPToolHooks(unittest.TestCase):
    def setUp(self):
        self.manager = HookManager()
        # Reset circuit breaker state before each test
        circuit_breaker_instance.state.clear()
        circuit_breaker_instance.max_failures = 3
        circuit_breaker_instance.reset_timeout = 60

    def test_pre_and_post_hooks_execution(self):
        """Test that pre and post hooks run without errors and capture timing."""
        tool_name = "devcore_knowledge_status"
        arguments = {}

        t0 = time.time()
        context = self.manager.run_pre_hooks(tool_name, arguments)
        t1 = time.time()

        self.assertIn("start_time", context)
        self.assertIn("timestamp", context)
        # Latency check: pre-hooks overhead should be under 50ms
        self.assertLess((t1 - t0), 0.050)

        raw_result = {"success": True, "stdout": "test output"}
        t2 = time.time()
        final_result = self.manager.run_post_hooks(tool_name, arguments, raw_result, context)
        t3 = time.time()

        self.assertIn("success", final_result)
        # Latency check: post-hooks overhead should be under 50ms
        self.assertLess((t3 - t2), 0.050)

    def test_circuit_breaker_trips(self):
        """Test that circuit breaker trips after 3 consecutive failures."""
        tool_name = "test_failing_tool"

        # Record 3 failures
        circuit_breaker_instance.record_failure(tool_name)
        circuit_breaker_instance.record_failure(tool_name)
        circuit_breaker_instance.record_failure(tool_name)

        # 4th pre-hook call must raise CircuitBreakerOpenError
        with self.assertRaises(CircuitBreakerOpenError):
            self.manager.run_pre_hooks(tool_name, {})

    def test_circuit_breaker_resets_on_success(self):
        """Test that a successful call resets failure count."""
        tool_name = "test_flaky_tool"
        circuit_breaker_instance.record_failure(tool_name)
        circuit_breaker_instance.record_failure(tool_name)
        
        # Success resets count
        circuit_breaker_instance.record_success(tool_name)
        self.assertEqual(circuit_breaker_instance.state[tool_name]["failures"], 0)

    def test_handle_tool_call_integration(self):
        """Test full handle_tool_call with hooks integration."""
        res = server.handle_tool_call("devcore_task_status", {})
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)

    def test_circuit_breaker_blocks_handle_tool_call(self):
        """Test handle_tool_call returns graceful error when circuit breaker is open."""
        tool_name = "devcore_event_emit"
        for _ in range(3):
            circuit_breaker_instance.record_failure(tool_name)

        res = server.handle_tool_call(tool_name, {"event_type": "TEST"})
        self.assertFalse(res.get("success"))
        self.assertTrue(res.get("circuit_breaker_open"))
        self.assertIn("Circuit breaker OPEN", res.get("error", ""))

if __name__ == "__main__":
    unittest.main()
