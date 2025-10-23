# Contributing to MineContext

Thank you for your interest in contributing to MineContext! We welcome contributions from the community.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/MineContext.git
   cd MineContext
   ```

2. **Set up your environment**

   We recommend using [uv](https://docs.astral.sh/uv/) for faster dependency management:

   **Option 1: Using uv (Recommended)**

   ```bash
   # Install uv if you haven't already
   # macOS/Linux:
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Windows:
   # powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Install dependencies
   uv sync

   # Run commands in the uv environment
   uv run opencontext start
   ```

   **Option 2: Using traditional venv**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

3. **Configure and run**

   **If using uv:**

   ```bash
   # Start with default configuration
   uv run opencontext start

   # Start with custom config
   uv run opencontext start --config /path/to/config.yaml

   # Start with custom port (useful for avoiding conflicts)
   uv run opencontext start --port 1733
   ```

   **If using traditional venv:**

   ```bash
   # Make sure virtual environment is activated first
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Start with default configuration
   opencontext start

   # Start with custom config
   opencontext start --config /path/to/config.yaml

   # Start with custom port
   opencontext start --port 1733
   ```

   **Available startup options:**

   - `--config`: Path to configuration file
   - `--host`: Host address (overrides config file)
   - `--port`: Port number (overrides config file)

## How to Contribute

### Reporting Issues

Found a bug or have a feature request? [Create an issue](https://github.com/volcengine/MineContext/issues) with:

- Clear description of the problem or feature
- Steps to reproduce (for bugs)
- Your environment (OS, Python version, MineContext version)

### Branch Naming Convention

Use descriptive branch names with appropriate prefixes:

| Prefix                | Purpose                   | Example                           |
| --------------------- | ------------------------- | --------------------------------- |
| `feature/` or `feat/` | New features              | `feature/add-notion-integration`  |
| `fix/`                | Bug fixes                 | `fix/screenshot-capture-error`    |
| `hotfix/`             | Critical production fixes | `hotfix/memory-leak`              |
| `docs/`               | Documentation only        | `docs/update-api-guide`           |
| `refactor/`           | Code refactoring          | `refactor/simplify-storage-layer` |
| `test/`               | Adding or updating tests  | `test/add-processor-tests`        |
| `chore/`              | Maintenance tasks         | `chore/update-dependencies`       |

### Submitting Code

1. **Create a branch**

   Follow the branch naming convention above:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Set up code formatting (first time only)**

   ```bash
   # Install formatting tools
   pip install black isort pre-commit

   # Set up automatic formatting on commit
   pre-commit install
   ```

3. **Make your changes**

   - Follow [PEP 8](https://pep8.org/) style guidelines
   - Add tests for new features
   - Update documentation if needed

4. **Commit your changes**

   Code will be **automatically formatted** when you commit:

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   If files are modified by the formatter:

   ```bash
   git add .  # Add the formatted changes
   git commit -m "feat: add your feature description"  # Commit again
   ```

5. **Push and create a Pull Request**

   ```bash
   git push origin feature/your-feature-name
   ```

   **Before submitting PR, ensure:**

   - ✅ All code is properly formatted (automatic if you set up pre-commit)
   - ✅ All tests pass
   - ✅ Documentation is updated if needed

## Code Style

We use automated tools to maintain consistent code formatting.

### Quick Setup (Recommended)

```bash
# 1. Install tools
pip install black isort pre-commit

# 2. Enable automatic formatting on commit
pre-commit install

# Done! Code will be formatted automatically when you commit
```

### How It Works

When you run `git commit`, Black and isort will automatically format your code:

- **Black**: Formats code style (spacing, line breaks, etc.)
- **isort**: Sorts and organizes import statements

If files are modified during commit, just run `git commit` again.

### Manual Formatting (Optional)

If you need to format code manually:

```bash
# Format all code
pre-commit run --all-files

# Or format specific tools
black opencontext
isort opencontext
```

### Formatting Rules

- Maximum line length: 100 characters
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and well-documented

## Module Development Guide

### Backend Module Development

You can develop custom backend modules to capture data from new sources or process different types of raw materials.

#### Developing Custom Capture Modules

Capture modules collect raw data from various sources and convert it to `RawContextProperties`.

**Core Responsibility**: Fetch data → Create `RawContextProperties` → Return to system

```python
from opencontext.interfaces.capture_interface import ICaptureComponent
from opencontext.models.context import RawContextProperties, ContextSource

