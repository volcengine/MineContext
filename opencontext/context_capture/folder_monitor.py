#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Vault document monitoring component that monitors changes in the vaults table and generates context capture events
"""

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import json

from opencontext.context_capture import BaseCaptureComponent
from opencontext.models.context import RawContextProperties
from opencontext.models.enums import ContentFormat, ContextSource
from opencontext.context_processing.processor.document_processor import DocumentProcessor
from opencontext.storage.global_storage import get_storage
from opencontext.utils.logging_utils import get_logger
import hashlib
import os

logger = get_logger(__name__)


class VaultDocumentMonitor(BaseCaptureComponent):
    """
    Vault document monitoring component that monitors changes in the vaults table and generates context capture events
    """

    def __init__(self):
        """Initialize Vault document monitoring component"""
        super().__init__(
            name="VaultDocumentMonitor",
            description="Monitor document changes in vaults table",
            source_type=ContextSource.TEXT,
        )
        self._storage = None
        self._monitor_interval = 5  # Monitor interval (seconds)
        self._last_scan_time = None
        self._processed_vault_ids: Set[int] = set()
        # 文档id
        self._processed_folder_ids: Set[int] = set()
        self._document_events = []
        # 文件夹事件
        self._folder_events = []
        self._event_lock = threading.RLock()
        self._monitor_thread = None
        self._stop_event = threading.Event()

        # Statistics
        self._total_processed = 0
        self._last_activity_time = None

    def _initialize_impl(self, config: Dict[str, Any]) -> bool:
        """
        Initialize document monitoring component

        Args:
            config: Component configuration

        Returns:
            bool: Whether initialization was successful
        """
        try:
            # 理论上如果直接走folder就不需要再额外保存storage
            self._storage = get_storage()
            self._monitor_interval = config.get("monitor_interval", 5)
            self._watch_folder_paths = config.get("watch_folder_path", ["./watch_folder"])
            self._recursive = config.get("recursive", True)
            self._max_file_size = config.get("max_file_size", 104857600)

            # 存储文件信息的字典，用于检测变化
            self._file_info_cache = {}  # {file_path: {"mtime": float, "size": int, "hash": str}}

            # Set initial scan time to current time
            self._last_scan_time = datetime.now()

            logger.info(
                f"watch folders: {self._watch_folder_paths}, recursive: {self._recursive}, max file size: {self._max_file_size} bytes"
            )
            return True
        except Exception as e:
            logger.exception(f"文件夹扫描失败: {e}")
            logger.exception(f"Failed to initialize Vault document monitoring component: {str(e)}")
            return False

    def _start_impl(self) -> bool:
        """
        Start document monitoring

        Returns:
            bool: Whether startup was successful
        """
        try:
            # If initial scan is configured, scan existing documents first
            if self._config.get("initial_scan", True):
                self._scan_existing_documents()

            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, name="vault_document_monitor", daemon=True
            )
            self._monitor_thread.start()

            logger.info("Vault document monitoring started")
            return True
        except Exception as e:
            logger.exception(f"Failed to start Vault document monitoring: {str(e)}")
            return False

    def _stop_impl(self, graceful: bool = True) -> bool:
        """
        Stop document monitoring

        Returns:
            bool: Whether stopping was successful
        """
        try:
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=10 if graceful else 1)

            logger.info("Vault document monitoring stopped")
            return True
        except Exception as e:
            logger.exception(f"Failed to stop Vault document monitoring: {str(e)}")
            return False

    def _capture_impl(self) -> List[RawContextProperties]:
        """
        Execute document capture

        Returns:
            List[RawContextProperties]: List of captured context data
        """
        try:
            result = []

            # Get document events and process them
            with self._event_lock:
                events = self._document_events.copy()
                self._document_events.clear()

            for event in events:
                # 处理文件事件
                if event.get("event_type") in ["file_created", "file_updated", "file_deleted"]:
                    self._process_file_event(event)
                
                # 创建上下文数据
                context_data = self._create_context_from_event(event)
                if context_data:
                    result.append(context_data)
                    self._total_processed += 1

            return result
        except Exception as e:
            logger.exception(f"Document capture failed: {str(e)}")
            return []

    def _monitor_loop(self):
        """Monitor loop that periodically checks changes in the vaults table"""
        while not self._stop_event.is_set():
            try:
                self._scan_vault_changes()
                time.sleep(self._monitor_interval)
            except Exception as e:
                logger.exception(f"Monitor loop error: {e}")
                time.sleep(self._monitor_interval)

    def _get_file_hash(self, file_path: str) -> str:
        """
        计算文件的 SHA-256 哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件的哈希值
        """
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                # 分块读取文件以处理大文件
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for file {file_path}: {e}")
            return ""

    

    def _scan_folder_files(self, folder_path: str, recursive: bool = True) -> List[str]:
        """
        扫描文件夹中的所有文件
        
        Args:
            folder_path: 文件夹路径
            recursive: 是否递归扫描子文件夹
            
        Returns:
            List[str]: 文件路径列表
        """
        files = []
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                logger.warning(f"Folder does not exist or is not a directory: {folder_path}")
                return files

            if recursive:
                # 递归扫描所有文件
                for file_path in folder_path.rglob('*'):
                    file_ext = Path(context.content_path).suffix.lower()
                    if file_path.is_file() and file_ext in DocumentProcessor.get_supported_formats():
                        # 检查文件大小
                        try:
                            if file_path.stat().st_size <= self._max_file_size:
                                files.append(str(file_path.absolute()))
                        except OSError as e:
                            logger.warning(f"Failed to get file stats for {file_path}: {e}")
            else:
                # 只扫描当前文件夹
                for file_path in folder_path.iterdir():
                    if file_path.is_file() and self._is_supported_file_type(str(file_path)):
                        # 检查文件大小
                        try:
                            if file_path.stat().st_size <= self._max_file_size:
                                files.append(str(file_path.absolute()))
                        except OSError as e:
                            logger.warning(f"Failed to get file stats for {file_path}: {e}")

        except Exception as e:
            logger.exception(f"Error scanning folder {folder_path}: {e}")

        return files

    def _get_folder_ids(self, folder_path: str) -> int:
        """使用哈希算法把folder_path转换为一个uni的id"""
        # 使用SHA-256哈希算法生成唯一ID
        folder_id = int(hashlib.sha256(folder_path.encode('utf-8')).hexdigest(), 16) % (10 ** 16)
        return folder_id

    def _scan_existing_folder(self, config: Dict[str, Any]):
        """Scan existing folder (initial scan)"""
        folders = config.get("watch_folder_path", "./watch_folder")
        for folder in folders:
            folder_id = self._get_folder_ids(folder)
            if os.path.isdir(folder):
                event = {
                    "event_type": "existing",
                    "folder_id": folder_id,
                    "folder_path": folder,
                    "timestamp": datetime.now(),
                }
                with self._event_lock:
                    self._folder_events.append(event)

                self._processed_folder_ids.add(folder_id)


    def _scan_existing_documents(self):
        """Scan existing documents (initial scan)"""
        try:
            logger.info("Starting initial scan of existing vault documents")
            documents = self._storage.get_vaults(limit=1000, offset=0, is_deleted=False)

            for doc in documents:
                if doc["id"] not in self._processed_vault_ids:
                    event = {
                        "event_type": "existing",
                        "vault_id": doc["id"],
                        "document_data": doc,
                        "timestamp": datetime.now(),
                    }

                    with self._event_lock:
                        self._document_events.append(event)

                    self._processed_vault_ids.add(doc["id"])

            logger.info(f"Initial scan completed, found {len(documents)} documents")
        except Exception as e:
            logger.exception(f"Initial scan failed: {e}")

    def _scan_folder_file_changes(self):
        """扫描配置文件夹中的文件变化"""
        try:
            # todo 这里是对自身的文件做扫描，如果在这个场景，应该要对文件夹（config）内部的文件做扫描。所以需要在外部获取到所有文件夹内的文件信息。os path遍历一次。同时要在这里注意处理不同的文件
            # Get recent documents (based on created_at and updated_at)
            current_time = datetime.now()
            new_files = []
            updated_files = []
            deleted_files = []

            # 获取当前所有文件
            current_files = set()
            for folder_path in self._watch_folder_paths:
                folder_files = self._scan_folder_files(folder_path, self._recursive)
                current_files.update(folder_files)

            # 检测新文件和更新的文件
            for file_path in current_files:
                try:
                    file_stat = os.stat(file_path)
                    file_mtime = file_stat.st_mtime
                    file_size = file_stat.st_size

                    if file_path not in self._file_info_cache:
                        # 新文件
                        file_hash = self._get_file_hash(file_path)
                        self._file_info_cache[file_path] = {
                            "mtime": file_mtime,
                            "size": file_size,
                            "hash": file_hash
                        }
                        new_files.append(file_path)
                        logger.debug(f"Detected new file: {file_path}")
                    else:
                        # 检查文件是否有变化
                        cached_info = self._file_info_cache[file_path]
                        if (file_mtime > cached_info["mtime"] or 
                            file_size != cached_info["size"]):
                            # 重新计算哈希
                            file_hash = self._get_file_hash(file_path)
                            if file_hash != cached_info["hash"]: # 确定出现变化则更新文件，并添加到update队列中
                                self._file_info_cache[file_path] = {
                                    "mtime": file_mtime,
                                    "size": file_size,
                                    "hash": file_hash
                                }
                                updated_files.append(file_path)
                                logger.debug(f"Detected file update: {file_path}")

                except OSError as e:
                    logger.warning(f"Failed to get file stats for {file_path}: {e}")
                    continue

            # 检测删除的文件
            cached_files = set(self._file_info_cache.keys())
            deleted_files = list[Any](cached_files - current_files)
            for file_path in deleted_files:
                del self._file_info_cache[file_path]
                logger.debug(f"Detected file deletion: {file_path}")

            # 生成事件
            for file_path in new_files:
                event = {
                    "event_type": "file_created",
                    "file_path": file_path,
                    "timestamp": current_time,
                    "file_info": self._file_info_cache[file_path]
                }
                with self._event_lock:
                    self._document_events.append(event)

            for file_path in updated_files:
                event = {
                    "event_type": "file_updated",
                    "file_path": file_path,
                    "timestamp": current_time,
                    "file_info": self._file_info_cache[file_path]
                }
                with self._event_lock:
                    self._document_events.append(event)

            for file_path in deleted_files:
                event = {
                    "event_type": "file_deleted",
                    "file_path": file_path,
                    "timestamp": current_time,
                }
                with self._event_lock:
                    self._document_events.append(event)

            # 更新扫描时间
            self._last_scan_time = current_time
            self._last_activity_time = current_time

            if new_files or updated_files or deleted_files:
                logger.info(
                    f"文件扫描完成: {len(new_files)} 个新文件, {len(updated_files)} 个更新文件, {len(deleted_files)} 个删除文件"
                )

        except Exception as e:
            logger.exception(f"文件夹扫描失败: {e}")

    def _process_file_event(self, event):
        """处理文件事件，根据文件类型进行相应处理"""
        try:
            file_path = event["file_path"]
            event_type = event["event_type"]
            
            if event_type == "file_deleted":
                logger.info(f"文件已删除: {file_path}")
                # todo 此时需要清空已存在的对应上下文
                return

        except Exception as e:
            logger.error(f"处理文件事件失败: {e}")

    def _process_folder_event(self, event):
        """处理文件夹事件，根据文件类型进行相应处理"""
        try:
            # todo 这里的文件format，IMAGE和FILE边界不是很清晰
            if file_ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
                content_format = ContentFormat.IMAGE
            elif file_ext in {".pdf", ".docx", ".doc", ".pptx", ".ppt"}:
                content_format = ContentFormat.FILE
            elif file_ext in {".xlsx", ".xls", ".csv", ".jsonl"}:
                content_format = ContentFormat.FILE
            else:
                content_format = ContentFormat.FILE

            
            # Create RawContextProperties for the document
            raw_context = RawContextProperties(
                source=ContextSource.LOCAL_FILE,
                content_path=document_path,
                content_format=content_format,
                create_time=datetime.now(),
                content_text="",
            )
            
            # Check if processor can handle this file
            if not DocumentProcessor().can_process(raw_context):
                print(f"Error: Processor cannot handle this file type: {file_ext}")
                return
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
                if file_size > self._max_file_size:
                    logger.warning(f"文件过大，跳过处理: {file_path} ({file_size} bytes)")
                    return
            except OSError as e:
                logger.warning(f"无法获取文件大小: {file_path}, 错误: {e}")
                return
            
            contexts = DocumentProcessor().real_process(raw_context)
            if contexts:
                print(f"Successfully queued document: {Path(document_path).name}")
                processed_count += 1
                chunk_result = []
                for context in contexts:
                    chunk_result.append(context.extracted_data.summary)
                    print('----------------chunk-------------\n')
                    print(f"{context.extracted_data.summary}")

                # Dump chunk_result to JSON file
                output_filename = f"{Path(document_path).stem}_chunks.json"
                output_path = Path(document_path).parent / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk_result, f, ensure_ascii=False, indent=2)
                print(f"\nChunk results saved to: {output_path}")

            else:
                print(f"Failed to queue document: {Path(document_path).name}")
            
                
        except Exception as e:
            logger.exception(f"处理文件事件失败: {event}, 错误: {e}")
    

    def _create_context_from_event(self, event: Dict[str, Any]) -> Optional[RawContextProperties]:
        """
        Create RawContextProperties from event

        Args:
            event: Document event

        Returns:
            RawContextProperties: Context properties object
        """
        # 不需要返回raw context，参考example中的内容，可以直接得到processed context
        return
        try:
            event_type = event.get("event_type", "")
            
            # 处理文件事件
            if event_type in ["file_created", "file_updated", "file_deleted"]:
                file_path = event["file_path"]
                timestamp = event["timestamp"]
                
                # 对于删除的文件，不创建上下文。
                # todo 还要清除已加入的上下文
                if event_type == "file_deleted":
                    return None
                
                # 读取文件内容（仅对文本文件）
                content_text = ""
                try:
                    if self._is_supported_file_type(file_path):
                        file_ext = os.path.splitext(file_path)[1].lower()
                        if file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content_text = f.read()
                except Exception as e:
                    logger.warning(f"无法读取文件内容: {file_path}, 错误: {e}")
                
                # 创建文件上下文数据
                context_data = RawContextProperties(
                    source=ContextSource.VAULT,
                    content_format=ContentFormat.TEXT,
                    content_text=content_text,
                    create_time=timestamp,
                    filter_path=file_path,
                    additional_info={
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "file_type": os.path.splitext(file_path)[1].lower(),
                        "event_type": event_type,
                        "file_info": event.get("file_info", {}),
                    },
                    enable_merge=False,
                )
                
                return context_data
            
            # 处理原有的文档事件
            elif "document_data" in event and "vault_id" in event:
                doc = event["document_data"]
                vault_id = event["vault_id"]

                # Create context data
                context_data = RawContextProperties(
                    source=ContextSource.VAULT,
                    content_format=ContentFormat.TEXT,
                    content_text=doc.get("title", "") + doc.get("summary", "") + doc.get("content", ""),
                    create_time=datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00")),
                    filter_path=self._get_document_path(doc),
                    additional_info={
                        "vault_id": vault_id,
                        "title": doc.get("title", ""),
                        "summary": doc.get("summary", ""),
                        "tags": doc.get("tags", ""),
                        "document_type": doc.get("document_type", "vaults"),
                        "event_type": event_type,
                    },
                    enable_merge=False,
                )

                return context_data
            
            return None
            
        except Exception as e:
            logger.exception(f"Failed to create context from event: {e}")
            return None

    def _get_document_path(self, doc: Dict[str, Any]) -> str:
        """
        Get complete path of document (based on parent_id hierarchy)

        Args:
            doc: Document data

        Returns:
            str: Document path
        """
        try:
            if not doc.get("parent_id"):
                return f"/{doc.get('title', 'untitled')}"

            # TODO: Implement complete path building logic
            # This requires recursive lookup of parent_id to build complete path
            # Return simple path for now
            return f"/folder/{doc.get('title', 'untitled')}"
        except Exception as e:
            logger.debug(f"Failed to build document path: {e}")
            return f"/{doc.get('title', 'untitled')}"

    def _get_config_schema_impl(self) -> Dict[str, Any]:
        """
        Get configuration schema implementation

        Returns:
            Dict[str, Any]: Configuration schema
        """
        return {
            "properties": {
                "monitor_interval": {
                    "type": "integer",
                    "description": "Monitor interval (seconds)",
                    "minimum": 1,
                    "default": 5,
                },
                "initial_scan": {
                    "type": "boolean",
                    "description": "Whether to perform initial scan",
                    "default": True,
                },
                "watch_folder_path": {
                    "type": "array",
                    "description": "List of folder paths to monitor",
                    "items": {
                        "type": "string"
                    },
                    "default": ["./watch_folder"],
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to scan folders recursively",
                    "default": True,
                },
                "max_file_size": {
                    "type": "integer",
                    "description": "Maximum file size to process (bytes)",
                    "minimum": 1,
                    "default": 104857600,  # 100MB
                },
            }
        }

    def _validate_config_impl(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration implementation

        Args:
            config: Configuration to validate

        Returns:
            bool: Whether configuration is valid
        """
        try:
            monitor_interval = config.get("monitor_interval", 5)
            if not isinstance(monitor_interval, int) or monitor_interval < 1:
                logger.error("monitor_interval must be an integer greater than 0")
                return False

            watch_folder_path = config.get("watch_folder_path", ["./watch_folder"])
            if not isinstance(watch_folder_path, list):
                logger.error("watch_folder_path must be a list of strings")
                return False
            
            for folder_path in watch_folder_path:
                if not isinstance(folder_path, str):
                    logger.error("Each folder path in watch_folder_path must be a string")
                    return False

            max_file_size = config.get("max_file_size", 104857600)
            if not isinstance(max_file_size, int) or max_file_size < 1:
                logger.error("max_file_size must be an integer greater than 0")
                return False

            return True
        except Exception as e:
            logger.exception(f"Configuration validation failed: {e}")
            return False

    def _get_status_impl(self) -> Dict[str, Any]:
        """
        Get status implementation

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "monitor_interval": self._monitor_interval,
            "processed_vault_count": len(self._processed_vault_ids),
            "pending_events": len(self._document_events),
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "is_monitoring": not self._stop_event.is_set(),
        }

    def _get_statistics_impl(self) -> Dict[str, Any]:
        """
        Get statistics implementation

        Returns:
            Dict[str, Any]: Statistics information
        """
        return {
            "total_processed": self._total_processed,
            "last_activity_time": (
                self._last_activity_time.isoformat() if self._last_activity_time else None
            ),
        }

    def _reset_statistics_impl(self) -> None:
        """Reset statistics implementation"""
        self._total_processed = 0
        self._last_activity_time = None
        with self._event_lock:
            self._document_events.clear()
