<div align="center">

<picture>
  <img alt="MineContext" src="src/MineContext-Banner.svg" width="80%" height="auto">
</picture>

An open-source,proactive context-aware AI partner,dedicated to bringing clarity and efficiency to your work, study and creation.

<a href="https://github.com/volcengine/MineContext/issues">Report Issues</a> · <a href="https://bytedance.larkoffice.com/share/base/form/shrcnPAjJtlufuhBZGegll41NOh">Feedback</a>

[中文](README_zh.md) / English

👋 Join our [WeChat / Lark / Red Note Group](https://bytedance.larkoffice.com/wiki/Hg6VwrxnTiXtWUkgHexcFTqrnpg)

🌍  Join our [Discord Group](https://discord.gg/tGj7RQ3nUR)

[App Download for Mac](https://github.com/volcengine/MineContext/releases/tag/0.1.0)

</div>

Table of Contents

- [👋🏻 What is MineContext](#-what-is-minecontext)
- [🚀 Key Features](#-key-features)
- [🏁 Quick Start](#-quick-start)
  - [1. Installation](#1-installation)
  - [2. Disable the quarantine attribute](#2-disable-the-quarantine-attribute)
  - [3. Enter Your API-Key](#3-enter-your-api-key)
  - [4. Start Recording](#4-start-recording)
  - [5. Forget it](#5-forget-it)
- [💎 The Philosophy Behind the Name](#-the-philosophy-behind-the-name)
- [🎯 Target User](#-target-user)
- [🔌 Context-Source](#-context-source)
- [🆚 Comparison with Familiar Application](#-comparison-with-familiar-application)
  - [MineContext  vs ChatGPT Pulse](#minecontext--vs-chatgpt-pulse)
  - [MineContext vs Dayflow](#minecontext-vs-dayflow)
- [🏗️ Backend Architecture](#️-backend-architecture)
  - [Core Architecture Components](#core-architecture-components)
  - [Layer Responsibilities](#layer-responsibilities)
- [🚀 Backend Usage](#-backend-usage)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Server](#running-the-server)
    - [👥 Community](#-community)
  - [Community and Support](#community-and-support)
- [📃 License](#-license)

<br>

## 👋🏻 What is MineContext

MineContext is a proactive context-aware AI partner. By utilizing screenshots and content comprehension (with future support for multi-source multimodal information including documents, images, videos, code, and external application data), it can see and understand the user's digital world context. Based on an underlying contextual engineering framework, it actively delivers high-quality information such as insights, daily/weekly summaries, to-do lists, and activity records.

![feature.gif](src/feature.gif)

## 🚀 Key Features

MineContext focuses on five key features: effortless collection, intelligent resurfacing, and proactive delivery.

1. 📥 Effortless Collection
   Capable of gathering and processing massive amounts of context. Designed storage management enables extensive collection without adding mental burden.
2. 🚀 Proactive Delivery
   Delivers key information and insights proactively in daily use. It extracts summarized content from your context—such as daily/weekly summaries, tips, and todos—and pushes them directly to your homepage.
3. 💡 Intelligent Resurfacing
   Surfaces relevant and useful context intelligently during creation. Ensures assisted creativity without overwhelming you with information.
4. 🛡️ Privacy-First
    All data is stored locally, ensuring your privacy and security.
5. 🎯 Context Engineering Architecture
   Supports the complete lifecycle of multimodal, multi-source data—from capture, processing, and storage to management, retrieval, and consumption—enabling the generation of six types of intelligent context.

## 🏁 Quick Start

### 1. Installation

Click [Github Latest Release](https://github.com/volcengine/MineContext/releases) to Download

![Download APP](src/Download-App.gif)

### 2. Disable the quarantine attribute

Enter the following command in the terminal to disable the quarantine attribute before running the application.

```
sudo xattr -d com.apple.quarantine "/Applications/MineContext.app"
```
![Quarantine](src/Quarantine.gif)

### 3. Enter Your API-Key

After the application loads（initial run may require installation of some backend environments, which may take a few minutes）, follow the instructions to enter your API-Key. We currently support Doubao and OpenAI, with more platforms and local Ollama models to be added in the future.

![Enter API-Key](src/Enter-API-Key.gif)

### 4. Start Recording

Enter 【Screen Monitor】 to enable the system permissions for screen sharing. After completing the setup, you need to restart the application for the changes to take effect.
![Enable-Permissions](src/Enable-Permissions.gif)

After restarting the application, please first set your screen sharing area in 【Settings】, then click [Start Recording] to begin taking screenshots.
![Screen-Settings](src/Screen-Settings.gif)

### 5. Forget it

After starting the recording, your context will gradually be collected. It will take some time to generate value. So, forget about it and focus on other tasks with peace of mind. MineContext will generate to-dos, prompts, summaries, and activities for you in the background. Of course, you can also engage in proactive Q&A through [Chat with AI].



## 💎 The Philosophy Behind the Name

The naming of MineContext also reflects the team's ingenuity. It signifies both "my context" and "mining context." It draws inspiration from the core philosophy of Minecraft—openness, creativity, and exploration.

If vast amounts of context are like scattered "blocks," then MineContext provides a "world" where you can freely build, combine, and create. Users can reimagine and create new content based on the collected massive context and generate high-quality information.

## 🎯 Target User

| Target User Category | Specific Roles/Identities          | Core Needs/Pain Points                                                                                   |
| -------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Knowledge Workers    | Researchers, Analysts              | Navigating vast amounts of information, improving information processing and analysis efficiency         |
| Content Creators     | Writers, Bloggers                  | Craving endless inspiration, optimizing content creation workflows                                       |
| Lifelong Learners    | Students, Researchers              | Building systematic knowledge systems, efficiently managing and connecting learning materials            |
| Project Managers     | Product Managers, Project Managers | Integrating multi-source information and data, ensuring project alignment and decision-making efficiency |

## 🔌 Context-Source

We will prioritize the expansion of Context Sources according to the following plan, and we warmly welcome everyone to actively contribute code to our efforts.

- P0: Digital life and public information loop (PC screen capture and link upload)
- P1: Personal text context loop (file upload, file tracking)
- P2: AI and common office context loop (MCP, meeting notes)
- P3: High-quality information acquisition loop (DeepResearch and RSS)
- P4: Personal deep context loop (WeChat, QQ chat data acquisition, mobile screenshots)
- P5: Physical world context loop (smart wearable synchronization, smart glasses synchronization)

| Context Capture Capability   | Context Source                     | Priority | Completion Status |
| :--------------------------- | :--------------------------------- | :------- | :---------------- |
| Desktop Screenshot Monitor   | User PC Information                | P0       | ✅                |
| Link Upload                  | Internet Information               | P0       |                   |
| File Upload                  | Structured Documents               | P1       |                   |
| File Upload                  | Unstructured Documents             | P1       |                   |
| File Upload                  | Images                             | P1       |                   |
| File Upload                  | Audio                              | P4       |                   |
| File Upload                  | Video                              | P4       |                   |
| File Upload                  | Code                               | P4       |                   |
| Browser Extension            | AI Conversation Records            | P2       |                   |
| Browser Extension            | Refined Internet Information       | P5       |                   |
| Meeting Records              | Meeting Information                | P2       |                   |
| RSS                          | Consultation Information           | P3       |                   |
| Deep Research                | High-Quality Research Analysis     | P3       |                   |
| Application MCP/API          | Payment Records                    | P4       |                   |
| Application MCP/API          | Research Papers                    | P3       |                   |
| Application MCP/API          | News                               | P4       |                   |
| Application MCP/API          | Emails                             | P4       |                   |
| Application MCP/API          | Notion                             | P2       |                   |
| Application MCP/API          | Obsidian                           | P2       |                   |
| Application MCP/API          | Slack                              | P4       |                   |
| Application MCP/API          | Jira                               | P4       |                   |
| Application MCP/API          | Figma                              | P2       |                   |
| Application MCP/API          | Linear                             | P4       |                   |
| Application MCP/API          | Todoist                            | P4       |                   |
| Memory Bank Migration Import | User Memory                        | P4       |                   |
| WeChat Data Capture          | WeChat Chat History                | P4       |                   |
| QQ Data Capture              | QQ Chat History                    | P4       |                   |
| Mobile Screenshot Monitor    | User Mobile End Information        | P4       |                   |
| Smart Glasses Data Sync      | Physical World Interaction Records | P5       |                   |
| Smart Bracelet Data Sync     | Physiological Data                 | P5       |                   |

## 🆚 Comparison with Familiar Application

### MineContext  vs ChatGPT Pulse

- 🖥️ Comprehensive Digital Context:
  MineContext captures your entire digital workflow by reading from screen screenshots, providing a rich, visual context of your daily activities and applications. ChatGPT Pulse, in contrast, is limited to the context of a single text-based conversation.
- 🔒 Local-First Data & Privacy:
  Your data is processed and stored entirely on your local device, ensuring complete privacy and security without relying on cloud servers. ChatGPT Pulse requires data to be sent to and stored on OpenAI's servers.
- 🚀 Proactive & Diverse Insights:
  MineContext delivers a wider variety of intelligent, auto-generated content—including daily summaries, actionable todos, and activity reports—not just simple tips. ChatGPT Pulse primarily offers reactive assistance within the chat interface.
- 🔧 Open Source & Customizable:
  As an open-source project, MineContext allows developers to freely inspect, modify, and build upon the codebase for complete customization. ChatGPT Pulse is a closed, proprietary product with no option for modification.
- 💰 Cost-Effective API Usage:
  MineContext avoids the need for a costly $200/month Pro subscription by allowing you to use your own API key, giving you full control over your spending. ChatGPT Pulse's advanced features are locked behind its expensive premium tier.

### MineContext vs Dayflow

- 💡 Richer, Proactive Insights:
  ineContext delivers a more diverse range of automated, intelligent content—including concise summaries, actionable todos, and contextual tips—going beyond basic activity tracking. DayFlow primarily focuses on logging user activity.
- 🧠 Context-Aware Q&A & Creation:
  MineContext enables you to ask questions and generate new content based on your captured context, unlocking wider application scenarios like content drafting and project planning. DayFlow is limited to passive activity recording and review.
- ✨ Superior Activity Generation & Experience:
  MineContext produces activity records with greater clarity and detail, featuring a more intuitive and interactive dashboard for a seamless user experience. DayFlow's activity logs are more basic with limited interactivity.

<br>

## 🏗️ Backend Architecture

MineContext adopts a modular, layered architecture design with clear separation of concerns and well-defined responsibilities for each component.

### Core Architecture Components

```
opencontext/
├── server/             # Web server and API layer
├── managers/           # Business logic managers
├── context_capture/    # Context acquisition modules
├── context_processing/ # Context processing pipeline
├── context_consumption/# Context consumption and generation
├── storage/            # Multi-backend storage layer
├── llm/               # LLM integration layer
├── tools/             # Tool system
└── monitoring/        # System monitoring
```

### Layer Responsibilities

1. **Server Layer** (`server/`)

   - FastAPI-based RESTful API
   - WebSocket support for real-time communication
   - Static file serving and template rendering
2. **Manager Layer** (`managers/`)

   - `CaptureManager`: Manages all context capture sources
   - `ProcessorManager`: Coordinates context processing pipeline
   - `ConsumptionManager`: Handles context consumption and generation
   - `EventManager`: Event-driven system coordination
3. **Context Capture Layer** (`context_capture/`)

   - Screenshot monitoring
   - Document monitoring
   - Extensible capture interface for future sources
4. **Processing Layer** (`context_processing/`)

   - Document chunking strategies
   - Entity extraction and normalization
   - Context merging and deduplication
   - Multi-modal content processing (text, images)
5. **Storage Layer** (`storage/`)

   - Multi-backend support (SQLite, ChromaDB, VikingDB)
   - Vector storage for similarity search
   - Unified storage interface
6. **LLM Integration** (`llm/`)

   - Support for multiple LLM providers (OpenAI, Doubao)
   - VLM (Vision-Language Model) integration
   - Embedding generation services

## 🚀 Backend Usage

### Installation

```bash
# Clone repository
git clone https://github.com/volcengine/MineContext.git
cd MineContext

python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Basic Configuration** (`config/config.yaml`):

```yaml
server:
  host: 127.0.0.1
  port: 8765
  debug: false

embedding_model:
  provider: doubao  # 选项: openai, doubao
  api_key: your-api-key
  model: doubao-embedding-large-text-240915

vlm_model:
  provider: doubao  # 选项: openai, doubao
  api_key: your-api-key
  model: doubao-seed-1-6-flash-250828

capture:
  enabled: true
  screenshot:
    enabled: true # 开启截图捕获
    capture_interval: 5  # 截图间隔（秒）
```

2. **Prompt Templates** (`config/prompts_*.yaml`):
   - `prompts_en.yaml`: English prompt templates
   - `prompts_zh.yaml`: Chinese prompt templates

### Running the Server

```bash
# Start with default configuration
python -m opencontext.cli start

# Start with custom config
python -m opencontext.cli start --config /path/to/config.yaml
```

#### 👥 Community

### Community and Support

- [GitHub Issues](https://github.com/bytedance/MineContext/issues): Errors and issues encountered while using MineContext.
- [Email Support](mailto:minecontext@bytedance.com): Feedback and questions about using MineContext.
- <a href="Online Supportl">WeChat Group</a>: Discuss SwanLab usage and share the latest AI technologies.

## 📃 License

This repository is licensed under the Apache 2.0 License.

<!-- link -->

[release-shield]: https://img.shields.io/github/v/release/volcengine/MineContext?color=369eff&labelColor=black&logo=github&style=flat-square
[release-link]: https://github.com/volcengine/MineContext/releases
[license-shield]: https://img.shields.io/badge/license-apache%202.0-white?labelColor=black&style=flat-square
[license-shield-link]: https://github.com/volcengine/MineContext/blob/main/LICENSE
[last-commit-shield]: https://img.shields.io/github/last-commit/volcengine/MineContext?color=c4f042&labelColor=black&style=flat-square
[last-commit-shield-link]: https://github.com/volcengine/MineContext/commits/main
[wechat-shield]: https://img.shields.io/badge/WeChat-微信-4cb55e?labelColor=black&style=flat-square
[wechat-shield-link]: https://bytedance.larkoffice.com/wiki/Hg6VwrxnTiXtWUkgHexcFTqrnpg
[github-stars-shield]: https://img.shields.io/github/stars/volcengine/MineContext?labelColor&style=flat-square&color=ffcb47
[github-stars-link]: https://github.com/volcengine/MineContext
[github-issues-shield]: https://img.shields.io/github/issues/volcengine/MineContext?labelColor=black&style=flat-square&color=ff80eb
[github-issues-shield-link]: https://github.com/volcengine/MineContext/issues
[github-contributors-shield]: https://img.shields.io/github/contributors/volcengine/MineContext?color=c4f042&labelColor=black&style=flat-square
[github-contributors-link]: https://github.com/volcengine/MineContext/graphs/contributors
