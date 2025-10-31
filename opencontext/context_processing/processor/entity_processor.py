#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Entity processing module
"""
import asyncio
import datetime
import json
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from opencontext.models.context import *
from opencontext.tools.profile_tools.profile_entity_tool import ProfileEntityTool
from opencontext.utils.logging_utils import get_logger
from opencontext.utils.json_parser import parse_json_from_response
from opencontext.llm.global_embedding_client import do_vectorize_async

logger = get_logger(__name__)


def validate_and_clean_entities(raw_entities) -> Dict[str, ProfileContextMetadata]:
    """Validate and clean entity list, ensure it contains name and type fields, and extract description and metadata"""
    if not isinstance(raw_entities, list):
        logger.warning(f"Entity is not a list type: {type(raw_entities)}, using empty list")
        return {}
    entities_info = {}
    for entity in raw_entities:
        if isinstance(entity, dict) and "name" in entity:
            name = str(entity["name"]).strip()
            entity_type = entity.get("type", "other")
            if name:
                entity_info = ProfileContextMetadata(
                    entity_canonical_name=name,
                    entity_type=entity_type,
                    entity_description=entity.get("description", ""),
                    entity_metadata=entity.get("metadata", {}),
                    entity_aliases=entity.get("aliases", []) + [name],
                )
                entities_info[name] = entity_info
            else:
                logger.warning(f"Skipping invalid entity type {type(entity)}: {entity}")
    return entities_info


async def _process_single_entity(entity_name: str, entity_info: ProfileContextMetadata, context_text: str, entity_tool: ProfileEntityTool, all_entities: List[str]) -> tuple:
    """Process a single entity (async wrapper for concurrent execution)"""
    entity_name = str(entity_name).strip()
    if not entity_name:
        return None, None

    entity_type = entity_info.entity_type
    matched_name, matched_context = entity_tool.match_entity(entity_name, entity_type, judge=False)

    if matched_context:
        # logger.info(f"Matched entity: {entity_name} -> {matched_name}")
        entity_data = matched_context.metadata
        entity_canonical_name = entity_data.get(
            "entity_canonical_name", matched_name or entity_name
        )
        entity_aliases = entity_data.get("entity_aliases", [])
        if entity_name not in entity_aliases:
            entity_aliases.append(entity_name)
        matched_context.metadata["entity_aliases"] = list(set(entity_aliases))
        # update_info = entity_tool.update_entity_meta(
        #     entity_canonical_name,
        #     context_text,
        #     ProfileContextMetadata.from_dict(entity_data),
        #     entity_info,
        # )
        # matched_context.metadata = update_info.to_dict()
        return entity_canonical_name, {
            "entity_name": entity_canonical_name,
            "entity_type": entity_type,
            "context": matched_context,
            # "entity_info": update_info,
            "entity_info": ProfileContextMetadata.from_dict(matched_context.metadata),
        }

    # Create new entity context
    now = datetime.datetime.now()
    entity_info.entity_aliases.append(entity_name)
    entity_context = ProcessedContext(
        properties=ContextProperties(
            create_time=now,
            event_time=now,
            update_time=now,
            # enable_merge=True,
        ),
        extracted_data=ExtractedData(
            title=entity_name,
            summary=entity_info.entity_description,
            entities=all_entities,
            context_type=ContextType.ENTITY_CONTEXT,
        ),
        metadata=entity_info.to_dict(),
        vectorize=Vectorize(
            text=entity_name+" "+entity_info.entity_description,
        ),
    )

    await do_vectorize_async(entity_context.vectorize)

    return entity_name, {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "context": entity_context,
        "entity_info": entity_info,
    }


async def refresh_entities(entities_info: Dict[str, ProfileContextMetadata], context_text: str) -> List[str]:
    """
    Entity processing main workflow - Three-step strategy (optimized with concurrent processing)
    """
    entity_tool = ProfileEntityTool()
    all_entities = list(entities_info.keys())

    # Process all entities concurrently (including match, update, create context, and vectorize)
    tasks = [
        _process_single_entity(entity_name, entity_info, context_text, entity_tool, all_entities)
        for entity_name, entity_info in entities_info.items()
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results
    processed_entities = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Entity processing failed: {result}")
            continue
        if result and result[0]:
            key, value = result
            processed_entities[key] = value

    # Build entities_link for relationship tracking
    entities_link = {}
    for entity_name, value in processed_entities.items():
        entity_info = value["entity_info"]
        entity_type = entity_info.entity_type
        if not entities_link.get(entity_type):
            entities_link[entity_type] = dict()
        if value["context"]:
            entities_link[entity_type][value["context"].id] = entity_info.entity_canonical_name
    
    # Build relationships and prepare contexts for batch upsert
    from opencontext.storage.global_storage import get_global_storage
    contexts_to_upsert = []

    for value in processed_entities.values():
        context = value["context"]
        entity_info = value["entity_info"]
        entity_type = entity_info.entity_type
        link = deepcopy(entities_link)
        link[entity_type].pop(context.id)
        entity_relationships = entity_info.entity_relationships
        for link_type, link_ids in link.items():
            final_type_link = []
            for item in entity_relationships.get(link_type, []):
                if item["entity_id"] not in link_ids:
                    link_ids[item["entity_id"]] = item["entity_name"]
            for id, name in link_ids.items():
                final_type_link.append({"entity_id": id, "entity_name": name})
            entity_info.entity_relationships[link_type] = final_type_link
        entity_info.entity_relationships = entity_relationships
        entity_info.entity_aliases = list(set(entity_info.entity_aliases))
        context.metadata = entity_info.to_dict()
        contexts_to_upsert.append(context)

    # Batch upsert all contexts at once
    if contexts_to_upsert:
        get_global_storage().batch_upsert_processed_context(contexts_to_upsert)

    return list(processed_entities.keys())
