# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Datetime helpers for normalizing mixed timestamp inputs.

MineContext currently stores a large amount of legacy timestamps as naive local
datetime strings, while some newer inputs arrive as ISO8601 strings with an
explicit offset or ``Z`` suffix. The rest of the codebase still compares
against naive ``datetime.now()`` values in many places, so the safest
compatibility strategy is to normalize all incoming values to local naive
datetimes before they enter comparison-heavy logic.
"""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo


def get_local_timezone() -> tzinfo:
    """Return the current local timezone, falling back to UTC."""
    return datetime.now().astimezone().tzinfo or timezone.utc


def ensure_local_naive(value: datetime) -> datetime:
    """Normalize a datetime to a local naive value for safe comparisons."""
    if value.tzinfo is None:
        return value
    return value.astimezone(get_local_timezone()).replace(tzinfo=None)


def parse_local_datetime(value: str | datetime) -> datetime:
    """Parse a datetime-like value and normalize it to a local naive datetime."""
    if isinstance(value, datetime):
        return ensure_local_naive(value)

    if not isinstance(value, str):
        raise TypeError(f"Unsupported datetime value type: {type(value)!r}")

    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    return ensure_local_naive(datetime.fromisoformat(text))


def now_local() -> datetime:
    """Return the current local time as a naive datetime."""
    return ensure_local_naive(datetime.now().astimezone())
