#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
SQLite document note storage backend implementation
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from opencontext.storage.base_storage import (
    DataType,
    DocumentData,
    IDocumentStorageBackend,
    QueryResult,
    StorageType,
)
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class SQLiteBackend(IDocumentStorageBackend):
    """
    SQLite document note storage backend
    Specialized for storing activity generated markdown content and notes
    """

    def __init__(self):
        self.db_path: Optional[str] = None
        self.connection: Optional[sqlite3.Connection] = None
        self._initialized = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize SQLite database"""
        try:
            # Use path from configuration, default to ./persist/sqlite/app.db
            self.db_path = config.get("config", {}).get(
                "path", "./persist/sqlite/app.db")

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            self.connection = sqlite3.connect(
                self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Allow column name access

            # Create table structure
            self._create_tables()

            self._initialized = True
            logger.info(
                f"SQLite backend initialized successfully, database path: {self.db_path}")
            return True

        except Exception as e:
            logger.exception(f"SQLite backend initialization failed: {e}")
            return False

    def _create_tables(self):
        """Create database table structure"""
        cursor = self.connection.cursor()

        # vaults table - reports
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vaults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                summary TEXT,
                content TEXT,
                tags TEXT,
                parent_id INTEGER,
                is_folder BOOLEAN DEFAULT 0,
                is_deleted BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                document_type TEXT DEFAULT 'vaults',
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (parent_id) REFERENCES vaults (id)
            )
        """
        )

        # Todo table - todo items
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS todo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                status INTEGER DEFAULT 0,
                urgency INTEGER DEFAULT 0,
                assignee TEXT
            )
        """
        )

        cursor.execute(
            """
            PRAGMA table_info(todo)
        """
        )
        columns = [column[1] for column in cursor.fetchall()]
        if "assignee" not in columns:
            cursor.execute(
                """
                ALTER TABLE todo ADD COLUMN assignee TEXT
            """
            )
        if "reason" not in columns:
            cursor.execute(
                """
                ALTER TABLE todo ADD COLUMN reason TEXT
            """
            )

        # Activity table - activity records
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                resources JSON,
                metadata JSON,
                start_time DATETIME,
                end_time DATETIME
            )
        """
        )

        cursor.execute(
            """
            PRAGMA table_info(activity)
        """
        )
        columns = [column[1] for column in cursor.fetchall()]
        if "metadata" not in columns:
            cursor.execute(
                """
                ALTER TABLE activity ADD COLUMN metadata JSON
            """
            )

        # Tips table - tips
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Monitoring tables
        # Token usage tracking - keep 7 days of data
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_bucket TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(time_bucket, model)
            )
        """
        )

        # Stage timing tracking - LLM API calls and processing stages
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_stage_timing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_bucket TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                total_duration_ms INTEGER NOT NULL,
                min_duration_ms INTEGER NOT NULL,
                max_duration_ms INTEGER NOT NULL,
                avg_duration_ms INTEGER NOT NULL,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(time_bucket, stage_name)
            )
        """
        )

        # Data statistics tracking - images/screenshots and documents
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_data_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_bucket TEXT NOT NULL,
                data_type TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                context_type TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(time_bucket, data_type, context_type)
            )
        """
        )

        # Conversation tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT,
              user_id TEXT,
              page_name VARCHAR(20) DEFAULT 'home',
              status VARCHAR(20) DEFAULT 'active',
              metadata JSON DEFAULT '{}',
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id INTEGER NOT NULL,
              parent_message_id TEXT,
              role TEXT NOT NULL,
              content TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'pending',
              token_count INTEGER DEFAULT 0,
              metadata JSON DEFAULT '{}',
              latency_ms INTEGER DEFAULT 0,
              error_message TEXT DEFAULT '',
              completed_at DATETIME,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """
        )

        # New table indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_vaults_created ON vaults (created_at)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_vaults_type ON vaults (document_type)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_vaults_folder ON vaults (is_folder)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_vaults_deleted ON vaults (is_deleted)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_todo_status ON todo (status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_todo_urgency ON todo (urgency)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_todo_created ON todo (created_at)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_time ON activity (start_time, end_time)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tips_time ON tips (created_at)")

        # Monitoring table indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_token_created ON monitoring_token_usage (created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_token_model ON monitoring_token_usage (model)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_stage_created ON monitoring_stage_timing (created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_stage_name ON monitoring_stage_timing (stage_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_data_created ON monitoring_data_stats (created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_data_type ON monitoring_data_stats (data_type)"
        )

        # Conversation/Message indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_page ON conversations(user_id, page_name)"
        )

        # Message thinking table (stores thinking process for messages)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS message_thinking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                stage TEXT,
                progress REAL DEFAULT 0.0,
                sequence INTEGER DEFAULT 0,
                metadata JSON DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
            """
        )

        # Message thinking indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_thinking_message_id ON message_thinking(message_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_thinking_stage ON message_thinking(message_id, stage)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_thinking_sequence ON message_thinking(message_id, sequence)"
        )

        self.connection.commit()

        # Add default Quick Start document (only on first initialization)
        self._insert_default_vault_document()

    def _insert_default_vault_document(self):
        """Insert default Quick Start document"""
        cursor = self.connection.cursor()

        # Check if Quick Start document already exists
        cursor.execute(
            "SELECT COUNT(*) FROM vaults WHERE title = 'Start With Tutorial'")
        if cursor.fetchone()[0] > 0:
            return

        try:
            config_dir = "./config"
            quick_start_file = os.path.join(
                config_dir, "quick_start_default.md")

            if os.path.exists(quick_start_file):
                with open(quick_start_file, "r", encoding="utf-8") as f:
                    default_content = f.read()
            else:
                # If file doesn't exist, use fallback content
                logger.error(
                    f"Quick Start document {quick_start_file} does not exist")
                default_content = "Welcome to MineContext!\n\nYour Context-Aware AI Partner is ready to help you work, study, and create better."

        except Exception as e:
            default_content = "Welcome to MineContext!\n\nYour Context-Aware AI Partner is ready to help you work, study, and create better."

        # Insert default document
        try:
            cursor.execute(
                """
                INSERT INTO vaults (title, summary, content, document_type, tags, is_folder, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "Start With Tutorial",
                    "",
                    default_content,
                    "vaults",
                    "guide,welcome,quick-start",
                    False,
                    False,
                ),
            )
            vault_id = cursor.lastrowid
            self.connection.commit()
            logger.info("Default Quick Start document inserted")
            from opencontext.managers.event_manager import EventType, get_event_manager

            event_type = EventType.SYSTEM_STATUS
            data = {
                "title": "Start With Tutorial",
                "content": default_content,
                "doc_type": "vaults",
                "doc_id": vault_id,
            }
            event_manager = get_event_manager()
            event_manager.publish_event(event_type=event_type, data=data)

        except Exception as e:
            logger.exception(
                f"Failed to insert default Quick Start document: {e}")
            self.connection.rollback()

    # Report table operations
    def insert_vaults(
        self,
        title: str,
        summary: str,
        content: str,
        document_type: str,
        tags: str = None,
        parent_id: int = None,
        is_folder: bool = False,
    ) -> int:
        """Insert report record"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO vaults (title, summary, content, tags, parent_id, is_folder, document_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    title,
                    summary,
                    content,
                    tags,
                    parent_id,
                    is_folder,
                    document_type,
                    datetime.now(),
                    datetime.now(),
                ),
            )

            vault_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Report inserted, ID: {vault_id}")
            return vault_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert report: {e}")
            raise

    def get_reports(
        self, limit: int = 100, offset: int = 0, is_deleted: bool = False
    ) -> List[Dict]:
        """Get report list"""
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT id, title, summary, content, tags, parent_id, is_folder, is_deleted,
                       created_at, updated_at, document_type
                FROM vaults
                WHERE is_deleted = ? AND document_type != 'Note'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                (is_deleted, limit, offset),
            )

            rows = cursor.fetchall()
            logger.info(f"Got report list successfully, {len(rows)} records")
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get report list: {e}")
            return []

    def get_vaults(
        self,
        limit: int = 100,
        offset: int = 0,
        is_deleted: bool = False,
        document_type: str = None,
        created_after: datetime = None,
        created_before: datetime = None,
        updated_after: datetime = None,
        updated_before: datetime = None,
    ) -> List[Dict]:
        """
        Get vaults list with more filter conditions

        Args:
            limit: Return record count limit
            offset: Offset
            is_deleted: Whether deleted
            document_type: Document type filter (e.g. 'Report', 'vaults' etc)
            created_after: Creation time lower bound
            created_before: Creation time upper bound
            updated_after: Update time lower bound
            updated_before: Update time upper bound

        Returns:
            List[Dict]: Vaults record list
        """
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            # Build WHERE conditions and parameters
            where_clauses = ["is_deleted = ?"]
            params = [is_deleted]

            if document_type:
                where_clauses.append("document_type = ?")
                params.append(document_type)

            if created_after:
                where_clauses.append("created_at >= ?")
                params.append(created_after.isoformat())

            if created_before:
                where_clauses.append("created_at <= ?")
                params.append(created_before.isoformat())

            if updated_after:
                where_clauses.append("updated_at >= ?")
                params.append(updated_after.isoformat())

            if updated_before:
                where_clauses.append("updated_at <= ?")
                params.append(updated_before.isoformat())

            # Add LIMIT and OFFSET parameters
            params.extend([limit, offset])

            where_clause = " AND ".join(where_clauses)
            sql = f"""
                SELECT id, title, summary, content, tags, parent_id, is_folder, is_deleted,
                       created_at, updated_at, document_type
                FROM vaults
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # logger.info(f"Got vaults list successfully, {len(rows)} records")
            return [dict(row) for row in rows]

        except Exception as e:
            logger.exception(f"Failed to get vaults list: {e}")
            return []

    def get_vault(self, vault_id: int) -> Optional[Dict]:
        """Get vaults by ID"""
        if not self._initialized:
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT id, title, summary, content, tags, parent_id, is_folder, is_deleted,
                       created_at, updated_at, document_type
                FROM vaults
                WHERE id = ?
            """,
                (vault_id,),
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.exception(f"Failed to get vaults: {e}")
            return None

    def update_vault(self, vault_id: int, **kwargs) -> bool:
        """Update report"""
        if not self._initialized:
            return False

        cursor = self.connection.cursor()
        try:
            # Build dynamic update statement
            set_clauses = []
            params = []

            for key, value in kwargs.items():
                if key in [
                    "title",
                    "summary",
                    "content",
                    "tags",
                    "parent_id",
                    "is_folder",
                    "is_deleted",
                ]:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)

            if not set_clauses:
                return False

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(vault_id)

            sql = f"UPDATE vaults SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, params)

            success = cursor.rowcount > 0
            self.connection.commit()
            return success
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to update report: {e}")
            return False

    # Todo table operations
    def insert_todo(
        self,
        content: str,
        start_time: datetime = None,
        end_time: datetime = None,
        status: int = 0,
        urgency: int = 0,
        assignee: str = None,
        reason: str = None,
    ) -> int:
        """Insert todo item"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO todo (content, start_time, end_time, status, urgency, assignee, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    content,
                    start_time or datetime.now(),
                    end_time,
                    status,
                    urgency,
                    assignee,
                    reason,
                    datetime.now(),
                ),
            )

            todo_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Todo item inserted, ID: {todo_id}")
            return todo_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert todo item: {e}")
            raise

    def get_todos(
        self,
        status: int = None,
        limit: int = 100,
        offset: int = 0,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> List[Dict]:
        """Get todo item list"""
        if not self._initialized:
            return []
        cursor = self.connection.cursor()
        try:
            where_conditions = []
            params = []
            if start_time:
                where_conditions.append("start_time >= ?")
                params.append(start_time)
            if end_time:
                where_conditions.append("end_time <= ?")
                params.append(end_time)
            if status is not None:
                where_conditions.append("status = ?")
                params.append(status)
            where_clause = " AND ".join(
                where_conditions) if where_conditions else "1=1"
            params.extend([limit, offset])
            cursor.execute(
                f"""
                SELECT id, content, created_at, start_time, end_time, status, urgency, assignee, reason
                FROM todo
                WHERE {where_clause}
                ORDER BY urgency DESC, created_at DESC
                LIMIT ? OFFSET ?
            """,
                params,
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get todo item list: {e}")
            return []

    def update_todo_status(self, todo_id: int, status: int, end_time: datetime = None) -> bool:
        """Update todo item status"""
        if not self._initialized:
            return False

        cursor = self.connection.cursor()
        try:
            if status == 1 and end_time is None:
                end_time = datetime.now()

            cursor.execute(
                """
                UPDATE todo SET status = ?, end_time = ?
                WHERE id = ?
            """,
                (status, end_time, todo_id),
            )

            success = cursor.rowcount > 0
            self.connection.commit()
            return success
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to update todo item status: {e}")
            return False

    # Activity table operations
    def insert_activity(
        self,
        title: str,
        content: str,
        resources: str = None,
        metadata: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> int:
        """Insert activity record

        Args:
            title: Activity title
            content: Activity content
            resources: Resource information (JSON string)
            metadata: Metadata information (JSON string), including category, insights, etc.
            start_time: Start time
            end_time: End time

        Returns:
            int: Activity record ID
        """
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO activity (title, content, resources, metadata, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    title,
                    content,
                    resources,
                    metadata,
                    start_time or datetime.now(),
                    end_time or datetime.now(),
                ),
            )

            activity_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Activity record inserted, ID: {activity_id}")
            return activity_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert activity record: {e}")
            raise

    def get_activities(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Get activity record list"""
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            where_conditions = []
            params = []

            if start_time:
                where_conditions.append("start_time >= ?")
                params.append(start_time)
            if end_time:
                where_conditions.append("end_time <= ?")
                params.append(end_time)

            where_clause = " AND ".join(
                where_conditions) if where_conditions else "1=1"
            params.extend([limit, offset])

            cursor.execute(
                f"""
                SELECT id, title, content, resources, metadata, start_time, end_time
                FROM activity
                WHERE {where_clause}
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """,
                params,
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get activity record list: {e}")
            return []

    # Tips table operations
    def insert_tip(self, content: str) -> int:
        """Insert tip"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO tips (content, created_at)
                VALUES (?, ?)
            """,
                (content, datetime.now()),
            )

            tip_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Tip inserted, ID: {tip_id}")
            return tip_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert tip: {e}")
            raise

    def get_tips(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Get tip list"""
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            where_conditions = []
            params = []

            if start_time:
                where_conditions.append("created_at >= ?")
                params.append(start_time.isoformat())
            if end_time:
                where_conditions.append("created_at <= ?")
                params.append(end_time.isoformat())

            where_clause = " AND ".join(
                where_conditions) if where_conditions else "1=1"
            params.extend([limit, offset])

            cursor.execute(
                f"""
                SELECT id, content, created_at
                FROM tips
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                params,
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get tip list: {e}")
            return []

    def get_name(self) -> str:
        return "sqlite"

    def get_storage_type(self) -> StorageType:
        return StorageType.DOCUMENT_DB

    # Monitoring data operations
    def save_monitoring_token_usage(
        self, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int
    ) -> bool:
        """Save token usage monitoring data (aggregated by hour using UPSERT)"""
        if not self._initialized:
            return False

        try:
            cursor = self.connection.cursor()

            # Calculate time bucket (hour precision)
            now = datetime.now()
            time_bucket = now.strftime("%Y-%m-%d %H:00:00")

            # Use INSERT ... ON CONFLICT to update or insert
            cursor.execute(
                """
                INSERT INTO monitoring_token_usage (time_bucket, model, prompt_tokens, completion_tokens, total_tokens, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(time_bucket, model)
                DO UPDATE SET
                    prompt_tokens = prompt_tokens + ?,
                    completion_tokens = completion_tokens + ?,
                    total_tokens = total_tokens + ?
                """,
                (
                    time_bucket,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    now,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                ),
            )

            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save token usage: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return False

    def save_monitoring_stage_timing(
        self,
        stage_name: str,
        duration_ms: int,
        status: str = "success",
        metadata: Optional[str] = None,
    ) -> bool:
        """Save stage timing monitoring data (aggregated by hour using UPSERT)"""
        if not self._initialized:
            return False

        try:
            cursor = self.connection.cursor()

            # Calculate time bucket (hour precision)
            now = datetime.now()
            time_bucket = now.strftime("%Y-%m-%d %H:00:00")

            # First, get existing stats if any
            cursor.execute(
                """
                SELECT count, total_duration_ms, min_duration_ms, max_duration_ms, success_count, error_count
                FROM monitoring_stage_timing
                WHERE time_bucket = ? AND stage_name = ?
                """,
                (time_bucket, stage_name),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record with aggregated stats
                old_count, old_total, old_min, old_max, old_success, old_error = existing
                new_count = old_count + 1
                new_total = old_total + duration_ms
                new_min = min(old_min, duration_ms)
                new_max = max(old_max, duration_ms)
                new_avg = new_total // new_count
                new_success = old_success + (1 if status == "success" else 0)
                new_error = old_error + (0 if status == "success" else 1)

                cursor.execute(
                    """
                    UPDATE monitoring_stage_timing
                    SET count = ?,
                        total_duration_ms = ?,
                        min_duration_ms = ?,
                        max_duration_ms = ?,
                        avg_duration_ms = ?,
                        success_count = ?,
                        error_count = ?
                    WHERE time_bucket = ? AND stage_name = ?
                    """,
                    (
                        new_count,
                        new_total,
                        new_min,
                        new_max,
                        new_avg,
                        new_success,
                        new_error,
                        time_bucket,
                        stage_name,
                    ),
                )
            else:
                # Insert new record
                cursor.execute(
                    """
                    INSERT INTO monitoring_stage_timing
                    (time_bucket, stage_name, count, total_duration_ms, min_duration_ms, max_duration_ms, avg_duration_ms, success_count, error_count, metadata, created_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        time_bucket,
                        stage_name,
                        duration_ms,
                        duration_ms,
                        duration_ms,
                        duration_ms,
                        1 if status == "success" else 0,
                        0 if status == "success" else 1,
                        metadata,
                        now,
                    ),
                )

            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save stage timing: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return False

    def save_monitoring_data_stats(
        self,
        data_type: str,
        count: int = 1,
        context_type: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> bool:
        """Save data statistics monitoring data (aggregated by hour using UPSERT)"""
        if not self._initialized:
            return False

        try:
            cursor = self.connection.cursor()

            # Calculate time bucket (hour precision)
            now = datetime.now()
            time_bucket = now.strftime("%Y-%m-%d %H:00:00")

            # Use INSERT ... ON CONFLICT to update or insert
            # First, try to get existing count
            cursor.execute(
                """
                INSERT INTO monitoring_data_stats (time_bucket, data_type, count, context_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(time_bucket, data_type, context_type)
                DO UPDATE SET count = count + ?
                """,
                (time_bucket, data_type, count, context_type, metadata, now, count),
            )

            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save data stats: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return False

    def query_monitoring_token_usage(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Query token usage monitoring data"""
        if not self._initialized:
            return []

        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_bucket = cutoff_time.strftime("%Y-%m-%d %H:00:00")
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT model, prompt_tokens, completion_tokens, total_tokens, time_bucket
                FROM monitoring_token_usage
                WHERE time_bucket >= ?
                ORDER BY time_bucket DESC
                """,
                (cutoff_bucket,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "model": row[0],
                    "prompt_tokens": row[1],
                    "completion_tokens": row[2],
                    "total_tokens": row[3],
                    "time_bucket": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to query token usage: {e}")
            return []

    def query_monitoring_stage_timing(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Query stage timing monitoring data"""
        if not self._initialized:
            return []

        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_bucket = cutoff_time.strftime("%Y-%m-%d %H:00:00")
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT stage_name, count, total_duration_ms, min_duration_ms, max_duration_ms, avg_duration_ms, success_count, error_count, time_bucket
                FROM monitoring_stage_timing
                WHERE time_bucket >= ?
                ORDER BY time_bucket DESC
                """,
                (cutoff_bucket,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "stage_name": row[0],
                    "count": row[1],
                    "total_duration": row[2],
                    "min_duration": row[3],
                    "max_duration": row[4],
                    "duration_ms": row[5],  # avg_duration_ms
                    "success_count": row[6],
                    "error_count": row[7],
                    # Backward compatibility
                    "status": "success" if row[6] > 0 else "error",
                    "time_bucket": row[8],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to query stage timing: {e}")
            return []

    def query_monitoring_data_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Query data statistics monitoring data"""
        if not self._initialized:
            return []

        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_bucket = cutoff_time.strftime("%Y-%m-%d %H:00:00")
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT data_type, SUM(count) as total_count, context_type
                FROM monitoring_data_stats
                WHERE time_bucket >= ?
                GROUP BY data_type, context_type
                """,
                (cutoff_bucket,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "data_type": row[0],
                    "count": row[1],
                    "context_type": row[2],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to query data stats: {e}")
            return []

    def query_monitoring_data_stats_by_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Query data statistics monitoring data by custom time range"""
        if not self._initialized:
            return []

        try:
            # Convert datetime to hourly bucket format
            start_bucket = start_time.strftime("%Y-%m-%d %H:00:00")
            end_bucket = end_time.strftime("%Y-%m-%d %H:00:00")

            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT data_type, SUM(count) as total_count, context_type
                FROM monitoring_data_stats
                WHERE time_bucket >= ? AND time_bucket <= ?
                GROUP BY data_type, context_type
                """,
                (start_bucket, end_bucket),
            )
            rows = cursor.fetchall()
            return [
                {
                    "data_type": row[0],
                    "count": row[1],
                    "context_type": row[2],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to query data stats by range: {e}")
            return []

    def query_monitoring_data_stats_trend(
        self, hours: int = 24, interval_hours: int = 1
    ) -> List[Dict[str, Any]]:
        """Query data statistics trend with time grouping

        Args:
            hours: Time range in hours
            interval_hours: Group interval in hours (default 1 hour)

        Returns:
            List of records with timestamp, data_type, count
        """
        if not self._initialized:
            return []

        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_bucket = cutoff_time.strftime("%Y-%m-%d %H:00:00")
            cursor = self.connection.cursor()

            # Query using time_bucket directly (already hourly grouped)
            cursor.execute(
                """
                SELECT
                    time_bucket,
                    data_type,
                    SUM(count) as total_count,
                    context_type
                FROM monitoring_data_stats
                WHERE time_bucket >= ?
                GROUP BY time_bucket, data_type, context_type
                ORDER BY time_bucket ASC
                """,
                (cutoff_bucket,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "data_type": row[1],
                    "count": row[2],
                    "context_type": row[3],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to query data stats trend: {e}")
            return []

    def cleanup_old_monitoring_data(self, days: int = 7) -> bool:
        """Clean up monitoring data older than specified days"""
        if not self._initialized:
            return False

        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            cutoff_bucket = cutoff_time.strftime("%Y-%m-%d %H:00:00")
            cursor = self.connection.cursor()

            # Clean up token usage data (use time_bucket)
            cursor.execute(
                "DELETE FROM monitoring_token_usage WHERE time_bucket < ?",
                (cutoff_bucket,),
            )

            # Clean up stage timing data (use time_bucket)
            cursor.execute(
                "DELETE FROM monitoring_stage_timing WHERE time_bucket < ?",
                (cutoff_bucket,),
            )

            # Clean up data stats (use time_bucket)
            cursor.execute(
                "DELETE FROM monitoring_data_stats WHERE time_bucket < ?",
                (cutoff_bucket,),
            )

            self.connection.commit()
            logger.info(f"Cleaned up monitoring data older than {days} days")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup old monitoring data: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return False

    # Conversation/Message operations
    def create_conversation(
        self,
        page_name: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new conversation (4.1.1)
        """
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            now = datetime.now()
            meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"

            cursor.execute(
                """
                INSERT INTO conversations (page_name, user_id, title, metadata, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (page_name, user_id, title, meta_str, "active", now, now),
            )

            conversation_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Conversation created, ID: {conversation_id}")
            return self.get_conversation(conversation_id)
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to create conversation: {e}")
            return None

    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single conversation's details (4.1.2)
        """
        if not self._initialized:
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT id, title, user_id, page_name, status, metadata, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.exception(f"Failed to get conversation: {e}")
            return None

    def get_conversation_list(
        self,
        limit: int = 20,
        offset: int = 0,
        page_name: Optional[str] = None,
        user_id: Optional[str] = None,
        status: str = "active",
    ) -> Dict[str, Any]:
        """
        Get a list of conversations with pagination (4.1.3)
        """
        if not self._initialized:
            return {"items": [], "total": 0}

        cursor = self.connection.cursor()
        try:
            where_clauses = []
            params = []

            if status:
                where_clauses.append("status = ?")
                params.append(status)
            if page_name:
                where_clauses.append("page_name = ?")
                params.append(page_name)
            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)

            where_sql = " AND ".join(
                where_clauses) if where_clauses else "1=1"

            # Get total count
            count_params = params[:]
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM conversations
                WHERE {where_sql}
                """,
                count_params,
            )
            total = cursor.fetchone()[0]

            # Get items
            list_params = params + [limit, offset]
            cursor.execute(
                f"""
                SELECT id, title, user_id, page_name, status, metadata, created_at, updated_at
                FROM conversations
                WHERE {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                list_params,
            )
            rows = cursor.fetchall()
            items = [dict(row) for row in rows]

            return {"items": items, "total": total}

        except Exception as e:
            logger.exception(f"Failed to get conversation list: {e}")
            return {"items": [], "total": 0}

    def update_conversation(
        self,
        conversation_id: int,
        title: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a conversation's title or status (4.1.4, 4.1.5)
        """
        if not self._initialized:
            return None

        cursor = self.connection.cursor()
        try:
            set_clauses = []
            params = []

            if title is not None:
                set_clauses.append("title = ?")
                params.append(title)
            if status is not None:
                # Handle typo in spec 'delected' -> 'deleted'
                set_clauses.append("status = ?")
                params.append("deleted" if status == "delected" else status)

            if not set_clauses:
                # No change, return current
                return self.get_conversation(conversation_id)

            set_clauses.append("updated_at = ?")
            params.append(datetime.now())
            params.append(conversation_id)

            sql = f"UPDATE conversations SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, params)

            self.connection.commit()

            if cursor.rowcount > 0:
                logger.info(f"Conversation {conversation_id} updated.")
                return self.get_conversation(conversation_id)
            else:
                logger.warning(
                    f"Failed to update conversation {conversation_id}, row not found or no change.")
                return None
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to update conversation: {e}")
            return None

    def delete_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """
        Mark a conversation as deleted (4.1.5)
        """
        # Note: The spec uses 'delected', we'll update status to 'deleted'
        updated_convo = self.update_conversation(
            conversation_id=conversation_id, status="deleted"
        )
        success = updated_convo is not None
        return {"success": success, "id": conversation_id}

    # -----------------------------------------------------------------
    # Conversation/Message operations (Continued)
    # -----------------------------------------------------------------

    def get_message(self, message_id: int, include_thinking: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get a single message by its ID, optionally including thinking records.

        Args:
            message_id: The message ID
            include_thinking: Whether to include thinking array (default: True)

        Returns:
            Message dict with optional 'thinking' array
        """
        if not self._initialized:
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT * FROM messages WHERE id = ?
                """,
                (message_id,),
            )
            row = cursor.fetchone()
            if row:
                message = dict(row)

                # Include thinking records if requested
                if include_thinking:
                    message['thinking'] = self.get_message_thinking(message_id)

                return message
            return None
        except Exception as e:
            logger.exception(f"Failed to get message: {e}")
            return None

    def create_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        is_complete: bool = True,
        token_count: int = 0,
        parent_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new message (4.2.2)
        """
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            now = datetime.now()
            # Map is_complete to status and completed_at
            status = "completed" if is_complete else "streaming"
            completed_at = now if is_complete else None
            meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"

            cursor.execute(
                """
                INSERT INTO messages (conversation_id, role, content, status, token_count,
                                      parent_message_id, metadata, completed_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    status,
                    token_count,
                    parent_message_id,
                    meta_str,
                    completed_at,
                    now,
                    now,
                ),
            )
            message_id = cursor.lastrowid

            # Update conversation's updated_at timestamp
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )

            self.connection.commit()
            logger.info(f"Message created, ID: {message_id}")
            return self.get_message(message_id)  # Return the created message
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to create message: {e}")
            return None

    def create_streaming_message(
        self,
        conversation_id: int,
        role: str,
        parent_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new streaming message (initial content is empty, status is 'streaming') (4.2.3)
        """
        return self.create_message(
            conversation_id=conversation_id,
            role=role,
            content="",
            is_complete=False,  # This sets status='streaming'
            token_count=0,
            parent_message_id=parent_message_id,
            metadata=metadata,
        )

    def update_message(
        self,
        message_id: int,
        new_content: str,
        is_complete: Optional[bool] = None,
        token_count: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a message's content and optionally mark it complete (4.2.4)
        This SETS the content, it does not append.
        """
        if not self._initialized:
            return None

        cursor = self.connection.cursor()
        try:
            now = datetime.now()
            set_clauses = ["content = ?", "updated_at = ?"]
            params = [new_content, now]

            if token_count is not None:
                set_clauses.append("token_count = ?")
                params.append(token_count)

            if is_complete is True:
                set_clauses.append("status = ?")
                params.append("completed")
                set_clauses.append("completed_at = ?")
                params.append(now)
            elif is_complete is False:
                set_clauses.append("status = ?")
                params.append("streaming")  # Assume if update, it's streaming
                set_clauses.append("completed_at = NULL")

            params.append(message_id)

            sql = f"UPDATE messages SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, params)

            # Update conversation's updated_at
            cursor.execute(
                """
                UPDATE conversations SET updated_at = ?
                WHERE id = (SELECT conversation_id FROM messages WHERE id = ?)
                """,
                (now, message_id),
            )

            self.connection.commit()

            if cursor.rowcount > 0:
                return self.get_message(message_id)
            else:
                logger.warning(
                    f"Failed to update message {message_id}, not found.")
                return None
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to update message: {e}")
            return None

    def append_message_content(
        self,
        message_id: int,
        content_chunk: str,
        token_count: int = 0,
    ) -> bool:
        """
        Append content to a streaming message (4.2.5)
        """
        if not self._initialized:
            return False

        cursor = self.connection.cursor()
        try:
            now = datetime.now()

            # Use SQLite string concatenation ||
            # Also update status to 'streaming' if it was 'pending'
            cursor.execute(
                """
                UPDATE messages
                SET content = content || ?,
                    token_count = token_count + ?,
                    status = CASE WHEN status = 'pending' THEN 'streaming' ELSE status END,
                    updated_at = ?
                WHERE id = ?
                """,
                (content_chunk, token_count, now, message_id),
            )

            if cursor.rowcount == 0:
                logger.warning(
                    f"Failed to append message {message_id}, not found.")
                return False

            # Update conversation's updated_at
            cursor.execute(
                """
                UPDATE conversations SET updated_at = ?
                WHERE id = (SELECT conversation_id FROM messages WHERE id = ?)
                """,
                (now, message_id),
            )

            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to append message content: {e}")
            return False

    def update_message_metadata(
        self,
        message_id: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update message metadata
        """
        if not self._initialized:
            return False

        cursor = self.connection.cursor()
        try:
            now = datetime.now()
            meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"

            cursor.execute(
                """
                UPDATE messages
                SET metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                (meta_str, now, message_id),
            )

            success = cursor.rowcount > 0
            self.connection.commit()
            return success
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to update message metadata: {e}")
            return False

    def mark_message_finished(
        self,
        message_id: int,
        status: str = "completed",
        error_message: Optional[str] = None
    ) -> bool:
        """
        Mark a message as finished (completed, failed, or cancelled) (4.2.6 & Interrupt)
        """
        if not self._initialized:
            return False

        if status not in ["completed", "failed", "cancelled"]:
            status = "completed"  # Default to completed

        cursor = self.connection.cursor()
        try:
            now = datetime.now()

            set_clauses = ["status = ?", "completed_at = ?", "updated_at = ?"]
            params = [status, now, now]

            if error_message:
                set_clauses.append("error_message = ?")
                params.append(error_message)

            params.append(message_id)
            # Only update if not already in that state
            set_clauses.append("status != ?")
            params.append(status)

            sql = f"UPDATE messages SET {', '.join(set_clauses)} WHERE id = ? AND {set_clauses[-1]}"
            # Remove the last part from sql
            sql = f"UPDATE messages SET {', '.join(set_clauses[:-1])} WHERE id = ? AND {set_clauses[-1]}"

            cursor.execute(sql, params)

            success = cursor.rowcount > 0
            if not success:
                # Check if it failed because it was already in the desired state
                cursor.execute(
                    "SELECT status FROM messages WHERE id = ?", (message_id,))
                row = cursor.fetchone()
                if row and row[0] == status:
                    success = True  # Already done, count as success
                else:
                    logger.warning(
                        f"Failed to mark message {message_id} as {status}, not found or no change.")

            # Update conversation's updated_at
            cursor.execute(
                """
                UPDATE conversations SET updated_at = ?
                WHERE id = (SELECT conversation_id FROM messages WHERE id = ?)
                """,
                (now, message_id),
            )

            self.connection.commit()
            return success
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to mark message {status}: {e}")
            return False

    def interrupt_message(self, message_id: int) -> bool:
        """
        Interrupt a streaming message (marks as 'cancelled')
        """
        return self.mark_message_finished(
            message_id=message_id,
            status="cancelled",
            error_message="Message interrupted by user."
        )

    def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific conversation, ordered by creation time (4.2.7)
        Each message includes its thinking records if available.
        """
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            rows = cursor.fetchall()
            # Convert sqlite3.Row objects to standard dicts and add thinking records
            messages = []
            for row in rows:
                message = dict(row)
                # Add thinking records for this message
                message['thinking'] = self.get_message_thinking(message['id'])
                messages.append(message)
            return messages
        except Exception as e:
            logger.exception(f"Failed to get conversation messages: {e}")
            return []

    def delete_message(self, message_id: int) -> bool:
        """
        Delete a message from the database.

        Args:
            message_id: The ID of the message to delete

        Returns:
            bool: True if the message was deleted successfully, False otherwise
        """
        if not self._initialized:
            logger.warning("Storage not initialized")
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "DELETE FROM messages WHERE id = ?",
                (message_id,)
            )
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to delete message {message_id}: {e}")
            return False

    # Message Thinking Management Methods

    def add_message_thinking(
        self,
        message_id: int,
        content: str,
        stage: Optional[str] = None,
        progress: float = 0.0,
        sequence: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Add a thinking record to a message.

        Args:
            message_id: The message ID to attach thinking to
            content: Thinking content
            stage: Workflow stage (e.g., 'intent_analysis', 'context_gathering')
            progress: Progress value (0.0-1.0)
            sequence: Sequence number (auto-incremented if not provided)
            metadata: Additional metadata

        Returns:
            int: Thinking record ID if successful, None otherwise
        """
        if not self._initialized:
            logger.warning("Storage not initialized")
            return None

        cursor = self.connection.cursor()
        try:
            # Auto-increment sequence if not provided
            if sequence is None:
                cursor.execute(
                    "SELECT COALESCE(MAX(sequence), -1) + 1 FROM message_thinking WHERE message_id = ?",
                    (message_id,)
                )
                sequence = cursor.fetchone()[0]

            meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"

            cursor.execute(
                """
                INSERT INTO message_thinking
                (message_id, content, stage, progress, sequence, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, content, stage, progress, sequence, meta_str),
            )
            thinking_id = cursor.lastrowid
            self.connection.commit()
            logger.debug(f"Added thinking record {thinking_id} to message {message_id}")
            return thinking_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to add thinking to message {message_id}: {e}")
            return None

    def get_message_thinking(self, message_id: int) -> List[Dict[str, Any]]:
        """
        Get all thinking records for a message, ordered by sequence.

        Args:
            message_id: The message ID

        Returns:
            List of thinking records
        """
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT id, message_id, content, stage, progress, sequence, metadata, created_at
                FROM message_thinking
                WHERE message_id = ?
                ORDER BY sequence ASC, created_at ASC
                """,
                (message_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get thinking for message {message_id}: {e}")
            return []

    def clear_message_thinking(self, message_id: int) -> bool:
        """
        Clear all thinking records for a message.

        Args:
            message_id: The message ID

        Returns:
            bool: True if successful
        """
        if not self._initialized:
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "DELETE FROM message_thinking WHERE message_id = ?",
                (message_id,)
            )
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to clear thinking for message {message_id}: {e}")
            return False

    def query(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Query documents"""
        if not self._initialized:
            return QueryResult(documents=[], total_count=0)

        cursor = self.connection.cursor()

        try:
            # Build query conditions
            where_conditions = []
            params = []

            # Text search conditions
            if query:
                where_conditions.append(
                    '(content LIKE ? OR JSON_EXTRACT(metadata, "$.title") LIKE ?)'
                )
                query_pattern = f"%{query}%"
                params.extend([query_pattern, query_pattern])

            # Filter conditions
            if filters:
                if "content_type" in filters:
                    where_conditions.append(
                        'JSON_EXTRACT(metadata, "$.content_type") = ?')
                    params.append(filters["content_type"])

                if "data_type" in filters:
                    where_conditions.append("data_type = ?")
                    params.append(filters["data_type"])

                if "tags" in filters:
                    tags = (
                        filters["tags"] if isinstance(filters["tags"], list) else [
                            filters["tags"]]
                    )
                    if tags:
                        # Use proper parameterized query for tags
                        tag_placeholders = ",".join(["?"] * len(tags))
                        where_conditions.append(
                            f'id IN (SELECT document_id FROM document_tags WHERE tag IN ({tag_placeholders}))'
                        )
                        for tag in tags:
                            params.append(tag.lower())

            # Build SQL query
            where_clause = " AND ".join(
                where_conditions) if where_conditions else "1=1"

            # Get documents
            # Use text() for safe SQL composition with parameters
            base_sql = """
                SELECT DISTINCT d.id, d.content, d.data_type, d.metadata, d.created_at, d.updated_at
                FROM documents d
                LEFT JOIN document_tags dt ON d.id = dt.document_id
                WHERE """
            sql = base_sql + where_clause + """
                ORDER BY d.updated_at DESC
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            documents = []
            for row in rows:
                # Get images for each document
                cursor.execute(
                    "SELECT image_path FROM images WHERE document_id = ? ORDER BY id", (
                        row["id"],)
                )
                images = [img_row[0] for img_row in cursor.fetchall()]

                # Parse metadata
                metadata = {}
                if row["metadata"]:
                    try:
                        metadata = json.loads(row["metadata"])
                    except json.JSONDecodeError:
                        pass

                documents.append(
                    DocumentData(
                        id=row["id"],
                        content=row["content"],
                        metadata=metadata,
                        data_type=DataType(row["data_type"]),
                        images=images if images else None,
                    )
                )

            # Get total count
            count_base_sql = """
                SELECT COUNT(DISTINCT d.id)
                FROM documents d
                LEFT JOIN document_tags dt ON d.id = dt.document_id
                WHERE """
            count_sql = count_base_sql + where_clause
            cursor.execute(count_sql, params[:-1])  # Exclude limit parameter
            total_count = cursor.fetchone()[0]

            return QueryResult(documents=documents, total_count=total_count)

        except Exception as e:
            logger.exception(f"SQLite text search failed: {e}")
            return QueryResult(documents=[], total_count=0)

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self._initialized = False
            logger.info("SQLite database connection closed")
