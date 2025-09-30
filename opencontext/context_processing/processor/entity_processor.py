#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Entity processing module
"""
import asyncio
from copy import deepcopy
from typing import Dict, List
from opencontext.utils.logging_utils import get_logger
import datetime
from opencontext.tools.profile_tools.profile_entity_tool import ProfileEntityTool
from opencontext.models.context import *

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


def refresh_entities(
    entities_info: Dict[str, ProfileContextMetadata],
    context_text: str
) -> List[str]:
    """
    Entity processing main workflow - Three-step strategy
    1. Exact match -> Find then asynchronously update information
    2. Similar match -> LLM judgment -> If yes, update aliases and information
    3. No match -> Extract information -> Create new entity
    """
    
    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    entity_tool = ProfileEntityTool()
    processed_entities = {}
    
    for entity_name, entity_info in entities_info.items():
        entity_name = str(entity_name).strip()
        if not entity_name:
            continue
            
        entity_type = entity_info.entity_type
        matched_name, matched_context = entity_tool.match_entity(entity_name, entity_type)
        
        if matched_context:
            entity_data = matched_context.metadata
            entity_canonical_name = entity_data.get("entity_canonical_name", matched_name or entity_name)
            entity_aliases = entity_data.get('entity_aliases', [])
            if entity_name not in entity_aliases:
                entity_aliases.append(entity_name)
            matched_context.metadata['entity_aliases'] = entity_aliases
            update_info = entity_tool.update_entity_meta(entity_canonical_name, context_text, 
                            ProfileContextMetadata.from_dict(entity_data), entity_info)
            matched_context.metadata = update_info.to_dict()
            processed_entities[entity_canonical_name] = {"entity_name": entity_canonical_name, "entity_type": entity_type, "context": matched_context, "entity_info": update_info}
            continue
        
        processed_entities[entity_name] = {"entity_name": entity_name, "entity_type": entity_type, "context": None, "entity_info": entity_info}
    
    now = datetime.datetime.now().astimezone()
    all_entities = list(processed_entities.keys())
    entities_link = {}
    for entity_name, value in processed_entities.items():
        entity_info = value['entity_info']
        entity_type = entity_info.entity_type
        if not entities_link.get(entity_type):
            entities_link[entity_type] = dict()
        if value["context"]:
            entities_link[entity_type][value["context"].id] = entity_info.entity_canonical_name
            continue
        entity_info.entity_aliases.append(entity_name)
        entity_context = ProcessedContext(
            properties = ContextProperties(
                create_time=now,
                event_time=now,
                update_time=now,
                # enable_merge=True,
            ),
            extracted_data = ExtractedData(
                title=entity_name,
                summary=entity_info.entity_description,
                entities=all_entities,
                context_type=ContextType.ENTITY_CONTEXT,
            ),
            metadata = entity_info.to_dict(),
            vectorize=Vectorize(
                text=entity_name,
            )
        )
        value["context"] = entity_context
        entities_link[entity_type][entity_context.id] = entity_name
    from opencontext.storage.global_storage import get_global_storage
    for entity_name, value in processed_entities.items():
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
        get_global_storage().upsert_processed_context(context)
    return list(processed_entities.keys())
        