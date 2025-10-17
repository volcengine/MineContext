# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Event Manager - Cached version, supports get and clear mechanism
"""

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """Event type enumeration"""

    TIP_GENERATED = "tip"
    TODO_GENERATED = "todo"
    ACTIVITY_GENERATED = "activity"
    DAILY_SUMMARY_GENERATED = "daily_summary"
    WEEKLY_SUMMARY_GENERATED = "weekly_summary"
    SYSTEM_STATUS = "system_status"


@dataclass
class Event:
    """Event data structure"""

    id: str
    type: EventType
    data: Dict[str, Any]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class EventManager:
    """Cached Event Manager"""

    def __init__(self):
        self.event_cache: deque[Event] = deque()
        self.max_cache_size = 1000
        self._lock = threading.Lock()  # Ensure thread safety

    def publish_event(self, event_type: EventType, data: Dict[str, Any]) -> str:
        """Publish event to cache"""
        event_id = str(uuid.uuid4())
        event = Event(id=event_id, type=event_type, data=data, timestamp=time.time())

        with self._lock:
            self.event_cache.append(event)

            # Limit cache size to avoid memory overflow
            while len(self.event_cache) > self.max_cache_size:
                removed_event = self.event_cache.popleft()
                logger.warning(f"Cache overflow, removing old event: {removed_event.id}")

        logger.info(f"Published event to cache: {event_type.value}, ID: {event_id}")
        return event_id

    def fetch_and_clear_events(self) -> List[Dict[str, Any]]:
        """Fetch all cached events and clear the cache"""
        with self._lock:
            # Get all current events
            events = [event.to_dict() for event in self.event_cache]
            # Clear the cache
            self.event_cache.clear()

        logger.info(f"Returned and cleared {len(events)} cached events")
        return events

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status"""
        with self._lock:
            cache_size = len(self.event_cache)

        return {
            "cache_size": cache_size,
            "max_cache_size": self.max_cache_size,
            "supported_event_types": [t.value for t in EventType],
        }


# Global event manager instance
_event_manager = None


def get_event_manager() -> EventManager:
    """Get global event manager instance"""
    global _event_manager
    if _event_manager is None:
        _event_manager = EventManager()
    return _event_manager


def publish_event(event_type: EventType, data: Dict[str, Any]) -> str:
    """Publish event to cache"""
    return get_event_manager().publish_event(event_type, data)
