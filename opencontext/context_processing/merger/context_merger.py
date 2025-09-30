#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Context merge processor - Responsible for merging similar contexts into one.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import math

from opencontext.config import GlobalConfig
from opencontext.context_processing.processor.base_processor import BaseContextProcessor
from opencontext.context_processing.merger.merge_strategies import StrategyFactory, ContextTypeAwareStrategy
from opencontext.context_processing.merger.cross_type_relationships import CrossTypeRelationshipManager
from opencontext.llm.global_vlm_client import generate_with_messages
from opencontext.llm.global_embedding_client import do_vectorize
from opencontext.storage.global_storage import get_storage
from opencontext.models.context import *
from opencontext.models.enums import MergeType, ContextType
from opencontext.utils.logging_utils import get_logger
from opencontext.utils.json_parser import parse_json_from_response
import json

logger = get_logger(__name__)


class ContextMerger(BaseContextProcessor):
    def __init__(self):
        from opencontext.config.global_config import get_config, get_prompt_manager
        config = get_config('processing.context_merger') or {}
        super().__init__(config)
        
        self.prompt_manager = get_prompt_manager()
        self._similarity_threshold = config.get('similarity_threshold', 0.85)
        self.associative_similarity_threshold = config.get('associative_similarity_threshold', 0.6)
        self._statistics = {"merges_attempted": 0, "merges_succeeded": 0, "errors": 0}
        self.merge_type_for_target = {}
        
        # Initialize strategy management
        self.strategies: Dict[ContextType, ContextTypeAwareStrategy] = {}
        self._initialize_strategies()
        
        # Intelligent merging switch
        self.use_intelligent_merging = config.get('use_intelligent_merging', True)
    
    @property
    def storage(self):
        """Get storage from global singleton"""
        return get_storage()

    def get_name(self) -> str:
        return "merger"

    def get_description(self) -> str:
        return "Merges similar contexts using intelligent type-aware strategies."
    
    def _initialize_strategies(self):
        """Initialize all supported merge strategies"""
        from opencontext.context_processing.merger.merge_strategies import StrategyFactory
        
        supported_types = StrategyFactory.get_supported_types()
        for context_type in supported_types:
            strategy = StrategyFactory.get_strategy(context_type, self.config)
            if strategy:
                self.strategies[context_type] = strategy
                logger.info(f"Initialized merge strategy for {context_type.value}")
        
        logger.info(f"Initialized {len(self.strategies)} context merge strategies")

    def process(self, context: ProcessedContext) -> List[ProcessedContext]:
        return []

    def can_process(self, context: ProcessedContext) -> bool:
        return context.extracted_data.summary is not None

    def find_merge_target(self, context: ProcessedContext) -> ProcessedContext:
        """
        Find merge target using intelligent strategies
        """
        if not context.properties.enable_merge:
            return None
        
        # Check for vectorization
        if not context.vectorize:
            return None
        do_vectorize(context.vectorize)
        
        context_type = context.extracted_data.context_type
        
        # Use intelligent merging strategy
        if self.use_intelligent_merging and context_type in self.strategies:
            return self._find_intelligent_merge_target(context)
        
        # Fallback to legacy logic
        return self._find_legacy_merge_target(context)
    
    def _find_intelligent_merge_target(self, context: ProcessedContext) -> Optional[ProcessedContext]:
        """Find merge target using intelligent strategies"""
        context_type = context.extracted_data.context_type
        strategy = self.strategies.get(context_type)
        
        if not strategy:
            logger.warning(f"No strategy found for context type {context_type.value}")
            return None
        
        try:
            # Get candidates with same type
            candidates = self._get_merge_candidates(context)
            
            best_target = None
            best_score = 0.0
            
            for candidate in candidates:
                if candidate.id == context.id:
                    continue
                
                can_merge, score = strategy.can_merge(candidate, context)
                if can_merge and score > best_score:
                    best_target = candidate
                    best_score = score
            
            if best_target:
                self.merge_type_for_target[best_target.id] = MergeType.SIMILARITY
                logger.info(f"Found intelligent merge target {best_target.id} for {context.id} with score {best_score:.3f}")
            
            return best_target
            
        except Exception as e:
            logger.error(f"Error in intelligent merge target finding: {e}", exc_info=True)
            return None
    
    def _get_merge_candidates(self, context: ProcessedContext, max_candidates: int = 10) -> List[ProcessedContext]:
        """Get merge candidate contexts"""
        try:
            backend = self.storage._get_or_create_backend(context.extracted_data.context_type.value)
            if not backend:
                return []
            
            # Use vector similarity query
            similar_results = backend.query(
                query=Vectorize(vector=context.vectorize.vector), 
                top_k=max_candidates + 1,  # +1 because the result might include self
                filters={}
            )
            
            # Return context objects (excluding self)
            candidates = [result[0] for result in similar_results if result[0].id != context.id]
            return candidates[:max_candidates]
            
        except Exception as e:
            logger.error(f"Error getting merge candidates: {e}", exc_info=True)
            return []
    
    def _find_legacy_merge_target(self, context: ProcessedContext) -> Optional[ProcessedContext]:
        """Find merge target using legacy logic (for backward compatibility)"""
        # Strategy 1: Associative Merge
        assoc_target, _ = self._find_associative_merge_target(context)
        if assoc_target:
            self.merge_type_for_target[assoc_target.id] = MergeType.ASSOCIATIVE
            return assoc_target

        # Strategy 2: Similarity Merge
        sim_target, _ = self._find_similarity_merge_target(context)
        if sim_target and (not assoc_target or sim_target.id != assoc_target.id):
            self.merge_type_for_target[sim_target.id] = MergeType.SIMILARITY
            return sim_target

        return None

    def _find_associative_merge_target(self, context: ProcessedContext) -> tuple[Optional[ProcessedContext], float]:
        """
        Finds a recent context of the same type that is associatively related, created within the last 30 minutes.
        Association is determined by semantic similarity and shared entities.
        """
        try:

            context_entities = set(context.extracted_data.entities)
            
            # Define time window for recent contexts
            thirty_minutes_ago = datetime.now() - timedelta(minutes=30)
            time_filter = {"update_time_ts": {"$gte": int(thirty_minutes_ago.timestamp())}}

            # Get the appropriate storage backend
            backend = self.storage._get_or_create_backend(context.extracted_data.context_type.value)
            if not backend:
                logger.warning(f"No backend found for context type {context.extracted_data.context_type.value}")
                return None, 0.0

            # Query for similar contexts within the time window
            similar_results = backend.query(query=Vectorize(vector=context.vectorize.vector), top_k=5, filters=time_filter)
            
            # Filter out the context itself from the results
            similar_results = [res for res in similar_results if res[0].id != context.id]

            if not similar_results:
                return None, 0.0

            # Check for similarity score and entity overlap
            for recent_ctx, score in similar_results:
                if score > self.associative_similarity_threshold:
                    recent_entities = set(recent_ctx.extracted_data.entities)
                    # If the source context has no entities, any similar context is a potential match.
                    # Otherwise, require entity overlap.
                    if not context_entities or (recent_entities and context_entities.intersection(recent_entities)):
                        logger.info(f"Found potential associative merge target {recent_ctx.id} for {context.id} with score {score} and entity overlap.")
                        return recent_ctx, score

        except Exception as e:
            logger.error(f"Error finding associative merge target for {context.id}: {e}", exc_info=True)

        return None, 0.0

    def _find_similarity_merge_target(self, context: ProcessedContext) -> tuple[Optional[ProcessedContext], float]:

        try:
            backend = self.storage._get_or_create_backend(context.extracted_data.context_type.value)
            similar_results = backend.query(query=Vectorize(vector=context.vectorize.vector), top_k=2, filters={})
            similar_results = [res for res in similar_results if res[0].id != context.id]

            if similar_results:
                most_similar_context, score = similar_results[0]
                logger.info(f"Most similar context to {context.id} is {most_similar_context.id} with score: {score}")
                if score > self._similarity_threshold:
                    return most_similar_context, score
        except Exception as e:
            logger.error(f"Error querying for similar contexts for target {context.id}: {e}", exc_info=True)

        return None, 0.0


    def merge_multiple(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Merges multiple source contexts into a target context using intelligent strategies.
        """
        if not sources:
            return target

        self._statistics["merges_attempted"] += 1
        
        try:
            context_type = target.extracted_data.context_type
            
            # Use intelligent merging strategy
            if self.use_intelligent_merging and context_type in self.strategies:
                merged_context = self._merge_with_intelligent_strategy(target, sources)
            else:
                # Fallback to LLM merging
                merged_context = self._merge_with_llm(target, sources)
            
            if merged_context:
                self._statistics["merges_succeeded"] += 1
                return merged_context
            else:
                self._statistics["errors"] += 1
                logger.warning(f"Merging failed for target {target.id}. Returning None.")
                return None
              
        except Exception as e:
            logger.error(f"An exception occurred during merging for target {target.id}: {e}", exc_info=True)
            self._statistics["errors"] += 1
            return None
    
    def _merge_with_intelligent_strategy(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """Merge using intelligent strategies"""
        context_type = target.extracted_data.context_type
        strategy = self.strategies.get(context_type)
        
        if not strategy:
            logger.warning(f"No strategy found for context type {context_type.value}, falling back to LLM merge")
            return self._merge_with_llm(target, sources)
        
        try:
            merged_context = strategy.merge_contexts(target, sources)
            if merged_context:
                logger.info(f"Successfully merged using {context_type.value} strategy: {len(sources)} sources into target {target.id}")
            return merged_context
        
        except Exception as e:
            logger.error(f"Error in intelligent strategy merge: {e}", exc_info=True)
            # Fallback to LLM merging
            logger.info("Falling back to LLM-based merge")
            return self._merge_with_llm(target, sources)

    def _merge_with_llm(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Uses an LLM to merge a list of source contexts into a target context.
        """
        try:
            # Try to use a type-specific prompt
            context_type = target.extracted_data.context_type
            type_specific_prompt = f"merging.{context_type.value}_merging"
            
            # First, try the type-specific prompt
            prompt_group = self.prompt_manager.get_prompt_group(type_specific_prompt)
            if prompt_group and "user" in prompt_group:
                prompt_name = type_specific_prompt
                logger.info(f"Using type-specific prompt: {prompt_name}")
            else:
                # Fallback to the generic prompt
                prompt_name = "merging.context_merging_multiple"
                prompt_group = self.prompt_manager.get_prompt_group(prompt_name)
                logger.info(f"Using generic prompt: {prompt_name}")
            
            if not prompt_group or "user" not in prompt_group:
                logger.error(f"User prompt for '{prompt_name}' not found.")
                return None

            user_template = prompt_group["user"]
            system_prompt = prompt_group.get("system")

            target_context_json = target.extracted_data.model_dump_json(exclude={'context_type'}, indent=2)
            source_contexts_json = json.dumps(
                [s.extracted_data.model_dump(exclude={'context_type'}) for s in sources], 
                indent=2, 
                ensure_ascii=False
            )
            user_prompt = user_template.format(
                target_context_json=target_context_json,
                source_contexts_json=source_contexts_json
            )
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            # logger.info(f"LLM messages for merging: {messages}")
            response = generate_with_messages(messages)
            if response:
                if "无需合并" in response:
                    logger.info(f"LLM indicated no merge needed for target {target.id}.")
                    return None
                
                try:
                    response_data = parse_json_from_response(response)
                    required_fields = ['title', 'summary', 'keywords', 'entities', 'tags', 'importance', 'confidence']
                    if not all(field in response_data for field in required_fields):
                        logger.warning(f"LLM response is missing one or more required fields. Got: {response_data.keys()}")
                        return None
                    extracted_data = ExtractedData(
                        title=response_data['title'],
                        summary=response_data['summary'],
                        keywords=response_data['keywords'],
                        entities=response_data['entities'],
                        tags=response_data.get('tags', []),
                        context_type=target.extracted_data.context_type,
                        confidence=int(response_data['confidence']),
                        importance=int(response_data['importance']),
                    )
                    now = datetime.datetime.now()
                    properties = ContextProperties(
                        raw_properties=target.properties.raw_properties,
                        create_time=target.properties.create_time,
                        event_time=target.properties.event_time,
                        is_processed=True,
                        has_compression=True,
                        update_time=now,
                        merge_count=target.properties.merge_count,
                        duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
                        enable_merge=True,
                    )
                    if response_data.get("event_time", "null") != "null" and response_data.get("event_time") is not None:
                        try:
                            event_time_str = response_data.get("event_time")
                            # Check if it's only the time part, e.g., '11:53:00'
                            if len(event_time_str) == 8 and ':' in event_time_str:
                                # Add the current date to form a full ISO format
                                today = datetime.date.today().isoformat()
                                full_event_time_str = f"{today}T{event_time_str}"
                                properties.event_time = datetime.datetime.fromisoformat(full_event_time_str)
                            else:
                                # Try to parse directly
                                properties.event_time = datetime.datetime.fromisoformat(event_time_str)
                        except ValueError:
                            logger.warning(f"无法解析event_time格式: {event_time_str}")
                            # Keep the original event_time
                    
                    merged_context = ProcessedContext(
                        extracted_data=extracted_data,
                        properties=properties,
                        vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
                    )
                    logger.info(f"Successfully merged {len(sources)} sources into context {target.id}")
                    return merged_context
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode LLM response as JSON: {response}")
                    return None
            else:
                logger.warning("LLM returned no response for merging.")
                return None
        except Exception as e:
            logger.exception(f"Error during LLM-based merging: {e}")
            return None

    def get_statistics(self):
        return self._statistics

    def periodic_memory_compression(self, interval_seconds: int):
        """
        定期对上下文进行记忆压缩
        1. 获取指定时间窗口内、未压缩、可合并的上下文。
        2. 对这些上下文按相似度进行分组。
        3. 在每个分组内部，将较早的上下文合并到最新的一个上下文中。
        4. 更新合并后的上下文，并删除被合并的源上下文。
        """
        if interval_seconds <= 0:
            logger.warning("interval_seconds must be greater than 0.")
            return
        logger.info("Starting periodic memory compression...")
        try:
            # 1. 获取所有截图上下文
            filter = {
                "update_time_ts": {"$gte": int((datetime.datetime.now() - timedelta(seconds=interval_seconds) - timedelta(minutes=5)).timestamp()),
                                   "$lte": int((datetime.datetime.now() - timedelta(minutes=5)).timestamp())},
                "has_compression": False,
                "enable_merge": True,
            }
            limit = 1000
            offset = 0
            while True:
                contexts_by_backend = self.storage.get_all_processed_contexts(limit=limit, offset=offset, filter=filter)

                if not any(contexts_by_backend.values()):
                    logger.info("No more recent contexts to process in this iteration.")
                    break
                has_merge = False
                for backend_name, backend_contexts in contexts_by_backend.items():
                    if len(backend_contexts) < 2:
                        continue
                    has_merge = True
                    logger.info(f"Processing {len(backend_contexts)} contexts from backend '{backend_name}'.")
                    
                    groups = self._group_contexts_by_similarity(backend_contexts, self._similarity_threshold)

                    for group in groups:
                        if len(group) > 1:
                            group.sort(key=lambda c: c.properties.create_time)
                            target_candidate = group[-1]
                            sources = group[:-1]
                            
                            logger.info(f"Merging {len(sources)} contexts into {target_candidate.id} within the group.")
                            merged_context = self.merge_multiple(target_candidate, sources)
                            if merged_context:
                                self.storage.upsert_processed_context(merged_context)
                                self.storage.delete_processed_context(target_candidate.id, target_candidate.extracted_data.context_type.value)
                                for ctx in sources:
                                    self.storage.delete_processed_context(ctx.id, ctx.extracted_data.context_type.value)
                                logger.info(f"Successfully merged within group and cleaned up {len(sources)} source contexts.")
                
                if not has_merge:
                    break
                offset += limit

            logger.info("Periodic memory compression finished.")
        except Exception as e:
            logger.exception(f"Error during periodic memory compression: {e}")

    def _group_contexts_by_similarity(self, contexts: List[ProcessedContext], threshold: float) -> List[List[ProcessedContext]]:
        """Greedily groups contexts by similarity based on their embeddings."""
        if not contexts:
            return []

        groups = []
        remaining_contexts = list(contexts)

        while remaining_contexts:
            seed = remaining_contexts.pop(0)
            new_group = [seed]
            
            # Use a list comprehension to build the list of contexts to remove, then iterate
            to_remove = []
            seed_embedding = seed.vectorize.vector
            for i, ctx in enumerate(remaining_contexts):
                ctx_embedding = ctx.vectorize.vector
                if self._calculate_similarity(seed_embedding, ctx_embedding) > threshold:
                    new_group.append(ctx)
                    to_remove.append(i)
            
            # Remove items in reverse index order to avoid index shifting issues
            for i in sorted(to_remove, reverse=True):
                remaining_contexts.pop(i)

            groups.append(new_group)
            
        return groups

    def _calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculates cosine similarity between two embeddings."""
        if emb1 is None or emb2 is None or not emb1 or not emb2:
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        
        # Calculate norms
        norm_emb1 = math.sqrt(sum(a * a for a in emb1))
        norm_emb2 = math.sqrt(sum(b * b for b in emb2))
        
        if norm_emb1 == 0 or norm_emb2 == 0:
            return 0.0
            
        return dot_product / (norm_emb1 * norm_emb2)
        
    def intelligent_memory_cleanup(self):
        """
        智能记忆清理：基于遗忘曲线和重要性进行选择性清理
        """
        if not self.enable_memory_management:
            return
            
        logger.info("Starting intelligent memory cleanup...")
        
        try:
            cleanup_stats = {"total_checked": 0, "cleaned_up": 0, "errors": 0}
            
            # 遍历所有支持策略的上下文类型
            for context_type, strategy in self.strategies.items():
                type_stats = self._cleanup_contexts_by_type(context_type, strategy)
                cleanup_stats["total_checked"] += type_stats["checked"]
                cleanup_stats["cleaned_up"] += type_stats["cleaned"]
                cleanup_stats["errors"] += type_stats["errors"]
            
            logger.info(f"Memory cleanup completed. Checked: {cleanup_stats['total_checked']}, "
                       f"Cleaned: {cleanup_stats['cleaned_up']}, Errors: {cleanup_stats['errors']}")
        
        except Exception as e:
            logger.error(f"Error during intelligent memory cleanup: {e}", exc_info=True)
    
    def _cleanup_contexts_by_type(self, context_type: ContextType, strategy: ContextTypeAwareStrategy) -> Dict[str, int]:
        """按类型清理上下文"""
        stats = {"checked": 0, "cleaned": 0, "errors": 0}
        
        try:
            # 获取该类型的所有上下文
            backend = self.storage._get_or_create_backend(context_type.value)
            if not backend:
                return stats
            
            # 分批获取上下文进行清理
            limit = 100
            offset = 0
            
            while True:
                contexts = self._get_contexts_for_cleanup(context_type.value, limit, offset)
                if not contexts:
                    break
                
                for context in contexts:
                    stats["checked"] += 1
                    
                    try:
                        if strategy.should_cleanup(context):
                            self.storage.delete_processed_context(context.id, context_type.value)
                            stats["cleaned"] += 1
                            logger.debug(f"Cleaned up context {context.id} of type {context_type.value}")
                    
                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(f"Error cleaning up context {context.id}: {e}")
                
                if len(contexts) < limit:
                    break
                offset += limit
            
            logger.info(f"Cleanup for {context_type.value}: checked {stats['checked']}, cleaned {stats['cleaned']}")
        
        except Exception as e:
            logger.error(f"Error in cleanup for {context_type.value}: {e}", exc_info=True)
            stats["errors"] += 1
        
        return stats
    
    def _get_contexts_for_cleanup(self, context_type_value: str, limit: int, offset: int) -> List[ProcessedContext]:
        """获取需要清理检查的上下文"""
        try:
            contexts_dict = self.storage.get_all_processed_contexts(
                limit=limit, 
                offset=offset,
                filter={}
            )
            
            return contexts_dict.get(context_type_value, [])
        
        except Exception as e:
            logger.error(f"Error getting contexts for cleanup: {e}")
            return []
    
    def memory_reinforcement(self, context_ids: List[str]):
        """
        记忆强化：重置指定上下文的遗忘状态，提升重要性
        """
        if not context_ids:
            return
        
        logger.info(f"Starting memory reinforcement for {len(context_ids)} contexts")
        
        reinforced_count = 0
        
        for context_id in context_ids:
            try:
                # 通过所有后端查找上下文
                context = self._find_context_by_id(context_id)
                if not context:
                    logger.warning(f"Context {context_id} not found for reinforcement")
                    continue
                
                # 应用记忆强化
                reinforced_context = self._apply_memory_reinforcement(context)
                if reinforced_context:
                    # 更新存储
                    self.storage.upsert_processed_context(reinforced_context)
                    reinforced_count += 1
                    logger.debug(f"Reinforced context {context_id}")
                
            except Exception as e:
                logger.error(f"Error reinforcing context {context_id}: {e}", exc_info=True)
        
        logger.info(f"Memory reinforcement completed: {reinforced_count}/{len(context_ids)} contexts reinforced")
    
    def _find_context_by_id(self, context_id: str) -> Optional[ProcessedContext]:
        """在所有后端中查找指定ID的上下文"""
        try:
            # 遍历所有后端查找
            for context_type in ContextType:
                backend = self.storage._get_or_create_backend(context_type.value)
                if backend:
                    # 这里需要实现根据ID查找的方法，当前storage可能不支持
                    # 暂时使用查询方法的变通方案
                    contexts_dict = self.storage.get_all_processed_contexts(limit=1000, offset=0, filter={})
                    all_contexts = []
                    for contexts_list in contexts_dict.values():
                        all_contexts.extend(contexts_list)
                    
                    for context in all_contexts:
                        if context.id == context_id:
                            return context
                            
            return None
            
        except Exception as e:
            logger.error(f"Error finding context {context_id}: {e}", exc_info=True)
            return None
    
    def _apply_memory_reinforcement(self, context: ProcessedContext) -> Optional[ProcessedContext]:
        """应用记忆强化逻辑"""
        from opencontext.models.context import ContextProperties
        
        try:
            # 创建强化后的属性
            reinforced_properties = ContextProperties(
                raw_properties=context.properties.raw_properties,
                create_time=context.properties.create_time,
                event_time=context.properties.event_time,
                is_processed=context.properties.is_processed,
                has_compression=context.properties.has_compression,
                update_time=datetime.now(),  # 更新时间，影响遗忘曲线
                merge_count=context.properties.merge_count + 1,  # 增加访问计数
                duration_count=context.properties.duration_count,
                enable_merge=context.properties.enable_merge,
            )
            
            # 提升重要性（最多到9）
            reinforced_importance = min(context.extracted_data.importance + 1, 9)
            
            reinforced_extracted_data = ExtractedData(
                title=context.extracted_data.title,
                summary=context.extracted_data.summary,
                keywords=context.extracted_data.keywords,
                entities=context.extracted_data.entities,
                tags=context.extracted_data.tags,
                context_type=context.extracted_data.context_type,
                confidence=context.extracted_data.confidence,
                importance=reinforced_importance,
            )
            
            return ProcessedContext(
                id=context.id,  # 保持原ID
                extracted_data=reinforced_extracted_data,
                properties=reinforced_properties,
                vectorize=context.vectorize,
            )
            
        except Exception as e:
            logger.error(f"Error applying memory reinforcement: {e}", exc_info=True)
            return None
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取记忆管理统计信息"""
        stats = {
            "merge_statistics": self._statistics,
            "strategy_count": len(self.strategies),
            "supported_types": [ct.value for ct in self.strategies.keys()],
            "config": {
                "use_intelligent_merging": self.use_intelligent_merging,
                "enable_memory_management": self.enable_memory_management,
                "cleanup_interval_hours": self.cleanup_interval_hours,
            }
        }
        
        # 添加各策略的统计信息
        strategy_stats = {}
        for context_type, strategy in self.strategies.items():
            try:
                strategy_stats[context_type.value] = {
                    "similarity_threshold": strategy.similarity_threshold,
                    "retention_days": strategy.retention_days,
                    "max_merge_count": strategy.max_merge_count,
                }
            except Exception as e:
                logger.error(f"Error getting stats for {context_type.value}: {e}")
        
        stats["strategy_configurations"] = strategy_stats
        
        # 添加跨类型关联统计
        if self.enable_cross_type_processing:
            stats["cross_type_statistics"] = self.cross_type_manager.get_conversion_statistics()
        
        return stats

    def process_cross_type_relationships(self, contexts: List[ProcessedContext]) -> List[ProcessedContext]:
        """
        处理跨类型关联：识别转换机会并创建新的关联上下文
        """
        if not self.enable_cross_type_processing or not contexts:
            return []
        
        logger.info(f"Processing cross-type relationships for {len(contexts)} contexts")
        
        try:
            # 识别转换机会
            conversion_opportunities = self.cross_type_manager.identify_conversion_opportunities(contexts)
            
            new_contexts = []
            
            for context, transition, confidence in conversion_opportunities:
                logger.info(f"Converting {context.id} via {transition.value} with confidence {confidence:.3f}")
                
                converted_context = self.cross_type_manager.convert_context_type(context, transition)
                if converted_context:
                    new_contexts.append(converted_context)
            
            logger.info(f"Generated {len(new_contexts)} cross-type converted contexts")
            return new_contexts
            
        except Exception as e:
            logger.error(f"Error in cross-type relationship processing: {e}", exc_info=True)
            return []
    
    def find_related_contexts_across_types(self, context: ProcessedContext, limit: int = 5) -> List[Tuple[ProcessedContext, str, float]]:
        """
        跨类型寻找相关上下文
        """
        if not self.enable_cross_type_processing:
            return []
        
        try:
            # 获取所有上下文进行关联分析
            all_contexts_dict = self.storage.get_all_processed_contexts(limit=1000, offset=0, filter={})
            all_contexts = []
            for contexts_list in all_contexts_dict.values():
                all_contexts.extend(contexts_list)
            
            # 使用跨类型管理器寻找关联
            related_contexts = self.cross_type_manager.suggest_related_contexts(
                context, all_contexts
            )
            
            return related_contexts[:limit]
            
        except Exception as e:
            logger.error(f"Error finding related contexts across types: {e}", exc_info=True)
            return []
    
    def intelligent_context_evolution(self):
        """
        智能上下文演化：定期处理跨类型转换和关联
        """
        if not self.enable_cross_type_processing:
            return
        
        logger.info("Starting intelligent context evolution process")
        
        try:
            # 获取最近的上下文进行演化分析
            recent_filter = {
                "update_time_ts": {
                    "$gte": int((datetime.now() - timedelta(hours=self.cleanup_interval_hours)).timestamp())
                }
            }
            
            contexts_dict = self.storage.get_all_processed_contexts(
                limit=500, 
                offset=0, 
                filter=recent_filter
            )
            
            all_contexts = []
            for contexts_list in contexts_dict.values():
                all_contexts.extend(contexts_list)
            
            if not all_contexts:
                logger.info("No recent contexts found for evolution processing")
                return
            
            # 处理跨类型关联
            new_contexts = self.process_cross_type_relationships(all_contexts)
            
            # 存储新生成的关联上下文
            stored_count = 0
            for new_context in new_contexts:
                try:
                    self.storage.upsert_processed_context(new_context)
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing evolved context: {e}")
            
            logger.info(f"Context evolution completed: {stored_count} new contexts created")
            
        except Exception as e:
            logger.error(f"Error during intelligent context evolution: {e}", exc_info=True)
    
    def analyze_context_relationships(self, context_id: str) -> Dict[str, Any]:
        """
        分析指定上下文的跨类型关系
        """
        try:
            # 找到目标上下文
            target_context = self._find_context_by_id(context_id)
            if not target_context:
                return {"error": f"Context {context_id} not found"}
            
            # 分析关系
            related_contexts = self.find_related_contexts_across_types(target_context, limit=10)
            
            # 识别可能的转换
            conversion_opportunities = self.cross_type_manager.identify_conversion_opportunities([target_context])
            
            return {
                "context_id": context_id,
                "context_type": target_context.extracted_data.context_type.value,
                "related_contexts": [
                    {
                        "id": ctx.id,
                        "type": ctx.extracted_data.context_type.value,
                        "title": ctx.extracted_data.title,
                        "relation_type": rel_type,
                        "strength": strength
                    }
                    for ctx, rel_type, strength in related_contexts
                ],
                "conversion_opportunities": [
                    {
                        "transition": transition.value,
                        "confidence": confidence,
                        "target_type": self.cross_type_manager._get_target_type(transition).value
                    }
                    for _, transition, confidence in conversion_opportunities
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing context relationships: {e}", exc_info=True)
            return {"error": str(e)}