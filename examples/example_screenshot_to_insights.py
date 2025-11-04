#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Example: Screenshot to Insights Pipeline
This example demonstrates how to process screenshots and generate comprehensive insights
including activities, todos, tips, and reports - all without writing to the database.

Usage:
    # Process screenshots from a directory
    python example_screenshot_to_insights.py /path/to/screenshots/

    # Process specific files
    python example_screenshot_to_insights.py /path/to/img1.png /path/to/img2.png
"""

import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path to import opencontext modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from opencontext.config.global_config import get_prompt_group
from opencontext.context_processing.processor.screenshot_processor import ScreenshotProcessor
from opencontext.llm.global_vlm_client import generate_with_messages, generate_with_messages_async
from opencontext.models.context import (
    ContentFormat,
    ContextSource,
    ProcessedContext,
    RawContextProperties,
)
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.utils.logging_utils import get_logger, setup_logging

# Initialize logging
setup_logging({"level": "INFO", "log_path": None})
logger = get_logger(__name__)

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def scan_directory_for_screenshots(directory_path: str, limit: int = None) -> List[str]:
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


async def process_screenshots(screenshot_paths: List[str]) -> List[ProcessedContext]:
    """
    Process screenshots and extract content.

    Args:
        screenshot_paths: List of paths to screenshot files

    Returns:
        List of ProcessedContext objects
    """
    print("\n" + "=" * 80)
    print("STEP 1: Processing Screenshots")
    print("=" * 80)

    # Initialize the screenshot processor
    processor = ScreenshotProcessor()

    # Create RawContextProperties for each screenshot
    raw_contexts = []
    for screenshot_path in screenshot_paths:
        raw_context = RawContextProperties(
            source=ContextSource.SCREENSHOT,
            content_path=screenshot_path,
            content_format=ContentFormat.IMAGE,
            create_time=datetime.datetime.now(),
            content_text="",
        )
        raw_contexts.append(raw_context)

    print(f"Processing {len(raw_contexts)} screenshots...\n")

    # Process screenshots (this calls VLM internally)
    try:
        processed_contexts = await processor.batch_process(raw_contexts)
        processor.shutdown(graceful=True)

        print(f"\nSuccessfully processed {len(processed_contexts)} contexts\n")
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
        return processed_contexts

    except Exception as e:
        print(f"Error processing screenshots: {e}")
        import traceback

        traceback.print_exc()
        processor.shutdown(graceful=True)
        return []


async def generate_activity(
    processed_contexts: List[ProcessedContext], start_time: int, end_time: int
) -> Optional[Dict[str, Any]]:
    """
    Generate activity summary from processed contexts (without database writes).

    Args:
        processed_contexts: List of processed contexts
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        Activity summary dictionary
    """
    print("\n" + "=" * 80)
    print("STEP 2: Generating Activity Summary")
    print("=" * 80)

    if not processed_contexts:
        print("No contexts to generate activity from")
        return None

    try:
        # Get prompt template
        prompt_group = get_prompt_group("generation.realtime_activity_monitor")
        system_prompt = prompt_group["system"]
        user_prompt_template = prompt_group["user"]

        # Prepare context data grouped by type
        context_data = {}
        for context in processed_contexts:
            context_type = context.extracted_data.context_type.value
            if context_type not in context_data:
                context_data[context_type] = []
            context_data[context_type].append(context.get_llm_context_string())

        # Format time information
        start_time_str = datetime.datetime.fromtimestamp(start_time).strftime("%H:%M")
        end_time_str = datetime.datetime.fromtimestamp(end_time).strftime("%H:%M")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build user prompt
        user_prompt = user_prompt_template.format(
            current_time=current_time,
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            context_data=json.dumps(context_data, ensure_ascii=False, indent=2),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print("Calling LLM to generate activity summary...")
        response = generate_with_messages(messages)

        # Parse response
        activity_result = parse_json_from_response(response)

        # Normalize category distribution
        category_dist = activity_result.get("category_distribution", {})
        if category_dist:
            total = sum(category_dist.values())
            if total > 0:
                category_dist = {k: round(v / total, 2) for k, v in category_dist.items()}

        activity = {
            "title": activity_result.get("title", "Recent Activities"),
            "description": activity_result.get(
                "description", "Detected various user activities."
            ),
            "category_distribution": category_dist,
            "extracted_insights": activity_result.get(
                "extracted_insights",
                {
                    "potential_todos": [],
                    "tip_suggestions": [],
                    "key_entities": [],
                    "focus_areas": [],
                    "work_patterns": {},
                },
            ),
        }

        print(f"\n✓ Activity Generated: {activity['title']}")
        print(f"  Description: {activity['description']}")
        print(f"  Categories: {', '.join(category_dist.keys())}")
        print(
            f"  Insights: {len(activity['extracted_insights'].get('potential_todos', []))} potential todos, "
            f"{len(activity['extracted_insights'].get('key_entities', []))} key entities\n"
        )

        return activity

    except Exception as e:
        logger.exception(f"Failed to generate activity: {e}")
        return None


async def generate_todos(
    processed_contexts: List[ProcessedContext],
    activity_insights: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate todo tasks from contexts and activity insights (without database writes).

    Args:
        processed_contexts: List of processed contexts
        activity_insights: Activity insights dictionary

    Returns:
        List of todo task dictionaries
    """
    print("\n" + "=" * 80)
    print("STEP 3: Generating Todo Tasks")
    print("=" * 80)

    if not processed_contexts:
        print("No contexts to generate todos from")
        return []

    try:
        # Get prompt template
        prompt_group = get_prompt_group("generation.todo_extraction")
        system_prompt = prompt_group["system"]
        user_prompt_template = prompt_group["user"]

        # Prepare context data
        context_data = [ctx.get_llm_context_string() for ctx in processed_contexts]

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build user prompt
        user_prompt = user_prompt_template.format(
            current_time=current_time,
            historical_todos="[]",  # No historical todos in this example
            potential_todos=json.dumps(
                activity_insights.get("potential_todos", []), ensure_ascii=False, indent=2
            )
            if activity_insights
            else "[]",
            context_data=json.dumps(context_data, ensure_ascii=False, indent=2),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print("Calling LLM to extract todo tasks...")
        response = generate_with_messages(messages)

        # Parse response
        tasks = parse_json_from_response(response)

        # Post-process tasks
        processed_tasks = []
        for task in tasks:
            if not task.get("description", "").strip():
                continue

            processed_task = {
                "title": task.get("title", "Untitled Task"),
                "description": task.get("description", ""),
                "category": task.get("category", "General Task"),
                "priority": task.get("priority", "Medium Priority"),
                "due_date": task.get("due_date", ""),
                "due_time": task.get("due_time", ""),
                "reason": task.get("reason", ""),
            }
            processed_tasks.append(processed_task)

        print(f"\n✓ Generated {len(processed_tasks)} todo tasks:")
        for i, task in enumerate(processed_tasks, 1):
            print(f"  {i}. [{task['priority']}] {task['title']}")
            print(f"     {task['description'][:80]}...")

        print()
        return processed_tasks

    except Exception as e:
        logger.exception(f"Failed to generate todos: {e}")
        return []


async def generate_tips(
    processed_contexts: List[ProcessedContext],
    activity_patterns: Dict[str, Any],
    start_time: int,
    end_time: int,
) -> Optional[str]:
    """
    Generate smart tips from contexts and activity patterns (without database writes).

    Args:
        processed_contexts: List of processed contexts
        activity_patterns: Activity pattern analysis
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        Tips content string
    """
    print("\n" + "=" * 80)
    print("STEP 4: Generating Smart Tips")
    print("=" * 80)

    if not processed_contexts:
        print("No contexts to generate tips from")
        return None

    try:
        # Get prompt template
        prompt_group = get_prompt_group("generation.smart_tip_generation")
        system_prompt = prompt_group["system"]
        user_prompt_template = prompt_group["user"]

        # Prepare context data
        context_data = [ctx.get_llm_context_string() for ctx in processed_contexts]

        # Format time information
        start_time_str = datetime.datetime.fromtimestamp(start_time).strftime("%H:%M:%S")
        end_time_str = datetime.datetime.fromtimestamp(end_time).strftime("%H:%M:%S")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build user prompt
        user_prompt = user_prompt_template.format(
            current_time=current_time,
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            context_data=json.dumps(context_data, ensure_ascii=False, indent=2),
            activity_patterns_info=json.dumps(activity_patterns, ensure_ascii=False, indent=2)
            if activity_patterns
            else "{}",
            recent_tips_info="[]",  # No recent tips in this example
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print("Calling LLM to generate smart tips...")
        tip_content = generate_with_messages(messages)

        if tip_content and len(tip_content.strip()) >= 10:
            print(f"\n✓ Tips Generated:")
            print(f"  {tip_content[:150]}...\n")
            return tip_content
        else:
            print("No valuable tip content was generated\n")
            return None

    except Exception as e:
        logger.exception(f"Failed to generate tips: {e}")
        return None


async def generate_report(
    processed_contexts: List[ProcessedContext],
    start_time: int,
    end_time: int,
    tips: Optional[str] = None,
    todos: List[Dict[str, Any]] = None,
    activity: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Generate comprehensive report from contexts (without database writes).

    Args:
        processed_contexts: List of processed contexts
        start_time: Start timestamp
        end_time: End timestamp
        tips: Generated tips content
        todos: Generated todo tasks
        activity: Generated activity summary

    Returns:
        Report content string
    """
    print("\n" + "=" * 80)
    print("STEP 5: Generating Comprehensive Report")
    print("=" * 80)

    if not processed_contexts:
        print("No contexts to generate report from")
        return None

    try:
        # Get prompt template
        prompt_group = get_prompt_group("generation.generation_report")
        system_prompt = prompt_group["system"]
        user_prompt_template = prompt_group["user"]

        # Prepare context data
        contexts = [ctx.get_llm_context_string() for ctx in processed_contexts]

        # Format time information
        start_time_str = datetime.datetime.fromtimestamp(start_time).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        end_time_str = datetime.datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")

        # Prepare tips data
        tips_list = []
        if tips:
            tips_list.append({
                "id": "generated",
                "content": tips,
                "created_at": datetime.datetime.now().isoformat(),
            })

        # Prepare todos data
        todos_list = []
        if todos:
            for todo in todos:
                todos_list.append({
                    "id": "generated",
                    "content": todo.get("description", ""),
                    "status": 0,
                    "status_label": "pending",
                    "urgency": todo.get("priority", "Medium Priority"),
                    "assignee": todo.get("title", ""),
                    "reason": todo.get("reason", ""),
                    "created_at": datetime.datetime.now().isoformat(),
                })

        # Prepare activities data
        activities_list = []
        if activity:
            activities_list.append({
                "id": "generated",
                "title": activity.get("title", ""),
                "content": activity.get("description", ""),
                "metadata": {
                    "category_distribution": activity.get("category_distribution", {}),
                    "extracted_insights": activity.get("extracted_insights", {}),
                },
                "start_time": datetime.datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.datetime.fromtimestamp(end_time).isoformat(),
            })

        # Build user prompt
        user_prompt = user_prompt_template.format(
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            start_timestamp=start_time,
            end_timestamp=end_time,
            contexts=json.dumps(contexts, ensure_ascii=False, indent=2),
            tips=json.dumps(tips_list, ensure_ascii=False, indent=2),
            todos=json.dumps(todos_list, ensure_ascii=False, indent=2),
            activities=json.dumps(activities_list, ensure_ascii=False, indent=2),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print("Calling LLM to generate comprehensive report...")
        report = await generate_with_messages_async(messages)

        if report:
            print(f"\n✓ Report Generated ({len(report)} characters)")
            print(f"  Preview: {report[:200]}...\n")
            return report
        else:
            print("Failed to generate report\n")
            return None

    except Exception as e:
        logger.exception(f"Failed to generate report: {e}")
        return None


def print_final_summary(
    activity: Optional[Dict[str, Any]],
    todos: List[Dict[str, Any]],
    tips: Optional[str],
    report: Optional[str],
):
    """
    Print a final summary of all generated insights.

    Args:
        activity: Activity summary
        todos: List of todo tasks
        tips: Tips content
        report: Report content
    """
    print("\n" + "=" * 80)
    print("FINAL SUMMARY: Generated Insights")
    print("=" * 80)

    print("\n📊 ACTIVITY SUMMARY")
    print("-" * 80)
    if activity:
        print(f"Title: {activity['title']}")
        print(f"Description: {activity['description']}")
        print(f"\nCategory Distribution:")
        for category, percentage in activity.get("category_distribution", {}).items():
            print(f"  - {category}: {percentage * 100:.0f}%")
        print(f"\nKey Insights:")
        insights = activity.get("extracted_insights", {})
        print(f"  - Potential Todos: {len(insights.get('potential_todos', []))}")
        print(f"  - Key Entities: {len(insights.get('key_entities', []))}")
        print(f"  - Focus Areas: {len(insights.get('focus_areas', []))}")
    else:
        print("No activity generated")

    print("\n✅ TODO TASKS")
    print("-" * 80)
    if todos:
        for i, task in enumerate(todos, 1):
            print(f"\n{i}. {task['title']}")
            print(f"   Priority: {task['priority']}")
            print(f"   Description: {task['description']}")
            if task.get("reason"):
                print(f"   Reason: {task['reason']}")
    else:
        print("No todos generated")

    print("\n💡 SMART TIPS")
    print("-" * 80)
    if tips:
        print(tips)
    else:
        print("No tips generated")

    print("\n📝 COMPREHENSIVE REPORT")
    print("-" * 80)
    if report:
        print(report)
    else:
        print("No report generated")

    print("\n" + "=" * 80)
    print("Processing Complete!")
    print("=" * 80)


async def main_pipeline(screenshot_paths: List[str]):
    """
    Main processing pipeline.

    Args:
        screenshot_paths: List of screenshot file paths
    """
    if not screenshot_paths:
        print("No screenshot files provided")
        return

    # Define time range for analysis
    end_time = int(datetime.datetime.now().timestamp())
    start_time = end_time - 3600  # Last hour

    # Step 1: Process screenshots
    processed_contexts = await process_screenshots(screenshot_paths)
    if not processed_contexts:
        print("Failed to process screenshots. Exiting.")
        return

    # Step 2: Generate activity
    activity = await generate_activity(processed_contexts, start_time, end_time)

    # Step 3: Generate todos
    activity_insights = activity.get("extracted_insights", {}) if activity else {}
    todos = await generate_todos(processed_contexts, activity_insights)

    # Step 4: Generate tips
    activity_patterns = activity_insights.get("work_patterns", {}) if activity_insights else {}
    tips = await generate_tips(processed_contexts, activity_patterns, start_time, end_time)

    # Step 5: Generate report (must be last, as it uses all previous results)
    report = await generate_report(processed_contexts, start_time, end_time, tips, todos, activity)

    # Print final summary
    print_final_summary(activity, todos, tips, report)


def main():
    """Main entry point."""
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
        print("  python example_screenshot_to_insights.py /path/to/screenshots/")
        print("  python example_screenshot_to_insights.py /path/to/screenshots/ 5")
        print("  python example_screenshot_to_insights.py img1.png img2.png img3.png")
        return

    if not screenshot_paths:
        print("No valid screenshot files found.")
        return

    # Validate screenshot paths
    valid_paths = [path for path in screenshot_paths if os.path.exists(path)]
    if not valid_paths:
        print("No valid screenshot files found.")
        return

    print(f"\nStarting insights pipeline with {len(valid_paths)} screenshots...")

    # Run the async pipeline
    asyncio.run(main_pipeline(valid_paths))


if __name__ == "__main__":
    main()
