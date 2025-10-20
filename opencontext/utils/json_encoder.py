# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
OpenContext module: json_encoder
"""

import datetime
import json
from dataclasses import asdict, is_dataclass

from pydantic import BaseModel


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)
