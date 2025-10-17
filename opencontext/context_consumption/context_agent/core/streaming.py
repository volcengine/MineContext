#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Streaming Manager
Manages event streams and streaming content output.
"""

import asyncio
from typing import AsyncIterator, Optional

from ..models.enums import WorkflowStage
from ..models.events import StreamEvent


class StreamingManager:
    """Streaming manager."""

    def __init__(self):
        self.event_queue: Optional[asyncio.Queue] = None

    async def _ensure_queue(self):
        """Ensure the queue is initialized in the current event loop."""
        if self.event_queue is None:
            self.event_queue = asyncio.Queue(maxsize=1000)

    async def emit(self, event: StreamEvent):
        """Emit an event - a unified interface to handle all events."""
        await self._ensure_queue()
        await self.event_queue.put(event)

    async def stream(self) -> AsyncIterator[StreamEvent]:
        """Stream events."""
        await self._ensure_queue()
        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                yield event
                if event.stage in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                    print("Exiting event capture")
                    break
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
