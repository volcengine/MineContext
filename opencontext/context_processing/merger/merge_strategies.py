#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
ContextType-based intelligent merge strategy system
Provides specialized merge strategies and memory management mechanisms for different types of contexts
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple, Any
import math

from opencontext.models.context import ProcessedContext, ExtractedData
from opencontext.models.enums import ContextType, MergeType
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ContextTypeAwareStrategy(ABC):
    """
    Context type-aware merge strategy base class
    Each ContextType has specialized merge logic and memory management strategies
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.context_type = self.get_context_type()
        self.similarity_threshold = config.get(f'{self.context_type.value}_similarity_threshold', 0.8)
        self.retention_days = config.get(f'{self.context_type.value}_retention_days', 30)
        self.max_merge_count = config.get(f'{self.context_type.value}_max_merge_count', 3)
        
    @abstractmethod
    def get_context_type(self) -> ContextType:
        """Return the context type handled by this strategy"""
        pass
    
    @abstractmethod
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        Determine if two contexts can be merged, return (can_merge, similarity_score)
        """
        pass
    
    @abstractmethod 
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Execute specific merge logic, return merged context
        """
        pass
    
    def calculate_forgetting_probability(self, context: ProcessedContext) -> float:
        """
        Calculate forgetting probability based on forgetting curve, different types have different forgetting strategies
        """
        if not context.properties.update_time:
            return 0.0
            
        # Calculate age in days
        age_days = (datetime.now() - context.properties.update_time).days
        
        # Basic forgetting curve: P(t) = 1 - e^(-t/τ), where τ is the time constant
        tau = self.retention_days / 3  # Time constant, 1/3 of retention_days
        base_forgetting = 1.0 - math.exp(-age_days / tau)
        
        # Importance adjustment: higher importance means lower forgetting probability
        importance_factor = (10 - context.extracted_data.importance) / 10.0
        
        # Access frequency adjustment: more frequent access means lower forgetting probability
        access_factor = 1.0 / (1 + context.properties.merge_count)
        
        # Final forgetting probability
        forgetting_prob = base_forgetting * importance_factor * access_factor
        
        return min(forgetting_prob, 0.95)  # Maximum forgetting probability capped at 95%
    
    def should_cleanup(self, context: ProcessedContext) -> bool:
        """
        Determine if this context should be cleaned up
        """
        if not context.properties.update_time:
            return False
            
        age_days = (datetime.now() - context.properties.update_time).days
        
        # Clean up if exceeds retention period and has low importance
        if age_days > self.retention_days and context.extracted_data.importance < 5:
            return True
            
        # Probabilistic cleanup based on forgetting curve
        import random
        forgetting_prob = self.calculate_forgetting_probability(context)
        return random.random() < forgetting_prob
    
    def get_merge_prompt_name(self) -> str:
        """Get type-specific merge prompt name"""
        return f"merging.{self.context_type.value}_merging"


class ProfileContextStrategy(ContextTypeAwareStrategy):
    """Personal identity profile merge strategy"""
    
    def get_context_type(self) -> ContextType:
        return ContextType.ENTITY_CONTEXT
    
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        Profile type merge criteria:
        1. High entity overlap (same person)
        2. Related skills and characteristics
        3. Time span not too large
        """
        # Entity overlap check
        target_entities = set(target.extracted_data.entities)
        source_entities = set(source.extracted_data.entities)
        
        if not target_entities or not source_entities:
            return False, 0.0
        
        entity_overlap = len(target_entities.intersection(source_entities)) / len(target_entities.union(source_entities))
        
        if entity_overlap < 0.3:  # Profile requires high entity overlap
            return False, 0.0
        
        # Vector similarity check
        if target.vectorize and source.vectorize:
            vector_sim = self._calculate_cosine_similarity(
                target.vectorize.vector, 
                source.vectorize.vector
            )
            
            # Profile type requires higher similarity threshold
            if vector_sim > 0.85:
                # Composite score: entity overlap + vector similarity
                final_score = (entity_overlap * 0.4) + (vector_sim * 0.6)
                return True, final_score
        
        return False, 0.0
    
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Profile merge logic: incremental identity construction
        """
        # Merge entities and keywords, maintaining uniqueness
        merged_entities = list(set(target.extracted_data.entities))
        merged_keywords = list(set(target.extracted_data.keywords))
        merged_tags = list(set(target.extracted_data.tags))
        
        for source in sources:
            merged_entities.extend([e for e in source.extracted_data.entities if e not in merged_entities])
            merged_keywords.extend([k for k in source.extracted_data.keywords if k not in merged_keywords])
            merged_tags.extend([t for t in source.extracted_data.tags if t not in merged_tags])
        
        # Generate merged title and summary
        merged_title = self._merge_profile_titles(target, sources)
        merged_summary = self._merge_profile_summaries(target, sources)
        
        # Take highest importance, average confidence
        merged_importance = max([target.extracted_data.importance] + [s.extracted_data.importance for s in sources])
        merged_confidence = sum([target.extracted_data.confidence] + [s.extracted_data.confidence for s in sources]) // (len(sources) + 1)
        
        return self._create_merged_context(target, sources, {
            'title': merged_title,
            'summary': merged_summary,
            'entities': merged_entities,
            'keywords': merged_keywords,
            'tags': merged_tags,
            'importance': merged_importance,
            'confidence': merged_confidence
        })
    
    def _merge_profile_titles(self, target: ProcessedContext, sources: List[ProcessedContext]) -> str:
        """Merge profile titles: highlight core identity"""
        titles = [target.extracted_data.title] + [s.extracted_data.title for s in sources]
        
        # Simple title merging logic, may need LLM processing in practice
        main_entities = list(set(target.extracted_data.entities))
        if main_entities:
            return f"{main_entities[0]} Comprehensive Identity Profile"
        return f"Comprehensive Identity Profile - Based on {len(sources)+1} records"
    
    def _merge_profile_summaries(self, target: ProcessedContext, sources: List[ProcessedContext]) -> str:
        """合并Profile摘要：综合描述身份特征"""
        summaries = [target.extracted_data.summary] + [s.extracted_data.summary for s in sources]
        
        # 简化的摘要合并，实际应该用LLM进行智能融合
        return f"综合{len(summaries)}项记录的身份信息: " + "; ".join(summaries[:3])
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _create_merged_context(self, target: ProcessedContext, sources: List[ProcessedContext], merged_data: Dict[str, Any]) -> ProcessedContext:
        """创建合并后的上下文对象"""
        from opencontext.models.context import ContextProperties, Vectorize
        
        extracted_data = ExtractedData(
            title=merged_data['title'],
            summary=merged_data['summary'],
            keywords=merged_data['keywords'],
            entities=merged_data['entities'],
            tags=merged_data['tags'],
            context_type=target.extracted_data.context_type,
            confidence=merged_data['confidence'],
            importance=merged_data['importance'],
        )
        
        properties = ContextProperties(
            raw_properties=target.properties.raw_properties,
            create_time=target.properties.create_time,
            event_time=target.properties.event_time,
            is_processed=True,
            has_compression=True,
            update_time=datetime.now(),
            merge_count=target.properties.merge_count + len(sources),
            duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
            enable_merge=True,
        )
        
        return ProcessedContext(
            extracted_data=extracted_data,
            properties=properties,
            vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
        )


class ActivityContextStrategy(ContextTypeAwareStrategy):
    """行为活动历史记录合并策略"""
    
    def get_context_type(self) -> ContextType:
        return ContextType.ACTIVITY_CONTEXT
    
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        Activity类型的合并判断：
        1. 时间窗口内的活动
        2. 相同项目或任务的活动
        3. 相似的行为模式
        """
        # 时间窗口检查（默认24小时）
        time_window = timedelta(hours=self.config.get(f'{self.context_type.value}_time_window_hours', 24))
        
        if target.properties.create_time and source.properties.create_time:
            time_diff = abs(target.properties.create_time - source.properties.create_time)
            if time_diff > time_window:
                return False, 0.0
        
        # 实体和关键词重叠检查（项目/任务相关性）
        target_entities = set(target.extracted_data.entities)
        source_entities = set(source.extracted_data.entities)
        target_keywords = set(target.extracted_data.keywords)
        source_keywords = set(source.extracted_data.keywords)
        
        entity_overlap = 0.0
        if target_entities and source_entities:
            entity_overlap = len(target_entities.intersection(source_entities)) / len(target_entities.union(source_entities))
        
        keyword_overlap = 0.0
        if target_keywords and source_keywords:
            keyword_overlap = len(target_keywords.intersection(source_keywords)) / len(target_keywords.union(source_keywords))
        
        # Activity需要中等程度的重叠
        if entity_overlap > 0.2 or keyword_overlap > 0.3:
            # 向量相似度检查
            if target.vectorize and source.vectorize:
                vector_sim = self._calculate_cosine_similarity(
                    target.vectorize.vector, 
                    source.vectorize.vector
                )
                
                if vector_sim > 0.7:  # Activity相似度阈值
                    final_score = (entity_overlap * 0.3) + (keyword_overlap * 0.3) + (vector_sim * 0.4)
                    return True, final_score
        
        return False, 0.0
    
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Activity合并逻辑：时间序列聚合和行为模式提取
        """
        # 按时间排序所有活动
        all_contexts = [target] + sources
        all_contexts.sort(key=lambda x: x.properties.create_time or datetime.min)
        
        # 提取时间范围
        start_time = all_contexts[0].properties.create_time
        end_time = all_contexts[-1].properties.create_time
        
        # 合并实体和关键词，保持出现频次信息
        merged_entities = self._merge_with_frequency([ctx.extracted_data.entities for ctx in all_contexts])
        merged_keywords = self._merge_with_frequency([ctx.extracted_data.keywords for ctx in all_contexts])
        merged_tags = list(set([tag for ctx in all_contexts for tag in ctx.extracted_data.tags]))
        
        # 生成活动序列摘要
        merged_title = f"活动序列: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}"
        merged_summary = self._create_activity_sequence_summary(all_contexts)
        
        # 重要性和置信度计算
        merged_importance = max([ctx.extracted_data.importance for ctx in all_contexts])
        merged_confidence = sum([ctx.extracted_data.confidence for ctx in all_contexts]) // len(all_contexts)
        
        return self._create_merged_context(target, sources, {
            'title': merged_title,
            'summary': merged_summary,
            'entities': merged_entities,
            'keywords': merged_keywords,
            'tags': merged_tags,
            'importance': merged_importance,
            'confidence': merged_confidence
        })
    
    def _merge_with_frequency(self, item_lists: List[List[str]]) -> List[str]:
        """合并项目列表，保持高频项目在前"""
        from collections import Counter
        
        all_items = [item for sublist in item_lists for item in sublist]
        counter = Counter(all_items)
        
        # 返回按频次排序的项目列表，最多保留10个
        return [item for item, count in counter.most_common(10)]
    
    def _create_activity_sequence_summary(self, contexts: List[ProcessedContext]) -> str:
        """创建活动序列摘要"""
        if len(contexts) == 1:
            return contexts[0].extracted_data.summary
        
        # 提取关键活动点
        key_activities = []
        for ctx in contexts:
            # 简化逻辑：取每个活动的标题作为关键点
            key_activities.append(ctx.extracted_data.title)
        
        return f"包含{len(contexts)}个活动的序列: " + " -> ".join(key_activities[:5])
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _create_merged_context(self, target: ProcessedContext, sources: List[ProcessedContext], merged_data: Dict[str, Any]) -> ProcessedContext:
        """创建合并后的上下文对象"""
        from opencontext.models.context import ContextProperties, Vectorize
        
        extracted_data = ExtractedData(
            title=merged_data['title'],
            summary=merged_data['summary'],
            keywords=merged_data['keywords'],
            entities=merged_data['entities'],
            tags=merged_data['tags'],
            context_type=target.extracted_data.context_type,
            confidence=merged_data['confidence'],
            importance=merged_data['importance'],
        )
        
        properties = ContextProperties(
            raw_properties=target.properties.raw_properties,
            create_time=min([target.properties.create_time] + [s.properties.create_time for s in sources if s.properties.create_time]),
            event_time=target.properties.event_time,
            is_processed=True,
            has_compression=True,
            update_time=datetime.now(),
            merge_count=target.properties.merge_count + len(sources),
            duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
            enable_merge=True,
        )
        
        return ProcessedContext(
            extracted_data=extracted_data,
            properties=properties,
            vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
        )


class StateContextStrategy(ContextTypeAwareStrategy):
    """状态进度监控记录合并策略"""
    
    def get_context_type(self) -> ContextType:
        return ContextType.STATE_CONTEXT
    
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        State类型的合并判断：
        1. 很短的时间窗口（分钟级）
        2. 相同监控对象
        3. 状态变化的连续性
        """
        # 短时间窗口检查（默认30分钟）
        time_window = timedelta(minutes=self.config.get(f'{self.context_type.value}_time_window_minutes', 30))
        
        if target.properties.create_time and source.properties.create_time:
            time_diff = abs(target.properties.create_time - source.properties.create_time)
            if time_diff > time_window:
                return False, 0.0
        
        # 监控对象相同性检查（基于实体）
        target_entities = set(target.extracted_data.entities)
        source_entities = set(source.extracted_data.entities)
        
        if not target_entities or not source_entities:
            return False, 0.0
        
        entity_overlap = len(target_entities.intersection(source_entities)) / len(target_entities.union(source_entities))
        
        # State需要高度的实体重叠（监控同一对象）
        if entity_overlap > 0.8:
            return True, entity_overlap
        
        return False, 0.0
    
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        State合并逻辑：状态序列压缩和趋势提取
        """
        # 按时间排序
        all_contexts = [target] + sources
        all_contexts.sort(key=lambda x: x.properties.create_time or datetime.min)
        
        # 提取状态序列的关键信息
        start_time = all_contexts[0].properties.create_time
        end_time = all_contexts[-1].properties.create_time
        
        # 合并实体（监控对象）和关键词（状态指标）
        merged_entities = list(set([entity for ctx in all_contexts for entity in ctx.extracted_data.entities]))
        merged_keywords = self._extract_state_trends([ctx.extracted_data.keywords for ctx in all_contexts])
        merged_tags = list(set([tag for ctx in all_contexts for tag in ctx.extracted_data.tags]))
        
        # 生成状态趋势摘要
        merged_title = f"状态监控: {merged_entities[0] if merged_entities else '系统'} ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})"
        merged_summary = self._create_state_trend_summary(all_contexts)
        
        # 状态类型的重要性通常较低，但最新的状态最重要
        merged_importance = all_contexts[-1].extracted_data.importance  # 取最新状态的重要性
        merged_confidence = sum([ctx.extracted_data.confidence for ctx in all_contexts]) // len(all_contexts)
        
        return self._create_merged_context(target, sources, {
            'title': merged_title,
            'summary': merged_summary,
            'entities': merged_entities,
            'keywords': merged_keywords,
            'tags': merged_tags,
            'importance': merged_importance,
            'confidence': merged_confidence
        })
    
    def _extract_state_trends(self, keyword_lists: List[List[str]]) -> List[str]:
        """从状态序列中提取趋势关键词"""
        from collections import Counter
        
        all_keywords = [kw for sublist in keyword_lists for kw in sublist]
        counter = Counter(all_keywords)
        
        # 状态关键词通常是数值和趋势词汇
        trend_keywords = []
        for kw, count in counter.most_common(8):
            if any(indicator in kw.lower() for indicator in ['增长', '下降', '稳定', '异常', '正常', '%', 'cpu', 'memory', 'disk']):
                trend_keywords.append(kw)
        
        return trend_keywords[:6]
    
    def _create_state_trend_summary(self, contexts: List[ProcessedContext]) -> str:
        """创建状态趋势摘要"""
        if len(contexts) == 1:
            return contexts[0].extracted_data.summary
        
        # 简化的趋势分析
        first_state = contexts[0].extracted_data.summary
        last_state = contexts[-1].extracted_data.summary
        
        return f"状态变化序列({len(contexts)}个数据点): {first_state[:50]}... -> {last_state[:50]}..."
    
    def calculate_forgetting_probability(self, context: ProcessedContext) -> float:
        """State类型的遗忘概率更高，因为状态信息时效性强"""
        base_prob = super().calculate_forgetting_probability(context)
        
        # State类型的遗忘速度是基础速度的2倍
        return min(base_prob * 2.0, 0.98)
    
    def should_cleanup(self, context: ProcessedContext) -> bool:
        """State类型更积极地清理过期数据"""
        if not context.properties.update_time:
            return False
        
        age_hours = (datetime.now() - context.properties.update_time).total_seconds() / 3600
        
        # 超过48小时的状态数据，如果重要性低于6就清理
        if age_hours > 48 and context.extracted_data.importance < 6:
            return True
        
        return super().should_cleanup(context)
    
    def _create_merged_context(self, target: ProcessedContext, sources: List[ProcessedContext], merged_data: Dict[str, Any]) -> ProcessedContext:
        """创建合并后的上下文对象"""
        from opencontext.models.context import ContextProperties, Vectorize
        
        extracted_data = ExtractedData(
            title=merged_data['title'],
            summary=merged_data['summary'],
            keywords=merged_data['keywords'],
            entities=merged_data['entities'],
            tags=merged_data['tags'],
            context_type=target.extracted_data.context_type,
            confidence=merged_data['confidence'],
            importance=merged_data['importance'],
        )
        
        properties = ContextProperties(
            raw_properties=target.properties.raw_properties,
            create_time=min([target.properties.create_time] + [s.properties.create_time for s in sources if s.properties.create_time]),
            event_time=max([target.properties.event_time] + [s.properties.event_time for s in sources if s.properties.event_time], default=None),
            is_processed=True,
            has_compression=True,
            update_time=datetime.now(),
            merge_count=target.properties.merge_count + len(sources),
            duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
            enable_merge=True,
        )
        
        return ProcessedContext(
            extracted_data=extracted_data,
            properties=properties,
            vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
        )


class IntentContextStrategy(ContextTypeAwareStrategy):
    """意图规划目标记录合并策略"""
    
    def get_context_type(self) -> ContextType:
        return ContextType.INTENT_CONTEXT
    
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        Intent类型的合并判断：
        1. 相同目标或项目的意图
        2. 时间相关的计划安排
        3. 具有层次关系的目标
        """
        # 实体重叠检查（项目/目标相关性）
        target_entities = set(target.extracted_data.entities)
        source_entities = set(source.extracted_data.entities)
        
        entity_overlap = 0.0
        if target_entities and source_entities:
            entity_overlap = len(target_entities.intersection(source_entities)) / len(target_entities.union(source_entities))
        
        # 关键词重叠检查（意图类型相关性）
        target_keywords = set(target.extracted_data.keywords)
        source_keywords = set(source.extracted_data.keywords)
        
        keyword_overlap = 0.0
        if target_keywords and source_keywords:
            keyword_overlap = len(target_keywords.intersection(source_keywords)) / len(target_keywords.union(source_keywords))
        
        # Intent需要较强的语义相关性
        if entity_overlap > 0.25 or keyword_overlap > 0.35:
            # 向量相似度检查
            if target.vectorize and source.vectorize:
                vector_sim = self._calculate_cosine_similarity(
                    target.vectorize.vector, 
                    source.vectorize.vector
                )
                
                if vector_sim > 0.75:  # Intent相似度阈值
                    final_score = (entity_overlap * 0.35) + (keyword_overlap * 0.35) + (vector_sim * 0.3)
                    return True, final_score
        
        return False, 0.0
    
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Intent合并逻辑：目标层次合并和计划整合
        """
        # 按时间排序（更好地理解计划发展）
        all_contexts = [target] + sources
        all_contexts.sort(key=lambda x: x.properties.create_time or datetime.min)
        
        # 合并目标和计划
        merged_entities = self._merge_intent_entities([ctx.extracted_data.entities for ctx in all_contexts])
        merged_keywords = self._merge_intent_keywords([ctx.extracted_data.keywords for ctx in all_contexts])
        merged_tags = list(set([tag for ctx in all_contexts for tag in ctx.extracted_data.tags]))
        
        # 生成整合后的意图描述
        merged_title = self._create_integrated_intent_title(all_contexts)
        merged_summary = self._create_integrated_intent_summary(all_contexts)
        
        # 意图的重要性通常较高，取最高值
        merged_importance = max([ctx.extracted_data.importance for ctx in all_contexts])
        merged_confidence = sum([ctx.extracted_data.confidence for ctx in all_contexts]) // len(all_contexts)
        
        return self._create_merged_context(target, sources, {
            'title': merged_title,
            'summary': merged_summary,
            'entities': merged_entities,
            'keywords': merged_keywords,
            'tags': merged_tags,
            'importance': merged_importance,
            'confidence': merged_confidence
        })
    
    def _merge_intent_entities(self, entity_lists: List[List[str]]) -> List[str]:
        """合并意图实体，识别目标层次"""
        from collections import Counter
        
        all_entities = [entity for sublist in entity_lists for entity in sublist]
        counter = Counter(all_entities)
        
        # 优先保留高频实体（核心目标）
        return [entity for entity, count in counter.most_common(8)]
    
    def _merge_intent_keywords(self, keyword_lists: List[List[str]]) -> List[str]:
        """合并意图关键词，保持计划特征"""
        from collections import Counter
        
        all_keywords = [kw for sublist in keyword_lists for kw in sublist]
        counter = Counter(all_keywords)
        
        # 优先保留计划相关的关键词
        intent_keywords = []
        for kw, count in counter.most_common(10):
            if any(indicator in kw.lower() for indicator in ['计划', '目标', '完成', '实现', '希望', '打算']):
                intent_keywords.append(kw)
        
        # 补充其他高频关键词
        for kw, count in counter.most_common(6):
            if kw not in intent_keywords:
                intent_keywords.append(kw)
        
        return intent_keywords[:8]
    
    def _create_integrated_intent_title(self, contexts: List[ProcessedContext]) -> str:
        """创建整合的意图标题"""
        if len(contexts) == 1:
            return contexts[0].extracted_data.title
        
        # 提取核心实体作为主题
        main_entities = self._merge_intent_entities([ctx.extracted_data.entities for ctx in contexts])
        if main_entities:
            return f"{main_entities[0]}相关计划整合 ({len(contexts)}项意图)"
        
        return f"整合意图规划 ({len(contexts)}项计划)"
    
    def _create_integrated_intent_summary(self, contexts: List[ProcessedContext]) -> str:
        """创建整合的意图摘要"""
        if len(contexts) == 1:
            return contexts[0].extracted_data.summary
        
        # 按重要性排序，突出关键计划
        sorted_contexts = sorted(contexts, key=lambda x: x.extracted_data.importance, reverse=True)
        
        key_intents = []
        for ctx in sorted_contexts[:3]:  # 最多取3个关键意图
            key_intents.append(f"[{ctx.extracted_data.importance}] {ctx.extracted_data.summary[:60]}...")
        
        return f"包含{len(contexts)}个相关意图的整合计划: " + "; ".join(key_intents)
    
    def calculate_forgetting_probability(self, context: ProcessedContext) -> float:
        """Intent的遗忘策略：未完成的意图需要保留，已完成的可以转化"""
        base_prob = super().calculate_forgetting_probability(context)
        
        # 检查是否包含完成相关的关键词
        completion_indicators = ['完成', '达成', '实现', '成功']
        has_completion = any(indicator in context.extracted_data.summary for indicator in completion_indicators)
        
        if has_completion:
            # 已完成的意图可以有更高的遗忘概率（转化为活动记录）
            return min(base_prob * 1.5, 0.9)
        else:
            # 未完成的意图需要保留
            return base_prob * 0.7
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _create_merged_context(self, target: ProcessedContext, sources: List[ProcessedContext], merged_data: Dict[str, Any]) -> ProcessedContext:
        """创建合并后的上下文对象"""
        from opencontext.models.context import ContextProperties, Vectorize
        
        extracted_data = ExtractedData(
            title=merged_data['title'],
            summary=merged_data['summary'],
            keywords=merged_data['keywords'],
            entities=merged_data['entities'],
            tags=merged_data['tags'],
            context_type=target.extracted_data.context_type,
            confidence=merged_data['confidence'],
            importance=merged_data['importance'],
        )
        
        properties = ContextProperties(
            raw_properties=target.properties.raw_properties,
            create_time=min([target.properties.create_time] + [s.properties.create_time for s in sources if s.properties.create_time]),
            event_time=target.properties.event_time,
            is_processed=True,
            has_compression=True,
            update_time=datetime.now(),
            merge_count=target.properties.merge_count + len(sources),
            duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
            enable_merge=True,
        )
        
        return ProcessedContext(
            extracted_data=extracted_data,
            properties=properties,
            vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
        )
class SemanticContextStrategy(ContextTypeAwareStrategy):
    """语义知识概念记录合并策略"""
    
    def get_context_type(self) -> ContextType:
        return ContextType.SEMANTIC_CONTEXT
    
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        Semantic类型的合并判断：
        1. 概念相关性
        2. 知识领域的重叠
        3. 定义的互补性
        """
        # 实体重叠（概念相关性）
        target_entities = set(target.extracted_data.entities)
        source_entities = set(source.extracted_data.entities)
        
        entity_overlap = 0.0
        if target_entities and source_entities:
            entity_overlap = len(target_entities.intersection(source_entities)) / len(target_entities.union(source_entities))
        
        # 关键词重叠（知识领域相关性）
        target_keywords = set(target.extracted_data.keywords)
        source_keywords = set(source.extracted_data.keywords)
        
        keyword_overlap = 0.0
        if target_keywords and source_keywords:
            keyword_overlap = len(target_keywords.intersection(source_keywords)) / len(target_keywords.union(source_keywords))
        
        # Semantic需要中等程度的相关性
        if entity_overlap > 0.3 or keyword_overlap > 0.4:
            # 向量相似度检查
            if target.vectorize and source.vectorize:
                vector_sim = self._calculate_cosine_similarity(
                    target.vectorize.vector, 
                    source.vectorize.vector
                )
                
                if vector_sim > 0.72:  # Semantic相似度阈值
                    final_score = (entity_overlap * 0.3) + (keyword_overlap * 0.4) + (vector_sim * 0.3)
                    return True, final_score
        
        return False, 0.0
    
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Semantic合并逻辑：知识图谱构建和概念层次合并
        """
        # 合并概念实体，构建知识网络
        merged_entities = self._merge_semantic_entities([target.extracted_data.entities] + [s.extracted_data.entities for s in sources])
        merged_keywords = self._merge_semantic_keywords([target.extracted_data.keywords] + [s.extracted_data.keywords for s in sources])
        merged_tags = list(set([tag for ctx in [target] + sources for tag in ctx.extracted_data.tags]))
        
        # 生成综合的概念描述
        merged_title = self._create_semantic_title(target, sources)
        merged_summary = self._create_semantic_summary(target, sources)
        
        # 语义知识的重要性基于概念的核心程度
        merged_importance = max([target.extracted_data.importance] + [s.extracted_data.importance for s in sources])
        merged_confidence = sum([target.extracted_data.confidence] + [s.extracted_data.confidence for s in sources]) // (len(sources) + 1)
        
        return self._create_merged_context(target, sources, {
            'title': merged_title,
            'summary': merged_summary,
            'entities': merged_entities,
            'keywords': merged_keywords,
            'tags': merged_tags,
            'importance': merged_importance,
            'confidence': merged_confidence
        })
    
    def _merge_semantic_entities(self, entity_lists: List[List[str]]) -> List[str]:
        """合并语义实体，识别核心概念"""
        from collections import Counter
        
        all_entities = [entity for sublist in entity_lists for entity in sublist]
        counter = Counter(all_entities)
        
        # 优先保留高频实体（核心概念）
        return [entity for entity, count in counter.most_common(10)]
    
    def _merge_semantic_keywords(self, keyword_lists: List[List[str]]) -> List[str]:
        """合并语义关键词，保持知识特征"""
        from collections import Counter
        
        all_keywords = [kw for sublist in keyword_lists for kw in sublist]
        counter = Counter(all_keywords)
        
        # 优先保留概念相关的关键词
        semantic_keywords = []
        for kw, count in counter.most_common(12):
            if any(indicator in kw.lower() for indicator in ['定义', '概念', '理论', '方法', '原理', '特征']):
                semantic_keywords.append(kw)
        
        # 补充其他高频关键词
        for kw, count in counter.most_common(8):
            if kw not in semantic_keywords:
                semantic_keywords.append(kw)
        
        return semantic_keywords[:10]
    
    def _create_semantic_title(self, target: ProcessedContext, sources: List[ProcessedContext]) -> str:
        """创建语义概念标题"""
        if len(sources) == 0:
            return target.extracted_data.title
        
        # 提取核心概念
        all_entities = self._merge_semantic_entities([target.extracted_data.entities] + [s.extracted_data.entities for s in sources])
        if all_entities:
            return f"{all_entities[0]}相关概念知识 ({len(sources)+1}项整合)"
        
        return f"概念知识整合 ({len(sources)+1}项定义)"
    
    def _create_semantic_summary(self, target: ProcessedContext, sources: List[ProcessedContext]) -> str:
        """创建语义概念摘要"""
        if len(sources) == 0:
            return target.extracted_data.summary
        
        # 按置信度排序，优先展示可靠的定义
        all_contexts = [target] + sources
        sorted_contexts = sorted(all_contexts, key=lambda x: x.extracted_data.confidence, reverse=True)
        
        key_concepts = []
        for ctx in sorted_contexts[:3]:  # 最多取3个关键概念
            key_concepts.append(f"[置信度{ctx.extracted_data.confidence}] {ctx.extracted_data.summary[:80]}...")
        
        return f"知识整合的{len(all_contexts)}个相关概念: " + "; ".join(key_concepts)
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _create_merged_context(self, target: ProcessedContext, sources: List[ProcessedContext], merged_data: Dict[str, Any]) -> ProcessedContext:
        """创建合并后的上下文对象"""
        from opencontext.models.context import ContextProperties, Vectorize
        
        extracted_data = ExtractedData(
            title=merged_data['title'],
            summary=merged_data['summary'],
            keywords=merged_data['keywords'],
            entities=merged_data['entities'],
            tags=merged_data['tags'],
            context_type=target.extracted_data.context_type,
            confidence=merged_data['confidence'],
            importance=merged_data['importance'],
        )
        
        properties = ContextProperties(
            raw_properties=target.properties.raw_properties,
            create_time=target.properties.create_time,
            event_time=target.properties.event_time,
            is_processed=True,
            has_compression=True,
            update_time=datetime.now(),
            merge_count=target.properties.merge_count + len(sources),
            duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
            enable_merge=True,
        )
        
        return ProcessedContext(
            extracted_data=extracted_data,
            properties=properties,
            vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
        )


class ProceduralContextStrategy(ContextTypeAwareStrategy):
    """流程方法操作记录合并策略"""
    
    def get_context_type(self) -> ContextType:
        return ContextType.PROCEDURAL_CONTEXT
    
    def can_merge(self, target: ProcessedContext, source: ProcessedContext) -> Tuple[bool, float]:
        """
        Procedural类型的合并判断：
        1. 相同工具或方法
        2. 类似的操作流程
        3. 相关的应用场景
        """
        # 实体重叠（工具/方法相关性）
        target_entities = set(target.extracted_data.entities)
        source_entities = set(source.extracted_data.entities)
        
        entity_overlap = 0.0
        if target_entities and source_entities:
            entity_overlap = len(target_entities.intersection(source_entities)) / len(target_entities.union(source_entities))
        
        # 关键词重叠（操作步骤相关性）
        target_keywords = set(target.extracted_data.keywords)
        source_keywords = set(source.extracted_data.keywords)
        
        keyword_overlap = 0.0
        if target_keywords and source_keywords:
            keyword_overlap = len(target_keywords.intersection(source_keywords)) / len(target_keywords.union(source_keywords))
        
        # Procedural需要中高程度的相关性
        if entity_overlap > 0.35 or keyword_overlap > 0.45:
            # 向量相似度检查
            if target.vectorize and source.vectorize:
                vector_sim = self._calculate_cosine_similarity(
                    target.vectorize.vector, 
                    source.vectorize.vector
                )
                
                if vector_sim > 0.75:  # Procedural相似度阈值
                    final_score = (entity_overlap * 0.35) + (keyword_overlap * 0.35) + (vector_sim * 0.3)
                    return True, final_score
        
        return False, 0.0
    
    def merge_contexts(self, target: ProcessedContext, sources: List[ProcessedContext]) -> Optional[ProcessedContext]:
        """
        Procedural合并逻辑：流程步骤整合和最佳实践提取
        """
        # 合并工具和方法
        merged_entities = self._merge_procedural_entities([target.extracted_data.entities] + [s.extracted_data.entities for s in sources])
        merged_keywords = self._merge_procedural_keywords([target.extracted_data.keywords] + [s.extracted_data.keywords for s in sources])
        merged_tags = list(set([tag for ctx in [target] + sources for tag in ctx.extracted_data.tags]))
        
        # 生成整合的流程描述
        merged_title = self._create_procedural_title(target, sources)
        merged_summary = self._create_procedural_summary(target, sources)
        
        # 流程的重要性基于实用性和完整性
        merged_importance = max([target.extracted_data.importance] + [s.extracted_data.importance for s in sources])
        merged_confidence = sum([target.extracted_data.confidence] + [s.extracted_data.confidence for s in sources]) // (len(sources) + 1)
        
        return self._create_merged_context(target, sources, {
            'title': merged_title,
            'summary': merged_summary,
            'entities': merged_entities,
            'keywords': merged_keywords,
            'tags': merged_tags,
            'importance': merged_importance,
            'confidence': merged_confidence
        })
    
    def _merge_procedural_entities(self, entity_lists: List[List[str]]) -> List[str]:
        """合并流程实体，识别核心工具和方法"""
        from collections import Counter
        
        all_entities = [entity for sublist in entity_lists for entity in sublist]
        counter = Counter(all_entities)
        
        # 优先保留工具和方法相关的实体
        return [entity for entity, count in counter.most_common(8)]
    
    def _merge_procedural_keywords(self, keyword_lists: List[List[str]]) -> List[str]:
        """合并流程关键词，保持操作特征"""
        from collections import Counter
        
        all_keywords = [kw for sublist in keyword_lists for kw in sublist]
        counter = Counter(all_keywords)
        
        # 优先保留操作相关的关键词
        procedural_keywords = []
        for kw, count in counter.most_common(12):
            if any(indicator in kw.lower() for indicator in ['步骤', '操作', '方法', '流程', '配置', '设置', '安装']):
                procedural_keywords.append(kw)
        
        # 补充其他高频关键词
        for kw, count in counter.most_common(8):
            if kw not in procedural_keywords:
                procedural_keywords.append(kw)
        
        return procedural_keywords[:10]
    
    def _create_procedural_title(self, target: ProcessedContext, sources: List[ProcessedContext]) -> str:
        """创建流程方法标题"""
        if len(sources) == 0:
            return target.extracted_data.title
        
        # 提取核心工具/方法
        all_entities = self._merge_procedural_entities([target.extracted_data.entities] + [s.extracted_data.entities for s in sources])
        if all_entities:
            return f"{all_entities[0]}操作指南合集 ({len(sources)+1}项整合)"
        
        return f"操作流程指南 ({len(sources)+1}项方法)"
    
    def _create_procedural_summary(self, target: ProcessedContext, sources: List[ProcessedContext]) -> str:
        """创建流程方法摘要"""
        if len(sources) == 0:
            return target.extracted_data.summary
        
        # 按重要性排序，突出关键步骤
        all_contexts = [target] + sources
        sorted_contexts = sorted(all_contexts, key=lambda x: x.extracted_data.importance, reverse=True)
        
        key_procedures = []
        for ctx in sorted_contexts[:3]:  # 最多取3个关键流程
            key_procedures.append(f"[重要性{ctx.extracted_data.importance}] {ctx.extracted_data.summary[:70]}...")
        
        return f"包含{len(all_contexts)}个相关操作流程的整合指南: " + "; ".join(key_procedures[:5])
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _create_merged_context(self, target: ProcessedContext, sources: List[ProcessedContext], merged_data: Dict[str, Any]) -> ProcessedContext:
        """创建合并后的上下文对象"""
        from opencontext.models.context import ContextProperties, Vectorize
        
        extracted_data = ExtractedData(
            title=merged_data['title'],
            summary=merged_data['summary'],
            keywords=merged_data['keywords'],
            entities=merged_data['entities'],
            tags=merged_data['tags'],
            context_type=target.extracted_data.context_type,
            confidence=merged_data['confidence'],
            importance=merged_data['importance'],
        )
        
        properties = ContextProperties(
            raw_properties=target.properties.raw_properties,
            create_time=target.properties.create_time,
            event_time=target.properties.event_time,
            is_processed=True,
            has_compression=True,
            update_time=datetime.now(),
            merge_count=target.properties.merge_count + len(sources),
            duration_count=target.properties.duration_count + sum(s.properties.duration_count for s in sources),
            enable_merge=True,
        )
        
        return ProcessedContext(
            extracted_data=extracted_data,
            properties=properties,
            vectorize=Vectorize(text=extracted_data.title + " " + extracted_data.summary),
        )


class StrategyFactory:
    """Merge strategy factory"""
    
    def __init__(self, config: dict):
        self.config = config
        self._strategies = {
            ContextType.ENTITY_CONTEXT: ProfileContextStrategy(config),
            ContextType.ACTIVITY_CONTEXT: ActivityContextStrategy(config),
            ContextType.STATE_CONTEXT: StateContextStrategy(config),
            ContextType.INTENT_CONTEXT: IntentContextStrategy(config),
            ContextType.SEMANTIC_CONTEXT: SemanticContextStrategy(config),
            ContextType.PROCEDURAL_CONTEXT: ProceduralContextStrategy(config),
        }
    
    def get_strategy(self, context_type: ContextType) -> Optional[ContextTypeAwareStrategy]:
        """Get the merge strategy for a specific context type"""
        return self._strategies.get(context_type)