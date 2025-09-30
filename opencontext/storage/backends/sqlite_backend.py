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
                   status: int = 0, urgency: int = 0, assignee: str = None) -> int:
        """Insert todo item"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")
        
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO todo (content, start_time, end_time, status, urgency, assignee, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (content, start_time or datetime.now(), end_time, status, urgency, assignee, datetime.now()))
            
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
                SELECT id, content, created_at, start_time, end_time, status, urgency, assignee
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
    
    # Tips表操作
    def insert_tip(self, content: str) -> int:
        """插入提示"""
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
            logger.info(f"提示已插入，ID: {tip_id}")
            return tip_id
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"插入提示失败: {e}")
            raise
    
    def get_tips(self, start_time: datetime = None, end_time: datetime = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取提示列表"""
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
            logger.exception(f"获取提示列表失败: {e}")
            return []
    
    def get_name(self) -> str:
        return "sqlite"
    
    def get_storage_type(self) -> StorageType:
        return StorageType.DOCUMENT_DB
    
    def store_generated_document(self, doc_id: str, document_type: str, title: str, content: str, 
                                summary: str = None, generation_params: dict = None, 
                                source_time_start: int = None, source_time_end: int = None,
                                metadata: dict = None, tags: list = None) -> str:
        """存储生成文档"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO generated_documents 
                (id, document_type, title, content, summary, generation_status, generation_params,
                 source_time_start, source_time_end, metadata, tags, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                doc_id,
                document_type,
                title,
                content,
                summary,
                json.dumps(generation_params, ensure_ascii=False) if generation_params else None,
                source_time_start,
                source_time_end,
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
                ','.join(tags) if tags else None
            ))
            
            self.connection.commit()
            logger.info(f"生成文档已存储到SQLite: {doc_id}")
            return doc_id
            
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"存储生成文档到SQLite失败: {e}")
            raise
    
    def append_to_document(self, doc_id: str, append_content: str, append_params: dict = None,
                          source_time_start: int = None, source_time_end: int = None) -> bool:
        """追加内容到现有文档"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")
        
        cursor = self.connection.cursor()
        
        try:
            # 检查文档是否存在
            cursor.execute('SELECT id, content, append_count FROM generated_documents WHERE id = ?', (doc_id,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"文档 {doc_id} 不存在，无法追加内容")
                return False
            
            current_content = row['content']
            current_append_count = row['append_count']
            
            # 追加内容
            new_content = current_content + "\n\n" + append_content
            new_append_count = current_append_count + 1
            
            # 更新主文档
            cursor.execute('''
                UPDATE generated_documents 
                SET content = ?, append_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_content, new_append_count, doc_id))
            
            # 记录追加历史
            cursor.execute('''
                INSERT INTO document_append_history 
                (document_id, append_content, append_params, source_time_start, source_time_end)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                doc_id,
                append_content,
                json.dumps(append_params, ensure_ascii=False) if append_params else None,
                source_time_start,
                source_time_end
            ))
            
            self.connection.commit()
            logger.info(f"文档 {doc_id} 已追加内容，追加次数增加到 {new_append_count}")
            return True
            
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"追加内容到文档 {doc_id} 失败: {e}")
            return False
    
    def update_document_status(self, doc_id: str, status: str, error_message: str = None) -> bool:
        """更新文档生成状态"""
        if not self._initialized:
            return False
        
        cursor = self.connection.cursor()
        
        try:
            if status == 'completed':
                cursor.execute('''
                    UPDATE generated_documents 
                    SET generation_status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP,
                        completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, doc_id))
            else:
                cursor.execute('''
                    UPDATE generated_documents 
                    SET generation_status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, doc_id))
            
            self.connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"更新文档状态失败: {e}")
            return False
    
    def list_generated_documents(self, document_type: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """列出生成文档"""
        if not self._initialized:
            return []
        
        cursor = self.connection.cursor()
        
        try:
            where_clause = ""
            params = []
            
            if document_type:
                where_clause = "WHERE document_type = ?"
                params.append(document_type)
            
            sql = f'''
                SELECT id, document_type, title, summary, generation_status,
                       created_at, updated_at, completed_at, append_count, tags
                FROM generated_documents
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            documents = []
            for row in rows:
                documents.append({
                    'id': row['id'],
                    'document_type': row['document_type'],
                    'title': row['title'],
                    'summary': row['summary'],
                    'generation_status': row['generation_status'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'completed_at': row['completed_at'],
                    'append_count': row['append_count'],
                    'tags': row['tags'].split(',') if row['tags'] else []
                })
            
            return documents
            
        except Exception as e:
            logger.exception(f"列出生成文档失败: {e}")
            return []
    
    def delete_generated_document(self, doc_id: str) -> bool:
        """删除生成文档"""
        if not self._initialized:
            return False
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute('DELETE FROM generated_documents WHERE id = ?', (doc_id,))
            deleted_count = cursor.rowcount
            self.connection.commit()
            
            if deleted_count > 0:
                logger.info(f"已从SQLite删除生成文档: {doc_id}")
                return True
            else:
                logger.warning(f"SQLite中未找到要删除的生成文档: {doc_id}")
                return False
                
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"从SQLite删除生成文档失败: {e}")
            return False
    
    def store(self, document: DocumentData) -> str:
        """存储单个文档（保持向后兼容）"""
        return self.store_generated_document(
            doc_id=document.id,
            document_type='legacy',
            title=document.metadata.get('title', ''),
            content=document.content,
            metadata=document.metadata
        )
    
    def _process_image_path(self, image_path: str) -> str:
        """处理图片路径，添加opencontext://协议"""
        if not image_path.startswith('MineContext://'):
            return f'MineContext://{image_path}'
        return image_path
    
    def _update_document_tags(self, doc_id: str, metadata: Dict[str, Any]):
        """更新文档标签"""
        cursor = self.connection.cursor()
        
        # 删除旧标签
        cursor.execute('DELETE FROM document_tags WHERE document_id = ?', (doc_id,))
        
        # 添加新标签
        tags = set()
        
        # 从metadata中提取标签
        if 'tags' in metadata and isinstance(metadata['tags'], list):
            tags.update(metadata['tags'])
        
        if 'content_type' in metadata:
            tags.add(metadata['content_type'])
        
        if 'title' in metadata:
            # 简单的关键词提取
            title_words = metadata['title'].split()[:3]  # 取前3个词作为标签
            tags.update(title_words)
        
        # 插入标签
        for tag in tags:
            if tag and isinstance(tag, str):
                cursor.execute('''
                    INSERT OR IGNORE INTO document_tags (document_id, tag)
                    VALUES (?, ?)
                ''', (doc_id, tag.lower()))
    
    def batch_store(self, documents: List[DocumentData]) -> List[str]:
        """批量存储文档"""
        stored_ids = []
        for document in documents:
            try:
                doc_id = self.store(document)
                stored_ids.append(doc_id)
            except Exception as e:
                logger.error(f"批量存储文档 {document.id} 失败: {e}")
        return stored_ids
    
    def get_generated_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取生成文档"""
        if not self._initialized:
            return None
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute('''
                SELECT id, document_type, title, content, summary, generation_status,
                       generation_params, error_message, created_at, updated_at, completed_at,
                       source_time_start, source_time_end, parent_document_id, append_count,
                       metadata, tags
                FROM generated_documents WHERE id = ?
            ''', (doc_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 获取关联的图片
            cursor.execute('''
                SELECT image_path, image_type FROM document_images 
                WHERE document_id = ? 
                ORDER BY created_at
            ''', (doc_id,))
            
            images = [{'path': img_row[0], 'type': img_row[1]} for img_row in cursor.fetchall()]
            
            # 解析JSON字段
            generation_params = None
            if row['generation_params']:
                try:
                    generation_params = json.loads(row['generation_params'])
                except json.JSONDecodeError:
                    pass
            
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    pass
            
            tags = row['tags'].split(',') if row['tags'] else []
            
            return {
                'id': row['id'],
                'document_type': row['document_type'],
                'title': row['title'],
                'content': row['content'],
                'summary': row['summary'],
                'generation_status': row['generation_status'],
                'generation_params': generation_params,
                'error_message': row['error_message'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'completed_at': row['completed_at'],
                'source_time_start': row['source_time_start'],
                'source_time_end': row['source_time_end'],
                'parent_document_id': row['parent_document_id'],
                'append_count': row['append_count'],
                'metadata': metadata,
                'tags': tags,
                'images': images
            }
            
        except Exception as e:
            logger.exception(f"从SQLite获取生成文档失败: {e}")
            return None
    
    def get(self, doc_id: str) -> Optional[DocumentData]:
        """根据ID获取文档（保持向后兼容）"""
        # 先尝试从新表获取
        doc = self.get_generated_document(doc_id)
        if doc:
            return DocumentData(
                id=doc['id'],
                content=doc['content'],
                metadata=doc['metadata'],
                data_type=DataType.MARKDOWN,  # 默认类型
                images=[img['path'] for img in doc['images']] if doc['images'] else None
            )
        return None
    
    def query(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """查询文档"""
        return self.text_search(query, limit, filters)
    
    def text_search(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """文本搜索"""
        if not self._initialized:
            return QueryResult(documents=[], total_count=0)
        
        cursor = self.connection.cursor()
        
        try:
            # 构建查询条件
            where_conditions = []
            params = []
            
            # 文本搜索条件
            if query:
                where_conditions.append('(content LIKE ? OR JSON_EXTRACT(metadata, "$.title") LIKE ?)')
                query_pattern = f'%{query}%'
                params.extend([query_pattern, query_pattern])
            
            # 过滤条件
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
            
            # 构建SQL查询
            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
            
            # 获取文档
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
                # 获取每个文档的图片
                cursor.execute('SELECT image_path FROM images WHERE document_id = ? ORDER BY id', (row['id'],))
                images = [img_row[0] for img_row in cursor.fetchall()]
                
                # 解析metadata
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
            
            # 获取总数
            count_sql = f'''
                SELECT COUNT(DISTINCT d.id)
                FROM documents d
                LEFT JOIN document_tags dt ON d.id = dt.document_id
                WHERE {where_clause}
            '''
            cursor.execute(count_sql, params[:-1])  # 排除limit参数
            total_count = cursor.fetchone()[0]
            
            return QueryResult(
                documents=documents,
                total_count=total_count
            )
            
        except Exception as e:
            logger.exception(f"SQLite文本搜索失败: {e}")
            return QueryResult(documents=[], total_count=0)
    
    def update(self, doc_id: str, document: DocumentData) -> bool:
        """更新文档（保持向后兼容）"""
        try:
            # 更新时使用相同的存储逻辑
            updated_id = self.store(document)
            return updated_id == doc_id
        except Exception as e:
            logger.exception(f"更新SQLite文档失败: {e}")
            return False
    
    def delete(self, doc_id: str) -> bool:
        """删除文档（保持向后兼容）"""
        # 先尝试从新表删除
        return self.delete_generated_document(doc_id)
    
    def list_documents(self, limit: int = 100, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> QueryResult:
        """列出文档（保持向后兼容）"""
        return self.query('', limit, filters)
    
    def store_image(self, image_data: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        """存储图片数据"""
        if not self._initialized:
            raise RuntimeError("SQLite backend not initialized")
        
        cursor = self.connection.cursor()
        
        try:
            # 生成图片ID
            image_id = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # 如果是字节数据，需要保存到文件系统
            if isinstance(image_data, bytes):
                # 创建图片存储目录
                image_dir = os.path.join(os.path.dirname(self.db_path), 'images')
                os.makedirs(image_dir, exist_ok=True)
                
                # 保存图片文件
                image_path = os.path.join(image_dir, f"{image_id}.png")
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                
                # 使用opencontext://协议
                stored_path = f"MineContext://{image_path}"
            else:
                # 字符串路径直接处理
                stored_path = self._process_image_path(image_data)
            
            # 存储到数据库
            cursor.execute('''
                INSERT INTO images (id, image_path, metadata)
                VALUES (?, ?, ?)
            ''', (
                image_id,
                stored_path,
                json.dumps(metadata, ensure_ascii=False)
            ))
            
            self.connection.commit()
            return stored_path
            
        except Exception as e:
            self.connection.rollback()
            logger.exception(f"存储图片到SQLite失败: {e}")
            raise
    
    def get_image(self, image_id: str) -> Optional[Union[str, bytes]]:
        """获取图片数据"""
        if not self._initialized:
            return None
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute('SELECT image_path FROM images WHERE id = ?', (image_id,))
            row = cursor.fetchone()
            
            if row:
                image_path = row[0]
                
                # 如果是opencontext://协议，返回路径
                if image_path.startswith('MineContext://'):
                    return image_path
                
                # 尝试读取文件内容
                if os.path.isfile(image_path):
                    with open(image_path, 'rb') as f:
                        return f.read()
            
            return None
            
        except Exception as e:
            logger.exception(f"从SQLite获取图片失败: {e}")
            return None
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self._initialized = False
            logger.info("SQLite database connection closed")