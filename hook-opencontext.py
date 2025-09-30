# -*- coding: utf-8 -*-

"""
PyInstaller runtime hook for OpenContext
确保运行时能正确找到资源文件
"""

import sys
import os
from pathlib import Path

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # 开发环境
        return os.path.join(os.path.dirname(__file__), relative_path)

# 设置环境变量，让应用知道资源路径
if hasattr(sys, '_MEIPASS'):
    os.environ['CONTEXT_LAB_BUNDLE_DIR'] = sys._MEIPASS
    os.environ['CONTEXT_LAB_STATIC_DIR'] = os.path.join(sys._MEIPASS, 'opencontext', 'web', 'static')
    os.environ['CONTEXT_LAB_TEMPLATES_DIR'] = os.path.join(sys._MEIPASS, 'opencontext', 'web', 'templates')
    os.environ['CONTEXT_LAB_CONFIG_DIR'] = os.path.join(sys._MEIPASS, 'config')