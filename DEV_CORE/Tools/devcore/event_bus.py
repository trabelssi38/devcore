import os
import sys
import uuid
import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any

# Add tools to sys path if needed
tools_dir = Path(__file__).resolve().parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from devcore.paths import get_paths

logger = logging.getLogger("event_bus")


class EventBus:
    """Internal EventBus module supporting local subscription and retrocompatible filesystem queue publishing."""

    def __init__(self, data_root: Optional[Path] = None):
        self._listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.data_root = data_root

    def _get_data_root(self) -> Path:
        if self.data_root:
            return self.data_root
        try:
            return get_paths().data_root
        except Exception:
            # Fallback path if platform environment is not configured
            return Path("C:/devcore/DEV_CORE_DATA")

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback listener for a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all local subscribers and persist it to the file-based events queue."""
        event_id = f"evt-{uuid.uuid4()}"
        event = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **payload
        }

        # 1. Trigger in-memory subscribers
        listeners = self._listeners.get(event_type, [])
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.exception(f"Error in subscriber callback for event {event_type}: {e}")

        # 2. Persist to file-based events queue for backward compatibility
        try:
            data_root = self._get_data_root()
            events_dir = data_root / "Bus" / "events"
            events_dir.mkdir(parents=True, exist_ok=True)

            event_file = events_dir / f"{event_type}_{event_id}.json"
            event_file.write_text(json.dumps(event, indent=2), encoding="utf-8")
            logger.info(f"[EventBus] Published event {event_type} to file: {event_file.name}")
        except Exception as e:
            logger.error(f"[EventBus] Failed to persist event {event_type}: {e}")
