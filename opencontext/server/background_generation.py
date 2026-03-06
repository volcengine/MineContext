#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Background Generation Manager
Manages background AI generation tasks so they continue even if the SSE
HTTP connection is dropped by the client (e.g., user switches conversations).

Design:
  - Each generation is an asyncio.Task running independently of the SSE connection.
  - The task writes chunks to the DB AND to an asyncio.Queue consumed by the SSE generator.
  - If the SSE connection drops, the Queue simply accumulates (unlimited) and is garbage-
    collected when the task finishes. The task itself keeps running.
  - A global Semaphore(3) limits concurrent background generations.
"""

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional

from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Sentinel object — placed in queue to signal that generation has finished
_DONE = object()

# Maximum number of concurrent background generation tasks
MAX_CONCURRENT = 3


class BackgroundGenerationManager:
    """
    Singleton manager for background AI generation tasks.

    Usage::

        mgr = BackgroundGenerationManager.get_instance()

        # Start a task; returns an asyncio.Queue the SSE generator can read from.
        queue = await mgr.submit_task(
            session_id="...",
            conversation_id=42,
            coro_factory=lambda q: my_generation_coro(q, ...),
        )

        # SSE generator reads from the queue until it receives None (done sentinel).
        while True:
            item = await queue.get()
            if item is _DONE:
                break
            yield ...

        # Hard-cancel a running task (e.g., on delete).
        await mgr.cancel_task(session_id="...")
    """

    _instance: Optional["BackgroundGenerationManager"] = None

    def __new__(cls) -> "BackgroundGenerationManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _ensure_ready(self) -> None:
        """Lazy-initialize asyncio primitives (must run inside an event loop)."""
        if self._ready:
            return
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._tasks: Dict[str, asyncio.Task] = {}  # session_id → Task
        self._queues: Dict[str, asyncio.Queue] = {}  # session_id → Queue
        self._conv_map: Dict[str, int] = {}  # session_id → conversation_id
        self._ready = True

    @classmethod
    def get_instance(cls) -> "BackgroundGenerationManager":
        inst = cls()
        inst._ensure_ready()
        return inst

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit_task(
        self,
        session_id: str,
        conversation_id: int,
        coro_factory: Callable[["asyncio.Queue[Any]"], Coroutine],
    ) -> "asyncio.Queue[Any]":
        """
        Submit a generation coroutine as a background task.

        ``coro_factory`` is called with the per-task Queue as its sole argument and
        must return a coroutine.  The coroutine should:
          - Put event dicts into the queue while generating.
          - Put the ``DONE_SENTINEL`` (imported from this module) when finished.
          - Handle ``asyncio.CancelledError`` gracefully (mark message cancelled in DB).

        Returns the Queue so the caller (SSE generator) can read events from it.
        Raises ``RuntimeError`` with status 429 if the semaphore limit is reached.
        """
        self._ensure_ready()

        # Check semaphore without blocking — return 429 if all slots are taken
        if not self._semaphore._value:  # type: ignore[attr-defined]
            raise RuntimeError(
                f"Maximum concurrent generation limit ({MAX_CONCURRENT}) reached. "
                "Please wait for an existing generation to complete."
            )

        # Cancel any existing task for the same session
        await self._cancel_session(session_id)

        queue: asyncio.Queue = asyncio.Queue()
        self._queues[session_id] = queue
        self._conv_map[session_id] = conversation_id

        async def _run() -> None:
            async with self._semaphore:
                try:
                    logger.info(
                        f"Background generation started: session={session_id}, conv={conversation_id}"
                    )
                    await coro_factory(queue)
                except asyncio.CancelledError:
                    logger.info(f"Background generation cancelled: session={session_id}")
                    # Signal SSE consumer to stop
                    await _safe_put(queue, _DONE)
                    # Re-raise so asyncio knows the task was cancelled
                    raise
                except Exception as exc:
                    logger.exception(f"Background generation error: session={session_id}: {exc}")
                    await _safe_put(queue, {"type": "error", "content": str(exc)})
                    await _safe_put(queue, _DONE)
                finally:
                    self._cleanup(session_id)
                    logger.info(f"Background generation finished: session={session_id}")

        task = asyncio.create_task(_run(), name=f"gen-{session_id}")
        self._tasks[session_id] = task
        return queue

    async def cancel_task(self, session_id: str) -> None:
        """Cancel a running background generation task and wait for it to stop."""
        await self._cancel_session(session_id)

    def is_running(self, session_id: str) -> bool:
        """Return True if the given session has an active (not-done) task."""
        self._ensure_ready()
        task = self._tasks.get(session_id)
        return task is not None and not task.done()

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Return a list of {session_id, conversation_id} for all running tasks."""
        self._ensure_ready()
        return [
            {"session_id": sid, "conversation_id": self._conv_map.get(sid)}
            for sid, task in list(self._tasks.items())
            if not task.done()
        ]

    def find_session_by_conversation(self, conversation_id: int) -> Optional[str]:
        """Return the session_id for a running task associated with *conversation_id*, or None."""
        self._ensure_ready()
        for sid, cid in list(self._conv_map.items()):
            if cid == conversation_id and self.is_running(sid):
                return sid
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _cancel_session(self, session_id: str) -> None:
        self._ensure_ready()
        task = self._tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        self._cleanup(session_id)

    def _cleanup(self, session_id: str) -> None:
        self._tasks.pop(session_id, None)
        self._queues.pop(session_id, None)
        self._conv_map.pop(session_id, None)


async def _safe_put(queue: asyncio.Queue, item: Any) -> None:
    """Put an item in the queue without blocking (best-effort)."""
    try:
        queue.put_nowait(item)
    except Exception:
        pass


# Module-level sentinel export so the SSE generator can import it
DONE_SENTINEL = _DONE


# Convenience accessor
def get_background_manager() -> BackgroundGenerationManager:
    """Return the ready singleton instance."""
    return BackgroundGenerationManager.get_instance()
