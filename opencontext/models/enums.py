#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0


"""
Context type and constant enumeration definitions
"""

from enum import Enum


class ContextSource(str, Enum):
    """Context source enumeration"""
    SCREENSHOT = "screenshot"
    VAULT = "vault"
    FILE = "file"
    FOLDER = "folder"
    DATA_STREAM = "data_stream"
    CHAT = "chat"
    AI_CONVERSATION = "ai_conversation"
    TEXT = "text"
    OTHER = "other"

class FileType(str, Enum):
    """File type enumeration"""
    PDF = "pdf"
    FAQ_XLSX = "faq.xlsx"
    XLSX = "xlsx"
    CSV = "csv"
    JSONL = "jsonl"
    PARQUET = "parquet"


# Structured document type constants - these document types should be processed by specialized structured chunkers
STRUCTURED_FILE_TYPES = {
    FileType.XLSX, FileType.CSV, FileType.JSONL, FileType.PARQUET, FileType.FAQ_XLSX,
}
    

class ContentFormat(str, Enum):
    """Content format enumeration"""
    
    UNSTRUCTURED = "unstructured"
        
    # Text format
    TEXT = "text"
    
    # Image format
    IMAGE = "image"
    
    # Structured data (JSON, XML, etc.)
    STRUCTURED = "structured"
    
    # FAQ format
    FAQ = "faq"

    # PDF format
    PDF = "pdf"

    # Binary data
    BINARY = "binary"
    
    # Audio format
    AUDIO = "audio"
    
    # Video format
    VIDEO = "video"
    
    IMAGE_TEXT = "image_text"
    
    VECTOR = "vector"


class MergeType(str, Enum):
    """Merge type enumeration"""
    ASSOCIATIVE = "associative"
    SIMILARITY = "similarity"


class ContextType(str, Enum):
    """Context type enumeration - for classifying different types of knowledge and information"""
    
    # Entity feature information
    ENTITY_CONTEXT = "entity_context"
    # Behavioral activities and historical records
    ACTIVITY_CONTEXT = "activity_context" 
    # Intent planning and goal information
    INTENT_CONTEXT = "intent_context"
    # Semantic knowledge and conceptual information
    SEMANTIC_CONTEXT = "semantic_context"
    # Procedural methods and operational guides
    PROCEDURAL_CONTEXT = "procedural_context"
    # Status monitoring and progress information
    STATE_CONTEXT = "state_context"

class VaultType(str, Enum):
    """Document type enumeration"""
    DAILY_REPORT = "DailyReport"
    WEEKLY_REPORT = "WeeklyReport"
    NOTE = "Note"
    

ContextSimpleDescriptions = {
    ContextType.ENTITY_CONTEXT.value: {
        "name": ContextType.ENTITY_CONTEXT.value,
        "description": "Entity profile information management",
        "purpose": "Record and manage profile information of various entities (people, projects, teams, organizations), support entity autonomous learning and knowledge accumulation"
    },
    ContextType.ACTIVITY_CONTEXT.value: {
        "name": ContextType.ACTIVITY_CONTEXT.value,
        "description": "Behavioral activity history records",
        "purpose": "Record specific behavioral trajectories, completed tasks, participated activities, etc."
    },
    ContextType.INTENT_CONTEXT.value: {
        "name": ContextType.INTENT_CONTEXT.value,
        "description": "Intent planning and goal records",
        "purpose": "Record forward-looking information such as future plans, goal setting, and action intentions"
    },
    ContextType.SEMANTIC_CONTEXT.value: {
        "name": ContextType.SEMANTIC_CONTEXT.value,
        "description": "Semantic knowledge and concept records",
        "purpose": "Record semantic information such as concept definitions, knowledge systems, and theoretical understanding"
    },
    ContextType.PROCEDURAL_CONTEXT.value: {
        "name": ContextType.PROCEDURAL_CONTEXT.value,
        "description": "Procedural method and operation records",
        "purpose": "Record procedural knowledge such as operation steps, workflows, and method skills"
    },
    ContextType.STATE_CONTEXT.value: {
        "name": ContextType.STATE_CONTEXT.value,
        "description": "Status and progress monitoring records",
        "purpose": "Record status information such as current status, progress tracking, and performance indicators"
    },
}

