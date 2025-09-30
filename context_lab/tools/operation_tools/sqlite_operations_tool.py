#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
SQLite 数据库操作工具
提供 SQLite 数据库的查询、更新、插入、删除等操作，支持 diff 对比和审核机制
"""

import sqlite3
import json
import copy
import re
from typing import Dict, Any, Optional, List, Union, Tuple
from context_lab.tools.base import BaseTool
from context_lab.storage.global_storage import get_storage
from context_lab.utils.logging_utils import get_logger
from context_lab.config.global_config import get_config

logger = get_logger(__name__)


class SQLiteOperationsTool(BaseTool):
    """SQLite 数据库操作工具"""
    
    def __init__(self):
        super().__init__()
        # 从配置中获取SQLite操作配置
        self.sqlite_config = get_config('tools.operation_tools.sqlite_operations') or {}
        self.always_approve = self.sqlite_config.get('always_approve', False)
        self.max_rows = self.sqlite_config.get('max_rows', 1000)
        # 允许的数据库操作
        self.allowed_operations = self.sqlite_config.get('allowed_operations', [
            'select', 'insert', 'update', 'delete'
        ])
    
    @property
    def storage(self):
        """从全局单例获取 storage"""
        return get_storage()
    
    @classmethod
    def get_name(cls) -> str:
        return "sqlite_operations"
    
    @classmethod
    def get_description(cls) -> str:
        return "执行 SQLite 数据库操作，包括查询、插入、更新、删除记录。修改操作支持 diff 预览和审核确认机制。"
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["select", "insert", "update", "delete", "schema", "tables"],
                    "description": "操作类型：select(查询), insert(插入), update(更新), delete(删除), schema(查看表结构), tables(列举表)"
                },
                "table": {
                    "type": "string",
                    "description": "表名"
                },
                "sql": {
                    "type": "string",
                    "description": "自定义SQL语句（高级用法）"
                },
                "where": {
                    "type": "string",
                    "description": "WHERE 条件语句"
                },
                "data": {
                    "type": "object",
                    "description": "插入或更新的数据，键值对形式"
                },
                "limit": {
                    "type": "integer",
                    "description": "查询结果限制数量，默认 100",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100
                },
                "always_approve": {
                    "type": "boolean",
                    "description": "是否自动批准修改操作（跳过 diff 确认），默认 false",
                    "default": False
                },
                "preview_only": {
                    "type": "boolean",
                    "description": "是否仅预览不执行（仅显示 diff），默认 false",
                    "default": False
                }
            },
            "required": ["operation"]
        }
    
    def execute(self, operation: str, table: str = None, sql: str = None, where: str = None,
                data: Dict[str, Any] = None, limit: int = 100, always_approve: bool = None,
                preview_only: bool = False, **kwargs) -> Dict[str, Any]:
        """执行 SQLite 操作"""
        try:
            # 检查操作是否被允许
            if operation not in self.allowed_operations and operation not in ['schema', 'tables']:
                return {
                    "success": False,
                    "error": f"操作不被允许: {operation}",
                    "operation": operation
                }
            
            # 获取数据库连接
            db_path = self._get_db_path()
            if not db_path:
                return {
                    "success": False,
                    "error": "无法获取数据库路径",
                    "operation": operation
                }
            
            # 如果有自定义SQL，优先使用
            if sql:
                return self._execute_custom_sql(sql, limit, preview_only)
            
            # 设置 always_approve 默认值
            if always_approve is None:
                always_approve = self.always_approve
            
            # 根据操作类型执行
            if operation == "select":
                return self._select_data(db_path, table, where, limit)
            elif operation == "insert":
                return self._insert_data(db_path, table, data, always_approve, preview_only)
            elif operation == "update":
                return self._update_data(db_path, table, data, where, always_approve, preview_only)
            elif operation == "delete":
                return self._delete_data(db_path, table, where, always_approve, preview_only)
            elif operation == "schema":
                return self._get_table_schema(db_path, table)
            elif operation == "tables":
                return self._list_tables(db_path)
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作类型: {operation}",
                    "operation": operation
                }
                
        except Exception as e:
            logger.error(f"SQLite operation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    def _get_db_path(self) -> Optional[str]:
        """获取数据库路径"""
        try:
            if self.storage and hasattr(self.storage, 'document_storage'):
                backend = self.storage.document_storage.backend
                if hasattr(backend, 'db_path'):
                    return backend.db_path
            
            # 备用方案：使用配置中的路径
            return self.sqlite_config.get('db_path', './persist/sqlite/app.db')
            
        except Exception as e:
            logger.error(f"Failed to get database path: {e}")
            return None
    
    def _execute_custom_sql(self, sql: str, limit: int, preview_only: bool) -> Dict[str, Any]:
        """执行自定义SQL"""
        try:
            db_path = self._get_db_path()
            
            # 安全检查：防止危险操作
            sql_upper = sql.upper().strip()
            dangerous_keywords = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE']
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return {
                        "success": False,
                        "error": f"不允许执行包含 {keyword} 的 SQL 语句",
                        "sql": sql
                    }
            
            if preview_only and not sql_upper.startswith('SELECT'):
                return {
                    "success": False,
                    "error": "预览模式仅支持 SELECT 语句",
                    "sql": sql
                }
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if sql_upper.startswith('SELECT'):
                    # 查询操作
                    cursor.execute(sql)
                    rows = cursor.fetchmany(limit) if limit else cursor.fetchall()
                    
                    return {
                        "success": True,
                        "operation": "custom_select",
                        "sql": sql,
                        "rows": [dict(row) for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    # 修改操作
                    if preview_only:
                        return {
                            "success": True,
                            "operation": "custom_preview",
                            "sql": sql,
                            "message": "预览：将执行自定义SQL语句",
                            "requires_approval": True
                        }
                    
                    cursor.execute(sql)
                    conn.commit()
                    
                    return {
                        "success": True,
                        "operation": "custom_modify",
                        "sql": sql,
                        "affected_rows": cursor.rowcount,
                        "message": f"SQL 执行成功，影响 {cursor.rowcount} 行"
                    }
                    
        except Exception as e:
            logger.error(f"Custom SQL execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }
    
    def _validate_table_name(self, table: str) -> bool:
        """验证表名是否安全，防止SQL注入"""
        if not table or not isinstance(table, str):
            return False
        # 只允许字母、数字、下划线，且必须以字母或下划线开头
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table))
    
    def _select_data(self, db_path: str, table: str, where: str, limit: int) -> Dict[str, Any]:
        """查询数据"""
        try:
            if not table:
                return {
                    "success": False,
                    "error": "表名不能为空",
                    "operation": "select"
                }
            
            # 验证表名安全性
            if not self._validate_table_name(table):
                return {
                    "success": False,
                    "error": "表名格式不合法，仅允许字母、数字和下划线",
                    "operation": "select"
                }
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询SQL，使用参数化查询
                sql = f"SELECT * FROM `{table}`"  # 使用反引号包围表名
                params = []
                
                if where:
                    sql += f" WHERE {where}"
                
                sql += f" LIMIT {limit}"
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                return {
                    "success": True,
                    "operation": "select",
                    "table": table,
                    "where": where,
                    "rows": [dict(row) for row in rows],
                    "row_count": len(rows),
                    "sql": sql
                }
                
        except Exception as e:
            logger.exception(f"Select data failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "select",
                "table": table
            }
    
    def _insert_data(self, db_path: str, table: str, data: Dict[str, Any], 
                     always_approve: bool, preview_only: bool) -> Dict[str, Any]:
        """插入数据"""
        try:
            if not table or not data:
                return {
                    "success": False,
                    "error": "表名和数据不能为空",
                    "operation": "insert"
                }
            
            # 验证表名安全性
            if not self._validate_table_name(table):
                return {
                    "success": False,
                    "error": "表名格式不合法，仅允许字母、数字和下划线",
                    "operation": "insert"
                }
            
            # 构建插入SQL
            columns = list(data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            sql = f"INSERT INTO `{table}` ({', '.join(columns)}) VALUES ({placeholders})"
            values = list(data.values())
            
            if preview_only or not always_approve:
                # 生成 diff 信息
                diff_info = {
                    "type": "insert",
                    "table": table,
                    "operation": "INSERT",
                    "new_data": data,
                    "sql": sql,
                    "values": values
                }
                
                result = {
                    "success": True,
                    "operation": "insert",
                    "table": table,
                    "diff": diff_info,
                    "requires_approval": not always_approve,
                    "preview": f"将向表 {table} 插入 1 条记录"
                }
                
                if preview_only:
                    result["message"] = "仅预览，未执行插入操作"
                    return result
                
                if not always_approve:
                    result["message"] = "插入操作需要确认，请审查 diff 信息"
                    return result
            
            # 执行插入
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, values)
                conn.commit()
                
                return {
                    "success": True,
                    "operation": "insert",
                    "table": table,
                    "affected_rows": cursor.rowcount,
                    "last_row_id": cursor.lastrowid,
                    "message": f"成功插入 {cursor.rowcount} 条记录"
                }
                
        except Exception as e:
            logger.error(f"Insert data failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "insert",
                "table": table
            }
    
    def _update_data(self, db_path: str, table: str, data: Dict[str, Any], where: str,
                     always_approve: bool, preview_only: bool) -> Dict[str, Any]:
        """更新数据"""
        try:
            if not table or not data:
                return {
                    "success": False,
                    "error": "表名和更新数据不能为空",
                    "operation": "update"
                }
            
            if not where:
                return {
                    "success": False,
                    "error": "更新操作必须指定 WHERE 条件以确保安全",
                    "operation": "update"
                }
            
            # 首先查询受影响的行（用于生成 diff）
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 查询当前数据
                select_sql = f"SELECT * FROM {table} WHERE {where}"
                cursor.execute(select_sql)
                old_rows = [dict(row) for row in cursor.fetchall()]
                
                if not old_rows:
                    return {
                        "success": False,
                        "error": "WHERE 条件未匹配到任何记录",
                        "operation": "update",
                        "table": table,
                        "where": where
                    }
                
                # 构建更新SQL
                set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
                update_sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
                values = list(data.values())
                
                if preview_only or not always_approve:
                    # 生成 diff 信息
                    changes = []
                    for old_row in old_rows:
                        row_changes = {}
                        for col, new_val in data.items():
                            if col in old_row and old_row[col] != new_val:
                                row_changes[col] = {
                                    "old": old_row[col],
                                    "new": new_val
                                }
                        if row_changes:
                            changes.append({
                                "row_id": old_row.get('id', 'unknown'),
                                "changes": row_changes
                            })
                    
                    diff_info = {
                        "type": "update",
                        "table": table,
                        "operation": "UPDATE",
                        "where": where,
                        "affected_rows": len(old_rows),
                        "changes": changes,
                        "sql": update_sql,
                        "values": values
                    }
                    
                    result = {
                        "success": True,
                        "operation": "update",
                        "table": table,
                        "diff": diff_info,
                        "requires_approval": not always_approve,
                        "preview": f"将更新表 {table} 中的 {len(old_rows)} 条记录"
                    }
                    
                    if preview_only:
                        result["message"] = "仅预览，未执行更新操作"
                        return result
                    
                    if not always_approve:
                        result["message"] = "更新操作需要确认，请审查 diff 信息"
                        return result
                
                # 执行更新
                cursor.execute(update_sql, values)
                conn.commit()
                
                return {
                    "success": True,
                    "operation": "update",
                    "table": table,
                    "where": where,
                    "affected_rows": cursor.rowcount,
                    "message": f"成功更新 {cursor.rowcount} 条记录"
                }
                
        except Exception as e:
            logger.error(f"Update data failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "update",
                "table": table
            }
    
    def _delete_data(self, db_path: str, table: str, where: str,
                     always_approve: bool, preview_only: bool) -> Dict[str, Any]:
        """删除数据"""
        try:
            if not table:
                return {
                    "success": False,
                    "error": "表名不能为空",
                    "operation": "delete"
                }
            
            if not where:
                return {
                    "success": False,
                    "error": "删除操作必须指定 WHERE 条件以确保安全",
                    "operation": "delete"
                }
            
            # 首先查询要删除的行（用于生成 diff）
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 查询要删除的数据
                select_sql = f"SELECT * FROM {table} WHERE {where}"
                cursor.execute(select_sql)
                rows_to_delete = [dict(row) for row in cursor.fetchall()]
                
                if not rows_to_delete:
                    return {
                        "success": False,
                        "error": "WHERE 条件未匹配到任何记录",
                        "operation": "delete",
                        "table": table,
                        "where": where
                    }
                
                delete_sql = f"DELETE FROM {table} WHERE {where}"
                
                if preview_only or not always_approve:
                    # 生成 diff 信息
                    diff_info = {
                        "type": "delete",
                        "table": table,
                        "operation": "DELETE",
                        "where": where,
                        "affected_rows": len(rows_to_delete),
                        "deleted_data": rows_to_delete,
                        "sql": delete_sql
                    }
                    
                    result = {
                        "success": True,
                        "operation": "delete",
                        "table": table,
                        "diff": diff_info,
                        "requires_approval": not always_approve,
                        "preview": f"将从表 {table} 删除 {len(rows_to_delete)} 条记录"
                    }
                    
                    if preview_only:
                        result["message"] = "仅预览，未执行删除操作"
                        return result
                    
                    if not always_approve:
                        result["message"] = "删除操作需要确认，请审查 diff 信息"
                        return result
                
                # 执行删除
                cursor.execute(delete_sql)
                conn.commit()
                
                return {
                    "success": True,
                    "operation": "delete",
                    "table": table,
                    "where": where,
                    "affected_rows": cursor.rowcount,
                    "message": f"成功删除 {cursor.rowcount} 条记录"
                }
                
        except Exception as e:
            logger.error(f"Delete data failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "delete",
                "table": table
            }
    
    def _get_table_schema(self, db_path: str, table: str) -> Dict[str, Any]:
        """获取表结构"""
        try:
            if not table:
                return {
                    "success": False,
                    "error": "表名不能为空",
                    "operation": "schema"
                }
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                if not columns:
                    return {
                        "success": False,
                        "error": f"表 {table} 不存在",
                        "operation": "schema",
                        "table": table
                    }
                
                schema_info = []
                for col in columns:
                    schema_info.append({
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "default_value": col[4],
                        "primary_key": bool(col[5])
                    })
                
                return {
                    "success": True,
                    "operation": "schema",
                    "table": table,
                    "columns": schema_info,
                    "column_count": len(schema_info)
                }
                
        except Exception as e:
            logger.error(f"Get table schema failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "schema",
                "table": table
            }
    
    def _list_tables(self, db_path: str) -> Dict[str, Any]:
        """列举所有表"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 查询所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [row[0] for row in cursor.fetchall()]
                
                return {
                    "success": True,
                    "operation": "tables",
                    "tables": tables,
                    "table_count": len(tables)
                }
                
        except Exception as e:
            logger.error(f"List tables failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "tables"
            }