#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import sys
import json
import logging

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
# -----------------

try:
    from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID

    logging.info("脚本启动，正在获取窗口列表...")

    window_list = CGWindowListCopyWindowInfo(
        kCGWindowListOptionAll, kCGNullWindowID)

    logging.info(f"成功获取到 {len(window_list)} 个原始窗口信息。")

    windows = []
    important_apps = ['zoom.us', 'Zoom', 'Microsoft PowerPoint', 'Notion', 'Slack',
                      'Microsoft Teams', 'MSTeams', 'Teams', 'Discord', 'Google Chrome',
                      'Microsoft Word', 'Microsoft Excel', 'Keynote', 'Figma',
                      'Sketch', 'Adobe Photoshop', 'Visual Studio Code', 'Cursor',
                      'Safari', 'Firefox', 'WeChat', 'Obsidian', 'Chrome']

    system_apps_to_skip = ['SystemUIServer', 'Dock', 'ControlCenter',
                           'WindowManager', 'MIRIX', 'Electron', 'Finder']

    app_windows = {}

    logging.info("开始遍历和过滤窗口...")
    for i, window in enumerate(window_list):
        window_num = window.get('kCGWindowNumber', 'N/A')
        app_name = window.get('kCGWindowOwnerName')
        window_title = window.get('kCGWindowName', '')

        logging.debug(
            f"--- 正在处理窗口 {i+1}/{len(window_list)}: App='{app_name}', Title='{window_title}', ID={window_num} ---")

        if not (app_name and window_num):
            logging.debug(f"跳过：缺少应用名称或窗口ID。")
            continue

        if app_name in system_apps_to_skip:
            logging.debug(f"跳过：属于系统应用 '{app_name}'。")
            continue

        bounds = window.get('kCGWindowBounds', {})
        width = bounds.get('Width', 0)
        height = bounds.get('Height', 0)

        if width < 50 or height < 50:
            logging.debug(f"跳过：窗口尺寸过小 ({width}x{height})。")
            continue

        layer = window.get('kCGWindowLayer', 0)
        if layer > 200:
            logging.debug(f"跳过：窗口层级过高 (Layer={layer})。")
            continue

        is_important = any(app.lower() in app_name.lower()
                           or app_name.lower() in app.lower() for app in important_apps)
        has_content = window_title.strip() != ''
        is_reasonable_size = (width > 300 and height > 200)

        should_include = (is_important or has_content or is_reasonable_size)

        if not should_include:
            logging.debug(
                f"跳过：不满足收录条件 (Important: {is_important}, HasContent: {has_content}, ReasonableSize: {is_reasonable_size})。")
            continue

        logging.debug(f"收录：满足条件，准备加入分组。")
        window_info = {
            'windowId': window['kCGWindowNumber'],
            'appName': app_name,
            'windowTitle': window_title,
            # <<<<<<<<<<<<<<<< THE FIX IS HERE <<<<<<<<<<<<<<<<
            'bounds': dict(bounds),
            'isOnScreen': window.get('kCGWindowIsOnscreen', False),
            'layer': layer,
            'isImportant': is_important,
            'area': width * height
        }

        if app_name not in app_windows:
            app_windows[app_name] = []
        app_windows[app_name].append(window_info)

    logging.info(f"过滤完成，共有 {len(app_windows)} 个应用的分组窗口。")
    logging.info("开始为每个应用筛选最佳窗口...")

    for app_name, app_window_list in app_windows.items():
        if not app_window_list:
            continue

        def window_score(w):
            return (
                w['isImportant'],
                w['area'],
                -w['layer'],
                bool(w['windowTitle'])
            )

        best_window = max(app_window_list, key=window_score)
        windows.append(best_window)
        logging.debug(
            f"应用 '{app_name}': 从 {len(app_window_list)} 个候选窗口中选择了 ID={best_window['windowId']} (Title: '{best_window['windowTitle']}')。")

    logging.info(f"筛选完成，最终选出 {len(windows)} 个代表性窗口。")

    windows.sort(key=lambda x: (not x['isImportant'], x['appName']))

    logging.info("排序完成，准备输出JSON结果。")
    print(json.dumps(windows, indent=2, ensure_ascii=False))

except ImportError as e:
    logging.error(f"导入错误: {e}. 这个脚本只能在 macOS 上运行。")
    print("[]")
except Exception as e:
    logging.exception("发生了一个意料之外的错误。")
    print("[]")