ContextDescriptions = {
    ContextType.ENTITY_CONTEXT: {
        "name": ContextType.ENTITY_CONTEXT.value,
        "description": """Entity profile information management - Record and manage complete profile information of various entities (people, projects, teams, organizations, etc.). Support entity autonomous learning, alias management, relationship tracking, and information accumulation. This type of information answers the question of \"who/what is this entity\" and is used to build an entity knowledge graph.""",
        "key_indicators": [
            "Contains information about entities such as people, projects, teams, and organizations",
            "Describes the basic attributes, characteristics, and role positioning of entities", 
            "Records various names of entities such as aliases, abbreviations, and full names",
            "Involves relationship information such as relationships, affiliations, and collaborations between entities",
            "Contains dynamic information such as the historical evolution and status changes of entities"
        ],
        "examples": [
            "Zhang San is a senior development engineer in our project team, specializing in Python and machine learning",
            "OpenContext project is ByteDance's intelligent context management system, abbreviated as CL", 
            "The technical department has three teams: front-end group, back-end group, and algorithm group"
        ],
        "classification_priority": 9
    },
    ContextType.ACTIVITY_CONTEXT: {
        "name": ContextType.ACTIVITY_CONTEXT.value,
        "description": """Behavioral activity history records - Record the historical trajectory of specific behaviors completed by individuals, activities participated in, and operations performed. This type of information answers the question of \"what have I done\" and is used to build behavioral patterns and accumulate experience.""",
        "key_indicators": [
            "Describes specific behaviors and operations that have been completed",
            "Records participation in meetings, training, and learning activities", 
            "Contains records of communication and interaction with others",
            "Involves the process and results of task execution",
            "Has clear time nodes and behavioral sequences"
        ],
        "examples": [
            "I attended yesterday's product planning meeting and discussed the functional priorities for Q4",
            "I have completed the study and exercises of Chapter 3 of the Python data analysis course", 
            "I discussed the specific plan for standardizing project documents with Zhang San"
        ],
        "classification_priority": 8
    },
    ContextType.INTENT_CONTEXT: {
        "name": ContextType.INTENT_CONTEXT.value,
        "description": """Intent planning and goal records - Record an individual's future plans, goal settings, action intentions, and other forward-looking information. This type of information answers the question of \"what am I going to do\" and is used for action planning and goal management.""",
        "key_indicators": [
            "Contains future plans and goal settings",
            "Describes the expected results and effects",
            "Involves action intentions and execution strategies",
            "Contains priority sorting and time planning",
            "Has forward-looking and guiding characteristics"
        ],
        "examples": [
            "I plan to complete the Python data analysis course next month",
            "My goal is to improve team collaboration efficiency by 20% in Q4",
            "I plan to reorganize the classification system of my personal knowledge management system"
        ],
        "classification_priority": 7
    },
    ContextType.SEMANTIC_CONTEXT: {
        "name": ContextType.SEMANTIC_CONTEXT.value,
        "description": """Semantic knowledge and concept records - Record semantic information such as concept definitions, knowledge systems, and theoretical understanding. This type of information answers the question of \"what is this concept\" and is used to build knowledge graphs and conceptual understanding.""",
        "key_indicators": [
            "Contains definitions and explanations of professional terms and concepts",
            "Describes knowledge systems and classification structures",
            "Involves theoretical principles and academic concepts",
            "Contains association relationships and hierarchical structures between concepts",
            "Has educational and knowledge inheritance value"
        ],
        "examples": [
            "Supervised learning in machine learning refers to training models using labeled data",
            "Agile development methodology includes specific frameworks such as Scrum and Kanban",
            "The Eisenhower matrix for time management divides tasks into four quadrants"
        ],
        "classification_priority": 6
    },
    ContextType.PROCEDURAL_CONTEXT: {
        "name": ContextType.PROCEDURAL_CONTEXT.value,
        "description": """Procedural method and operation records - Record procedural knowledge such as operation steps, workflows, and method skills. This type of information answers the question of \"how to do it\" and is used to guide specific operations and process execution.""",
        "key_indicators": [
            "Contains specific operation steps and execution sequences",
            "Describes workflows and standardized procedures",
            "Involves method skills and best practices",
            "Contains tool usage instructions and configuration methods",
            "Has repeatability and guiding characteristics"
        ],
        "examples": [
            "My code review process: check function -> verify test -> confirm documentation -> submit feedback",
            "Standard operating procedures for version control using Git",
            "Standard agenda for team meetings: opening -> topic discussion -> decision recording -> action allocation"
        ],
        "classification_priority": 5
    },
    ContextType.STATE_CONTEXT: {
        "name": ContextType.STATE_CONTEXT.value,
        "description": """Status and progress monitoring records - Record status information such as current status, progress tracking, and performance indicators. This type of information answers the question of \"how is the progress\" and is used to monitor execution and evaluate effectiveness.""",
        "key_indicators": [
            "Contains current execution status and completion status",
            "Describes project progress and time nodes",
            "Involves performance indicators and quantitative data",
            "Contains abnormal conditions and risk warnings",
            "Has real-time and dynamic change characteristics"
        ],
        "examples": [
            "The project development progress has been completed by 65% and is expected to be delivered on time",
            "The number of code submissions this week is 20, and the bug fix rate is 95%",
            "The system CPU usage is 85%, the memory usage is 2.3GB, and it is running normally"
        ],
        "classification_priority": 4
    }
}

