#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import sys
import json

args = json.loads(sys.argv[1])
app_name = args.get("appName")
old_window_id = args.get("windowId")
try:
    from Quartz import CGWindowListCreateImage, CGRectNull, kCGWindowListOptionIncludingWindow, kCGWindowImageBoundsIgnoreFraming, kCGWindowImageShouldBeOpaque, CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID
    from CoreFoundation import kCFNull
    import base64

    # Get fresh window list and find the app by name
    window_list = CGWindowListCopyWindowInfo(
        kCGWindowListOptionAll, kCGNullWindowID)
    target_window = None
    window_id = None

    # Look for the app by name in current window list and find the LARGEST window
    candidate_windows = []
    all_matching_windows = []  # Track ALL windows for this app for debugging
    all_windows_debug = []  # Track ALL windows for debugging

    for window in window_list:
        owner_name = window.get('kCGWindowOwnerName', '').lower()
        window_name = window.get('kCGWindowName', '').lower()
        bounds = window.get('kCGWindowBounds', {})
        width = bounds.get('Width', 0)
        height = bounds.get('Height', 0)

        # Track all windows for debugging
        all_windows_debug.append(
            (window.get('kCGWindowNumber'), width, height, owner_name, window_name))

        # More flexible matching for MSTeams and similar apps
        app_keywords = [app_name.lower()]
        if app_name.lower() == 'msteams' or app_name.lower() == 'microsoft teams':
            app_keywords.extend(
                ['microsoft teams', 'teams', 'com.microsoft.teams', 'msteams', 'com.microsoft.teams2'])
        elif app_name.lower() == 'notion':
            app_keywords.extend(['notion', 'com.notion.notion'])
        elif app_name.lower() == 'microsoft powerpoint':
            app_keywords.extend(['powerpoint', 'com.microsoft.powerpoint'])

        matches = False
        for keyword in app_keywords:
            if (keyword in owner_name or keyword in window_name):
                matches = True
                break

        if matches:
            all_matching_windows.append(
                (window.get('kCGWindowNumber'), width, height, owner_name, window_name))

            # Skip windows with very small bounds (likely not main windows)
            if width > 200 and height > 200:  # Increased minimum size
                # Store window and area
                candidate_windows.append((window, width * height))
                print(
                    f"DEBUG: Found candidate window {window.get('kCGWindowNumber')} for {app_name}: {width}x{height}", file=sys.stderr)

    # Debug: Show ALL matching windows regardless of size
    print(f"DEBUG: All windows found for {app_name}:", file=sys.stderr)
    for wid, w, h, owner, title in all_matching_windows:
        print(
            f"  Window {wid}: {w}x{h} owner='{owner}' title='{title}'", file=sys.stderr)

    # If no matches found, show some examples of available windows
    if not all_matching_windows:
        print(
            f"DEBUG: No matches for '{app_name}'. Sample of available windows:", file=sys.stderr)
        for wid, w, h, owner, title in all_windows_debug[:10]:  # Show first 10
            if w > 50 and h > 50:  # Only show reasonable sized windows
                print(
                    f"  Available: {wid}: {w}x{h} owner='{owner}' title='{title}'", file=sys.stderr)

    # Sort by area (largest first) but prefer non-webview windows
    if candidate_windows:
        # Sort with custom logic: prefer non-webview windows, then by area
        def window_priority(item):
            window, area = item
            owner = window.get('kCGWindowOwnerName', '').lower()
            # Penalize webview windows
            is_webview = 'webview' in owner
            # Return tuple: (webview penalty, negative area for descending sort)
            return (is_webview, -area)

        candidate_windows.sort(key=window_priority)
        target_window = candidate_windows[0][0]
        window_id = target_window.get('kCGWindowNumber')
        bounds = target_window.get('kCGWindowBounds', {})
        owner_name = target_window.get('kCGWindowOwnerName', '')
        print(
            f"DEBUG: Selected window ID {window_id} for {app_name} (was {old_window_id}): {bounds.get('Width', 0)}x{bounds.get('Height', 0)}, owner='{owner_name}'", file=sys.stderr)

    if not target_window:
        # If no large windows found, pick the largest available window regardless of size
        print(f"DEBUG: No large windows found, selecting largest available window", file=sys.stderr)
        if all_matching_windows:
            # Sort by area but prefer non-webview windows
            def fallback_priority(window_info):
                wid, w, h, owner, title = window_info
                area = w * h
                is_webview = 'webview' in owner.lower()
                # Return tuple: (webview penalty, negative area for descending sort)
                return (is_webview, -area)

            all_matching_windows.sort(key=fallback_priority)
            wid, w, h, owner, title = all_matching_windows[0]

            # Find the actual window object
            for window in window_list:
                if window.get('kCGWindowNumber') == wid:
                    target_window = window
                    window_id = wid
                    print(
                        f"DEBUG: Selected window ID {window_id} for {app_name}: {w}x{h}, owner='{owner}'", file=sys.stderr)
                    break

    if not target_window:
        print(
            f"ERROR: No suitable window found for {app_name} in current window list")
        sys.exit(1)

    # Check window properties that might affect capture
    window_layer = target_window.get('kCGWindowLayer', 'unknown')
    window_alpha = target_window.get('kCGWindowAlpha', 'unknown')
    window_bounds = target_window.get('kCGWindowBounds', {})

    print(
        f"DEBUG: Window layer: {window_layer}, alpha: {window_alpha}, bounds: {window_bounds}", file=sys.stderr)

    # Try different capture options
    capture_options = [
        kCGWindowImageBoundsIgnoreFraming | kCGWindowImageShouldBeOpaque,
        kCGWindowImageBoundsIgnoreFraming,
        kCGWindowImageShouldBeOpaque,
        0  # No special options
    ]

    image = None
    for i, options in enumerate(capture_options):
        print(f"DEBUG: Trying capture option {i+1}/4", file=sys.stderr)
        image = CGWindowListCreateImage(
            CGRectNull,
            kCGWindowListOptionIncludingWindow,
            window_id,
            options
        )
        if image:
            print(
                f"DEBUG: Capture succeeded with option {i+1}", file=sys.stderr)
            break

    if image:
        # Convert to PNG data
        from Quartz import CGImageDestinationCreateWithData, CGImageDestinationAddImage, CGImageDestinationFinalize
        from CoreFoundation import CFDataCreateMutable, kCFAllocatorDefault

        data = CFDataCreateMutable(kCFAllocatorDefault, 0)
        dest = CGImageDestinationCreateWithData(data, 'public.png', 1, None)
        CGImageDestinationAddImage(dest, image, None)
        CGImageDestinationFinalize(dest)

        # Convert to base64 and print
        import base64
        png_data = bytes(data)
        print(base64.b64encode(png_data).decode('utf-8'))
    else:
        # If direct window capture fails, try screen capture with cropping
        print("DEBUG: Direct window capture failed, trying screen capture with cropping", file=sys.stderr)
        try:
            from Quartz import CGDisplayCreateImage, CGMainDisplayID, CGImageCreateWithImageInRect
            from CoreGraphics import CGRectMake

            # Get the window bounds
            bounds = target_window.get('kCGWindowBounds', {})
            x = bounds.get('X', 0)
            y = bounds.get('Y', 0)
            width = bounds.get('Width', 0)
            height = bounds.get('Height', 0)

            if width > 0 and height > 0:
                # Capture entire screen
                screen_image = CGDisplayCreateImage(CGMainDisplayID())
                if screen_image:
                    # Crop to window bounds
                    crop_rect = CGRectMake(x, y, width, height)
                    cropped_image = CGImageCreateWithImageInRect(
                        screen_image, crop_rect)

                    if cropped_image:
                        # Convert to PNG
                        data = CFDataCreateMutable(kCFAllocatorDefault, 0)
                        dest = CGImageDestinationCreateWithData(
                            data, 'public.png', 1, None)
                        CGImageDestinationAddImage(dest, cropped_image, None)
                        CGImageDestinationFinalize(dest)

                        png_data = bytes(data)
                        print(base64.b64encode(png_data).decode('utf-8'))
                        print("DEBUG: Screen capture + crop succeeded",
                              file=sys.stderr)
                    else:
                        print("ERROR: Failed to crop screen image")
                else:
                    print("ERROR: Failed to capture screen")
            else:
                print("ERROR: Invalid window bounds for cropping")
        except Exception as crop_error:
            print(f"ERROR: Screen capture fallback failed: {crop_error}")
            print("ERROR: Failed to create image with all capture options")

except Exception as e:
    print(f"ERROR: {e}")