class MyCustomCapture(ICaptureComponent):

    def capture(self) -> List[RawContextProperties]:
        """
        The only method you must implement.

        Input: None (fetch from your source)
        Output: List[RawContextProperties]
        """
        # 1. Fetch your data (from API, file, database, etc.)
        data = fetch_from_your_source()

        # 2. Convert to RawContextProperties
        return [RawContextProperties(
            source=ContextSource.CUSTOM,      # Required: data source type
            content_text="your text content", # Required: text content
            content_path="/path/to/file",     # Optional: file path
            metadata={"key": "value"}         # Optional: any metadata
        )]

    # Other required methods (simple boilerplate)
    def get_name(self) -> str: return "my_capture"
    def get_description(self) -> str: return "My custom capture"
    def initialize(self, config) -> bool: return True
    def start(self) -> bool: return True
    def stop(self, graceful=True) -> bool: return True
    def is_running(self) -> bool: return True
    def get_config_schema(self) -> dict: return {}
    def validate_config(self, config) -> bool: return True
    def get_status(self) -> dict: return {}
    def get_statistics(self) -> dict: return {}
    def reset_statistics(self) -> bool: return True
    def set_callback(self, callback) -> bool: return True
```

**Key Data Structure - RawContextProperties**:

```python
RawContextProperties(
    source=ContextSource.CUSTOM,  # Where data comes from
    content_text="...",            # Main text content
    content_path="/path",          # Optional: file/image path
    metadata={...}                 # Optional: extra info
)
```

#### Developing Custom Processor Modules

Processor modules analyze raw data and extract structured information for storage and search.

**Core Responsibility**: Receive `RawContextProperties` → Extract info → Return `ProcessedContext`

```python
from datetime import datetime
from opencontext.context_processing.processor.base_processor import BaseContextProcessor
from opencontext.models.context import *
from opencontext.llm.global_embedding_client import do_vectorize

class MyCustomProcessor(BaseContextProcessor):

    def can_process(self, context) -> bool:
        """Check if this processor handles this type of data"""
        return context.source == ContextSource.CUSTOM

    def process(self, context: RawContextProperties) -> List[ProcessedContext]:
        """
        The core method you must implement.

        Input: RawContextProperties (raw data)
        Output: List[ProcessedContext] (structured, searchable data)
        """
        # 1. Extract information (use LLM, parsing, or any logic)
        title = "Extracted title"
        summary = "Extracted summary"
        keywords = ["keyword1", "keyword2"]

        # 2. Create processed context
        processed = ProcessedContext(
            properties=ContextProperties(
                raw_properties=[context],
                source=context.source,
                create_time=datetime.now(),
                update_time=datetime.now()
            ),
            extracted_data=ExtractedData(
                title=title,
                summary=summary,
                keywords=keywords,
                entities=[],
                importance=5,
                confidence=8
            ),
            vectorize=Vectorize(text=f"{title} {summary}")
        )

        # 3. Generate embeddings (required for search)
        do_vectorize(processed.vectorize)

        return [processed]

    # Required boilerplate methods
    def get_name(self) -> str: return "my_processor"
    def get_description(self) -> str: return "My custom processor"
```

**Key Data Structures**:

**Input** - `RawContextProperties`:

```python
context.source          # Where it came from
context.content_text    # Text content
context.content_path    # File path (if any)
context.metadata        # Extra data
```

**Output** - `ProcessedContext`:

```python
ProcessedContext(
    properties=ContextProperties(...),  # Metadata (time, source)
    extracted_data=ExtractedData(       # Extracted information
        title="...",
        summary="...",
        keywords=[...],
        entities=[...],
        importance=5,     # 0-10
        confidence=8      # 0-10
    ),
    vectorize=Vectorize(text="...")     # Text for embedding
)
```

### Quick Start

1. **Create your module file** in the appropriate directory
2. **Implement the core method** (`capture()` or `process()`)
3. **Register it** in the processor factory or configuration
4. **Test** with your data

### Reference Examples

See existing implementations for more details:

- `opencontext/context_processing/processor/screenshot_processor.py` - Handles images
- `opencontext/context_processing/processor/document_processor.py` - Handles documents

## Priority Areas

We especially welcome contributions in these areas:

- **P0-P1**: Link upload, file processing (documents, images, audio, video)
- **P2-P3**: MCP/API integrations (Notion, Obsidian, Figma), meeting recording
- **P4-P5**: Mobile screenshot monitoring, smart device sync

See the [Context Sources](README.md#-context-source) section for more details.

## Community

- **Issues**: [GitHub Issues](https://github.com/volcengine/MineContext/issues)
- **WeChat/Lark**: [Join our group](https://bytedance.larkoffice.com/wiki/Hg6VwrxnTiXtWUkgHexcFTqrnpg)
- **Discord**: [Join here](https://discord.gg/tGj7RQ3nUR)

## License

By contributing, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
