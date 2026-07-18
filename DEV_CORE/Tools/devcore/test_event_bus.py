import sys
import json
import pytest
from pathlib import Path

# Ensure devcore is in path
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.event_bus import EventBus


def test_event_bus_in_memory_subscription():
    """Verify that EventBus triggers in-memory callbacks correctly."""
    received_events = []
    
    def callback(evt):
        received_events.append(evt)

    bus = EventBus()
    bus.subscribe("test_event", callback)

    bus.publish("test_event", {"message": "hello", "value": 123})

    assert len(received_events) == 1
    assert received_events[0]["type"] == "test_event"
    assert received_events[0]["message"] == "hello"
    assert received_events[0]["value"] == 123
    assert received_events[0]["id"].startswith("evt-")
    assert "timestamp" in received_events[0]


def test_event_bus_filesystem_persistence(tmp_path):
    """Verify that EventBus logs events as JSON files in the bus queue directory."""
    bus = EventBus(data_root=tmp_path)
    
    bus.publish("custom_type", {"project": "devcore", "payload_key": "val"})

    events_dir = tmp_path / "Bus" / "events"
    assert events_dir.exists()

    # Find the generated json file
    json_files = list(events_dir.glob("*.json"))
    assert len(json_files) == 1
    
    event_file = json_files[0]
    assert event_file.name.startswith("custom_type_")
    
    # Read and assert json payload integrity
    event_data = json.loads(event_file.read_text(encoding="utf-8"))
    assert event_data["type"] == "custom_type"
    assert event_data["project"] == "devcore"
    assert event_data["payload_key"] == "val"
    assert "timestamp" in event_data
    assert "id" in event_data
