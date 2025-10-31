#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Profile Entity Tool
Unified entity management tool, integrating storage, search, matching and LLM interaction functions
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from opencontext.models.context import ProcessedContext, ProfileContextMetadata, Vectorize
from opencontext.models.enums import ContextType
from opencontext.storage.global_storage import get_storage
from opencontext.tools.base import BaseTool
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProfileEntityTool(BaseTool):
    """Unified entity management tool"""

    def __init__(self):
        super().__init__()
        self.storage = get_storage()
        self.similarity_threshold = 0.8

        # Current user entity
        self.current_user_entity = {
            "entity_canonical_name": "current_user",
            "entity_aliases": ["me", "user", "self", "myself"],
            "entity_type": "person",
            "description": "Current system user",
            "metadata": {},
            "relationships": {},
        }

    @classmethod
    def get_name(cls) -> str:
        return "profile_entity_tool"

    @classmethod
    def get_description(cls) -> str:
        return """Entity profile management tool for finding, matching, and exploring entities (people, projects, organizations, etc.) and their relationships. Provides intelligent entity resolution and relationship network analysis.

**When to use this tool:**
- When you need detailed information about a specific entity (person, project, team, organization)
- When resolving entity names to their canonical forms (e.g., "John" → "John Smith")
- When checking relationships between two entities (e.g., "Is Alice related to Project X?")
- When exploring an entity's relationship network (friends, collaborators, team members)
- When finding similar entities based on names or descriptions

**When NOT to use this tool:**
- For general content searches → use text_search instead
- For time-based filtering → use filter_context instead
- When searching for contexts mentioning entities → use text_search or filter_context with entity filter

**Supported operations:**
- **find_exact_entity**: Lookup entity by exact canonical name or alias
- **find_similar_entity**: Find entities with similar names or descriptions (fuzzy matching)
- **match_entity**: Intelligent entity resolution (exact match → semantic search → LLM-based judgment)
- **check_entity_relationships**: Check if two entities are related and how
- **get_entity_relationship_network**: Explore entity's relationship graph with configurable depth (1-5 hops)

**Key features:**
- Canonical name resolution with alias support
- Intelligent fuzzy matching and entity disambiguation
- Relationship type identification (colleague, team_member, supervisor, etc.)
- Multi-hop relationship network traversal
- Entity metadata enrichment (description, properties, relationships)
- LLM-powered entity matching for ambiguous cases

**Entity types supported:**
- person (people, individuals, users)
- project (projects, initiatives, products)
- team (teams, groups, departments)
- organization (companies, institutions, external entities)
- other (generic named entities)

**Use cases:**
- "Who is Alice?" → find_exact_entity
- "Find people similar to 'John'" → find_similar_entity
- "Match 'XYZ Corp' to known organization" → match_entity
- "Are Alice and Bob related?" → check_entity_relationships
- "Show me Bob's network of collaborators" → get_entity_relationship_network
"""

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get tool parameter definitions"""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "find_exact_entity",
                        "find_similar_entity",
                        "match_entity",
                        "check_entity_relationships",
                        "get_entity_relationship_network",
                    ],
                    "description": "Operation type: exact entity search, similar entity search, intelligent entity matching, entity relationship checking, get entity relationship network",
                },
                "entity_name": {
                    "type": "string",
                    "description": "Entity name to search. For queries related to the current user, always use 'current_user' as the entity name (aliases: 'me', 'user', 'myself')",
                },
                "entity_data": {
                    "type": "object",
                    "description": "Additional data information for entity",
                    "properties": {},
                },
                "entity1": {"type": "string", "description": "First entity in relationship check"},
                "entity2": {"type": "string", "description": "Second entity in relationship check"},
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of similar entities to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
                "context_text": {"type": "string", "description": "Context text to enhance search"},
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum hops for relationship network (1-5)",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute entity operation

        Returns:
            Dict containing operation results with success status
        """
        operation = kwargs.get("operation")

        operation_handlers = {
            "find_exact_entity": self._handle_find_exact,
            "find_similar_entity": self._handle_find_similar,
            "match_entity": self._handle_match,
            "check_entity_relationships": self._handle_check_relationships,
            "get_entity_relationship_network": self._handle_get_relationship_network,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}",
                "supported_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(kwargs)
        except Exception as e:
            logger.error(f"Failed to execute entity operation - {operation}: {e}", exc_info=True)
            return {"success": False, "error": str(e), "operation": operation}

    def _handle_find_exact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle exact search operation"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for find_exact_entity operation",
            }

        result = self.find_exact_entity(entity_name)
        if not result:
            return {
                "success": False,
                "error": f"Entity {entity_name} not found",
            }
        return {"success": True, "entity_info": result.metadata, "entity_name": entity_name}

    def _handle_find_similar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle similar search operation"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for find_similar_entity operation",
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
        """Handle intelligent matching operation - exact match first, then similar search + LLM judgment if not found"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {"success": False, "error": "entity_name is required for match_entity operation"}

        # Call match_entity method directly
        top_k = min(max(params.get("top_k", 5), 1), 10)
        entity_type = params.get("entity_type", None)
        matched_name, matched_context = self.match_entity(
            entity_name=entity_name, entity_type=entity_type, top_k=top_k
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
        """Handle relationship checking operation"""
        entity1 = params.get("entity1", "")
        entity2 = params.get("entity2", "")

        if not entity1 or not entity2:
            missing = []
            if not entity1:
                missing.append("entity1")
            if not entity2:
                missing.append("entity2")
            return {"success": False, "error": f"Missing required parameters: {', '.join(missing)}"}

        result = self.check_entity_relationships(entity1, entity2)
        return {"success": True, "entity1": entity1, "entity2": entity2, **result}

    def _handle_get_relationship_network(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get relationship network operation"""
        entity_name = params.get("entity_name", "")
        if not entity_name:
            return {
                "success": False,
                "error": "entity_name is required for get_entity_relationship_network operation",
            }

        max_hops = min(max(params.get("max_hops", 2), 1), 5)

        try:
            network = self.get_entity_relationship_network(entity_name, max_hops)
            return {
                "success": True,
                "entity_name": entity_name,
                "max_hops": max_hops,
                "network": network,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "entity_name": entity_name}

    def match_entity(
        self, entity_name: str, entity_type: str = None, top_k: int = 3, judge: bool = True
    ) -> Tuple[Optional[str], Optional[ProcessedContext]]:
        """Intelligent entity matching - exact match first, then similar search + LLM judgment if not found

        Args:
            entity_name: Entity name to match
            entity_type: Entity type (optional)
            top_k: Maximum number of similar search results

        Returns:
            Tuple[Optional[str], Optional[ProcessedContext]]: (Matched entity name, matched context)
        """
        # 1. Try exact match first
        exact_result = self.find_exact_entity([entity_name], entity_type)
        if exact_result:
            metadata = exact_result.metadata
            matched_name = metadata.get("entity_canonical_name", entity_name)
            return matched_name, exact_result

        # 2. Similar search
        top_k = min(max(top_k, 1), 10)
        similar_contexts = self.find_similar_entities([entity_name], entity_type, top_k=top_k)
        if not similar_contexts:
            # No similar entities found
            return None, None

        # 3. Use LLM to judge if similar entities really match
        if judge:
            matched_name, matched_context = self.judge_entity_match([entity_name], similar_contexts)
            return matched_name, matched_context
        else:
            return similar_contexts[0].metadata.get("entity_canonical_name", entity_name), similar_contexts[0]

    def find_exact_entity(
        self, entity_names: List[str], entity_type: str = None
    ) -> Optional[ProcessedContext]:
        """Exact entity search"""
        filter = {"entity_canonical_name": entity_names}
        if entity_type:
            filter["entity_type"] = entity_type
        contexts = self.storage.get_all_processed_contexts(
            context_types=[ContextType.ENTITY_CONTEXT], limit=1, filter=filter
        )
        if not contexts:
            return None

        entity_contexts = contexts.get(ContextType.ENTITY_CONTEXT.value, [])
        if entity_contexts:
            return entity_contexts[0]
        return None

    def find_similar_entities(
        self, entity_names: List[str], entity_type: str = None, top_k: int = 3
    ) -> List[ProcessedContext]:
        """Similar entity search - using vector search"""
        if not entity_names:
            return []
        filter = {}
        if entity_type:
            filter["entity_type"] = entity_type
        results = self.storage.search(
            query=Vectorize(text=" ".join(entity_names)),
            top_k=top_k,
            context_types=[ContextType.ENTITY_CONTEXT.value],
            filters=filter,
        )
        if not results:
            return []
        contexts = []
        for context, score in results:
            if score >= 0.90:
                contexts.append(context)
        return contexts

    def check_entity_relationships(self, entity1: str, entity2: str) -> Dict[str, Any]:
        """Check if two entities are related"""
        try:
            context1 = self.find_exact_entity([entity1])
            context2 = self.find_exact_entity([entity2])

            if not context1 or not context2:
                return {"related": False, "error": "One or both entities not found"}

            # Get entity data - metadata is in dictionary form of ProfileContextMetadata
            metadata1 = context1.metadata
            metadata2 = context2.metadata

            entity1_name = metadata1.get("entity_canonical_name", entity1)
            entity2_name = metadata2.get("entity_canonical_name", entity2)

            # Check entity_relationships field
            relationships1 = metadata1.get("entity_relationships", {})
            relationships2 = metadata2.get("entity_relationships", {})

            # Check if entity2 is in entity1's relationships
            for rel_type, rel_list in relationships1.items():
                if isinstance(rel_list, list) and entity2_name in rel_list:
                    return {
                        "related": True,
                        "relationship_type": rel_type,
                        "direction": f"{entity1_name} -> {entity2_name}",
                    }

            # Check if entity1 is in entity2's relationships
            for rel_type, rel_list in relationships2.items():
                if isinstance(rel_list, list) and entity1_name in rel_list:
                    return {
                        "related": True,
                        "relationship_type": rel_type,
                        "direction": f"{entity2_name} -> {entity1_name}",
                    }

            return {"related": False}

        except Exception as e:
            logger.error(f"Failed to check entity relationships: {e}")
            return {"related": False, "error": str(e)}

    def get_entity_relationship_network(
        self, entity_name: str, max_hops: int = 2
    ) -> Dict[str, Any]:
        """Get entity relationship network

        Args:
            entity_name: Starting entity name
            max_hops: Maximum hops (1-5)

        Returns:
            Dict containing the relationship network with nodes and edges
        """
        max_hops = min(max(max_hops, 1), 5)

        visited_ids = set()  # Use entity_id as visit record
        network = {
            "nodes": [],
            "edges": [],
            "statistics": {"total_nodes": 0, "total_edges": 0, "max_depth_reached": 0},
        }

        node_map = {}
        edge_set = set()

        def add_node(context: ProcessedContext, depth: int) -> str:
            """Add node to network, returns entity_id"""
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
                    "metadata": metadata.get("entity_metadata", {}),
                }
                network["nodes"].append(node_info)
                node_map[entity_id] = node_info
                network["statistics"]["total_nodes"] += 1
                network["statistics"]["max_depth_reached"] = max(
                    network["statistics"]["max_depth_reached"], depth
                )

            return entity_id

        def explore_entity_by_id(entity_id: str, current_depth: int):
            """Recursively explore entity relationships by entity_id"""
            if current_depth > max_hops:
                return

            if entity_id in visited_ids:
                return

            visited_ids.add(entity_id)

            # Find entity by entity_id
            context = self.storage.get_processed_context(
                entity_id, context_type=ContextType.ENTITY_CONTEXT.value
            )
            if not context:
                return

            current_node_id = add_node(context, current_depth)
            if not current_node_id:
                return

            # Process entity_relationships field
            metadata = context.metadata
            entity_relationships = metadata.get("entity_relationships", {})

            # entity_relationships structure is Dict[str, List[Dict]]
            # Example: {"friend": [{"entity_id": "123", "entity_name": "Alice"}]}
            for relationship_type, related_entities in entity_relationships.items():
                for related_entity_info in related_entities:
                    related_entity_id = related_entity_info.get("entity_id")
                    edge_key = (current_node_id, related_entity_id)
                    reverse_edge_key = (related_entity_id, current_node_id)

                    if edge_key not in edge_set and reverse_edge_key not in edge_set:
                        related_context = self.storage.get_processed_context(
                            related_entity_id, context_type=ContextType.ENTITY_CONTEXT.value
                        )
                        if not related_context:
                            continue
                        related_node_id = add_node(related_context, current_depth + 1)
                        if related_node_id:
                            edge_info = {
                                "source": current_node_id,
                                "target": related_node_id,
                                "relationship": relationship_type,
                                "depth": current_depth,
                            }
                            network["edges"].append(edge_info)
                            edge_set.add(edge_key)
                            network["statistics"]["total_edges"] += 1
                            if current_depth < max_hops:
                                explore_entity_by_id(related_entity_id, current_depth + 1)

        def explore_entity(entity_name: str, current_depth: int):
            """Start exploring from entity name"""
            context = self.find_exact_entity([entity_name])
            if not context:
                return

            entity_id = context.id
            if entity_id:
                explore_entity_by_id(entity_id, current_depth)
            explore_entity(entity_name, 0)

        return network

    def update_entity_meta(
        self,
        entity_name: str,
        context_text: str,
        old_entity_data: ProfileContextMetadata,
        new_entity_data: ProfileContextMetadata,
    ) -> ProfileContextMetadata:
        """Use LLM to intelligently merge entity metadata

        Args:
            entity_name: Entity name
            context_text: Context text
            old_entity_data: Currently stored entity data
            new_entity_data: Newly extracted entity data

        Returns:
            Dict: Update result
        """
        try:
            from opencontext.config.global_config import get_prompt_group

            prompt_template = get_prompt_group("entity_processing.entity_meta_merging")
            old_data = {
                "entity_canonical_name": old_entity_data.entity_canonical_name or entity_name,
                "entity_metadata": old_entity_data.entity_metadata or {},
                "entity_aliases": old_entity_data.entity_aliases or [],
                "entity_description": old_entity_data.entity_description or "",
            }
            new_data = {
                "entity_canonical_name": new_entity_data.entity_canonical_name or entity_name,
                "entity_metadata": new_entity_data.entity_metadata or {},
                "entity_aliases": new_entity_data.entity_aliases or [],
                "entity_description": new_entity_data.entity_description or "",
            }
            user_prompt = prompt_template["user"].format(
                old_entity_data=json.dumps(old_data, ensure_ascii=False, indent=2),
                new_entity_data=json.dumps(new_data, ensure_ascii=False, indent=2),
                context_text=context_text,
            )
            messages = [
                {"role": "system", "content": prompt_template["system"]},
                {"role": "user", "content": user_prompt},
            ]
            from opencontext.llm.global_vlm_client import generate_with_messages

            response = generate_with_messages(messages, thinking="disabled")
            result = parse_json_from_response(response)
            if "entity_canonical_name" in result and result["entity_canonical_name"]:
                old_entity_data.entity_canonical_name = result["entity_canonical_name"]
            if "entity_metadata" in result and isinstance(result["entity_metadata"], dict):
                old_entity_data.entity_metadata = result["entity_metadata"]
            if "entity_description" in result and result["entity_description"]:
                old_entity_data.entity_description = result["entity_description"]
            old_entity_data.entity_aliases = list(
                set(old_entity_data.entity_aliases or [])
                | set(new_entity_data.entity_aliases or [])
            )
            return old_entity_data
        except Exception as e:
            logger.exception(
                f"LLM failed to merge entity metadata {entity_name}: {e}", exc_info=True
            )
            return old_entity_data

    def judge_entity_match(
        self, extracted_names: List[str], candidates: List[ProcessedContext]
    ) -> Optional[Tuple[str, ProcessedContext]]:
        """Use LLM to judge if extracted entity matches one of the candidate entities"""
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
                    "description": entity_data.get("description", ""),
                }
                candidate_info.append(info)

            # Build prompt
            from opencontext.config.global_config import get_prompt_group

            prompt_template = get_prompt_group("entity_processing.entity_matching")

            user_prompt = prompt_template["user"].format(
                extracted_names=extracted_names,
                candidates=json.dumps(candidate_info, ensure_ascii=False, indent=2),
            )

            messages = [
                {"role": "system", "content": prompt_template["system"]},
                {"role": "user", "content": user_prompt},
            ]
            from opencontext.llm.global_vlm_client import generate_with_messages

            response = generate_with_messages(
                messages,
                thinking="disabled",
            )
            result = parse_json_from_response(response)
            if result.get("is_match") and result.get("matched_entity"):
                for candidate in candidates:
                    if result.get("matched_entity") in candidate.metadata.get("entity_aliases", []):
                        return candidate.metadata.get("entity_canonical_name"), candidate
            return None, None

        except Exception as e:
            logger.error(f"LLM failed to judge entity match: {e}")
            return None, None
