# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Define core data models used in OpenContext
"""
import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)

from opencontext.models.enums import ContentFormat, ContextSource, ContextType


class Chunk(BaseModel):
    """
    Represents a chunk split from a document or text
    """
    text: Optional[str] = None
    image: Optional[bytes] = None
    chunk_index: int = 0
    keywords: List[str] = Field(default_factory=list)  # keywords
    entities: List[str] = Field(default_factory=list)  # entities


class RawContextProperties(BaseModel):
    content_format: ContentFormat
    source: ContextSource
    create_time: datetime.datetime
    object_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_path: Optional[str] = None  # file path if ContentFormat is VIDEO or IMAGE; None if TEXT
    content_type: Optional[str] = None  # content type, e.g. "text", "image", "video"
    content_text: Optional[str] = None  # text content if ContentFormat is TEXT; None otherwise
    filter_path: Optional[str] = None  # filter path
    additional_info: Optional[Dict[str, Any]] = None  # additional information
    enable_merge: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawContextProperties":
        """Create model from dictionary"""
        return cls.model_validate(data)


class ExtractedData(BaseModel):
    """
    Represents information extracted from context data
    """

    title: Optional[str] = None
    summary: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)  # keywords
    entities: List[str] = Field(default_factory=list)  # entities
    context_type: ContextType  # context type
    confidence: int = 0  # confidence
    importance: int = 0  # importance

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedData":
        """Create model from dictionary"""
        return cls.model_validate(data)


class ContextProperties(BaseModel):
    """
    Represents context data attributes
    """

    raw_properties: list[RawContextProperties] = Field(
        default_factory=list
    )  # raw context properties
    create_time: datetime.datetime  # creation time
    event_time: datetime.datetime  # event occurrence time, can be future
    is_processed: bool = False  # whether processed
    has_compression: bool = False  # whether compressed
    update_time: datetime.datetime  # update time
    call_count: int = 0  # call count, updated during online service calls
    merge_count: int = 0  # merge count
    duration_count: int = 1  # context duration count
    enable_merge: bool = False
    is_happend: bool = False  # whether occurred
    last_call_time: Optional[datetime.datetime] = (
        None  # last call time, updated during online service calls
    )
    # position: Optional[Dict[str, Any]] = None # context position in original data

    # Document tracking fields
    file_path: Optional[str] = None  # file path (empty for documents)
    raw_type: Optional[str] = None  # raw type (e.g. 'vaults')
    raw_id: Optional[str] = None  # raw ID (ID in vaults table)


class Vectorize(BaseModel):
    """
    Vectorization configuration
    """

    content_format: ContentFormat = ContentFormat.TEXT
    image_path: Optional[str] = None
    text: Optional[str] = None
    vector: Optional[List[float]] = None
    # Future extension for multimodal embedding:
    # images: Optional[List[Any]] = None  # PIL Images or image data for multimodal models

    def get_vectorize_content(self) -> str:
        """Get vectorization content"""
        if self.content_format == ContentFormat.TEXT:
            return self.text
        elif self.content_format == ContentFormat.IMAGE:
            return self.image_path
        else:
            return ""


class ProcessedContext(BaseModel):
    """
    Represents processed context data
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    properties: ContextProperties
    extracted_data: ExtractedData
    vectorize: Vectorize
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )  # metadata for storing structured entity information

    def get_vectorize_content(self) -> str:
        """Get vectorization content"""
        if self.vectorize.content_format == ContentFormat.TEXT:
            return self.vectorize.text
        elif self.vectorize.content_format == ContentFormat.IMAGE:
            return self.vectorize.image_path
        else:
            return ""

    def get_llm_context_string(self) -> str:
        """Get context information string for LLM input"""
        parts = []
        ed = self.extracted_data
        parts.append(f"id: {self.id}")
        if ed.title:
            parts.append(f"title: {ed.title}")
        if ed.summary:
            parts.append(f"summary: {ed.summary}")
        if ed.keywords:
            parts.append(f"keywords: {', '.join(ed.keywords)}")
        if ed.entities:
            parts.append(f"entities: {', '.join(ed.entities)}")
        if ed.context_type:
            parts.append(f"context type: {ed.context_type.value}")
        if self.metadata:
            parts.append(f"metadata: {json.dumps(self.metadata, ensure_ascii=False)}")

        # Raw properties
        # raw_contexts_props = self.properties.raw_properties
        # for i, raw_prop in enumerate(raw_contexts_props):
        #     source = raw_prop.source.value if raw_prop.source else 'N/A'
        #     parts.append(f"raw context source {i+1}: {source}")
        create_time = self.properties.create_time
        parts.append(f"create time: {create_time.isoformat()}")
        event_time = self.properties.event_time
        parts.append(f"event time: {event_time.isoformat()}")
        duration_count = self.properties.duration_count
        parts.append(f"duration count: {duration_count}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump(exclude_none=True)

    def dump_json(self) -> str:
        """Convert model to JSON string"""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessedContext":
        """Create model from dictionary"""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "ProcessedContext":
        """Create model from JSON string"""
        return cls.model_validate_json(json_str)


class RawContextModel(BaseModel):
    """
    Raw context data model for API responses
    """

    object_id: str
    content_format: str
    source: str
    create_time: str
    content_path: Optional[str] = None
    content_text: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

    @classmethod
    def from_raw_context_properties(
        cls, rcp: "RawContextProperties", project_root: Path
    ) -> "RawContextModel":
        """Create API model from RawContextProperties object"""
        content_path = None
        if rcp.content_path:
            try:
                # Convert to relative path from project root
                relative_path = Path(rcp.content_path).relative_to(project_root)
                content_path = str(relative_path)
            except ValueError:
                # If path is not under project root, use absolute path
                content_path = rcp.content_path

        return cls(
            object_id=rcp.object_id,
            content_format=rcp.content_format.value,
            source=rcp.source.value,
            create_time=rcp.create_time.isoformat(),
            content_path=content_path,
            content_text=rcp.content_text,
            additional_info=rcp.additional_info,
        )


class ProcessedContextModel(BaseModel):
    """
    Processed context data model for API responses
    """

    id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    keywords: List[str] = []
    entities: List[str] = []
    context_type: str
    confidence: int
    importance: int
    is_processed: bool
    call_count: int
    merge_count: int  # merge count
    last_call_time: Optional[str] = None
    create_time: str
    update_time: str
    event_time: str
    embedding: Optional[List[float]] = None
    raw_contexts: List["RawContextModel"] = []
    duration_count: int  # context duration count
    is_happend: bool  # whether occurred
    metadata: Optional[Dict[str, Any]] = None  # metadata information

    @classmethod
    def from_processed_context(
        cls, pc: "ProcessedContext", project_root: Path
    ) -> "ProcessedContextModel":
        """Create API model from ProcessedContext object"""

        # Generate title
        title = pc.extracted_data.title

        # Create raw context model list
        raw_contexts = [
            RawContextModel.from_raw_context_properties(rcp, project_root)
            for rcp in pc.properties.raw_properties
        ]
        # logger.info(f"raw_contexts duration_count: {pc.properties.duration_count}")

        return cls(
            id=pc.id,
            title=title,
            summary=pc.extracted_data.summary,
            keywords=pc.extracted_data.keywords,
            entities=pc.extracted_data.entities,
            context_type=pc.extracted_data.context_type.value,
            confidence=pc.extracted_data.confidence,
            importance=pc.extracted_data.importance,
            is_processed=pc.properties.is_processed,
            call_count=pc.properties.call_count,
            merge_count=pc.properties.merge_count,  # set merge count
            duration_count=pc.properties.duration_count,  # set duration count
            last_call_time=(
                pc.properties.last_call_time.strftime("%Y-%m-%d %H:%M:%S")
                if pc.properties.last_call_time
                else None
            ),
            create_time=pc.properties.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            update_time=pc.properties.update_time.strftime("%Y-%m-%d %H:%M:%S"),
            event_time=pc.properties.event_time.strftime("%Y-%m-%d %H:%M:%S"),
            embedding=pc.vectorize.vector,
            raw_contexts=raw_contexts,
            is_happend=pc.properties.is_happend,
            metadata=pc.metadata,  # add metadata
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessedContextModel":
        """Create model from dictionary"""
        return cls.model_validate(data)


class ProfileContextMetadata(BaseModel):
    """Profile context additional information"""

    entity_type: str = ""
    entity_canonical_name: str = ""
    entity_aliases: List[str] = []
    entity_metadata: Dict[str, Any] = {}
    entity_relationships: Dict[str, List[Any]] = {}
    entity_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileContextMetadata":
        """Create model from dictionary"""
        return cls.model_validate(data)

class KnowledgeContextMetadata(BaseModel):
    """Knowledge context additional information"""
    knowledge_source: str = ""
    knowledge_file_path: str = ""
    knowledge_title: str = ""
    knowledge_raw_id: str = ""
