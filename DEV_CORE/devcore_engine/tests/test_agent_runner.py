import unittest
import asyncio
from DEV_CORE.devcore_engine.runners import (
    TaskSpec,
    ExecutionResult,
    HermesRunner,
    LocalProcessRunner,
)


class TestAgentRunner(unittest.TestCase):
    def test_hermes_runner_lifecycle(self):
        async def run_test():
            runner = HermesRunner()
            self.assertEqual(runner.name, "HermesRunner")
            self.assertFalse(await runner.has_active_task())
            
            task = TaskSpec(id="T-999", project="devcore", title="Test task Hermes")
            prompt = await runner.build_prompt(task)
            self.assertIn("T-999", prompt)

            res = await runner.run(task)
            self.assertEqual(res.status, "success")
            self.assertEqual(res.task_id, "T-999")

            status = await runner.report_status()
            self.assertEqual(status.health, "OK")
            self.assertFalse(status.active)

        asyncio.run(run_test())

    def test_process_runner_success(self):
        async def run_test():
            runner = LocalProcessRunner(default_cmd="python -c \"print('Hello ProcessRunner')\"")
            task = TaskSpec(id="T-998", project="devcore", title="Test process")
            res = await runner.run(task)
            self.assertEqual(res.status, "success")
            self.assertIn("Hello ProcessRunner", res.output)

        asyncio.run(run_test())

    def test_process_runner_timeout(self):
        async def run_test():
            runner = LocalProcessRunner(default_cmd="python -c \"import time; time.sleep(2)\"")
            task = TaskSpec(id="T-997", project="devcore", title="Test timeout", timeout=0.2)
            res = await runner.run(task)
            self.assertEqual(res.status, "timeout")
            self.assertIn("timed out", res.error.lower())

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
