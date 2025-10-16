#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Node Base Class
Base class definition for all processing nodes
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from opencontext.utils.logging_utils import get_logger

from ..core.state import WorkflowState
from ..core.streaming import StreamingManager
from ..models.enums import EventType, NodeType, WorkflowStage
from ..models.events import StreamEvent


class BaseNode(ABC):
    """Node base class"""

    def __init__(self, node_type: NodeType, streaming_manager: Optional[StreamingManager] = None):
        self.node_type = node_type
        self.streaming_manager = streaming_manager
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def process(self, state: WorkflowState) -> WorkflowState:
        pass

    async def execute(self, state: WorkflowState) -> WorkflowState:
        start_time = datetime.now()
        try:
            state = await self.process(state)
            duration = (datetime.now() - start_time).total_seconds()
            return state
        except Exception as e:
            self.logger.exception(f"Node execution failed: {e}")
            await self.streaming_manager.emit(
                StreamEvent(
                    type=EventType.FAIL,
                    stage=state.stage,
                    content=f"{self.node_type.value} node processing failed",
                )
            )
            state.add_error(f"{self.node_type.value}: {str(e)}")
            raise

    async def sleep(self, seconds: float):
        """Asynchronous sleep (for simulating processing delays)"""
        await asyncio.sleep(seconds)
