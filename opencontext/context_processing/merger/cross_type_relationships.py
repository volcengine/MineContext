#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Cross-Type Intelligent Relationship Processor
Implements intelligent conversion and association between different ContextTypes
Simulates the process of mutual transformation of different types of information in human memory
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from opencontext.models.context import ContextProperties, ExtractedData, ProcessedContext, Vectorize
from opencontext.models.enums import ContextType
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CrossTypeTransition(Enum):
    """Cross-type transition enum"""

    INTENT_TO_ACTIVITY = "intent_to_activity"  # Intent completion -> Activity record
    ACTIVITY_TO_PROFILE = "activity_to_profile"  # Activity accumulation -> Personal profile update
    PROCEDURAL_TO_SEMANTIC = "procedural_to_semantic"  # Method abstraction -> Semantic concept
    STATE_TO_ACTIVITY = "state_to_activity"  # State change -> Activity trace
    ACTIVITY_TO_INTENT = "activity_to_intent"  # Activity pattern -> New intent recognition
    SEMANTIC_TO_PROCEDURAL = "semantic_to_procedural"  # Concept application -> Operational method


class CrossTypeRelationshipManager:
    """Cross-Type Relationship Manager"""

    def __init__(self, config: dict):
        self.config = config
        self.enable_cross_type_conversion = config.get("enable_cross_type_conversion", True)
        self.conversion_confidence_threshold = config.get("conversion_confidence_threshold", 0.8)
        self.max_conversions_per_session = config.get("max_conversions_per_session", 10)

        # Transition rule configuration
        self.transition_rules = self._initialize_transition_rules()
        self.conversion_stats = {"attempts": 0, "successes": 0, "failures": 0, "by_type": {}}

    def _initialize_transition_rules(self) -> Dict[CrossTypeTransition, Dict]:
        """Initialize transition rules"""
        return {
            CrossTypeTransition.INTENT_TO_ACTIVITY: {
                "trigger_keywords": ["complete", "achieve", "finish", "succeed", "end"],
                "confidence_boost": 0.1,
                "importance_adjustment": -1,  # Lower importance for completed intents
                "retention_days": 90,
            },
            CrossTypeTransition.ACTIVITY_TO_PROFILE: {
                "trigger_keywords": ["skill", "ability", "expertise", "experience", "achievement"],
                "confidence_boost": 0.2,
                "importance_adjustment": 1,  # Increase importance for personal profile
                "retention_days": 365,
                "min_activity_count": 3,  # At least 3 related activities to convert
            },
            CrossTypeTransition.PROCEDURAL_TO_SEMANTIC: {
                "trigger_keywords": ["principle", "theory", "concept", "methodology", "pattern"],
                "confidence_boost": 0.15,
                "importance_adjustment": 0,
                "retention_days": 180,
            },
            CrossTypeTransition.STATE_TO_ACTIVITY: {
                "trigger_keywords": ["change", "update", "upgrade", "complete", "switch"],
                "confidence_boost": 0.1,
                "importance_adjustment": -2,  # Importance of state changes is usually lower
                "retention_days": 30,
            },
            CrossTypeTransition.ACTIVITY_TO_INTENT: {
                "trigger_keywords": ["plan", "prepare", "start", "launch", "goal"],
                "confidence_boost": 0.2,
                "importance_adjustment": 2,  # New intents have higher importance
                "retention_days": 180,
                "pattern_threshold": 0.7,  # Activity pattern recognition threshold
            },
            CrossTypeTransition.SEMANTIC_TO_PROCEDURAL: {
                "trigger_keywords": ["apply", "practice", "operate", "steps", "implement"],
                "confidence_boost": 0.1,
                "importance_adjustment": 1,
                "retention_days": 120,
            },
        }

    def identify_conversion_opportunities(
        self, contexts: List[ProcessedContext]
    ) -> List[Tuple[ProcessedContext, CrossTypeTransition, float]]:
        """Identify cross-type conversion opportunities"""
        if not self.enable_cross_type_conversion:
            return []

        opportunities = []

        for context in contexts:
            # Check for possible conversions for each context
            for transition, rule in self.transition_rules.items():
                confidence = self._evaluate_conversion_confidence(context, transition, rule)
                if confidence > self.conversion_confidence_threshold:
                    opportunities.append((context, transition, confidence))

        # Sort by confidence
        opportunities.sort(key=lambda x: x[2], reverse=True)

        # Limit the number of conversions
        return opportunities[: self.max_conversions_per_session]

    def _evaluate_conversion_confidence(
        self, context: ProcessedContext, transition: CrossTypeTransition, rule: Dict
    ) -> float:
        """Evaluate conversion confidence"""
        confidence = 0.0

        # Check if the source type matches
        source_type = self._get_source_type(transition)
        if context.extracted_data.context_type != source_type:
            return 0.0

        # Keyword match check
        trigger_keywords = rule.get("trigger_keywords", [])
        keyword_matches = 0

        content_text = (context.extracted_data.title + " " + context.extracted_data.summary).lower()
        for keyword in trigger_keywords:
            if keyword in content_text:
                keyword_matches += 1

        if trigger_keywords:
            keyword_confidence = keyword_matches / len(trigger_keywords)
            confidence += keyword_confidence * 0.4

        # Based on context confidence
        base_confidence = context.extracted_data.confidence / 10.0
        confidence += base_confidence * 0.3

        # Based on importance
        importance_confidence = context.extracted_data.importance / 10.0
        confidence += importance_confidence * 0.2

        # Specific rule check
        confidence += self._evaluate_specific_rules(context, transition, rule)

        return min(confidence, 1.0)

    def _evaluate_specific_rules(
        self, context: ProcessedContext, transition: CrossTypeTransition, rule: Dict
    ) -> float:
        """Evaluate specific transition rules"""
        bonus_confidence = 0.0

        if transition == CrossTypeTransition.INTENT_TO_ACTIVITY:
            # Check if the intent is marked as completed
            if any(
                indicator in context.extracted_data.summary.lower()
                for indicator in ["completed", "finished", "achieved"]
            ):
                bonus_confidence += 0.2

        elif transition == CrossTypeTransition.ACTIVITY_TO_PROFILE:
            # Check if the activity reflects personal growth
            if any(
                indicator in context.extracted_data.keywords
                for indicator in ["learn", "improve", "master"]
            ):
                bonus_confidence += 0.15

        elif transition == CrossTypeTransition.STATE_TO_ACTIVITY:
            # Check if the state change is significant enough
            if context.extracted_data.importance >= 6:  # Important state change
                bonus_confidence += 0.1

        return bonus_confidence

    def _get_source_type(self, transition: CrossTypeTransition) -> ContextType:
        """Get the source type of the transition"""
        mapping = {
            CrossTypeTransition.INTENT_TO_ACTIVITY: ContextType.INTENT_CONTEXT,
            CrossTypeTransition.ACTIVITY_TO_PROFILE: ContextType.ACTIVITY_CONTEXT,
            CrossTypeTransition.PROCEDURAL_TO_SEMANTIC: ContextType.PROCEDURAL_CONTEXT,
            CrossTypeTransition.STATE_TO_ACTIVITY: ContextType.STATE_CONTEXT,
            CrossTypeTransition.ACTIVITY_TO_INTENT: ContextType.ACTIVITY_CONTEXT,
            CrossTypeTransition.SEMANTIC_TO_PROCEDURAL: ContextType.SEMANTIC_CONTEXT,
        }
        return mapping.get(transition)

    def _get_target_type(self, transition: CrossTypeTransition) -> ContextType:
        """Get the target type of the transition"""
        mapping = {
            CrossTypeTransition.INTENT_TO_ACTIVITY: ContextType.ACTIVITY_CONTEXT,
            CrossTypeTransition.ACTIVITY_TO_PROFILE: ContextType.ENTITY_CONTEXT,
            CrossTypeTransition.PROCEDURAL_TO_SEMANTIC: ContextType.SEMANTIC_CONTEXT,
            CrossTypeTransition.STATE_TO_ACTIVITY: ContextType.ACTIVITY_CONTEXT,
            CrossTypeTransition.ACTIVITY_TO_INTENT: ContextType.INTENT_CONTEXT,
            CrossTypeTransition.SEMANTIC_TO_PROCEDURAL: ContextType.PROCEDURAL_CONTEXT,
        }
        return mapping.get(transition)

    def convert_context_type(
        self, context: ProcessedContext, transition: CrossTypeTransition
    ) -> Optional[ProcessedContext]:
        """Execute cross-type conversion"""
        self.conversion_stats["attempts"] += 1

        try:
            target_type = self._get_target_type(transition)
            rule = self.transition_rules[transition]

            # Create converted extracted data
            converted_data = self._create_converted_extracted_data(
                context, target_type, transition, rule
            )

            # Create converted properties
            converted_properties = self._create_converted_properties(context, rule)

            # Create converted context
            converted_context = ProcessedContext(
                extracted_data=converted_data,
                properties=converted_properties,
                vectorize=Vectorize(text=converted_data.title + " " + converted_data.summary),
            )

            self.conversion_stats["successes"] += 1
            self.conversion_stats["by_type"][transition.value] = (
                self.conversion_stats["by_type"].get(transition.value, 0) + 1
            )

            logger.info(
                f"Successfully converted {context.extracted_data.context_type.value} to {target_type.value} via {transition.value}"
            )

            return converted_context

        except Exception as e:
            self.conversion_stats["failures"] += 1
            logger.error(f"Error converting context type: {e}", exc_info=True)
            return None

    def _create_converted_extracted_data(
        self,
        context: ProcessedContext,
        target_type: ContextType,
        transition: CrossTypeTransition,
        rule: Dict,
    ) -> ExtractedData:
        """Create converted extracted data"""

        # Basic conversion
        converted_title = self._convert_title(context, transition)
        converted_summary = self._convert_summary(context, transition)

        # Adjust importance and confidence
        importance_adjustment = rule.get("importance_adjustment", 0)
        confidence_boost = rule.get("confidence_boost", 0.0)

        new_importance = max(1, min(10, context.extracted_data.importance + importance_adjustment))
        new_confidence = max(
            1, min(10, int(context.extracted_data.confidence + confidence_boost * 10))
        )

        return ExtractedData(
            title=converted_title,
            summary=converted_summary,
            keywords=self._adapt_keywords(context.extracted_data.keywords, transition),
            entities=context.extracted_data.entities.copy(),  # Keep entities
            context_type=target_type,
            confidence=new_confidence,
            importance=new_importance,
        )

    def _create_converted_properties(
        self, context: ProcessedContext, rule: Dict
    ) -> ContextProperties:
        """Create converted properties"""
        return ContextProperties(
            raw_properties=context.properties.raw_properties,
            create_time=datetime.now(),  # Converted context gets a new creation time
            event_time=context.properties.event_time,
            is_processed=True,
            has_compression=False,  # Converted context is not yet compressed
            update_time=datetime.now(),
            merge_count=0,  # Reset merge count for new context
            duration_count=context.properties.duration_count,
            enable_merge=True,
        )

    def _convert_title(self, context: ProcessedContext, transition: CrossTypeTransition) -> str:
        """Convert title"""
        original_title = context.extracted_data.title

        conversion_prefixes = {
            CrossTypeTransition.INTENT_TO_ACTIVITY: "Completed Activity",
            CrossTypeTransition.ACTIVITY_TO_PROFILE: "Profile Update",
            CrossTypeTransition.PROCEDURAL_TO_SEMANTIC: "Methodology Summary",
            CrossTypeTransition.STATE_TO_ACTIVITY: "State Change Record",
            CrossTypeTransition.ACTIVITY_TO_INTENT: "Activity-Based Plan",
            CrossTypeTransition.SEMANTIC_TO_PROCEDURAL: "Concept Practice Guide",
        }

        prefix = conversion_prefixes.get(transition, "Conversion Record")
        return f"{prefix}: {original_title}"

    def _convert_summary(self, context: ProcessedContext, transition: CrossTypeTransition) -> str:
        """Convert summary"""
        original_summary = context.extracted_data.summary

        conversion_templates = {
            CrossTypeTransition.INTENT_TO_ACTIVITY: f"Activity completed based on the original plan: {original_summary}",
            CrossTypeTransition.ACTIVITY_TO_PROFILE: f"Personal ability demonstrated through the following activities: {original_summary}",
            CrossTypeTransition.PROCEDURAL_TO_SEMANTIC: f"Methodology abstracted from operational practice: {original_summary}",
            CrossTypeTransition.STATE_TO_ACTIVITY: f"Activity record corresponding to the state change: {original_summary}",
            CrossTypeTransition.ACTIVITY_TO_INTENT: f"New plan identified based on activity patterns: {original_summary}",
            CrossTypeTransition.SEMANTIC_TO_PROCEDURAL: f"Specific application method of conceptual knowledge: {original_summary}",
        }

        return conversion_templates.get(transition, f"Type Conversion: {original_summary}")

    def _adapt_keywords(self, keywords: List[str], transition: CrossTypeTransition) -> List[str]:
        """Adapt keywords"""
        adapted_keywords = keywords.copy()

        # Add specific keywords based on transition type
        additional_keywords = {
            CrossTypeTransition.INTENT_TO_ACTIVITY: ["complete", "execute"],
            CrossTypeTransition.ACTIVITY_TO_PROFILE: ["ability", "skill"],
            CrossTypeTransition.PROCEDURAL_TO_SEMANTIC: ["methodology", "principle"],
            CrossTypeTransition.STATE_TO_ACTIVITY: ["change", "update"],
            CrossTypeTransition.ACTIVITY_TO_INTENT: ["plan", "goal"],
            CrossTypeTransition.SEMANTIC_TO_PROCEDURAL: ["practice", "application"],
        }

        extra_keywords = additional_keywords.get(transition, [])
        for keyword in extra_keywords:
            if keyword not in adapted_keywords:
                adapted_keywords.append(keyword)

        return adapted_keywords[:10]  # Limit number of keywords

    def get_conversion_statistics(self) -> Dict:
        """Get conversion statistics"""
        return {
            "total_attempts": self.conversion_stats["attempts"],
            "total_successes": self.conversion_stats["successes"],
            "total_failures": self.conversion_stats["failures"],
            "success_rate": (
                self.conversion_stats["successes"] / max(1, self.conversion_stats["attempts"])
            )
            * 100,
            "conversions_by_type": self.conversion_stats["by_type"],
            "config": {
                "enable_cross_type_conversion": self.enable_cross_type_conversion,
                "confidence_threshold": self.conversion_confidence_threshold,
                "max_conversions_per_session": self.max_conversions_per_session,
            },
        }

    def suggest_related_contexts(
        self, context: ProcessedContext, all_contexts: List[ProcessedContext]
    ) -> List[Tuple[ProcessedContext, str, float]]:
        """Suggest related cross-type contexts"""
        suggestions = []

        context_type = context.extracted_data.context_type
        context_entities = set(context.extracted_data.entities)
        context_keywords = set(context.extracted_data.keywords)

        for other_context in all_contexts:
            if (
                other_context.id == context.id
                or other_context.extracted_data.context_type == context_type
            ):
                continue

            # Calculate relationship strength
            other_entities = set(other_context.extracted_data.entities)
            other_keywords = set(other_context.extracted_data.keywords)

            entity_overlap = (
                len(context_entities.intersection(other_entities))
                / len(context_entities.union(other_entities))
                if context_entities or other_entities
                else 0
            )
            keyword_overlap = (
                len(context_keywords.intersection(other_keywords))
                / len(context_keywords.union(other_keywords))
                if context_keywords or other_keywords
                else 0
            )

            relation_strength = (entity_overlap * 0.6) + (keyword_overlap * 0.4)

            if relation_strength > 0.3:  # Association threshold
                relation_type = self._determine_relation_type(
                    context_type, other_context.extracted_data.context_type
                )
                suggestions.append((other_context, relation_type, relation_strength))

        # Sort by relationship strength
        suggestions.sort(key=lambda x: x[2], reverse=True)

        return suggestions[:5]  # Return top 5 suggestions

    def _determine_relation_type(self, type1: ContextType, type2: ContextType) -> str:
        """Determine relationship type"""
        relations = {
            (
                ContextType.INTENT_CONTEXT,
                ContextType.ACTIVITY_CONTEXT,
            ): "Plan-Execution Relationship",
            (
                ContextType.ACTIVITY_CONTEXT,
                ContextType.ENTITY_CONTEXT,
            ): "Capability-Embodiment Relationship",
            (
                ContextType.PROCEDURAL_CONTEXT,
                ContextType.SEMANTIC_CONTEXT,
            ): "Method-Theory Relationship",
            (ContextType.STATE_CONTEXT, ContextType.ACTIVITY_CONTEXT): "State-Change Relationship",
        }

        # Bidirectional lookup
        relation = relations.get((type1, type2)) or relations.get((type2, type1))
        return relation or "Semantic-Association Relationship"
