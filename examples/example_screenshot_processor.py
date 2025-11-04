#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Example 1: Screenshot Processor - Extract content from screenshots
This example demonstrates how to use the ScreenshotProcessor to extract content from screenshots
without storing them in the database.

Usage:
    # Scan a directory for screenshots
    python example_screenshot_processor.py /path/to/screenshots/

    # Process specific files
    python example_screenshot_processor.py /path/to/img1.png /path/to/img2.png
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import opencontext modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from opencontext.context_processing.processor.screenshot_processor import ScreenshotProcessor
from opencontext.models.context import ContentFormat, ContextSource, RawContextProperties
from opencontext.utils.logging_utils import get_logger, setup_logging

# Initialize logging first
setup_logging({"level": "INFO", "log_path": None})  # Only console output for this example

logger = get_logger(__name__)

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def scan_directory_for_screenshots(directory_path: str, limit: int = None) -> list[str]:
    """
    Scan a directory for screenshot/image files.

    Args:
        directory_path: Path to the directory to scan
        limit: Maximum number of screenshots to return (None for all)

    Returns:
        List of screenshot file paths
    """
    screenshot_paths = []

    try:
        directory = Path(directory_path)
        if not directory.exists():
            print(f"Error: Directory does not exist: {directory_path}")
            return []

        if not directory.is_dir():
            print(f"Error: Not a directory: {directory_path}")
            return []

        # Scan for image files
        for file_path in sorted(directory.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
                screenshot_paths.append(str(file_path))
                if limit and len(screenshot_paths) >= limit:
                    break

        print(f"Found {len(screenshot_paths)} images")

    except Exception as e:
        print(f"Error scanning directory: {e}")

    return screenshot_paths


async def process_screenshots_example(screenshot_paths: list[str]):
    """
    Process screenshots and extract content without storing in database.

    Args:
        screenshot_paths: List of paths to screenshot files
    """
    print("=" * 80)
    print("Screenshot Processor - Extract Content from Screenshots")
    print("=" * 80)

    # Validate screenshot paths
    valid_paths = []
    for path in screenshot_paths:
        if os.path.exists(path):
            valid_paths.append(path)
        else:
            print(f"Warning: File not found: {path}")

    if len(valid_paths) == 0:
        print("\nNo valid screenshot files found.")
        return

    print(f"\nProcessing {len(valid_paths)} screenshots...\n")

    # Initialize the screenshot processor
    processor = ScreenshotProcessor()

    # Create RawContextProperties for each screenshot
    raw_contexts = []
    for i, screenshot_path in enumerate(valid_paths, 1):
        raw_context = RawContextProperties(
            source=ContextSource.SCREENSHOT,
            content_path=screenshot_path,
            content_format=ContentFormat.IMAGE,
            create_time=datetime.now(),
            content_text="",
        )
        raw_contexts.append(raw_context)

    # Process screenshots in batch (this will call the Vision LLM)
    try:
        processed_contexts = await processor.batch_process(raw_contexts)

        print("=" * 80)
        print("Extraction Results")
        print("=" * 80)

        # The processor stores results in _processed_cache
        for processed_context in processed_contexts:
            print(f"Title: {processed_context.extracted_data.title}")
            print(f"Summary: {processed_context.extracted_data.summary}")
            print(f"Keywords: {', '.join(processed_context.extracted_data.keywords)}")
            print(f"Type: {processed_context.extracted_data.context_type}")
            print(f"Importance: {processed_context.extracted_data.importance}/10")
            print(f"Confidence: {processed_context.extracted_data.confidence}/10")

            if processed_context.extracted_data.entities:
                print(f"Entities: {processed_context.extracted_data.entities}")

            print(f"Event Time: {processed_context.properties.event_time}")
            print("-" * 80)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point for the example."""
    screenshot_paths = []

    if len(sys.argv) > 1:
        input_path = sys.argv[1]

        # Check if it's a directory or file
        if os.path.isdir(input_path):
            # Scan directory for screenshots
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
            screenshot_paths = scan_directory_for_screenshots(input_path, limit=limit)
        else:
            # Treat as individual file paths
            screenshot_paths = sys.argv[1:]
    else:
        print("Usage:")
        print("  python example_screenshot_processor.py /path/to/screenshots/")
        print("  python example_screenshot_processor.py /path/to/screenshots/ 5")
        print("  python example_screenshot_processor.py img1.png img2.png img3.png")
        return

    if not screenshot_paths:
        print("No valid screenshot files found.")
        return

    # Run the async function
    asyncio.run(process_screenshots_example(screenshot_paths))


if __name__ == "__main__":
    main()
