# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Event push routes - Cached version, supports fetch and clear mechanism
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from opencontext.managers.event_manager import EventType, get_event_manager
from opencontext.server.middleware.auth import auth_dependency
from opencontext.server.opencontext import OpenContext
from opencontext.server.utils import convert_resp, get_context_lab
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["events"])


class PublishEventRequest(BaseModel):
    event_type: str
    data: dict


@router.get("/api/events/fetch")
async def fetch_and_clear_events(_auth: str = auth_dependency):
    """
    Fetch and clear cached events - Core API

    Returns all cached events and clears the cache.
    Frontend should call this endpoint periodically to get new events.
    """
    try:
        event_manager = get_event_manager()
        events = event_manager.fetch_and_clear_events()

        return convert_resp(data={"events": events, "count": len(events), "message": "success"})

    except Exception as e:
        logger.exception(f"Failed to fetch events: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to fetch events: {str(e)}")


@router.get("/api/events/status")
async def get_event_status(
    opencontext: OpenContext = Depends(get_context_lab), _auth: str = auth_dependency
):
    """Get event cache status"""
    try:
        event_manager = get_event_manager()
        status = event_manager.get_cache_status()

        return convert_resp(data={"event_system_status": "active", **status})

    except Exception as e:
        logger.exception(f"Failed to get event status: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to get event status: {str(e)}")


@router.post("/api/events/publish")
async def publish_event(
    request: PublishEventRequest,
    opencontext: OpenContext = Depends(get_context_lab),
    _auth: str = auth_dependency,
):
    """
    Publish event (mainly for testing)
    """
    try:
        event_manager = get_event_manager()

        # Validate event type
        try:
            event_type = EventType(request.event_type)
        except ValueError:
            return convert_resp(
                code=400, status=400, message=f"Invalid event type: {request.event_type}"
            )

        # Publish event
        event_id = event_manager.publish_event(event_type=event_type, data=request.data)

        return convert_resp(
            data={
                "event_id": event_id,
                "event_type": request.event_type,
                "message": "Event published successfully",
            }
        )

    except Exception as e:
        logger.exception(f"Failed to publish event: {e}")
        return convert_resp(code=500, status=500, message=f"Failed to publish event: {str(e)}")