def get_context_type_options():
    """Get all available context type options"""
    return [ct.value for ct in ContextType]

def get_context_descriptions():
    """Get formatted context type descriptions"""
    descriptions = []
    for context_type in ContextType:
        desc = ContextDescriptions[context_type]
        descriptions.append(f"- {context_type.value}: {desc['description']}")
    return "\n".join(descriptions)

def validate_context_type(context_type: str) -> bool:
    """Validate if the context type is valid"""
    return context_type in get_context_type_options()

def get_context_type_for_analysis(context_type_str: str) -> 'ContextType':
    """
    Get the context type for analysis, with fault tolerance
    """
    if not context_type_str:
        return ContextType.SEMANTIC_CONTEXT
    
    # Normalize input
    context_type_str = context_type_str.lower().strip()
    
    # Direct match
    if validate_context_type(context_type_str):
        return ContextType(context_type_str)
    
    # Default to semantic context
    return ContextType.SEMANTIC_CONTEXT
    
def get_context_type_choices_for_tools():
    """
    Get a dynamic list of context type choices for tool parameters
    Used for enum values in API parameter definitions
    """
    return get_context_type_options()

def get_context_type_descriptions_for_prompts():
    """
    Get formatted context type descriptions for prompts
    """
    descriptions = []
    for context_type in ContextType:
        desc = ContextDescriptions[context_type]
        descriptions.append(f"*   `{context_type.value}`: {desc['description']}")
    return "\n            ".join(descriptions)

def get_context_type_descriptions_for_extraction():
    """
    Get context type descriptions for content extraction scenarios
    Mainly used for screenshot and vision processors
    """
    descriptions = []
    for context_type in ContextType:
        desc = ContextDescriptions[context_type]
        # Provide more detailed guidance for extraction scenarios, including identification indicators and examples
        key_indicators = desc.get('key_indicators', [])
        examples = desc.get('examples', [])
        
        description_parts = [f"`{context_type.value}`: {desc['description']}"]
        
        if key_indicators:
            indicators_str = ", ".join(key_indicators)  # Show all indicators
            description_parts.append(f"Identification indicators: {indicators_str}")
        
        if examples:
            examples_str = "; ".join(examples)  # Show all examples
            description_parts.append(f"Examples: {examples_str}")
        
        descriptions.append(f"*   {' | '.join(description_parts)}")
    
    return "\n            ".join(descriptions)

def get_context_type_descriptions_for_retrieval():
    """
    Get context type descriptions for retrieval scenarios
    Mainly used for query processing and retrieval tools
    """
    descriptions = []
    for context_type in ContextType:
        desc = ContextDescriptions[context_type]
        # Provide more focused descriptions for retrieval scenarios, highlighting purpose and classification priority
        description_parts = [f"`{context_type.value}`: {desc['description']}"]
        
        # # Add classification priority information to help with importance judgment during retrieval
        # priority = desc.get('classification_priority', 5)
        # if priority >= 8:
        #     description_parts.append("High priority")
        # elif priority >= 6:
        #     description_parts.append("Medium priority")
        
        descriptions.append(f"*   {' | '.join(description_parts)}")
    
    return "\n            ".join(descriptions)
  
  
class CompletionType(Enum):
  """Completion type enumeration"""
  SEMANTIC_CONTINUATION = "semantic_continuation"  # Semantic continuation
  TEMPLATE_COMPLETION = "template_completion"      # Template completion
  REFERENCE_SUGGESTION = "reference_suggestion"   # Reference suggestion
  CONTEXT_AWARE = "context_aware"                  # Context-aware completion
