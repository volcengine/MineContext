# Project Breakdown

## 1. Project Overview
- **Name:** MineContext — an open-source, proactive context-aware AI partner.
- **Purpose:** Capture and understand a user’s digital environment (screenshots, documents, notes) to surface actionable insights, summaries, to-dos, and activity logs while keeping data local-first.
- **Core Idea:** Context engineering pipeline that continuously collects, processes, stores, and reuses multi-modal information to augment productivity without overwhelming the user.

## 2. Key Capabilities
1. **Effortless Context Collection:** Modular capture components gather screenshots, vault documents, and other sources on configurable intervals.
2. **Context Processing & Intelligence:** Processors normalize, deduplicate, and enrich captured data, preparing it for downstream consumption and search.
3. **Rich Storage Layer:** Unified access to document and vector stores (SQLite + Chroma) managed through global storage abstractions.
4. **Proactive Consumption:** Scheduled generators produce real-time activity feeds, smart tips, todos, and daily reports delivered through the desktop app and backend APIs.
5. **Privacy First:** Processing happens locally; API keys and model endpoints are user-configurable.

## 3. System Architecture
### 3.1 Frontend (Electron + React + TypeScript)
- Located under `frontend/` with `src/main` (Electron main process), `src/preload` (secure bridge), `src/renderer` (React UI), and `packages/shared` (cross-process utilities).
- Uses Vite for bundling, Tailwind CSS for styling, Jotai/Redux for state, and pnpm workspaces for dependency management.
- Scripts: `pnpm dev` launches Electron+React dev environment, `pnpm build:*` packages platforms, `start-dev.sh` bootstraps coordinated backend/frontend dev mode.

### 3.2 Backend (OpenContext Python Service)
- Entry point `opencontext/cli.py` exposes `opencontext start` to initialize logging, configuration, capture, processing, storage, and FastAPI server.
- Layered managers orchestrate subsystems:
  - `ContextCaptureManager` registers capture components (`context_capture/`).
  - `ContextProcessorManager` routes raw context through processors (`context_processing/`).
  - `ConsumptionManager` drives generation pipelines (`context_consumption/generation`).
- FastAPI app (`opencontext/server/api.py`, `opencontext/server/opencontext.py`) serves REST/WebSocket endpoints, static assets, and screenshot mounts.
- Global services (`opencontext/config/global_config.py`, `opencontext/llm`, `opencontext/storage`) centralize configuration, LLM/VLM access, and persistence.

### 3.3 Shared Assets & Tooling
- `config/` houses default configuration YAML and prompt templates used by both backend and Electron preload.
- `build.sh` builds Python backend artifacts; `frontend/build-python.sh` mirrors packaging for Electron bundling.
- `src/` contains shared branding assets (e.g., `MineContext-Banner.svg`, product GIFs) consumed in marketing screens.

## 4. Context Lifecycle
1. **Capture:** Components like `ScreenshotCapture` or `VaultDocumentMonitor` (enabled via `config.capture.*`) collect raw context objects.
2. **Process:** `ContextProcessorManager` routes inputs to processors (e.g., `ScreenshotProcessor`, `DocumentProcessor`) that OCR, chunk, deduplicate, and enrich data.
3. **Store:** `GlobalStorage` persists processed context in Chroma (vector search) and SQLite (structured metadata) collections.
4. **Consume:** `ConsumptionManager` schedules generators to create activities, tips, todos, and reports; FastAPI endpoints serve query/search APIs to the desktop client.
5. **User Delivery:** React UI renders proactive cards, search results, and chat via preload IPC channels to the backend.

## 5. Key Components & Modules
- `opencontext/context_capture/`: Base classes and implementations for screenshot, file, and vault monitors.
- `opencontext/context_processing/`: Processor factory, screenshot/document processors, context merger.
- `opencontext/context_consumption/generation/`: Activity, tips, todo, and report generators with schedulers.
- `opencontext/server/`: FastAPI routers, component initialization, admin web console.
- `opencontext/storage/`: Abstractions for vector/document stores plus `global_storage` singleton.
- `opencontext/llm/`: Global embedding and VLM clients abstracting providers (Doubao, OpenAI, custom endpoints).
- `frontend/src/renderer/`: React feature modules (home, timeline, chat) integrating with context services.

## 6. Extensibility & Configuration
- Primary configuration: `config/config.yaml` — toggles capture modules, processing parameters, storage backends, content generation cadence, API auth, and LLM endpoints via environment substitution.
- New capture or processor modules register through `ComponentInitializer` (`opencontext/server/component_initializer.py`) which wires configs into manager registries.
- Prompt customization and localization use files in `config/prompts_*.yaml`.
- API authentication, logging levels, storage directories, and scheduled task intervals can be changed without code modifications.

## 7. Operations & Tooling
- **Backend:**
  ```bash
  uv sync && uv run opencontext start --config config/config.yaml
  ```
  Optional flags `--host`, `--port`, `--workers` override config; backend exposes FastAPI endpoints and mounts static assets.
- **Frontend:**
  ```bash
  cd frontend
  pnpm install
  pnpm dev
  ```
  Packaging commands (`pnpm build:mac`, etc.) emit installers to `frontend/dist`.
- **Integration Scripts:** `build.sh` (root) compiles backend wheel for Electron packaging; `frontend/start-dev.sh` coordinates simultaneous backend and Electron dev services.
