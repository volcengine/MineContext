# -*- coding: utf-8 -*-

"""
PyInstaller runtime hook for OpenContext
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(__file__), relative_path)


if hasattr(sys, "_MEIPASS"):
    os.environ["CONTEXT_LAB_BUNDLE_DIR"] = sys._MEIPASS
    os.environ["CONTEXT_LAB_STATIC_DIR"] = os.path.join(
        sys._MEIPASS, "opencontext", "web", "static"
    )
    os.environ["CONTEXT_LAB_TEMPLATES_DIR"] = os.path.join(
        sys._MEIPASS, "opencontext", "web", "templates"
    )
    os.environ["CONTEXT_LAB_CONFIG_DIR"] = os.path.join(sys._MEIPASS, "config")
