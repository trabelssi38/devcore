"""
test_event_bus.py -- Python Native Unit Test for EventBus Service
"""

import tempfile
import unittest
from pathlib import Path

from devcore_engine.services.events import EventBus


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="devcore_event_bus_test_"))
        self.db_path = self.tmp_dir / "devcore.db"
        self.bus = EventBus(self.db_path)

    def test_publish_and_tail(self):
        eid1 = self.bus.publish("TaskCreated", {"safe": "ok", "api_key": "secret"}, project="devcore", task_id="T-120")
        self.assertTrue(eid1.startswith("evt_"))

        evts = self.bus.tail(limit=10)
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0]["event_type"], "TaskCreated")

    def test_publish_multiple(self):
        self.bus.publish("TaskCreated", {"step": 1}, project="devcore", task_id="T-01")
        self.bus.publish("DashboardRefreshed", {"status": "success"}, project="devcore", task_id="T-01")

        evts = self.bus.tail(limit=1)
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0]["event_type"], "DashboardRefreshed")


if __name__ == "__main__":
    unittest.main()
