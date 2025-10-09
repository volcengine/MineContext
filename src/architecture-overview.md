# MineContext Architecture Overview

## System Architecture

MineContext is designed as a modular, event-driven system with clear separation of concerns. The architecture follows a layered approach with well-defined interfaces between components.

## System Components

### Core Architecture Layers

```
┌──────────────────────────────────────────────────────────┐
│                    Business Logic Layer                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Capture    │  │  Processor   │  │  Consumption │  │
│  │   Manager    │  │   Manager    │  │    Manager   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                    Processing Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Chunker   │  │   Processor  │  │    Merger    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Entity Analyzer│ │  Vectorizer  │  │  Knowledge   │  │
│  │              │  │              │  │  Extractor   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                     Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐  │
│  │    SQLite    │  │   ChromaDB   │  │
│  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                        LLM Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    OpenAI    │  │    Doubao    │  │  Vectorization│ │
│  │              │  │              │  │     Models   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### System Flow

The MineContext system flow is designed as a highly modular and extensible architecture, divided into five core components: context capture, processing, storage, services/tools, and consumption.

#### 1. Context Capture

- **Sources**:
  - **Local Files**: Monitor and capture locally created or modified files
  - **Data Stream Subscriptions**: Subscribe and receive information from various data sources (e.g., RSS, APIs)
  - **User Interactions**: Including chat logs, screenshots, and AI conversations
  - **Custom Methods**: Support user-defined capture methods

#### 2. Context Processing

- **Document Processing**:
  - **Structured Documents**: Perform local segmentation
  - **Unstructured Documents**: Slice through content understanding
- **Multimodal Understanding**:
  - Comprehensive understanding of screenshots, chat logs, etc.
  - Retrieve recent historical content and context information
- **Entity Extraction & Updates**: Identify and update entities from processed content
- **Knowledge Extraction**:
  - Denoise, merge, and classify information
  - Form objective knowledge, entity profiles, activity records, and process records
- **Vectorization**: Transform extracted knowledge into vector form for storage and retrieval
- **Time-driven Compression**: Compress context and retrieve associated events and similar knowledge

#### 3. Context Storage

- **Vector Databases**:
  - **Objective Knowledge Vector Store**: Store facts and general knowledge
  - **Event Records Vector Store**: Store information related to specific events
  - **Entity Relations Vector Store**: Store relationships between entities
  - **Others**: Store other types of processed data

#### 4. Context Services/Tools

- **Query Processing**:
  - **Intent Recognition & Rewriting**: Understand the true intent of user queries, rewrite and decompose them
- **Information Organization**:
  - **Relationship Networks**: Retrieve entity profiles and their relationship networks in events
  - **Timeline Views**: Generate timeline views based on semantic matching of time and actions
- **Retrieval & Aggregation**:
  - **Knowledge Aggregation**: Retrieve and aggregate fact-oriented and reusable knowledge
  - **Bidirectional Query**: Support bidirectional queries from time to event or event to time
  - **Hybrid Search**: Support cross-type semantic and keyword hybrid search with filtering, sorting, grouping, and weight decay features

#### 5. Context Consumption

- **MCP Server**: Provide services through Model Context Protocol (MCP)
- **Application Layer Consumption**: Provide processed and organized context to upper-layer applications

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Input Sources                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │Local Files │  │Data Stream │  │User        │  │Custom     │ │
│  │            │  │Subscription│  │Interaction │  │Sources    │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     Capture Manager                          │
│      (Monitor, Retrieve, Receive, Custom Capture Methods)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Processor Manager                         │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │  Document Processing │  │    Multimodal Understanding│ │
│  │  • Structured doc    │  │  • Screenshot/chat         │ │
│  │    segmentation      │  │    understanding           │ │
│  │  • Unstructured doc  │  │  • Historical content      │ │
│  │    slicing           │  │    retrieval               │ │
│  └──────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Knowledge Extraction Processing              │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │Entity Extraction &   │  │    Information Extraction  │ │
│  │      Updates         │  │  • Denoise/Merge/Classify │ │
│  │  • Entity recognition│  │  • Objective knowledge/    │ │
│  │  • Relation extraction│ │    Entity profiles         │ │
│  │  • Entity profile    │  │  • Activity/Process        │ │
│  │    updates           │  │    records                 │ │
│  └──────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Vectorization & Compression                 │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │ Vectorization Process│  │   Time-driven Compression │ │
│  │  • Text vectorization│  │  • Context compression     │ │
│  │  • Multimodal        │  │  • Related event retrieval│ │
│  │    vectorization     │  │  • Similar knowledge       │ │
│  │  • Feature extraction│  │    aggregation             │ │
│  └──────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Storage Manager                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Objective   │  │    Event     │  │    Entity    │ │
│  │  Knowledge   │  │   Records    │  │  Relations   │ │
│  │(Vector Store)│  │(Vector Store)│  │(Vector Store)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                      SQLite + ChromaDB                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Query & Retrieval Services                 │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │   Query Processing   │  │    Retrieval Aggregation   │ │
│  │  • Intent recognition│  │  • Knowledge aggregation   │ │
│  │  • Query rewriting/  │  │  • Bidirectional query     │ │
│  │    decomposition     │  │  • Hybrid search           │ │
│  │  • Parameter         │  │                            │ │
│  │    extraction        │  │                            │ │
│  └──────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Information Organization Service             │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │Relationship Network  │  │     Timeline Generation    │ │
│  │    Construction      │  │  • Time sequence matching │ │
│  │  • Entity profiles   │  │  • Action semantic        │ │
│  │  • Event relationship│  │    matching                │ │
│  │    networks          │  │  • Timeline views          │ │
│  │  • Entity relation   │  │                            │ │
│  │    graphs            │  │                            │ │
│  └──────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     Consumption Interface                    │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │     MCP Server       │  │   Application Layer API    │ │
│  │                      │  │                            │ │
│  └──────────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Extension Points

### 1. Adding New Context Sources

- Implement `CaptureInterface`
- Register in `CaptureManager`

### 2. Adding New Processing Strategies

- Implement `BaseProcessor`
- Register in `ProcessorFactory`

### 3. Adding New Storage Backends

- Implement `BaseStorage`
- Update configuration options

### 4. Adding New LLM Providers

- Implement LLM client interface
- Update configuration handling

## Configuration Management

The system uses a layered configuration approach:

1. **Default Configuration**: Built-in default values
2. **File Configuration**: `config.yaml` overrides
3. **Environment Variables**: Override file configuration
4. **Runtime Configuration**: API-based configuration updates

## Security Considerations

### 1. API Security

- Token-based authentication
- Rate limiting
- Input validation

### 2. Data Privacy

- Local storage
- Configurable data retention
- Secure API key management
- No storage of private data

## Deployment Architecture

### Standalone Deployment

```
┌─────────────┐
│  MineContext    │
│  Application    │
│                 │
│  - Web Server   │
│  - Processing   │
│  - Storage      │
└─────────────────┘
```

### Distributed Deployment

```
┌─────────────────┐     ┌─────────────────┐
│   Web Server    │────▶│ Processing Workers│
│   (Frontend)    │     │                 │
└─────────────────┘     └─────────────────┘
         │                       │
         └───────┬───────────────┘
                 ▼
         ┌───────────────┐
         │ Storage Backend│
         └───────────────┘
```