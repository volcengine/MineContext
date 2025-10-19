# Environment Variables Configuration Guide

This guide explains how to use `.env` files to manage environment variables in MineContext, keeping sensitive data like API keys secure and out of version control.

## Table of Contents

- [Why Use .env Files?](#why-use-env-files)
- [Quick Start](#quick-start)
- [Environment Variables Reference](#environment-variables-reference)
- [Configuration Examples](#configuration-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Why Use .env Files?

✅ **Security**: Keep API keys and sensitive data out of version control  
✅ **Flexibility**: Easy to switch between different configurations  
✅ **Portability**: Share `.env.example` without exposing credentials  
✅ **12-Factor App**: Follow industry best practices  

## Quick Start

### Step 1: Copy the Example File

```bash
cp .env.example .env
```

### Step 2: Edit Your Configuration

Open `.env` in your favorite editor and set your values:

```bash
# For Ollama (local, no API key needed)
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_KEY=
```

### Step 3: Start MineContext

```bash
./start-dev.sh
```

The application will automatically load variables from `.env`!

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider type | `ollama`, `openai`, `doubao`, `custom` |
| `LLM_MODEL` | Model ID to use | `qwen2.5:14b`, `gpt-4o` |
| `LLM_BASE_URL` | API endpoint URL | `http://localhost:11434/v1` |
| `EMBEDDING_MODEL` | Embedding model ID | `nomic-embed-text`, `text-embedding-3-large` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM | Empty (for local providers) |
| `EMBEDDING_PROVIDER` | Embedding provider | Same as `LLM_PROVIDER` |
| `EMBEDDING_BASE_URL` | Embedding API URL | Same as `LLM_BASE_URL` |
| `EMBEDDING_API_KEY` | Embedding API key | Same as `LLM_API_KEY` |
| `CONTEXT_PATH` | Data storage path | `.` (current directory) |
| `CONTEXT_API_KEY` | API authentication key | `test` |

## Configuration Examples

### Example 1: Ollama (Recommended for Getting Started)

```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_KEY=
```

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull qwen2.5:14b
ollama pull nomic-embed-text

# Start Ollama
ollama serve
```

### Example 2: OpenAI

```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-actual-openai-api-key-here

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-actual-openai-api-key-here
```

**Note:** Replace `sk-your-actual-openai-api-key-here` with your real API key from https://platform.openai.com/api-keys

### Example 3: Mixed Configuration

Use OpenAI for chat, Ollama for embeddings (save costs):

```bash
# .env
# Use OpenAI for VLM (better quality)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-actual-openai-api-key-here

# Use Ollama for embeddings (free)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_KEY=
```

### Example 4: Doubao (Volcengine)

```bash
# .env
LLM_PROVIDER=doubao
LLM_MODEL=doubao-seed-1-6-flash-250828
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_API_KEY=your-doubao-api-key-here

EMBEDDING_PROVIDER=doubao
EMBEDDING_MODEL=doubao-embedding
EMBEDDING_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
EMBEDDING_API_KEY=your-doubao-api-key-here
```

### Example 5: Custom Provider

```bash
# .env
LLM_PROVIDER=custom
LLM_MODEL=custom-model-name
LLM_BASE_URL=https://your-custom-endpoint.com/v1
LLM_API_KEY=your-custom-api-key

EMBEDDING_PROVIDER=custom
EMBEDDING_MODEL=custom-embedding-model
EMBEDDING_BASE_URL=https://your-custom-endpoint.com/v1
EMBEDDING_API_KEY=your-custom-api-key
```

## How It Works

### 1. Variable Loading Order

MineContext loads configuration in this order:

```
1. .env file (highest priority)
   ↓
2. System environment variables
   ↓
3. config.yaml defaults (lowest priority)
```

### 2. Variable Substitution in config.yaml

The `config.yaml` file uses environment variable placeholders:

```yaml
vlm_model:
  base_url: "${LLM_BASE_URL}"
  api_key: "${LLM_API_KEY:}"  # Empty string if not set
  model: "${LLM_MODEL}"
  provider: "${LLM_PROVIDER:}"

embedding_model:
  base_url: "${EMBEDDING_BASE_URL:${LLM_BASE_URL}}"  # Falls back to LLM_BASE_URL
  api_key: "${EMBEDDING_API_KEY:${LLM_API_KEY}}"    # Falls back to LLM_API_KEY
  model: "${EMBEDDING_MODEL}"
  provider: "${EMBEDDING_PROVIDER:${LLM_PROVIDER}}"  # Falls back to LLM_PROVIDER
```

**Syntax:**
- `${VAR}` - Required, will fail if not set
- `${VAR:}` - Optional, empty string if not set
- `${VAR:default}` - Optional, use `default` if not set
- `${VAR:${OTHER_VAR}}` - Optional, fall back to another variable

## Best Practices

### 🔒 Security

1. **Never commit `.env` to version control**
   ```bash
   # .gitignore already includes:
   .env
   .env.local
   ```

2. **Use `.env.example` as a template**
   - Commit `.env.example` with placeholder values
   - Team members copy it to `.env` and fill in their credentials

3. **Rotate API keys regularly**
   - Update `.env` file
   - Restart the application

### 📁 File Management

1. **Keep `.env` in the project root**
   ```
   MineContext/
   ├── .env                 ← Your actual configuration
   ├── .env.example         ← Template (committed to git)
   ├── config/
   │   └── config.yaml      ← Uses ${VARIABLES} from .env
   └── start-dev.sh
   ```

2. **Use different .env files for different environments**
   ```bash
   .env.development
   .env.production
   .env.testing
   ```
   
   Then load explicitly:
   ```bash
   cp .env.production .env
   ./start-dev.sh
   ```

### 🚀 Development Workflow

1. **First-time setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ./start-dev.sh
   ```

2. **Switching configurations:**
   ```bash
   # Switch to Ollama
   cp .env.ollama .env
   
   # Switch to OpenAI
   cp .env.openai .env
   ```

3. **Sharing configuration (without secrets):**
   ```bash
   # Share the example file
   git add .env.example
   git commit -m "docs: update .env.example"
   ```

## Troubleshooting

### Issue: "Environment variable not found"

**Symptom:**
```
ValueError: LLM_BASE_URL environment variable not set
```

**Solution:**
1. Check `.env` file exists in project root
2. Verify variable names are correct (case-sensitive)
3. Ensure no extra spaces around `=`

```bash
# ✅ Correct
LLM_MODEL=qwen2.5:14b

# ❌ Wrong (space before =)
LLM_MODEL =qwen2.5:14b

# ❌ Wrong (space after =)
LLM_MODEL= qwen2.5:14b
```

### Issue: ".env file not loading"

**Check:**
1. File is named exactly `.env` (not `env.txt` or `.env.txt`)
2. File is in the project root
3. File encoding is UTF-8
4. No BOM (Byte Order Mark) at the start

**Debug:**
```bash
# Check if file exists
ls -la .env

# Verify it's being loaded
./start-dev.sh
# Should print: "✓ Loaded environment variables from /path/to/.env"
```

### Issue: "API key still empty"

**Possible causes:**

1. **Trailing/leading spaces:**
   ```bash
   # Wrong
   LLM_API_KEY= sk-abc123 
   
   # Correct
   LLM_API_KEY=sk-abc123
   ```

2. **Quotes (usually not needed):**
   ```bash
   # Usually correct (no quotes)
   LLM_API_KEY=sk-abc123
   
   # Only use quotes if value contains spaces
   LLM_API_KEY="sk-abc 123"
   ```

3. **Variable name mismatch:**
   Check `config.yaml` uses the same variable name

### Issue: "Changes to .env not reflected"

**Solution:**
Restart the application:
```bash
# Stop with Ctrl+C
# Start again
./start-dev.sh
```

Environment variables are loaded once at startup.

## Advanced Usage

### Using System Environment Variables

You can also set variables in your shell:

```bash
# Temporary (current session only)
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen2.5:14b
./start-dev.sh

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export LLM_PROVIDER=ollama' >> ~/.bashrc
source ~/.bashrc
```

### Multiple Configurations

Create named env files:

```bash
# .env.ollama
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
...

# .env.openai
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
...

# Switch easily
cp .env.ollama .env && ./start-dev.sh
```

### Docker Integration

```dockerfile
# Dockerfile
ENV LLM_PROVIDER=ollama
ENV LLM_MODEL=qwen2.5:14b
```

Or use `docker-compose.yml`:

```yaml
services:
  minecontext:
    env_file:
      - .env
```

## Related Documentation

- [LLM Configuration Guide](LLM_CONFIGURATION_GUIDE.md) - Detailed LLM setup
- [config.yaml Reference](../config/config.yaml) - Full configuration file
- [.env.example](../.env.example) - Template file

## Support

For issues or questions:
- GitHub Issues: https://github.com/volcengine/MineContext/issues
- Documentation: https://github.com/volcengine/MineContext
