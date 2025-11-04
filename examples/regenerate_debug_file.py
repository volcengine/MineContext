#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Test script to regenerate content from a debug file and compare outputs.

Usage:
    python regenerate_debug_file.py --debug-file <path_to_debug_json>
    python regenerate_debug_file.py --debug-file debug/generation/activity/2025-10-20_18-01-26.json
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from opencontext.llm.global_vlm_client import generate_with_messages_async
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


def load_debug_file(filepath: str) -> Dict[str, Any]:
    """
    Load debug file and extract messages and original response.

    Args:
        filepath: Path to the debug JSON file

    Returns:
        Dict containing messages, original response, and metadata
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "messages": data.get("messages", []),
            "original_response": data.get("response", ""),
            "task_type": data.get("task_type", "unknown"),
            "timestamp": data.get("timestamp", "unknown"),
            "metadata": data.get("metadata", {}),
        }
    except FileNotFoundError:
        logger.error(f"Debug file not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in debug file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading debug file: {e}")
        raise


async def regenerate_content(messages: List[Dict[str, Any]]) -> str:
    """
    Regenerate content using LLM with the same messages.

    Args:
        messages: List of messages to send to LLM

    Returns:
        str: Generated response
    """
    try:
        logger.info("Starting content regeneration...")

        # Use the same parameters as in the original generation
        response = await generate_with_messages_async(
            messages=messages, enable_executor=False
        )

        logger.info("Content regeneration completed")
        return response

    except Exception as e:
        logger.error(f"Error during content regeneration: {e}")
        raise


def print_comparison(original: str, regenerated: str, task_type: str, metadata: Dict):
    """
    Print a formatted comparison of original and regenerated content.

    Args:
        original: Original response from debug file
        regenerated: Newly regenerated response
        task_type: Type of generation task
        metadata: Additional metadata from debug file
    """
    print("\n" + "=" * 80)
    print(f"TASK TYPE: {task_type}")
    print(f"METADATA: {json.dumps(metadata, ensure_ascii=False, indent=2)}")
    print("=" * 80)

    print("\n" + "-" * 80)
    print("ORIGINAL RESPONSE:")
    print("-" * 80)
    print(original)

    print("\n" + "-" * 80)
    print("REGENERATED RESPONSE:")
    print("-" * 80)
    print(regenerated)


async def main():
    """Main function to handle CLI arguments and execute regeneration."""
    parser = argparse.ArgumentParser(
        description="Regenerate content from a debug file and compare outputs"
    )
    parser.add_argument(
        "--debug-file",
        type=str,
        required=True,
        help="Path to the debug JSON file (absolute or relative to project root)",
    )

    args = parser.parse_args()

    # Resolve file path
    debug_file_path = Path(args.debug_file)
    if not debug_file_path.is_absolute():
        debug_file_path = project_root / debug_file_path

    logger.info(f"Loading debug file: {debug_file_path}")

    try:
        # Load debug file
        debug_data = load_debug_file(str(debug_file_path))

        logger.info(f"Task type: {debug_data['task_type']}")
        logger.info(f"Timestamp: {debug_data['timestamp']}")
        logger.info(f"Number of messages: {len(debug_data['messages'])}")

        # Regenerate content
        regenerated_response = await regenerate_content(debug_data["messages"])

        # Print comparison
        print_comparison(
            original=debug_data["original_response"],
            regenerated=regenerated_response,
            task_type=debug_data["task_type"],
            metadata=debug_data["metadata"],
        )

        # Save regenerated response to file
        output_file = debug_file_path.parent / f"{debug_file_path.stem}_regenerated.json"
        output_data = {
            "original_file": str(debug_file_path),
            "timestamp": debug_data["timestamp"],
            "task_type": debug_data["task_type"],
            "original_response": debug_data["original_response"],
            "regenerated_response": regenerated_response,
            "metadata": debug_data["metadata"],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Comparison saved to: {output_file}")

    except Exception as e:
        logger.error(f"Failed to regenerate content: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
