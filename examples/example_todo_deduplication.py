#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Example: TODO Deduplication with Vector Search
This example demonstrates how the SmartTodoManager uses vector similarity to deduplicate todos.
It shows both historical deduplication (against stored todos) and batch deduplication (within new todos).

Features demonstrated:
- Vector-based similarity detection
- Historical todo deduplication (stored in database)
- Batch todo deduplication (within the same submission)
- Customizable similarity threshold

Usage:
    # Run with default similarity threshold (0.85)
    python example_todo_deduplication.py

    # Run with custom similarity threshold
    python example_todo_deduplication.py 0.90
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add parent directory to path to import opencontext modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from opencontext.context_consumption.generation.smart_todo_manager import SmartTodoManager
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger, setup_logging

# Initialize logging first
setup_logging({"level": "INFO", "log_path": None})  # Only console output for this example

logger = get_logger(__name__)


def create_sample_todos() -> List[Dict]:
    """
    Create sample todo items for testing deduplication.

    Returns:
        List of sample todo dictionaries with various similarity patterns
    """
    return [
        {
            "title": "实现用户认证功能",
            "description": "添加用户登录和注册功能，使用 JWT 令牌进行身份验证",
            "priority": "高优先级",
            "status": "待处理",
        },
        {
            "title": "用户认证模块开发",
            "description": "开发用户登录注册系统，采用 JWT 认证方式",
            "priority": "高优先级",
            "status": "待处理",
        },
        {
            "title": "修复支付模块的bug",
            "description": "解决超过1000元的支付失败问题",
            "priority": "高优先级",
            "status": "待处理",
        },
        {
            "title": "更新项目文档",
            "description": "为新增的 API 接口编写文档说明",
            "priority": "中优先级",
            "status": "待处理",
        },
        {
            "title": "支付功能bug修复",
            "description": "修复大额交易（超过1000元）时支付处理失败的错误",
            "priority": "高优先级",
            "status": "待处理",
        },
        {
            "title": "搭建CI/CD流水线",
            "description": "配置 GitHub Actions 实现自动化测试和部署",
            "priority": "中优先级",
            "status": "待处理",
        },
        {
            "title": "编写单元测试",
            "description": "为认证模块添加全面的单元测试覆盖",
            "priority": "中优先级",
            "status": "待处理",
        },
        {
            "title": "认证功能测试",
            "description": "创建单元测试以覆盖用户认证相关功能",
            "priority": "中优先级",
            "status": "待处理",
        },
    ]


def run_deduplication_example(similarity_threshold: float = 0.85):
    """
    Demonstrate TODO deduplication with vector search.

    Args:
        similarity_threshold: Minimum similarity score (0-1) to consider todos as duplicates
    """
    print("=" * 80)
    print("TODO Deduplication with Vector Search Example")
    print("=" * 80)
    print(f"\nSimilarity Threshold: {similarity_threshold}")
    print("(Higher threshold = stricter matching, fewer duplicates detected)\n")

    # Initialize the SmartTodoManager
    todo_manager = SmartTodoManager()

    # Create sample todos
    sample_todos = create_sample_todos()

    print(f"Original TODO List ({len(sample_todos)} items):")
    print("-" * 80)
    for i, todo in enumerate(sample_todos, 1):
        print(f"\n[{i}] {todo['title']}")
        print(f"    Description: {todo['description']}")
        print(f"    Priority: {todo['priority']}")

    print("\n" + "=" * 80)
    print("Running Vector-Based Deduplication...")
    print("=" * 80)

    # Run deduplication
    try:
        deduplicated_todos = todo_manager._deduplicate_with_vector_search(
            sample_todos, similarity_threshold=similarity_threshold
        )

        todo_ids = []
        for task in deduplicated_todos:
            content = task["title"] + " " + task["description"]
            urgency = task.get("priority", "medium")
            deadline = task.get("deadline")
            participants_str = ", ".join(task.get("assignees", []))
            reason = task.get("reason", "")

            todo_id = get_storage().insert_todo(
                content=content,
                urgency=urgency,
                end_time=deadline,
                assignee=participants_str,
                reason=reason,
            )
            todo_ids.append(todo_id)

            # Store todo embedding to vector database for future deduplication
            if task.get("_embedding"):
                try:
                    get_storage().upsert_todo_embedding(
                        todo_id=todo_id,
                        content=content,
                        embedding=task["_embedding"],
                        metadata={
                            "urgency": urgency,
                            "priority": task.get("priority", "medium"),
                        },
                    )
                    logger.debug(f"Stored embedding for todo {todo_id}")
                except Exception as e:
                    logger.warning(f"Failed to store todo embedding for {todo_id}: {e}")

        print(f"\n✅ Deduplication Complete!")
        print("-" * 80)
        print(f"Original todos: {len(sample_todos)}")
        print(f"Duplicates filtered: {len(sample_todos) - len(deduplicated_todos)}")
        print(f"Unique todos remaining: {len(deduplicated_todos)}")

        if deduplicated_todos:
            print(f"\n{'=' * 80}")
            print(f"Final Unique TODO List ({len(deduplicated_todos)} items):")
            print("=" * 80)
            for i, todo in enumerate(deduplicated_todos, 1):
                print(f"\n[{i}] {todo['title']}")
                print(f"    Description: {todo['description']}")
                print(f"    Priority: {todo['priority']}")
                print(f"    Status: {todo['status']}")

        print("\n" + "=" * 80)
        print("Deduplication Analysis")
        print("=" * 80)
        print("The deduplication process works in two stages:")
        print("1. Historical deduplication: Compares with existing todos in database")
        print("2. Batch deduplication: Compares new todos with each other")
        print("\nExpected duplicates in this example:")
        print("- 'Implement user authentication' ≈ 'User auth implementation'")
        print("- 'Fix bug in payment module' ≈ 'Payment bug fix'")
        print("- 'Write unit tests' ≈ 'Authentication testing'")
        print("\nNote: The actual number of detected duplicates depends on:")
        print("- Similarity threshold setting")
        print("- Embedding model's understanding of semantic similarity")
        print("- Presence of similar todos in historical database")

    except Exception as e:
        print(f"\n❌ Error during deduplication: {e}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("Performance Note")
    print("=" * 80)
    print("The optimized deduplication algorithm:")
    print("- Caches embeddings to avoid redundant vectorization")
    print("- Time complexity: O(N) vectorizations for N todos")
    print("- Previously: O(N²) vectorizations (now fixed!)")
    print("\nFor large batches, this optimization significantly reduces:")
    print("- API calls to embedding services")
    print("- Processing time")
    print("- Resource usage")


def main():
    """Main entry point for the example."""
    similarity_threshold = 0.85  # Default threshold

    if len(sys.argv) > 1:
        try:
            similarity_threshold = float(sys.argv[1])
            if not (0.0 <= similarity_threshold <= 1.0):
                print("Error: Similarity threshold must be between 0.0 and 1.0")
                print("Using default value: 0.85")
                similarity_threshold = 0.85
        except ValueError:
            print("Error: Invalid similarity threshold. Must be a number between 0.0 and 1.0")
            print("Using default value: 0.85")
            similarity_threshold = 0.85

    try:
        run_deduplication_example(similarity_threshold)
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
