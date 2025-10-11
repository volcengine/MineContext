#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
SQLite document note storage backend implementation
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from opencontext.storage.base_storage import (
    IDocumentStorageBackend, StorageType, DataType, DocumentData, QueryResult
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
            self.db_path = config.get('config', {}).get('path', './persist/sqlite/app.db')
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Allow column name access
            
            # Create table structure
            self._create_tables()
            
            self._initialized = True
            logger.info(f"SQLite backend initialized successfully, database path: {self.db_path}")
            return True
            
        except Exception as e:
            logger.exception(f"SQLite backend initialization failed: {e}")
            return False
    
    def _create_tables(self):
        """Create database table structure"""
        cursor = self.connection.cursor()
        
        # vaults table - reports
        cursor.execute('''
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
        ''')
        
        # Todo table - todo items
        cursor.execute('''
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
        ''')

        cursor.execute('''
            PRAGMA table_info(todo)
        ''')
        columns = [column[1] for column in cursor.fetchall()]
        if 'assignee' not in columns:
            cursor.execute('''
                ALTER TABLE todo ADD COLUMN assignee TEXT
            ''')
        if 'reason' not in columns:
            cursor.execute('''
                ALTER TABLE todo ADD COLUMN reason TEXT
            ''')
        
        # Activity table - activity records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                resources JSON,
                metadata JSON,
                start_time DATETIME,
                end_time DATETIME
            )
        ''')

        cursor.execute('''
            PRAGMA table_info(activity)
        ''')
        columns = [column[1] for column in cursor.fetchall()]
        if 'metadata' not in columns:
            cursor.execute('''
                ALTER TABLE activity ADD COLUMN metadata JSON
            ''')
        
        # Tips table - tips
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # New table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vaults_created ON vaults (created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vaults_type ON vaults (document_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vaults_folder ON vaults (is_folder)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vaults_deleted ON vaults (is_deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_status ON todo (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_urgency ON todo (urgency)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_todo_created ON todo (created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_time ON activity (start_time, end_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tips_time ON tips (created_at)')
        
        self.connection.commit()
        
        # Add default Quick Start document (only on first initialization)
        self._insert_default_vault_document()
    
    def _insert_default_vault_document(self):
        """Insert default Quick Start document"""
        cursor = self.connection.cursor()
        
        # Check if Quick Start document already exists
        cursor.execute("SELECT COUNT(*) FROM vaults WHERE title = 'Start With Tutorial'")
        if cursor.fetchone()[0] > 0:
            return
        
        try:
            config_dir = "./config"
            quick_start_file = os.path.join(config_dir, 'quick_start_default.md')
            
            if os.path.exists(quick_start_file):
                with open(quick_start_file, 'r', encoding='utf-8') as f:
                    default_content = f.read()
            else:
                # If file doesn't exist, use fallback content
                logger.error(f"Quick Start document {quick_start_file} does not exist")
                default_content = "Welcome to MineContext!\n\nYour Context-Aware AI Partner is ready to help you work, study, and create better."
                
        except Exception as e:
            default_content = "Welcome to MineContext!\n\nYour Context-Aware AI Partner is ready to help you work, study, and create better."

        # Insert default document
        try:
            cursor.execute('''
                INSERT INTO vaults (title, summary, content, document_type, tags, is_folder, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'Start With Tutorial',
                '',
                default_content,
                'vaults',
                'guide,welcome,quick-start',
                False,
                False
            ))
            vault_id = cursor.lastrowid
            self.connection.commit()
            logger.info("Default Quick Start document inserted")
            from opencontext.managers.event_manager import get_event_manager, EventType
            event_type = EventType.SYSTEM_STATUS
            data = {
                "title": "Start With Tutorial",
                "content": default_content,
                "doc_type": "vaults",
                "doc_id": vault_id,
            }
            event_manager = get_event_manager()
            event_manager.publish_event(
                event_type=event_type,
                data=data
            )
            
        except Exception as e:
            logger.exception(f"Failed to insert default Quick Start document: {e}")
            self.connection.rollback()
    
    # Report table operations
    def insert_vaults(self, title: str, summary: str, content: str, document_type: str, tags: str = None, 
                     parent_id: int = None, is_folder: bool = False) -> int:
        """Insert report record"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")
        
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO vaults (title, summary, content, tags, parent_id, is_folder, document_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, summary, content, tags, parent_id, is_folder, document_type, datetime.now(), datetime.now()))
            
            vault_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Report inserted, ID: {vault_id}")
            return vault_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert report: {e}")
            raise
    
    def get_reports(self, limit: int = 100, offset: int = 0, is_deleted: bool = False) -> List[Dict]:
        """Get report list"""
        if not self._initialized:
            return []
        
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                SELECT id, title, summary, content, tags, parent_id, is_folder, is_deleted,
                       created_at, updated_at, document_type
                FROM vaults
                WHERE is_deleted = ? AND document_type != 'Note'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (is_deleted, limit, offset))
            
            rows = cursor.fetchall()
            logger.info(f"Got report list successfully, {len(rows)} records")
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get report list: {e}")
            return []
    
    def get_vaults(self, 
                   limit: int = 100, 
                   offset: int = 0, 
                   is_deleted: bool = False,
                   document_type: str = None,
                   created_after: datetime = None,
                   created_before: datetime = None,
                   updated_after: datetime = None,
                   updated_before: datetime = None) -> List[Dict]:
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
            where_clauses = ['is_deleted = ?']
            params = [is_deleted]
            
            if document_type:
                where_clauses.append('document_type = ?')
                params.append(document_type)
            
            if created_after:
                where_clauses.append('created_at >= ?')
                params.append(created_after.isoformat())
            
            if created_before:
                where_clauses.append('created_at <= ?')
                params.append(created_before.isoformat())
                
            if updated_after:
                where_clauses.append('updated_at >= ?')
                params.append(updated_after.isoformat())
                
            if updated_before:
                where_clauses.append('updated_at <= ?')
                params.append(updated_before.isoformat())
            
            # Add LIMIT and OFFSET parameters
            params.extend([limit, offset])
            
            where_clause = ' AND '.join(where_clauses)
            sql = f'''
                SELECT id, title, summary, content, tags, parent_id, is_folder, is_deleted,
                       created_at, updated_at, document_type
                FROM vaults
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            '''
            
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
            cursor.execute('''
                SELECT id, title, summary, content, tags, parent_id, is_folder, is_deleted,
                       created_at, updated_at, document_type
                FROM vaults
                WHERE id = ?
            ''', (vault_id,))
            
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
                if key in ['title', 'summary', 'content', 'tags', 'parent_id', 'is_folder', 'is_deleted']:
                    set_clauses.append(f'{key} = ?')
                    params.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append('updated_at = CURRENT_TIMESTAMP')
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
    def insert_todo(self, content: str, start_time: datetime = None, end_time: datetime = None,
                   status: int = 0, urgency: int = 0, assignee: str = None, reason: str = None) -> int:
        """Insert todo item"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")

        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO todo (content, start_time, end_time, status, urgency, assignee, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content, start_time or datetime.now(), end_time, status, urgency, assignee, reason, datetime.now()))

            todo_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Todo item inserted, ID: {todo_id}")
            return todo_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert todo item: {e}")
            raise
    
    def get_todos(self, status: int = None, limit: int = 100, offset: int = 0, start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """Get todo item list"""
        if not self._initialized:
            return []
        cursor = self.connection.cursor()
        try:
            where_conditions = []
            params = []
            if start_time:
                where_conditions.append('start_time >= ?')
                params.append(start_time)
            if end_time:
                where_conditions.append('end_time <= ?')
                params.append(end_time)
            if status is not None:
                where_conditions.append('status = ?')
                params.append(status)
            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
            params.extend([limit, offset])
            cursor.execute(f'''
                SELECT id, content, created_at, start_time, end_time, status, urgency, assignee, reason
                FROM todo
                WHERE {where_clause}
                ORDER BY urgency DESC, created_at DESC
                LIMIT ? OFFSET ?
            ''', params)
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
            
            cursor.execute('''
                UPDATE todo SET status = ?, end_time = ?
                WHERE id = ?
            ''', (status, end_time, todo_id))
            
            success = cursor.rowcount > 0
            self.connection.commit()
            return success
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to update todo item status: {e}")
            return False
    
    # Activity table operations
    def insert_activity(self, title: str, content: str, resources: str = None,
                       metadata: str = None, start_time: datetime = None, end_time: datetime = None) -> int:
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
            cursor.execute('''
                INSERT INTO activity (title, content, resources, metadata, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, content, resources, metadata, start_time or datetime.now(), end_time or datetime.now()))
            
            activity_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Activity record inserted, ID: {activity_id}")
            return activity_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert activity record: {e}")
            raise
    
    def get_activities(self, start_time: datetime = None, end_time: datetime = None, 
                      limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get activity record list
        """
        if not self._initialized:
            return []
        
        cursor = self.connection.cursor()
        try:
            where_conditions = []
            params = []
            
            if start_time:
                where_conditions.append('start_time >= ?')
                params.append(start_time)
            if end_time:
                where_conditions.append('end_time <= ?')
                params.append(end_time)
            
            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
            params.extend([limit, offset])
            
            cursor.execute(f'''
                SELECT id, title, content, resources, metadata, start_time, end_time
                FROM activity
                WHERE {where_clause}
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            ''', params)
            
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
            cursor.execute('''
                INSERT INTO tips (content, created_at)
                VALUES (?, ?)
            ''', (content, datetime.now()))

            tip_id = cursor.lastrowid
            self.connection.commit()
            logger.info(f"Tip inserted, ID: {tip_id}")
            return tip_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"Failed to insert tip: {e}")
            raise

    def get_tips(self, start_time: datetime = None, end_time: datetime = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get tip list"""
        if not self._initialized:
            return []

        cursor = self.connection.cursor()
        try:
            where_conditions = []
            params = []

            if start_time:
                where_conditions.append('created_at >= ?')
                params.append(start_time.isoformat())
            if end_time:
                where_conditions.append('created_at <= ?')
                params.append(end_time.isoformat())

            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
            params.extend([limit, offset])

            cursor.execute(f'''
                SELECT id, content, created_at
                FROM tips
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', params)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Failed to get tip list: {e}")
            return []
    
    def get_name(self) -> str:
        return "sqlite"
    
    def get_storage_type(self) -> StorageType:
        return StorageType.DOCUMENT_DB

    def query(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
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
                where_conditions.append('(content LIKE ? OR JSON_EXTRACT(metadata, "$.title") LIKE ?)')
                query_pattern = f'%{query}%'
                params.extend([query_pattern, query_pattern])

            # Filter conditions
            if filters:
                if 'content_type' in filters:
                    where_conditions.append('JSON_EXTRACT(metadata, "$.content_type") = ?')
                    params.append(filters['content_type'])

                if 'data_type' in filters:
                    where_conditions.append('data_type = ?')
                    params.append(filters['data_type'])

                if 'tags' in filters:
                    tags = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append('document_tags.tag = ?')
                        params.append(tag.lower())

                    if tag_conditions:
                        where_conditions.append(f'id IN (SELECT document_id FROM document_tags WHERE {" OR ".join(tag_conditions)})')

            # Build SQL query
            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

            # Get documents
            sql = f'''
                SELECT DISTINCT d.id, d.content, d.data_type, d.metadata, d.created_at, d.updated_at
                FROM documents d
                LEFT JOIN document_tags dt ON d.id = dt.document_id
                WHERE {where_clause}
                ORDER BY d.updated_at DESC
                LIMIT ?
            '''
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            documents = []
            for row in rows:
                # Get images for each document
                cursor.execute('SELECT image_path FROM images WHERE document_id = ? ORDER BY id', (row['id'],))
                images = [img_row[0] for img_row in cursor.fetchall()]

                # Parse metadata
                metadata = {}
                if row['metadata']:
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        pass

                documents.append(DocumentData(
                    id=row['id'],
                    content=row['content'],
                    metadata=metadata,
                    data_type=DataType(row['data_type']),
                    images=images if images else None
                ))

            # Get total count
            count_sql = f'''
                SELECT COUNT(DISTINCT d.id)
                FROM documents d
                LEFT JOIN document_tags dt ON d.id = dt.document_id
                WHERE {where_clause}
            '''
            cursor.execute(count_sql, params[:-1])  # Exclude limit parameter
            total_count = cursor.fetchone()[0]

            return QueryResult(
                documents=documents,
                total_count=total_count
            )

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