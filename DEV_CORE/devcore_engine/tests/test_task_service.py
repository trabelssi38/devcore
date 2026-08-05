"""
test_task_service.py -- Python Native Unit Test for TaskService
"""

import tempfile
import unittest
from pathlib import Path

from devcore_engine.services.tasks import TaskService


class TestTaskService(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="devcore_task_service_test_"))
        self.ts = TaskService(self.tmp_dir)

    def test_add_and_board(self):
        t1 = self.ts.add_task("First Task", mode="coding", steps=2, project_id="devcore")
        self.assertEqual(t1["id"], "T-01")
        self.assertEqual(t1["mode"], "coding")

        board = self.ts.get_board("devcore")
        self.assertEqual(len(board["tasks"]), 1)

    def test_next_task(self):
        self.ts.add_task("Task 1", mode="coding", project_id="devcore")
        self.ts.add_task("Task 2", mode="reasoning", project_id="devcore")

        active = self.ts.next_task("devcore")
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], "T-01")
        self.assertEqual(active["status"], "in_progress")

    def test_complete_task(self):
        self.ts.add_task("Task 1", mode="coding", project_id="devcore")
        active = self.ts.next_task("devcore")
        self.assertIsNotNone(active)

        comp = self.ts.complete_task("T-01", project_id="devcore")
        self.assertIsNotNone(comp)
        self.assertEqual(comp["status"], "done")

    def test_step_task(self):
        created = self.ts.add_task("Multi step task", mode="coding", steps=3, project_id="devcore")
        t_id = created["id"]
        self.ts.next_task("devcore")

        stepped = self.ts.step_task(t_id, step_number=1, project_id="devcore")
        self.assertEqual(stepped["steps_done"], 1)
        self.assertEqual(stepped["status"], "in_progress")

        stepped2 = self.ts.step_task(t_id, step_number=3, project_id="devcore")
        self.assertEqual(stepped2["steps_done"], 3)
        self.assertEqual(stepped2["status"], "done")



if __name__ == "__main__":
    unittest.main()
