#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Profile Entity Tool
统一的实体管理工具，整合存储、查找、匹配和LLM交互功能
"""

import json
from typing import Dict, List, Tuple, Any, Optional
from context_lab.models.context import Vectorize, ProcessedContext, ProfileContextMetadata
from context_lab.models.enums import ContextType
from context_lab.tools.base import BaseTool
from context_lab.storage.global_storage import get_storage
from context_lab.utils.logging_utils import get_logger
from context_lab.utils.json_parser import parse_json_from_response

logger = get_logger(__name__)


class ProfileEntityTool(BaseTool):
    """统一的实体管理工具"""
    
    def __init__(self):
        super().__init__()
        self.storage = get_storage()
        self.similarity_threshold = 0.8
        
        # 当前用户实体
        self.current_user_entity = {
            "entity_canonical_name": "current_user",
            "entity_aliases": ["我", "用户", "自己", "本人"],
            "entity_type": "person",
            "description": "系统当前用户",
            "metadata": {},
            "relationships": {}
        }
    
    @classmethod
    def get_name(cls) -> str:
        return "profile_entity_tool"
    
    @classmethod
    def get_description(cls) -> str:
        return "统一的实体管理工具，支持精确查找、相似查找、关系判断、创建和更新实体"
    
    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """获取工具参数定义"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["find_exact_entity", "find_similar_entity", "match_entity", "check_entity_relationships", "get_entity_relationship_network"],
                    "description": "操作类型: 实体精确查找、实体相似查找、实体智能匹配、实体之间关系检查、获取实体关系网络"
                },
                "entity_name": {
                    "type": "string",
                    "description": "要查找的实体名称"
                },
                "entity_data": {
                    "type": "object",
                    "description": "实体的附加数据信息",
                    "properties": {}
                },
                "entity1": {
                    "type": "string",
                    "description": "关系检查中的第一个实体"
                },
                "entity2": {
                    "type": "string",
                    "description": "关系检查中的第二个实体"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回相似实体的最大数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                },
                "context_text": {
                    "type": "string",
                    "description": "用于增强查找的上下文文本"
                },
                "max_hops": {
                    "type": "integer",
                    "description": "关系网络的最大跳数（1-5）",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5
                }
            },
            "required": ["operation"],
            "additionalProperties": False
        }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行实体操作
        
        Returns:
            Dict containing operation results with success status
        """
        operation = kwargs.get("operation")
        
        operation_handlers = {
            "find_exact_entity": self._handle_find_exact,
            "find_similar_entity": self._handle_find_similar,
            "match_entity": self._handle_match,
            "check_entity_relationships": self._handle_check_relationships,
            "get_entity_relationship_network": self._handle_get_relationship_network
        }
        
        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "success": False,
                "error": f"不支持的操作: {operation}",
                "supported_operations": list(operation_handlers.keys())
            }
        
        try:
            return handler(kwargs)
        except Exception as e:
            logger.error(f"执行实体操作失败 - {operation}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    def _handle_find_exact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理精确查找操作"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for find_exact_entity operation"
            }
        
        result = self.find_exact_entity(entity_name)
        if not result:
            return {
                "success": False,
                "error": f"Entity {entity_name} not found",
            }
        return {
            "success": True,
            "entity_info": result.metadata,
            "entity_name": entity_name
        }
    
    def _handle_find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理相似查找操作"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for find_similar_entity operation"
            }
        
        top_k = min(max(params.get("top_k", 10), 1), 100)
        results = self.find_similar_entities([entity_name], top_k=top_k)
        if not results:
            return {
                "success": False,
                "error": f"No similar entities found for {entity_name}",
            }
        return {
            "success": True,
            "simila_entity_info": [item.metadata for item in results],
        }
    
    def _handle_match(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理智能匹配操作 - 先精确匹配，没有则相似搜索+LLM判断"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for match_entity operation"
            }
        
        # 直接调用 match_entity 方法
        top_k = min(max(params.get("top_k", 5), 1), 10)
        entity_type = params.get("entity_type", None)
        matched_name, matched_context = self.match_entity(
            entity_name=entity_name, 
            entity_type=entity_type,
            top_k=top_k
        )
        if not matched_name:
            return {
                "success": False,
                "error": f"No matched entity found for {entity_name}",
            }
        return {
            "success": True,
            "entity_info": matched_context.metadata,
            "entity_name": entity_name,
        }
    
    def _handle_check_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理关系检查操作"""
        entity1 = params.get("entity1", "")
        entity2 = params.get("entity2", "")
        
        if not entity1 or not entity2:
            missing = []
            if not entity1:
                missing.append("entity1")
            if not entity2:
                missing.append("entity2")
            return {
                "success": False,
                "error": f"Missing required parameters: {', '.join(missing)}"
            }
        
        result = self.check_entity_relationships(entity1, entity2)
        return {
            "success": True,
            "entity1": entity1,
            "entity2": entity2,
            **result
        }
    
    def _handle_get_relationship_network(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取关系网络操作"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for get_entity_relationship_network operation"
            }
        
        max_hops = min(max(params.get("max_hops", 2), 1), 5)
        
        try:
            network = self.get_entity_relationship_network(entity_name, max_hops)
            return {
                "success": True,
                "entity_name": entity_name,
                "max_hops": max_hops,
                "network": network
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "entity_name": entity_name
            }
  
    def match_entity(self, entity_name: str, entity_type: str = None, top_k: int = 3) -> Tuple[Optional[str], Optional[ProcessedContext]]:
        """智能匹配实体 - 先精确匹配，没有则相似搜索+LLM判断
        
        Args:
            entity_name: 要匹配的实体名称
            entity_type: 实体类型（可选）
            top_k: 相似搜索返回的最大数量
            
        Returns:
            Tuple[Optional[str], Optional[ProcessedContext]]: (匹配的实体名称, 匹配的context)
        """
        # 1. 先尝试精确匹配
        exact_result = self.find_exact_entity([entity_name], entity_type)
        if exact_result:
            metadata = exact_result.metadata
            matched_name = metadata.get("entity_canonical_name", entity_name)
            return matched_name, exact_result
        
        # 2. 相似搜索
        top_k = min(max(top_k, 1), 10)
        similar_contexts = self.find_similar_entities([entity_name], entity_type, top_k=top_k)
        if not similar_contexts:
            # 没有找到任何相似的实体
            return None, None
        
        # 3. 使用LLM判断相似实体是否真的匹配
        matched_name, matched_context = self.judge_entity_match([entity_name], similar_contexts)
        return matched_name, matched_context
    
    def find_exact_entity(self, entity_names: List[str], entity_type: str = None) -> Optional[ProcessedContext]:
        """精确查找实体"""
        filter = {"entity_canonical_name": entity_names}
        if entity_type:
            filter["entity_type"] = entity_type
        contexts = self.storage.get_all_processed_contexts(
            context_types=[ContextType.ENTITY_CONTEXT],
            limit=1,
            filter=filter
        )
        if not contexts:
            return None
        
        entity_contexts = contexts.get(ContextType.ENTITY_CONTEXT.value, [])
        if entity_contexts:
            return entity_contexts[0]
        return None
    
    def find_similar_entities(self, entity_names: List[str], entity_type: str = None, top_k: int = 3) -> List[ProcessedContext]:
        """相似查找实体 - 使用向量搜索"""
        if not entity_names:
            return []
        filter = {}
        if entity_type:
            filter["entity_type"] = entity_type
        results = self.storage.search(
            query=Vectorize(text=" ".join(entity_names)),
            top_k=top_k,
            context_types=[ContextType.ENTITY_CONTEXT.value],
            filters=filter
        )
        if not results:
            return []
        contexts = []
        for context, score in results:
            contexts.append(context)
        return contexts
    
    def check_entity_relationships(self, entity1: str, entity2: str) -> Dict[str, Any]:
        """判断两个实体是否有关联"""
        try:
            context1 = self.find_exact_entity([entity1])
            context2 = self.find_exact_entity([entity2])
            
            if not context1 or not context2:
                return {
                    "related": False,
                    "error": "一个或两个实体未找到"
                }
            
            # 获取实体数据 - metadata 是 ProfileContextMetadata 的字典形式
            metadata1 = context1.metadata
            metadata2 = context2.metadata
            
            entity1_name = metadata1.get("entity_canonical_name", entity1)
            entity2_name = metadata2.get("entity_canonical_name", entity2)
            
            # 检查 entity_relationships 字段
            relationships1 = metadata1.get("entity_relationships", {})
            relationships2 = metadata2.get("entity_relationships", {})
            
            # 检查 entity1 的关系中是否有 entity2
            for rel_type, rel_list in relationships1.items():
                if isinstance(rel_list, list) and entity2_name in rel_list:
                    return {
                        "related": True,
                        "relationship_type": rel_type,
                        "direction": f"{entity1_name} -> {entity2_name}"
                    }
            
            # 检查 entity2 的关系中是否有 entity1
            for rel_type, rel_list in relationships2.items():
                if isinstance(rel_list, list) and entity1_name in rel_list:
                    return {
                        "related": True,
                        "relationship_type": rel_type,
                        "direction": f"{entity2_name} -> {entity1_name}"
                    }
            
            return {"related": False}
            
        except Exception as e:
            logger.error(f"检查实体关系失败: {e}")
            return {"related": False, "error": str(e)}
    
    def get_entity_relationship_network(self, entity_name: str, max_hops: int = 2) -> Dict[str, Any]:
        """获取实体的关系网络
        
        Args:
            entity_name: 起始实体名称
            max_hops: 最大跳数（1-5）
            
        Returns:
            Dict containing the relationship network with nodes and edges
        """
        max_hops = min(max(max_hops, 1), 5)
        
        visited_ids = set()  # 改为使用 entity_id 作为访问记录
        network = {
            "nodes": [],
            "edges": [],
            "statistics": {
                "total_nodes": 0,
                "total_edges": 0,
                "max_depth_reached": 0
            }
        }
        
        node_map = {}
        edge_set = set()
        
        def add_node(context: ProcessedContext, depth: int) -> str:
            """添加节点到网络，返回 entity_id"""
            if not context or not context.metadata:
                return None
            
            entity_id = context.id
            if not entity_id:
                return None
            metadata = context.metadata
            canonical_name = metadata.get("entity_canonical_name", "")
            
            if entity_id not in node_map:
                node_info = {
                    "id": entity_id,
                    "name": canonical_name,
                    "type": metadata.get("entity_type", "unknown"),
                    "description": metadata.get("entity_description", ""),
                    "aliases": metadata.get("entity_aliases", []),
                    "depth": depth,
                    "metadata": metadata.get("entity_metadata", {})
                }
                network["nodes"].append(node_info)
                node_map[entity_id] = node_info
                network["statistics"]["total_nodes"] += 1
                network["statistics"]["max_depth_reached"] = max(
                    network["statistics"]["max_depth_reached"], depth
                )
            
            return entity_id
        
        def explore_entity_by_id(entity_id: str, current_depth: int):
            """根据 entity_id 递归探索实体关系"""
            if current_depth > max_hops:
                return
                
            if entity_id in visited_ids:
                return
                
            visited_ids.add(entity_id)
            
            # 根据 entity_id 查找实体
            context = self.storage.get_processed_context(entity_id, context_type=ContextType.ENTITY_CONTEXT.value)
            if not context:
                return
            
            current_node_id = add_node(context, current_depth)
            if not current_node_id:
                return
            
            # 处理 entity_relationships 字段
            metadata = context.metadata
            entity_relationships = metadata.get("entity_relationships", {})
            
            # entity_relationships 结构是 Dict[str, List[Dict]]
            # 例如: {"friend": [{"entity_id": "123", "entity_name": "Alice"}]}
            for relationship_type, related_entities in entity_relationships.items():
                for related_entity_info in related_entities:
                    related_entity_id = related_entity_info.get("entity_id")
                    edge_key = (current_node_id, related_entity_id)
                    reverse_edge_key = (related_entity_id, current_node_id)
                    
                    if edge_key not in edge_set and reverse_edge_key not in edge_set:
                        related_context = self.storage.get_processed_context(related_entity_id, context_type=ContextType.ENTITY_CONTEXT.value)
                        if not related_context:
                            continue
                        related_node_id = add_node(related_context, current_depth + 1)
                        if related_node_id:
                            edge_info = {
                                "source": current_node_id,
                                "target": related_node_id,
                                "relationship": relationship_type,
                                "depth": current_depth
                            }
                            network["edges"].append(edge_info)
                            edge_set.add(edge_key)
                            network["statistics"]["total_edges"] += 1
                            if current_depth < max_hops:
                                explore_entity_by_id(related_entity_id, current_depth + 1)
        
        def explore_entity(entity_name: str, current_depth: int):
            """从实体名称开始探索"""
            context = self.find_exact_entity([entity_name])
            if not context:
                return

            entity_id = context.id
            if entity_id:
                explore_entity_by_id(entity_id, current_depth)
            explore_entity(entity_name, 0)
        return network

    def update_entity_meta(self, entity_name: str, context_text: str, old_entity_data: ProfileContextMetadata, new_entity_data: ProfileContextMetadata) -> ProfileContextMetadata :
        """使用LLM智能合并实体元信息
        
        Args:
            entity_name: 实体名称
            context_text: 上下文文本
            old_entity_data: 当前存储的实体数据
            new_entity_data: 新提取的实体数据
            
        Returns:
            Dict: 更新结果
        """
        try:
            from context_lab.config.global_config import get_prompt_group
            prompt_template = get_prompt_group('entity_processing.entity_meta_merging')
            old_data = {
                "entity_canonical_name": old_entity_data.entity_canonical_name or entity_name,
                "entity_metadata": old_entity_data.entity_metadata or {},
                "entity_aliases": old_entity_data.entity_aliases or [],
                "entity_description": old_entity_data.entity_description or ""
            }
            new_data = {
                "entity_canonical_name": new_entity_data.entity_canonical_name or entity_name,
                "entity_metadata": new_entity_data.entity_metadata or {},
                "entity_aliases": new_entity_data.entity_aliases or [],
                "entity_description": new_entity_data.entity_description or ""
            }
            user_prompt = prompt_template['user'].format(
                old_entity_data=json.dumps(old_data, ensure_ascii=False, indent=2),
                new_entity_data=json.dumps(new_data, ensure_ascii=False, indent=2),
                context_text=context_text,
            )
            messages = [
                {"role": "system", "content": prompt_template['system']},
                {"role": "user", "content": user_prompt}
            ]
            from context_lab.llm.global_vlm_client import generate_with_messages
            response = generate_with_messages(
                messages,
                temperature=0.1,
                thinking="disabled"
            )
            result = parse_json_from_response(response)
            if "entity_canonical_name" in result and result["entity_canonical_name"]:
                old_entity_data.entity_canonical_name = result["entity_canonical_name"]
            if "entity_metadata" in result and isinstance(result["entity_metadata"], dict):
                old_entity_data.entity_metadata = result["entity_metadata"]
            if "entity_description" in result and result["entity_description"]:
                old_entity_data.entity_description = result["entity_description"]
            old_entity_data.entity_aliases = list(set(old_entity_data.entity_aliases or []) | set(new_entity_data.entity_aliases or []))
            return old_entity_data
        except Exception as e:
            logger.exception(f"LLM合并实体元信息失败 {entity_name}: {e}", exc_info=True)
            return old_entity_data
    
    def judge_entity_match(self, extracted_names: List[str], candidates: List[ProcessedContext]) -> Optional[Tuple[str, ProcessedContext]]:
        """使用LLM判断提取的实体是否匹配候选实体之一"""
        if not candidates:
            return None, None
        
        try:
            candidate_info = []
            for context in candidates[:5]:
                entity_data = context.metadata
                info = {
                    "name": entity_data.get("entity_canonical_name", ""),
                    "entity_aliases": entity_data.get("entity_aliases", []),
                    "type": entity_data.get("entity_type", ""),
                    "description": entity_data.get("description", "")
                }
                candidate_info.append(info)
            
            # 构建prompt
            from context_lab.config.global_config import get_prompt_group
            prompt_template = get_prompt_group('entity_processing.entity_matching')
            
            user_prompt = prompt_template['user'].format(
                extracted_names=extracted_names,
                candidates=json.dumps(candidate_info, ensure_ascii=False, indent=2)
            )
            
            messages = [
                {"role": "system", "content": prompt_template['system']},
                {"role": "user", "content": user_prompt}
            ]
            from context_lab.llm.global_vlm_client import generate_with_messages
            response = generate_with_messages(
                messages,
                temperature=0.1,
                max_tokens=200,
                thinking="disabled",
            )
            result = parse_json_from_response(response)
            if result.get("is_match") and result.get("matched_entity"):
                for candidate in candidates:
                    if result.get("matched_entity") in candidate.metadata.get("entity_aliases", []):
                        return candidate.metadata.get("entity_canonical_name"), candidate
            return None, None
            
        except Exception as e:
            logger.error(f"LLM判断实体匹配失败: {e}")
            return None, None