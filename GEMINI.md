# MineContext Gemini 开发指南

本文件为使用 AI 助手进行 MineContext 项目开发提供了全面的指导，综合了 `README.md`、`CONTRIBUTING.md` 和核心代码文件的信息。

# 你必须要使用中文作为主要语言来回答问题

## 1. 项目概述

-   **项目名称**: MineContext
-   **项目简介**: 一个开源的、主动的上下文感知 AI 伙伴。它通过截图和其他内容来观察和理解用户的数字世界，然后主动提供见解、摘要和待办事项列表。
-   **代码仓库**: [https://github.com/volcengine/MineContext](https://github.com/volcengine/MineContext)
-   **核心功能**:
    -   **轻松采集 (Effortless Collection)**: 从多种来源收集上下文。
    -   **主动推送 (Proactive Delivery)**: 自动生成并推送每日/每周摘要、技巧和待办事项。
    -   **智能浮现 (Intelligent Resurfacing)**: 在创作任务中智能地提供相关上下文。
    -   **上下文工程架构 (Context Engineering Architecture)**: 管理多模态数据的完整生命周期。

## 2. 后端架构

后端是一个模块化、分层的系统，旨在实现清晰和可扩展性。

```
opencontext/
├── server/             # Web 服务器与 API 层 (FastAPI)
├── managers/           # 业务逻辑协调器 (Capture, Processor 等)
├── context_capture/    # 原始数据采集模块 (如截图、文件监控)
├── context_processing/ # 上下文处理流水线 (分块、提取、合并)
├── context_consumption/# 上下文消费与生成 (如摘要、待办事项)
├── storage/            # 多后端存储层 (SQLite, ChromaDB)
├── llm/                # LLM 集成 (OpenAI, Doubao)
├── tools/              # 用于 Agent 能力的工具系统
└── monitoring/         # 系统监控与指标
```

## 3. 开发环境设置

本项目使用 `uv` 进行快速依赖管理。

1.  **安装 `uv`** (如果尚未安装):
    -   macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    -   Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

2.  **安装依赖**:
    在项目根目录运行以下命令，以创建虚拟环境并安装所有必需的包。
    ```bash
    uv sync
    ```

3.  **激活虚拟环境**:
    要直接运行脚本，请激活由 `uv` 创建的环境。
    ```bash
    source .venv/bin/activate  # Windows 上使用: .venv\Scripts\activate
    ```

4.  **运行后端服务**:
    ```bash
    # 使用默认配置启动
    uv run opencontext start

    # 或者，在激活环境后
    opencontext start --port 1733
    ```

## 4. 代码风格与版本控制

### 代码风格

项目使用 `black` 和 `isort` 强制执行严格的代码风格。代码格式化通过 `pre-commit` 在提交时自动处理。

-   **首次设置**: 克隆仓库后，运行一次 `pre-commit install`。
-   **工作流程**: 当你运行 `git commit` 时，`pre-commit` 会格式化你的代码。如果文件被修改，你必须 `git add` 更改并再次提交。
-   **行长**: 100 个字符。

### 分支命名规范

所有分支必须遵循 `<类型>/<描述>` 的约定：

| 前缀       | 用途             | 示例                             |
| ---------- | ---------------- | -------------------------------- |
| `feature/` | 新功能           | `feature/add-notion-integration` |
| `fix/`     | 缺陷修复         | `fix/screenshot-capture-error`   |
| `docs/`    | 文档             | `docs/update-api-guide`          |
| `refactor/`| 代码重构         | `refactor/simplify-storage-layer`|
| `test/`    | 添加测试         | `test/add-processor-tests`       |
| `chore/`   | 日常维护         | `chore/update-dependencies`      |

### 提交信息格式

使用 [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) 规范。
-   **示例**: `feat: add support for PDF file processing`

## 5. 核心概念与数据模型

系统围绕两个主要的数据模型构建：

1.  **`RawContextProperties`**: 代表从来源捕获的、未经处理的原始数据。
    -   **来源 (Source)**: `opencontext.models.context.ContextSource` (例如 `SCREENSHOT`, `LOCAL_FILE`)。
    -   **内容 (Content)**: 可以是 `content_text` 或 `content_path` (用于文件/图像)。
    -   **用法示例** (来自 `examples/example_document_processor.py`):
        ```python
        from opencontext.models.context import RawContextProperties, ContextSource, ContentFormat

        raw_context = RawContextProperties(
            source=ContextSource.LOCAL_FILE,
            content_path="/path/to/file.pdf",
            content_format=ContentFormat.FILE,
            create_time=datetime.now(),
            content_text="",
        )
        ```

2.  **`ProcessedContext`**: 代表已结构化、已丰富的、可供存储和消费的数据。它是一个处理器的输出。
    -   包含 `extracted_data`，如 `title`, `summary`, `keywords`, 和 `entities`。
    -   包含一个 `vectorize` 对象，用于嵌入和相似性搜索。

## 6. 模块开发指南

### 采集模块 (Capture Modules)

采集模块继承自 `BaseCaptureComponent`，负责获取原始上下文。完整的实现可以参考 `opencontext/context_capture/screenshot.py`。

-   **关键文件**: `opencontext/context_capture/base.py` (定义了 `BaseCaptureComponent`)
-   **核心方法**: 实现 `_capture_impl()` 方法来执行数据捕获。
-   **返回值**: 该方法必须返回一个 `RawContextProperties` 对象的列表。
-   **示例 (`screenshot.py`)**:
    -   `_initialize_impl`: 设置配置（格式、质量、保存目录）。
    -   `_capture_impl`: 调用 `_take_screenshot()`。
    -   `_take_screenshot`: 使用 `mss` 库抓取屏幕像素。
    -   `_create_new_context`: 将截图打包成 `RawContextProperties` 对象。

### 处理模块 (Processor Modules)

处理模块继承自 `BaseContextProcessor`，将 `RawContextProperties` 转换为 `ProcessedContext`。

-   **关键文件**: `opencontext/context_processing/processor/base_processor.py`
-   **核心方法**:
    -   `can_process(context)`: 如果处理器能处理给定的 `RawContextProperties` 对象，则返回 `True`。
    -   `process(context)` 或 `real_process(context)`: 提取信息的核心逻辑，通常涉及调用 LLM。输出应该是一个 `ProcessedContext` 对象的列表。

## 7. 运行测试与示例

本项目不使用像 `pytest` 这样的正式测试运行器。相反，验证是通过运行 `examples/` 目录中的脚本来执行的。这是测试组件的标准方法。

1.  **激活虚拟环境**:
    ```bash
    source .venv/bin/activate
    ```

2.  **运行示例脚本**:
    -   **测试文档处理**:
        ```bash
        python examples/example_document_processor.py /path/to/your/documents
        ```
    -   **测试截图处理**:
        ```bash
        python examples/example_screenshot_processor.py /path/to/your/screenshots
        ```

这些脚本将初始化相应的处理器并在你的本地文件上运行它们，将输出打印到控制台。这为验证对处理器或其依赖项的更改提供了一种直接的方法。
